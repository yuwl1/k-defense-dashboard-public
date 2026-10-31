import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import base64

from pathlib import Path
from html import escape

from components.header import render_header
from components.icons import mask_icon_html
import importlib
# export_score.py를 고치면 Streamlit을 다시 시작하지 않아도 새로고침만으로 반영
# (예전 버전이 메모리에 남아 ImportError가 나는 것 방지 — common_ui와 같은 방식)
import components.export_score as _export_score
if getattr(_export_score, "LOADED_MTIME", None) != _export_score.Path(_export_score.__file__).stat().st_mtime_ns:
    _export_score = importlib.reload(_export_score)
from components.export_score import top_countries   # dashboard_score.py 결과 (01_main과 공통)
# weight_custom.py(가중치 커스텀 공용 부품)도 고치면 새로고침만으로 반영
import components.weight_custom as _weight_custom
if getattr(_weight_custom, "LOADED_MTIME", None) != _weight_custom.loaded_mtime():
    _weight_custom = importlib.reload(_weight_custom)
from components.weight_custom import (   # 가중치 커스텀 공용 부품 (02·04 공통, 상태 공유)
    TOTAL, WEIGHT_NAMES, DEFAULT_WEIGHTS,
    init_weight_state, render_weight_popover, custom_weights, is_default_weights, weight_summary,
    applied_weights, is_customized,
)
# common_ui.py를 고치면 새로고침만으로 반영 (01·03·04와 동일)
import importlib
import components.common_ui as _common_ui
if _common_ui.loaded_mtime() != _common_ui.LOADED_MTIME:
    _common_ui = importlib.reload(_common_ui)
from components.common_ui import (   # 01_main·03_weapon·04_country와 같은 공통 화면 요소
    TITLE_ICON_SIZE, TITLE_ICON_GAP, TITLE_FONT_SIZE, TITLE_FONT_WEIGHT,
    HELP_TOOLTIP_CSS, HELP_TOOLTIP_JS, help_icon_html,
    flag_thumb_base64,   # 국기 썸네일 (속도 개선)
)

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# 공통 상단 헤더
# ============================================================

render_header(
    title="기업별 수출 기회 분석",
    description=(
        "국내 방산기업별 강점과 유망 수출 후보국을 비교 분석합니다."
    ),
    page_file=__file__
)

# =========================================================
# 1. 기본 설정
# =========================================================

# 가중치 이름·기본값·합계(TOTAL)는 components/weight_custom.py에서 가져옴 (04_country와 공통)

COMPANIES = {
    "한화에어로스페이스": "hanwha_aerospace",
    "한화오션": "hanwha_ocean",
    "현대로템": "hyundai_rotem",
    "HD현대중공업": "hd_hyundai",
    "한국항공우주산업(KAI)": "kai",
    "LIG D&A": "lig_nex1",   # 2026년 LIG넥스원 → LIG D&A 사명 변경 (코드는 company_weapons와 동일)
}

# Streamlit 파일이 pages 폴더에 있어도 프로젝트 루트 기준
# images 폴더를 사용할 수 있도록 설정
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = (
    CURRENT_DIR.parent
    if CURRENT_DIR.name == "pages"
    else CURRENT_DIR
)

IMAGE_DIR = ROOT_DIR / "images"
WEAPON_IMAGE_DIR = IMAGE_DIR / "common" / "weapon"
COMMON_IMAGE_DIR = IMAGE_DIR / "common/etc"
# 실제 파일명과 확장자가 다를 때도 같은 모델 사진을 찾도록 보조
# 정확한 파일명을 우선 사용하고, 후보가 유일할 때만 자동 매칭
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

@st.cache_data(show_spinner=False)
def cached_weapon_image(path_text, modified_time):
    """무기 이미지 → 화면 표시용 작은 WebP(최대 360px)로 줄여 캐시 (03_weapon TOP 3와 같은 방식)
    원본 사진은 장당 2~3MB라 그대로 넣으면 기업 탭·가중치를 바꿀 때마다 화면이 느려짐"""
    from io import BytesIO
    from PIL import Image, ImageOps
    with Image.open(path_text) as source:
        photo = ImageOps.exif_transpose(source)
        photo.thumbnail((360, 360), Image.Resampling.LANCZOS)
        photo = photo.convert("RGBA" if "A" in photo.getbands() else "RGB")
        buffer = BytesIO()
        photo.save(buffer, format="WEBP", quality=82, method=0)
    return base64.b64encode(buffer.getvalue()).decode("ascii")

def resolve_weapon_image(image_filename, weapon_name):
    """images/common/weapon에서 무기 이미지 파일 찾기."""
    if not image_filename or not WEAPON_IMAGE_DIR.is_dir():
        return None

    # 1. COMPANY_INFO에 지정된 파일명 그대로 확인
    exact_path = WEAPON_IMAGE_DIR / image_filename
    if exact_path.is_file():
        return exact_path

    # 2. 대소문자 / 확장자 차이가 있는 경우 파일명 본체로 확인
    def normalized(text):
        return "".join(char for char in str(text).casefold() if char.isalnum())

    files = sorted(
        (path for path in WEAPON_IMAGE_DIR.iterdir()
         if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS),
        key=lambda path: path.name.casefold(),
    )
    image_stem = normalized(Path(image_filename).stem)
    stem_matches = [path for path in files if normalized(path.stem) == image_stem]
    if len(stem_matches) == 1:
        return stem_matches[0]

    # 정사각형 편집본처럼 원본 이름 뒤에 suffix가 추가된 경우
    if len(image_stem) >= 4:
        variant_matches = [
            path for path in files
            if normalized(path.stem).startswith(image_stem)
        ]
        if len(variant_matches) == 1:
            return variant_matches[0]

    # 3. 무기 모델명이 파일명 앞쪽에 붙은 경우 (후보 하나만 허용)
    model = normalized(weapon_name)
    if len(model) >= 4:
        model_matches = [
            path for path in files
            if normalized(path.stem).startswith(model)
        ]
        if len(model_matches) == 1:
            return model_matches[0]

    return None


# 국기 이미지 (01·03·04와 같은 원형 국기, flag-icons MIT)
FLAG_IMAGE_DIR = IMAGE_DIR / "common" / "country"

# 카드 제목 아이콘 (Material Symbols, 테마 글자색으로 표시)
TITLE_ICONS = {
    "weapons": IMAGE_DIR / "icon" / "material-swords.png",
    "top10": IMAGE_DIR / "01_main_images" / "emoji_events.png",
}


# 순위 아이콘
RANK_ICON_FILES = {
    1: "rank-1.png",
    2: "rank-2.png",
    3: "rank-3.png",
    4: "rank-4.png",
    5: "rank-5.png",
    6: "rank-6.png",
    7: "rank-7.png",
    8: "rank-8.png",
    9: "rank-9.png",
    10: "rank-10.png",
}

RANK_ICON_SIZE = 28



# =========================================================
# 2. 기업별 데이터
# =========================================================
# 기업별 대표 무기 및 장비: 3개 기업 × 5종 = 15종
# name: 대시보드 표시 명칭
# description: 무기·장비의 주요 특징 및 역할
# image: images/common/weapon 폴더 기준 파일명
# tags: 무기 분야 및 핵심 기능
# 이미지 파일명이 실제 저장된 이름과 일치해야 표시됨

COMPANY_INFO = {
    "한화에어로스페이스": {
        "weapons": [
            {
                "name": "K9 Thunder",
                "description": "155mm 궤도형 자주포로, 기동성과 장거리 포병 화력을 바탕으로 지상군의 화력 지원을 수행합니다.",
                "image": "k9.png",
                "tags": ["자주포", "155mm", "지상화력"],
            },
            {
                "name": "K332",
                "description": "화생방정찰차-II 차량형으로, 화학·생물학 작용제와 방사능을 탐지하고 관련 경보 정보를 신속하게 전파합니다.",
                "image": "K332.webp",
                "tags": ["화생방정찰", "CBRN", "탐지·경보"],
            },
            {
                "name": "K239 Chunmoo",
                "description": "다양한 로켓탄을 운용하는 차륜형 다연장로켓 체계로, 지상군에 광역 및 정밀 화력 지원을 제공합니다.",
                "image": "chunmoo.png",
                "tags": ["다연장로켓", "정밀타격", "지상화력"],
            },
            {
                "name": "AS21 Redback",
                "description": "보병 수송과 화력 지원을 수행하는 궤도형 보병전투장갑차로, 방호 성능과 전장 기동성을 갖춘 장비입니다.",
                "image": "AS21 Redback.png",
                "tags": ["보병전투장갑차", "병력수송", "방호"],
            },
            {
                "name": "L-SAM ABM",
                "description": "장거리 지대공 방어체계의 탄도미사일 요격용 유도탄으로, 고고도에서 탄도미사일을 직접 요격하도록 설계되었습니다.",
                "image": "L-SAM.jpg",
                "tags": ["요격미사일", "탄도탄방어", "고고도"],
            },
        ],
    },

    "한화오션": {
        "weapons": [
            {
                "name": "KSS-III",
                "description": "국내 기술로 개발된 3,000톤급 한국형 잠수함으로, 수중 작전 및 다양한 해상 안보 임무를 수행합니다.",
                "image": "KSS-III.png",
                "tags": ["잠수함", "수중작전", "해양전력"],
            },
            {
                "name": "DW-3000F",
                "description": "대우조선해양이 건조한 태국 해군용 다목적 호위함으로, 대함·대공·대잠 작전 수행을 위한 전투체계를 갖추고 있습니다.",
                "image": "HTMS_Bhumibol_Adulyadej_(FFG-471).jpg",
                "tags": ["호위함", "해외수출", "다목적함정"],
            },
            {
                "name": "Type-209/1400",
                "description": "인도네시아 해군에 공급된 1,400톤급 디젤전기 추진 잠수함으로, 수중 정찰 및 해상 방어 임무를 수행합니다.",
                "image": "Type-209-1400.jpg",
                "tags": ["잠수함", "해외수출", "수중작전"],
            },
            {
                "name": "KDX-III (Yulgok Yi I)",
                "description": "대우조선해양이 건조한 율곡이이함(DDG-992)으로, 이지스 전투체계를 활용해 광역 대공방어 및 해상 작전을 수행합니다.",
                "image": "ROKS_Yulgok_Yi_I_(DDG-992)_sails_during_the_at-sea_phase_of_RIMPAC_2024.jpg",
                "tags": ["이지스구축함", "대공방어", "해양전력"],
            },
            {
                "name": "FFG-823",
                "description": "대우조선해양이 건조한 대구급 호위함으로, 대잠전 능력을 중심으로 해상 경계 및 다목적 작전을 수행합니다.",
                "image": "FFG-823.jpg",
                "tags": ["호위함", "대잠작전", "해양전력"],
            },
        ],
    },

    "한국항공우주산업(KAI)": {
        "weapons": [
            {
                "name": "FA-50 Fighting Eagle",
                "description": "초음속 경전투기로, 전투 조종사 훈련과 공대공·공대지 작전을 지원하는 다목적 항공기입니다.",
                "image": "FA-50_fighting_Eagle_on_the_Runway.jpg",
                "tags": ["경전투기", "초음속", "다목적"],
            },
            {
                "name": "KF-21 Boramae",
                "description": "대한민국이 개발한 한국형 다목적 전투기로, 공중 우세 확보 및 다양한 항공 작전 수행을 목표로 개발되었습니다.",
                "image": "KF-21_Boramae_First_Production.jpg",
                "tags": ["전투기", "한국형전투기", "항공전력"],
            },
            {
                "name": "KT-1 Woongbi",
                "description": "국내 개발 기본훈련기로, 군 조종사의 기초 비행훈련과 비행 기술 습득에 활용됩니다.",
                "image": "Demonstration_Flight_of_ROKAF_New_Light_Trainer_KT-1_'Woongbi'.jpg",
                "tags": ["훈련기", "조종사양성", "기본비행"],
            },
            {
                "name": "KUH-1 Surion",
                "description": "국산 기동헬기로, 병력 및 물자 수송과 다양한 군 작전 지원 임무를 수행합니다.",
                "image": "KUH-1_Surion_Prototype_Flight_Test_(13614106523).jpg",
                "tags": ["기동헬기", "병력수송", "작전지원"],
            },
            {
                "name": "LAH Miron",
                "description": "국산 소형무장헬기로, 적 기갑전력 대응과 지상군 근접 화력 지원 임무를 수행하도록 개발되었습니다.",
                "image": "KAI_LAH-1_Miron_Armed_Helicopter_-_1.jpg",
                "tags": ["무장헬기", "대기갑", "화력지원"],
            },
        ],
    },

    
    "현대로템": {
        "weapons": [
            {
                "name": "K2 Black Panther",
                "description": "국산 120mm 활강포를 탑재한 3.5세대 주력전차로, 첨단 사격통제체계와 기동성을 바탕으로 지상 전투 임무를 수행합니다.",
                "image": "K2 Black Panther.png",
                "tags": ["주력전차", "120mm", "지상전력"],
            },
            {
                "name": "K1 AVLB",
                "description": "K1 전차 차체를 기반으로 개발된 교량전차로, 장애물과 하천 구간에 교량을 설치하여 기갑부대의 기동을 지원합니다.",
                "image": "K1 AVLB.png",
                "tags": ["교량전차", "장애물극복", "기동지원"],
            },
            {
                "name": "K600 CEV",
                "description": "지뢰와 다양한 장애물을 제거하는 장애물개척전차로, 위험 지역에 기동로를 확보하여 아군 부대의 진격을 지원합니다.",
                "image": "K600 CEV.png",
                "tags": ["장애물개척", "지뢰제거", "공병전력"],
            },
            {
                "name": "K808 WAV",
                "description": "8륜 구동 방식의 차륜형 장갑차로, 병력 수송과 신속한 전장 기동을 통해 보병부대의 작전 수행을 지원합니다.",
                "image": "K808 WAV.png",
                "tags": ["차륜형장갑차", "병력수송", "기동전력"],
            },
            {
                "name": "K1A1",
                "description": "120mm 활강포와 향상된 사격통제체계를 갖춘 K1 계열 주력전차로, 기갑부대의 직접 화력 지원과 지상 전투를 수행합니다.",
                "image": "K1A1.png",
                "tags": ["주력전차", "120mm", "기갑전력"],
            },
        ],
    },

    "LIG D&A": {
        "weapons": [
            {
                "name": "KGGB",
                "description": "일반 항공폭탄에 유도장치와 날개를 결합한 정밀유도폭탄 체계로, 항공기의 원거리 정밀 타격 능력을 지원합니다.",
                "image": "KGGB.png",
                "tags": ["정밀유도폭탄", "공대지", "정밀타격"],
            },
            {
                "name": "K745 Blue Shark",
                "description": "수상함과 항공기 등에서 운용하는 국산 경어뢰로, 수중의 적 잠수함을 탐지·추적하여 타격하는 대잠 작전에 활용됩니다.",
                "image": "K745 Blue Shark.png",
                "tags": ["경어뢰", "대잠작전", "수중무기"],
            },
            {
                "name": "SSM-700K",
                "description": "해성으로 알려진 국산 함대함 유도미사일로, 수상함에서 발사하여 적 함정을 원거리에서 정밀 타격하는 임무를 수행합니다.",
                "image": "SSM-700K.png",
                "tags": ["함대함미사일", "대함타격", "해양전력"],
            },
            {
                "name": "KM-SAM Block II",
                "description": "천궁-II로 알려진 중거리 지대공 유도무기체계로, 적 항공기와 탄도미사일을 요격하여 주요 시설과 영공을 방어합니다.",
                "image": "KM-SAM Block II.png",
                "tags": ["지대공미사일", "탄도탄요격", "방공전력"],
            },
            {
                "name": "ESR-500A",
                "description": "경전투기 탑재를 위해 개발된 공랭식 AESA 레이더로, 다수의 공중·지상·해상 표적을 탐지하고 추적하는 기능을 제공합니다.",
                "image": "ESR-500A.png",
                "tags": ["AESA레이더", "표적탐지", "항공전자"],
            },
        ],
    },

    "HD현대중공업": {
        "weapons": [
            {
                "name": "HHI-2600",
                "description": "약 2,600톤급 다목적 호위함 설계로, 해상 경계와 대함·대공·대잠 작전 등 다양한 해상 전투 임무를 지원합니다.",
                "image": "HHI-2600.png",
                "tags": ["호위함", "다목적함정", "해양전력"],
            },
            {
                "name": "HDF-3200",
                "description": "약 3,200톤급 다목적 호위함 설계로, 대공·대함·대잠 작전 수행을 위한 무장과 탐지체계를 갖춘 함정입니다.",
                "image": "HDF-3200.png",
                "tags": ["호위함", "대잠작전", "다목적함정"],
            },
            {
                "name": "AOE-51",
                "description": "대한민국 해군의 대형 군수지원함 소양함으로, 해상에서 작전 중인 함정에 유류와 탄약 등 군수물자를 보급합니다.",
                "image": "AOE-51.png",
                "tags": ["군수지원함", "해상보급", "작전지원"],
            },
            {
                "name": "DDG-995",
                "description": "정조대왕함으로 명명된 차세대 이지스구축함으로, 광역 대공방어와 탄도미사일 대응 및 다양한 해상 작전을 수행합니다.",
                "image": "DDG-995.png",
                "tags": ["이지스구축함", "대공방어", "해양전력"],
            },
            {
                "name": "SS-072",
                "description": "손원일함으로 명명된 214급 디젤전기 추진 잠수함으로, 수중 정찰과 대함·대잠 작전 등 다양한 해상 안보 임무를 수행합니다.",
                "image": "SS-072.png",
                "tags": ["잠수함", "수중작전", "해양전력"],
            },
        ],
    },
}



# =========================================================
# .국가별 점수 데이터 (추후 연결)
# =========================================================
# 아직 계산 결과가 없으므로 비워둠
#
# 추후 각 기업별 후보국 데이터를 연결할 때 사용
#
# 국가 데이터 구조 예시:
#
# {
#     "country": "국가명",
#     "iso_a3": "국가 ISO 코드",
#     "reason": "추천 근거",
#     "scores": {
#         "HHI": 0~100 점수,
#         "국방비": 0~100 점수,
#         "무기 매칭도": 0~100 점수,
#         "협력 관계": 0~100 점수,
#         "GPI": 0~100 점수,
#     },
# }
#
# scores에는 원본 지표가 아닌, 평가 방향까지
# 반영하여 정규화한 점수를 넣어야 함.

COUNTRY_DATA = {
    company: []
    for company in COMPANIES
}


# =========================================================
# 4. Session State 초기화
# =========================================================

if st.session_state.get("export_company") not in COMPANIES:
    st.session_state.export_company = list(COMPANIES)[0]

# 가중치 상태(기업별 초안·적용값·잠금) 준비 + 슬라이더를 선택 기업 값으로 채움 — 04_country와 공유
init_weight_state(st.session_state.export_company)

# TOP 10에서 국가를 눌렀으면 04 국가별 상세 분석으로 이동 (country_jump는 04가 읽고 지움)
if st.session_state.get("country_jump"):
    st.switch_page("pages/04_country.py")

# =========================================================
# 5. 가중치 계산 함수 → components/weight_custom.py로 이동 (04_country와 공통)
# =========================================================

def select_company(company):
    """선택 기업 변경"""
    st.session_state.export_company = company


# =========================================================
# 6. 국가별 적합도 계산 (데이터 연결용)
# =========================================================

def calculate_country_score(scores, weights):
    """
    이미 0~100점으로 변환된 6개 지표 점수에
    적용된 가중치를 곱해 최종 적합도를 계산.

    점수가 하나라도 없다면 None 반환.
    """
    if any(
        scores.get(name) is None
        for name in WEIGHT_NAMES
    ):
        return None

    return sum(
        float(scores[name]) * weights[i] / TOTAL
        for i, name in enumerate(WEIGHT_NAMES)
    )


# 2026년 수출 유망 국가 TOP 10: src/dashboard_score/dashboard_score.py 결과 (components/export_score.py)
#   - iso_a3 → 국기+국가명, rank → 순위, final_score → 추천 점수
#   - 가중치가 기본값이면 스크립트 결과(CRITIC 가중치) 그대로,
#     '가중치 커스텀'에서 바꿔 적용하면 같은 6개 지표 점수에 그 가중치를 곱해 다시 계산
TOP_N = 10


# TOP 10 국가 클릭 → 04_country 이동
#   JS가 국가 칸 클릭을 감지해 iso_a3를 보내면, 다음 실행에서 04로 이동
def on_top10_country_click():
    result = st.session_state.get("company_top10_click")
    iso = result.get("country") if isinstance(result, dict) else getattr(result, "country", None)
    if iso:
        st.session_state.country_jump = {"company": st.session_state.get("export_company"), "iso": str(iso)}


top10_click_bridge = None
if hasattr(getattr(st, "components", None), "v2"):
    top10_click_bridge = st.components.v2.component(
        name="company_top10_click_bridge",
        html='<span class="company-top10-click-bridge" aria-hidden="true"></span>',
        css=".company-top10-click-bridge{display:block;width:0;height:0;overflow:hidden;}",
        js=r"""
        export default function ({ setTriggerValue }) {
            const KEY = "__kDefenseTop10CountryClick";
            if (window[KEY]) {
                document.removeEventListener("click", window[KEY], true);
                document.removeEventListener("keydown", window[KEY], true);
            }
            function handler(event) {
                if (event.type === "keydown" && event.key !== "Enter") return;
                const target = event.target;
                const cell = target && target.closest ? target.closest(".company-country-link") : null;
                if (!cell || !cell.closest(".st-key-company_top10_table")) return;
                const iso = cell.getAttribute("data-iso");
                if (iso) setTriggerValue("country", iso);
            }
            window[KEY] = handler;
            document.addEventListener("click", handler, true);
            document.addEventListener("keydown", handler, true);
            return () => {
                if (window[KEY] === handler) {
                    document.removeEventListener("click", handler, true);
                    document.removeEventListener("keydown", handler, true);
                    delete window[KEY];
                }
            };
        }
        """,
    )


def get_top10_countries(company):
    """선택 기업의 2026년 수출 유망 국가 TOP 10"""
    weights = custom_weights(company)   # 기업별 가중치: 기본값(CRITIC)이면 None → dashboard_score.py 결과 그대로
    try:
        result = top_countries(company, TOP_N, weights)
    except Exception as error:   # 스크립트 오류가 나도 화면은 유지
        st.session_state["export_top10_error"] = str(error)
        return []
    st.session_state.pop("export_top10_error", None)
    return result

# ============================================================
# 7. 기업 선택: 책갈피형 탭
# ============================================================

selected_company = st.session_state.export_company
selected_info = COMPANY_INFO[selected_company]

# 선택된 기업 위치 (0~5)
selected_index = list(COMPANIES).index(selected_company)

tab_css = """
<style>
/* ==================================================
   1. 기업 탭 행
================================================== */

.st-key-export_tabs_panel
[data-testid="stHorizontalBlock"]:has(
    [class*="st-key-export_company_button_"]
) {
    position: relative !important;
    z-index: 5 !important;
}

/* ==================================================
   2. 기본 책갈피 디자인
================================================== */

[class*="st-key-export_company_button_"] button {
    width: 100% !important;

    min-height: 64px !important;
    height: 64px !important;

    padding: 10px 5px !important;

    /* 현재 테마 글자색을 사용 */
    color: inherit !important;

    /* 비활성 탭: 회색 배경 (현재 글자색 기준이라 다크 모드에서도 회색) */
    background-color: color-mix(
        in srgb,
        currentColor 12%,
        transparent
    ) !important;

    /* 테마에 따라 자동으로 달라지는 테두리 */
    border: 1px solid color-mix(
        in srgb,
        currentColor 25%,
        transparent
    ) !important;

    border-radius: 14px 14px 0 0 !important;

    box-shadow: none !important;

    position: relative !important;

    display: flex !important;
    align-items: center !important;
    justify-content: center !important;

    transition: background-color 0.15s ease !important;
}

/* 마우스를 올렸을 때: 조금 더 밝게 */
[class*="st-key-export_company_button_"] button:hover {
    background-color: color-mix(
        in srgb,
        currentColor 7%,
        transparent
    ) !important;
}

/* 기업명 (비활성): 흐린 글자 */
[class*="st-key-export_company_button_"] button p {
    font-size: 17px !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
    color: inherit !important;
    opacity: .55 !important;
}


/* ==================================================
   3. 콘텐츠 박스
================================================== */

.st-key-export_company_content {
    position: relative !important;
    z-index: 1 !important;

    background-color: transparent !important;

    /* 위쪽 모서리 직각, 아래쪽만 둥글게 */
    border-radius: 0 0 14px 14px !important;

    /* 위쪽 기본 테두리 제거 */
    border-top: none !important;
}

/* Streamlit 내부 콘텐츠 박스에도 적용 */
.st-key-export_company_content
> [data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 0 0 14px 14px !important;
    border-top: none !important;
}

"""

# ==================================================
# 4. 선택된 탭
# ==================================================

selected_code = COMPANIES[selected_company]

tab_css += f"""
/* 선택된 기업 */
.st-key-export_company_button_{selected_code} button,
.st-key-export_company_button_{selected_code} button:hover {{
    /* 활성 탭: 화면 배경색 (밝은 모드 흰색 / 어두운 모드 화면색) → 아래 콘텐츠와 이어짐 */
    background-color: var(--company-tab-bg, #ffffff) !important;

    border-bottom: none !important;

    top: 1px !important;
    z-index: 10 !important;
}}

/* 선택된 기업명 강조 */
.st-key-export_company_button_{selected_code} button p {{
    font-size: 19px !important;
    font-weight: 800 !important;
    opacity: 1 !important;
}}

/* 콘텐츠 위쪽 선: 선택된 탭 부분만 비우기 */
.st-key-export_company_content {{
    --tab-start: calc(
        (100% - 5rem) * {selected_index / 6:.6f}
        + {selected_index}rem
    );

    --tab-end: calc(
        (100% - 5rem) * {(selected_index + 1) / 6:.6f}
        + {selected_index}rem
    );
}}

.st-key-export_company_content::before {{
    content: "";
    position: absolute;

    top: 0;
    left: 0;
    right: 0;
    height: 1px;

    background: linear-gradient(
        to right,
        color-mix(in srgb, currentColor 25%, transparent)
            0 var(--tab-start),
        transparent
            var(--tab-start) var(--tab-end),
        color-mix(in srgb, currentColor 25%, transparent)
            var(--tab-end) 100%
    );

    pointer-events: none;
    z-index: 2;
}}
"""

# 기업 탭은 로고 이미지 없이 기업명 텍스트로 표시 (상표권 보호)

tab_css += "</style>"

st.markdown(tab_css + HELP_TOOLTIP_CSS, unsafe_allow_html=True)

# 활성 탭 배경 = 실제 화면 배경색 (테마 전환 시 0.5초 안에 반영) + 공통 도움말 말풍선 위치 보정
if hasattr(getattr(st, "components", None), "v2"):
    company_theme_sync = st.components.v2.component(
        name="company_theme_sync",
        html='<span class="company-theme-sync" aria-hidden="true"></span>',
        css=".company-theme-sync {display:block; width:0; height:0; overflow:hidden;}",
        js=HELP_TOOLTIP_JS + """
        export default function () {
            function applyTheme() {
                const app = document.querySelector(".stApp") || document.body;
                let bg = getComputedStyle(app).backgroundColor;
                if (!bg || bg === "rgba(0, 0, 0, 0)" || bg === "transparent") {
                    bg = getComputedStyle(document.body).backgroundColor;
                }
                document.documentElement.style.setProperty("--company-tab-bg", bg);
            }
            // TOP 10 표 행 높이: 표 아래끝을 왼쪽(무기체계) 카드 아래끝에 맞춤
            function stretchTop10Rows() {
                const list = document.querySelector(".company-top10-list");
                const table = document.querySelector(".st-key-company_top10_table");
                const wrap = document.querySelector(".st-key-export_company_content");
                if (!list || !table || !wrap) return;
                const cols = wrap.querySelectorAll('[data-testid="stColumn"]');
                if (cols.length < 2) return;
                const left = cols[0].querySelector('[data-testid="stVerticalBlock"]') || cols[0];

                // 좁은 화면(카드가 위아래로 쌓일 때)은 조정하지 않음
                if (cols[1].getBoundingClientRect().left < cols[0].getBoundingClientRect().right - 1) {
                    list.style.setProperty("--row-extra", "0px");
                    return;
                }
                // 원래 높이(0)에서 측정 → 계산한 높이 적용을 한 번에 처리
                // (같은 순간에 처리되어 화면에는 중간 모습이 그려지지 않음, 높이가 계속 늘어나지 않음)
                const memo = "__kDefenseTop10RowExtra";
                const before = list.style.getPropertyValue("--row-extra");
                list.style.setProperty("--row-extra", "0px");
                const rows = list.querySelectorAll(".company-top10-row").length || 1;
                const delta = left.getBoundingClientRect().bottom - table.getBoundingClientRect().bottom;
                const extra = Math.max(0, Math.floor(delta / rows));
                list.style.setProperty("--row-extra", extra + "px");
                window[memo] = extra;
                // 새 표가 생겼을 때(before 없음)에도 위에서 바로 최종 높이가 적용됨
                void before;
            }
            function tick() { applyTheme(); stretchTop10Rows(); }
            tick();
            const key = "__kDefenseCompanyThemeSync";
            if (window[key]) { clearInterval(window[key].timer); window[key].observer.disconnect(); }
            // 새 표·이미지가 그려지는 즉시(화면에 보이기 전) 높이 맞춤 + 0.5초마다 테마·높이 확인
            let frame = null;
            const observer = new MutationObserver(() => {
                stretchTop10Rows();
                if (frame === null) frame = requestAnimationFrame(() => { frame = null; stretchTop10Rows(); });
            });
            observer.observe(document.body, { childList: true, subtree: true });
            const timer = setInterval(tick, 500);
            const handle = { timer, observer };
            window[key] = handle;
            return () => {
                if (window[key] === handle) { clearInterval(timer); observer.disconnect(); delete window[key]; }
            };
        }
        """,
    )
    company_theme_sync(key="company_theme_sync")


def _image_base64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()


def company_rank_html(rank, size=RANK_ICON_SIZE):
    """1~3위 트로피(원본 색), 4위 이후 숫자 아이콘(테마 글자색) — 03·04와 동일"""
    path = COMMON_IMAGE_DIR / RANK_ICON_FILES.get(rank, "")
    if not path.is_file():
        return f'<strong>{rank}</strong>'
    if rank > 3:
        return " ".join(mask_icon_html(path, size=size).split())
    return (f'<img src="data:image/png;base64,{_image_base64(path)}" alt="{rank}위" '
            f'style="width:{size}px;height:{size}px;object-fit:contain;display:block;">')


def company_flag_html(iso_a3, size=25):
    """원형 국기 (images/common/country/ISO.png)"""
    if not iso_a3:
        return ""
    path = FLAG_IMAGE_DIR / f"{iso_a3}.png"
    if not path.is_file():
        return ""
    return (f'<img src="data:image/png;base64,{flag_thumb_base64(path)}" alt="" '
            f'style="width:{size}px;height:{size}px;border-radius:50%;'
            'object-fit:cover;flex-shrink:0;">')


COMPANY_TABLE_CSS = """
<style>
.company-top10-list { display:flex; flex-direction:column; }
.company-table-header {
    display:grid; gap:6px; padding:12px 8px; border-radius:10px;
    background:rgba(100,160,255,.10); font-size:13px; font-weight:700;
}
.company-table-header > span {
    display:flex; align-items:center; justify-content:center; gap:4px; min-width:0;
}
.company-table-header > span:nth-child(2) { justify-content:flex-start; padding-left:6px; }
.company-top10-cols { grid-template-columns:42px 150px minmax(0,1fr); }   /* A안: 국가 열 150px 고정 (04와 동일) */
.company-top10-row {
    /* --row-extra: 왼쪽 카드 높이에 맞추려고 JS가 넣는 추가 높이 (행마다 같은 값) */
    display:grid; gap:6px; align-items:center; min-height:54px;
    padding:calc(12px + var(--row-extra, 0px) / 2) 8px;
    border-bottom:1px solid rgba(128,128,128,.15); font-size:13px; box-sizing:border-box;
}
.company-top10-row:last-child { border-bottom:none; }
.company-top10-rank { display:flex; align-items:center; justify-content:center; width:30px; justify-self:center; }
.company-country-cell {
    display:flex; align-items:center; justify-content:flex-start; gap:7px;
    min-width:0; padding-left:6px; font-weight:650;
}
.company-country-name { min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }   /* 국가명 줄바꿈 금지 */
/* 국가를 누르면 04 국가별 상세 분석으로 이동 */
.company-country-link { cursor:pointer; }
.company-country-link:hover .company-country-name { color:#5B9CF5; text-decoration:underline; text-underline-offset:3px; }
.company-score { display:flex; flex-direction:column; align-items:center; gap:5px; font-weight:700; }
.company-score-empty > span:first-child { font-weight:650; opacity:.6; }
.company-score-track {
    width:100%; height:9px; border-radius:5px; background:rgba(100,160,255,.15);
    overflow:hidden; display:block;
}
.company-score-fill { display:block; height:100%; background:#5B9CF5; border-radius:5px; }
</style>
"""


def card_title_html(icon_key, text, tooltip=""):
    """카드 제목: 아이콘 28px + 제목 19px/750 (+ 파란 정보 아이콘) — 01·03·04 공통 형식"""
    icon = " ".join(mask_icon_html(TITLE_ICONS[icon_key], size=TITLE_ICON_SIZE).split())
    help_html = help_icon_html(tooltip, label=f"{text} 설명") if tooltip else ""
    return (
        f'<div style="display:flex; align-items:center; gap:{TITLE_ICON_GAP}px; margin:2px 0 14px;">'
        f'<span style="display:inline-flex; margin-top:-4px;">{icon}</span>'
        f'<span style="font-size:{TITLE_FONT_SIZE}px; font-weight:{TITLE_FONT_WEIGHT}; line-height:1.2;">'
        f'{escape(text)}</span>{help_html}</div>'
    )



# ---------------------------------------------------------
# 기업 선택 버튼
# ---------------------------------------------------------

# 탭과 콘텐츠를 하나의 레이아웃으로 묶기
tabs_host = st.container(
    key="export_tabs_panel",
    gap=None
)

company_columns = tabs_host.columns(
    len(COMPANIES),
    gap="small",
    vertical_alignment="top"
)

for index, (company, code) in enumerate(COMPANIES.items()):
    with company_columns[index]:
        st.button(
            company,
            key=f"export_company_button_{code}",
            type="secondary",
            use_container_width=True,
            on_click=select_company,
            args=(company,),
        )


# =========================================================
# 9. 기업 강점 무기 + TOP 10 후보국
# =========================================================

content_wrap = tabs_host.container(
    border=True,
    key="export_company_content"
)

with content_wrap:
    left_column, right_column = st.columns(
        [1, 1.25],
        gap="large"
    )

    
    # ---------------------------------------------------------
    # 9-1. 기업 강점 분야 및 무기체계
    # ---------------------------------------------------------
    with left_column:

        st.markdown(
            card_title_html("weapons", "기업 강점 무기체계 및 주요 무기"),
            unsafe_allow_html=True
        )

        # 03번 무기체계 TOP 3와 같은 사진 + 설명 카드
        # 사진과 설명 박스는 연결하고 같은 높이로 정렬
        st.html("""
        <style>
        
        /* 전체 무기 카드 */
        .company-weapon-card {
            --photo-width: min(46%, 230px);
            position: relative;
            display: block;
            width: 100%;
            margin-bottom: 14px;
            overflow: hidden;
            border-radius: 12px;
        }

        /* 왼쪽 사진 영역: 무조건 정사각형 */
        .company-weapon-photo {
            position: relative;
            width: var(--photo-width);
            aspect-ratio: 1 / 1;
            display: grid;
            place-items: center;
            overflow: hidden;
        }

        /* 이미지: 정사각형 영역에 정확히 맞춤 */
        .company-weapon-photo img {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            display: block;
            object-fit: contain;
        }

        /* 오른쪽 설명 박스: 사진과 같은 높이 */
        .company-weapon-info {
            position: absolute;
            left: var(--photo-width);
            right: 0;
            top: 0;
            bottom: 0;

            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 8px;
            min-width: 0;
            padding: 10px 12px;
            box-sizing: border-box;
            background: rgba(100, 160, 255, .10);
            text-align: center;
            overflow-y: auto;
        }


        .company-weapon-name {
            font-size: 22px;
            font-weight: 750;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }

        .company-weapon-description {
            font-size: 14px;
            line-height: 1.65;
            word-break: keep-all;
            overflow-wrap: anywhere;
        }

        .company-weapon-tags {
            font-size: 14px;
            opacity: .8;
            line-height: 1.5;
            word-break: keep-all;
        }

        .company-weapon-missing {
            color: inherit;
            opacity: .55;
            font-size: 13px;
            text-align: center;
        }
        </style>
        """)

        weapons = selected_info["weapons"]

        # 기업당 표시할 무기체계 수
        DISPLAY_WEAPON_COUNT = 5

        for index in range(DISPLAY_WEAPON_COUNT):

            weapon = weapons[index] if index < len(weapons) else None

            # ---------------------------------------------
            # 무기 이름 · 설명 · 이미지 경로
            # ---------------------------------------------
            if weapon:
                name = escape(str(weapon["name"]))
                description = escape(str(weapon["description"]))
                tags = escape(" · ".join(weapon.get("tags", [])))
                image_path = resolve_weapon_image(weapon["image"], weapon["name"])

            else:
                name = "무기 정보 준비 중"
                description = "무기 정보 확인 후 등록 예정"
                tags = "추후 데이터 입력"
                image_path = None

            # ---------------------------------------------
            # 이미지 파일이 있으면 표시, 없으면 안내
            # ---------------------------------------------
            if image_path is not None and image_path.is_file():

                suffix = image_path.suffix.lower()

                mime = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".webp": "image/webp",
                }.get(suffix, "image/png")

                encoded = cached_weapon_image(
                    str(image_path),
                    image_path.stat().st_mtime_ns
                )
                mime = "image/webp"   # cached_weapon_image가 WebP 썸네일로 변환

                image_html = (
                    f'<img src="data:{mime};base64,{encoded}" '
                    f'alt="{name}">'
                )

            else:
                image_html = (
                    '<span class="company-weapon-missing">'
                    '이미지 준비 중</span>'
                )

            # ---------------------------------------------
            # 무기 카드 출력
            # ---------------------------------------------
            st.html(f"""
            <div class="company-weapon-card">

                <div class="company-weapon-photo">
                    {image_html}
                </div>

                <div class="company-weapon-info">

                    <div class="company-weapon-name">
                        {name}
                    </div>

                    <div class="company-weapon-description">
                        {description}
                    </div>

                    <div class="company-weapon-tags">
                        {tags}
                    </div>

                </div>
            </div>
            """)

    # ---------------------------------------------------------
    # 9-2. TOP 10 후보국 및 가중치 설정
    # ---------------------------------------------------------
    with right_column:

        title_column, setting_column = st.columns(
            [2, 1],
            vertical_alignment="center"
        )

        with title_column:
            st.markdown(
                card_title_html(
                    "top10", "2026년 수출 유망 국가 TOP 10",
                    tooltip="2021~2025년 데이터로 6개 지표(HHI·국방비·무기 매칭도·협력 관계·GPI·신용도)를 "
                            "0~100점으로 바꾸고, 기업별 CRITIC 가중치를 곱해 추천 점수를 계산합니다.",
                ),
                unsafe_allow_html=True
            )

        with setting_column:

            # 가중치 커스텀 팝오버 (components/weight_custom.py, 04_country와 같은 상태 공유)
            render_weight_popover(selected_company)

        company_weights = applied_weights(selected_company)   # 선택 기업에 적용된 가중치

        is_default = is_default_weights(selected_company)

        if is_default:
            tooltip_title = (
                "프로젝트에서 설정한 기본 가중치가 "
                "적용됩니다."
            )
        else:
            tooltip_title = (
                "사용자가 조정한 가중치가 적용됩니다."
            )

        weight_details = ", ".join(
            f"{name} {company_weights[i] / 100:.2f}%"
            for i, name in enumerate(WEIGHT_NAMES)
        )

        tooltip_text = escape(
            f"{tooltip_title} {weight_details}",
            quote=True
        )

        # 적합도 TOP 10: 03_weapon '수출 추천 TOP 10'과 같은 HTML 표
        #   - 제목줄 파란 띠 / 1~3위 트로피, 4위 이후 테마색 숫자 아이콘
        #   - 국기+국가명 왼쪽 정렬 / 적합도 점수 + 막대
        top10 = get_top10_countries(selected_company)
        help_html = help_icon_html(
            "추천 점수(적합도): 0~100점. 막대는 100점 기준 비율입니다.\n"
            + ("기본: 기업별 CRITIC 가중치" if is_default
               else f"사용자 가중치 적용: {weight_details}"),
            size=15, label="추천 점수 설명"
        )

        rows = []
        for position in range(1, TOP_N + 1):
            country_data = top10[position - 1] if position <= len(top10) else None
            # 순위는 dashboard_score.py의 rank 그대로 (동점이면 같은 순위)
            rank = int(country_data["rank"]) if country_data else position

            if country_data:
                iso_a3 = str(country_data.get("iso_a3") or "").strip().upper()
                name = escape(str(country_data.get("country", "—")))
                score = float(country_data["suitability"])
                bar = max(0.0, min(score, 100.0))
                score_html = (
                    f'<span class="company-score"><span>{score:.1f}</span>'
                    f'<span class="company-score-track"><span class="company-score-fill" '
                    f'style="width:{bar:.1f}%"></span></span></span>'
                )
            else:
                iso_a3, name = "", "—"
                score_html = (
                    '<span class="company-score company-score-empty"><span>—</span>'
                    '<span class="company-score-track"></span></span>'
                )

            rows.append(
                '<div class="company-top10-row company-top10-cols">'
                f'<span class="company-top10-rank">{company_rank_html(rank)}</span>'
                + (f'<span class="company-country-cell company-country-link" data-iso="{escape(iso_a3, quote=True)}" '
                   f'title="{name} 상세 분석 보기" role="link" tabindex="0">'
                   if iso_a3 else '<span class="company-country-cell">')
                + f'{company_flag_html(iso_a3)}'
                f'<span class="company-country-name">{name}</span></span>'
                f'{score_html}</div>'
            )

        table_html = (
            '<div class="company-top10-list">'
            '<div class="company-table-header company-top10-cols">'
            '<span>순위</span><span>국가</span>'
            f'<span>추천 점수{help_html}</span></div>'
            + "".join(rows) + "</div>"
        )

        with st.container(border=True, key="company_top10_table"):
            st.html(COMPANY_TABLE_CSS + table_html)

        # 국가를 누르면 04 국가별 상세 분석으로 이동 (선택 기업·국가 유지, 가중치도 그대로 공유)
        if top10_click_bridge is not None:
            top10_click_bridge(key="company_top10_click", data={"company": selected_company},
                               on_country_change=on_top10_country_click)

        if not top10:
            error = st.session_state.get("export_top10_error")
            st.caption(
                f"추천 결과를 불러오지 못했습니다: {error}" if error else
                "점수 계산 결과가 연결되면 2026년 수출 유망 국가 TOP 10이 표시됩니다."
            )
