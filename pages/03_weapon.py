"""무기체계별 수출국 추천 대시보드.

기존 기능을 유지하면서 HTML·아이콘·차트 중복 코드는 함수로 통합했습니다.
공통 컴포넌트(components/header.py, components/icons.py)는 수정하지 않습니다.
"""

# ============================================================
# 공통 모듈 및 경로 설정
# ============================================================

import base64
import html
import math
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image, ImageOps

# 이미 분리되어 있는 공통 컴포넌트 재사용
from components.header import render_header
from components.icons import mask_icon_html
# 도움말 말풍선: 01·02·04·05와 같은 공통 디자인 (components/common_ui.py)
from components.common_ui import INFO_ICON_SIZE, HELP_TOOLTIP_CSS, HELP_TOOLTIP_JS, help_icon_html, flag_thumb_base64
import importlib
# export_score.py를 고치면 Streamlit을 다시 시작하지 않아도 새로고침만으로 반영 (01·02·04와 같은 방식)
import components.export_score as _export_score
if getattr(_export_score, "LOADED_MTIME", None) != _export_score.Path(_export_score.__file__).stat().st_mtime_ns:
    _export_score = importlib.reload(_export_score)
from components.export_score import weapon_top_countries   # dashboard_score_weapon.py 결과

# 현재 페이지 파일의 상위 상위 폴더 = 프로젝트 루트
BASE_DIR = Path(__file__).resolve().parent.parent

# 기존 데이터 경로 그대로 사용 (파일 이동·CSV 변경 없음)
DATA_PROCESSED = "data/processed/"
DATA_MAPPING = "data/mapping/"

# 모든 차트에서 동일하게 사용하는 최근 5개년
YEARS = list(range(2021, 2026))

# 도넛 차트 10개 그룹별 중복 없는 색상
PIE_COLORS = [
    "#1456AE", "#358DEF", "#32BDA0", "#FFC765", "#9274DC",
    "#F07869", "#59B85A", "#D49352", "#38B6CF", "#8290A8",
]

# TOP 5 / TOP 10에서 공통 사용하는 순위 아이콘
# 1~3위: 금·은·동 트로피(Material Symbols) / 4~10위: 숫자 원, 테마에 따라 색상 변경
RANK_IMAGES = {
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

# ============================================================
# 공통 함수: 이미지 캐시·경로·HTML·차트 보조 계산
# ============================================================

# TOP 3 사진은 원본을 잘라내지 않고, 화면 표시용 WebP로만 축소
# 파일 수정 시 modified_ns 값이 바뀌어 캐시도 자동 갱신됨

@st.cache_data(show_spinner=False)
def _thumbnail_base64(file_path: str, modified_ns: int) -> str:
    """원본 비율 유지, 사진 전체를 담는 작은 WebP로 캐시."""
    with Image.open(file_path) as source:
        # 휴대폰·카메라 EXIF 방향 정보를 반영
        photo = ImageOps.exif_transpose(source)
        # 정사각형 캔버스를 강제하지 않고 원본 비율 유지
        # 실제 출력 크기의 약 2배로 축소해 선명도와 로딩 속도 균형 유지
        photo.thumbnail((360, 360), Image.Resampling.LANCZOS)
        photo = photo.convert("RGBA" if "A" in photo.getbands() else "RGB")
        buf = BytesIO()
        photo.save(buf, format="WEBP", quality=82, method=0)
        return base64.b64encode(buf.getvalue()).decode("ascii")


# 순위 메달과 국기 파일도 캐시하여 Streamlit 재실행 시 중복 로딩 방지
@st.cache_data(show_spinner=False)
def _icon_base64(file_path: str, modified_ns: int) -> str:
    return base64.b64encode(Path(file_path).read_bytes()).decode("ascii")


# TOP 3 무기 이름 → 실제 사진 파일 탐색
#  - MMR: "MMR radar" 파일 사용 (MMR 국기 이미지와 충돌 방지)
#  - Arrow-3: 방공체계/요격미사일 그룹에 따라 다른 사진 사용
#  - EL/M-2052: Windows 파일명 제한으로 "/"를 "-"로 변환
#  - 정사각형으로 배경 확장된 사진을 넣으면 contain 상태로도 빈 공간 없이 표시
#  - 아직 실제 사진 파일이 없다면 무기명 + "이미지 파일 없음" 출력

def get_weapon_image_html(weapon_name: str, group_name: str) -> str:
    """기존 파일명 예외(MMR, Arrow-3, EL/M-2052)를 유지."""
    # 데이터와 대시보드에 표시하는 정식 무기명은 바꾸지 않음
    names = ["MMR radar"] if weapon_name == "MMR" else [weapon_name.replace("/", "-")]
    # Arrow-3는 하나의 무기명이 두 무기그룹에 존재하므로 파일명 분기
    if weapon_name == "Arrow-3":
        special = "Arrow-3 system" if group_name == "air_defence_systems" else "Arrow-3 missile"
        names.insert(0, special)
    for name in names:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            path = BASE_DIR / "images/common/weapon" / f"{name}{ext}"
            if path.is_file():
                # 현재 파일이 바뀌었는지 수정 시각까지 확인하고 캐시
                encoded = _thumbnail_base64(str(path), path.stat().st_mtime_ns)
                return (f'<img src="data:image/webp;base64,{encoded}" '
                        f'alt="{html.escape(weapon_name, quote=True)}" '
                        'width="200" height="200" loading="eager" decoding="async" '
                        'style="width:100%;height:100%;object-fit:contain;border-radius:8px;display:block;">')
    return (f'<span class="weapon-photo-missing">{html.escape(weapon_name)}'
            '<br>이미지 파일 없음</span>')


# 각 패널의 제목 아이콘: 공통 아이콘 함수를 쓰고 파일이 없으면 이모지 표시
def _icon_html(path: str, size: int, fallback: str) -> str:
    fallback_size = 25 if size == 28 else 23
    return (mask_icon_html(BASE_DIR / path, size=size)
            or f'<span style="font-size:{fallback_size}px">{fallback}</span>')


# 패널마다 반복되던 "원형 아이콘 + 제목 + 작은 설명" HTML을 함수로 통합
# annotation: 제목 옆 설명 / aside: 오른쪽 끝 설명


def _panel_heading(title: str, path: str, size: int, fallback: str, gap_bottom: int = 12,
                   annotation: str = "", aside: str = "", tooltip: str = "") -> str:
    icon = _icon_html(path, size, fallback)
    detail = f'<small class="weapon-title-detail">{html.escape(annotation)}</small>' if annotation else ""
    aside_html = f'<small class="weapon-title-aside">{html.escape(aside)}</small>' if aside else ""

    # 정보 아이콘 + 말풍선: 01_main과 같은 공통 도움말 (help_icon_html)
    info_html = (
        f'<span style="display:inline-flex;margin-left:4px;">'
        f'{help_icon_html(tooltip, size=INFO_ICON_SIZE, label=f"{title} 설명")}</span>'
        if tooltip else ""
    )

    return (f'<div class="weapon-panel-heading" style="margin-bottom:{gap_bottom}px">'
            f'<span class="weapon-heading-left"><span class="weapon-panel-icon">{icon}</span>'
            f'<strong class="weapon-panel-name">{html.escape(title)}</strong>{info_html}{detail}</span>'
            f'{aside_html}</div>')



# TOP 3 / TOP 5 / TOP 10 공통 순위 아이콘
# 1~3위는 원본 PNG 사용, 4위 이후는 다크·라이트 테마 마스크 적용

def _rank_html(rank: int, size: int = 28, shadow: bool = False) -> str:
    path = BASE_DIR / "images/common/etc" / RANK_IMAGES[rank]
    if path.is_file():
        if rank > 3:
            return mask_icon_html(path, size=size)
        encoded = _icon_base64(str(path), path.stat().st_mtime_ns)
        css_shadow = 'filter:drop-shadow(0 1px 2px rgba(0,0,0,0.8));' if shadow else ''
        return (f'<img src="data:image/png;base64,{encoded}" '
                f'style="width:{size}px;height:{size}px;object-fit:contain;display:block;{css_shadow}">')
    return (f'<span class="weapon-rank-fallback" style="width:{size}px;height:{size}px">'
            f'{rank}</span>')


# ISO_A3에 맞는 국기 파일을 읽고 원형 국기 HTML로 변환
def _flag_html(iso_code: str, size: int) -> str:
    path = BASE_DIR / "images/common/country" / f"{iso_code}.png"
    if not path.is_file():
        return ""
    encoded = flag_thumb_base64(path)   # 64px 썸네일 (속도 개선)
    return (f'<img src="data:image/png;base64,{encoded}" '
            f'style="width:{size}px;height:{size}px;border-radius:50%;'
            'object-fit:cover;flex-shrink:0;">')


# Y축 표시 최대값을 데이터 크기에 따라 1/10/100/1,000 단위로 올림
# TIV가 작은 무기그룹과 큰 무기그룹에 같은 그래프 함수를 사용하기 위함

def _axis_top(value: float) -> tuple[int, int]:
    unit = 1000 if value >= 10000 else 100 if value >= 100 else 10 if value >= 10 else 1
    return max(unit, int(math.ceil(value / unit) * unit)), unit


# TOP 3 전처리 완료 CSV 로딩
@st.cache_data(show_spinner=False)
def _load_top3_orders(file_path: str, modified_ns: int) -> pd.DataFrame:
    return pd.read_csv(
        file_path,
        usecols=["weapon_type_group_en", "rank", "weapon", "tiv_order"]
    )

# ============================================================
# 공통 데이터: TOP 3에 표시할 무기별 설명 (기존 30개 내용 유지)
# ============================================================

# key = (무기그룹 영문코드, 무기명) / value = 화면에 표시할 설명
WEAPON_DESCRIPTIONS = {
    # 방공체계
    ('air_defence_systems', 'Arrow-3'): '이스라엘·미국이 공동 개발한 탄도미사일 방어 시스템으로, 대기권 밖 요격을 담당합니다.',
    ('air_defence_systems', 'Patriot Configuration-3'): '패트리엇 PAC-3 계열 지대공 방공체계로, 항공기와 탄도미사일 위협에 대응합니다.',
    ('air_defence_systems', 'IRIS-T SL'): 'IRIS-T SLM·SLS 계열 지상 방공체계로, 항공기·드론·미사일 등에 대응합니다.',
    # 항공기·무인기
    ('aircraft_uavs', 'F-35A Lightning-2'): '미국의 5세대 스텔스 다목적 전투기로, 센서 융합과 정밀타격 능력을 갖추고 있습니다.',
    ('aircraft_uavs', 'Rafale F-4'): '프랑스 라팔 전투기의 F4 개량형으로, 전자전·센서·네트워크 운용 능력을 강화했습니다.',
    ('aircraft_uavs', 'P-8A Poseidon'): '보잉 737 기반의 해상초계기로, 잠수함 탐지와 해상 감시·대함 작전을 수행합니다.',
    # 기갑차량
    ('armoured_vehicles', 'K-2 Black Panther'): '대한민국의 K2 주력전차로, 120mm 활강포와 첨단 사격통제체계를 탑재합니다.',
    ('armoured_vehicles', 'M-1A2 SEPv-3 Abrams'): '미국 M1A2 에이브럼스 전차의 SEPv3 개량형으로, 방호와 전자장비를 강화했습니다.',
    ('armoured_vehicles', 'Eagle-5 4x4'): 'GDELS의 4×4 다목적 장갑차로, 병력 수송과 정찰 등 다양한 임무에 사용됩니다.',
    # 포병체계
    ('artillery', 'K-9 Thunder 155mm'): '대한민국의 155mm 궤도형 자주포로, 기동성을 활용해 신속한 포격과 진지 이동을 수행합니다.',
    ('artillery', 'HIMARS'): '미국의 차륜형 고기동 다연장로켓 발사체계로, 유도 로켓과 전술미사일을 운용합니다.',
    ('artillery', 'K-239 Chunmoo'): '대한민국의 차륜형 다연장로켓체계로, 여러 종류의 유도·비유도 로켓을 운용합니다.',
    # 엔진·추진체계
    ('engines', 'AL-31'): '러시아 AL-31 계열 터보팬 엔진으로, Su-27·Su-30 계열 전투기 등에 사용됩니다.',
    ('engines', 'F-404'): 'GE F404 계열 항공기 터보팬 엔진으로, F/A-18 등 전투기와 훈련기에 사용됩니다.',
    ('engines', 'F414'): 'GE F414 계열 고성능 터보팬 엔진으로, KF-21 등 전투기에 적용됩니다.',
    # 미사일·유도무기
    ('missiles_guided_weapons', 'AIM-120D AMRAAM'): '능동 레이더 유도 방식의 중거리 공대공미사일로, 가시거리 밖 표적을 요격합니다.',
    ('missiles_guided_weapons', 'Arrow-3'): 'Arrow-3 탄도미사일 방어체계에서 발사하는 외기권 요격미사일입니다.',
    ('missiles_guided_weapons', 'GMLRS'): 'HIMARS와 M270 계열 발사체계에서 사용하는 정밀 유도 다연장로켓탄입니다.',
    # 해군용 무기체계
    ('naval_weapons', 'Mk-41 VLS'): '군함에 장착하는 모듈형 수직발사체계로, 함대공·대잠·순항미사일 등을 운용합니다.',
    ('naval_weapons', 'Super Rapid Strales 76mm'): '76mm 함포에 유도탄 운용용 STRALES 기능을 결합한 함정 방어용 포체계입니다.',
    ('naval_weapons', 'VL-MICA-M'): '함정에서 수직 발사하는 MICA 계열 함대공미사일로, 항공기·미사일 위협에 대응합니다.',
    # 기타 체계·구성품
    ('other_systems_components', 'Guardian-30'): '스페인 EM&E가 개발한 30mm 원격조종 무인포탑으로, 장갑차 개량 사업에 사용됩니다.',
    ('other_systems_components', 'Protector-MC'): '콩스버그 PROTECTOR 계열 중구경 원격조종 포탑으로, 장갑차에 30mm급 화력을 제공합니다.',
    ('other_systems_components', 'CV-90 D-series'): 'CV90 장갑차용 신형 D-series 포탑으로, 네덜란드 CV90 성능개량 사업에 사용됩니다.',
    # 센서·감시정찰(ISR)·위성
    ('sensors_isr_satellites', 'EL/M-2052'): '이스라엘제 전투기용 AESA 레이더로, 공중·지상 표적의 탐지와 추적을 지원합니다.',
    ('sensors_isr_satellites', 'Litening-5'): '전투기 외부에 장착하는 전자광학·적외선 표적획득 포드로, 정밀 표적 식별을 지원합니다.',
    ('sensors_isr_satellites', 'MMR'): '다목적 레이더로, 공중표적 추적과 로켓·포탄 탐지 등에 운용됩니다.',
    # 함정
    ('ships', 'Type-214'): '독일 설계의 214형 디젤·전기 추진 잠수함 계열로, 해외 도입·현지건조 사업에 사용됩니다.',
    ('ships', 'FDI'): '프랑스의 FDI 중형 다목적 호위함으로, 대공·대함·대잠 임무를 수행합니다.',
    ('ships', 'Type-212'): '독일·이탈리아가 운용·개량하는 212형 잠수함 계열로, 수중 은밀성을 중시한 함정입니다.',
}

# ============================================================
# 공통 상단 헤더
# ============================================================

# 제목 / 부제 / 달력 / 테마 처리 등은 기존 render_header()를 그대로 사용
render_header(
    title="무기체계별 수출국 추천",
    description="무기체계별 글로벌 수요와 한국 수출 기회를 종합적으로 비교합니다.",
    page_file=__file__,
)

# ============================================================
# 공통 페이지 스타일
# ============================================================

# 중복된 인라인 스타일은 CSS 클래스에 모아 관리
# 박스 높이/간격/도넛 조각 선택 효과 등 기존 UI 동작은 유지
st.markdown(
    """
    <style>
    /* 1번 도넛: Streamlit 현재 테마의 글자색·여백 */
    .st-key-weapon_tiv_chart {
        color: var(--st-text-color,var(--text-color,inherit)) !important;
        margin-top: -35px;
        margin-bottom: -10px;
    }
    .st-key-weapon_tiv_chart .js-plotly-plot svg text {
        color: inherit !important;
        fill: currentColor !important;
    }
    .st-key-weapon_tiv_chart .js-plotly-plot g.slice path {
        stroke: var(--weapon-donut-border,#FFF) !important;
        stroke-width: 2px !important;
    }

    /* 3번 추이 차트: 위쪽 여백 및 한국 수출값의 테마별 색상 */
    .st-key-weapon_tiv_trend_chart {
        margin-top: -16px !important;
    }
    .st-key-weapon_tiv_trend_chart .js-plotly-plot .scatterlayer .trace.scatter text {
        fill: var(--weapon-trend-label-color,#1456AE) !important;
        stroke: var(--weapon-trend-label-halo,#FFF) !important;
        stroke-width: 2px !important;
        paint-order: stroke fill !important;
        opacity: 1 !important;
    }

    /* 모든 패널: 고정 높이와 내부 스크롤바 대신 콘텐츠 높이에 맞춤 */
    .st-key-weapon_donut_panel,.st-key-weapon_trend_panel,.st-key-weapon_top3_panel, .st-key-weapon_top5_panel,.st-key-weapon_recommend_tall {
        overflow: visible !important;
        height: auto;
        min-height: 0;
    }
    .weapon-top3-card,.weapon-top5-row,.weapon-recommend-row {
        box-sizing: border-box;
    }

    /* 무기 선택창 및 드롭다운 목록 가운데 정렬 */
    .st-key-weapon_select_radio [data-testid="stSelectbox"] input {
        text-align: center !important;
    }
    [data-testid="stSelectboxVirtualDropdown"] [data-item-hl] {
        justify-content: center !important;
        text-align: center !important;
    }
    
    /* 무기 선택창: 제목·부제 아래 오른쪽 정렬 (시안 A) */
    .st-key-weapon_select_radio {
        margin-left: auto !important;   /* 왼쪽 여백을 모두 채워 카드 오른쪽 끝에 붙임 */
        margin-right: 0 !important;
        margin-top: -15px !important;   /* 부제와의 간격을 15px 줄여 위로 이동 */
    }

    /* 공통 패널 제목: 원형 아이콘 / 제목 / 우측 보조 문구 */
    .weapon-panel-heading {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 7px;
        width: 100%;
    }
    .weapon-heading-left {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        column-gap: 6px;    /* 아이콘-제목 간격: 01_main 기준 (common_ui TITLE_ICON_GAP) */
        row-gap: 5px;
        min-width: 0;
    }
    
    /* 패널 아이콘: 원형 배경 제거 및 테마 자동 대응 */
    .weapon-panel-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        flex-shrink: 0;
        
        background: transparent;
        border: none;
        border-radius: 0;

        color: var(--st-text-color, var(--text-color, inherit));
    }
    .weapon-panel-name {
        font-size: 19px;
        font-weight: 750;
        line-height: 1.2;
        color: inherit;
    }
    .weapon-title-detail,.weapon-title-aside {
        font-size: 11px;
        opacity: .75;
        white-space: nowrap;
    }
    .weapon-title-aside {
        flex-shrink: 0;
    }

    /* 1번 도넛: 제목·부제·범례 */
    .weapon-donut-heading {
        margin: 4px 0;
    }
    .weapon-donut-heading strong {
        font-size: 19px;
        font-weight: 700;
        line-height: 1.3;
        display: block;
    }
    .weapon-donut-heading small {
        font-size: 14px;
        opacity: .7;
        line-height: 1.6;
        display: block;
        margin-top: 2px;
        padding-bottom: 4px;
    }
    /* 범례: 4열 격자(같은 너비) → 색 점이 세로로 줄맞춤
       칸보다 긴 분류명은 …으로 줄이고, 마우스를 올리면 전체 이름(title) 표시 */
    .weapon-donut-legend {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        column-gap: 10px;
        row-gap: 7px;
        width: 100%;
    }
    .weapon-legend-item {
        display: flex;
        align-items: center;
        gap: 5px;
        min-width: 0;
        cursor: default;
    }
    .weapon-legend-dot {
        width: 11px;
        height: 11px;
        flex-shrink: 0;
        border-radius: 50%;
    }
    .weapon-legend-label {
        font-size: 11px;
        line-height: 1.4;
        color: inherit;
        white-space: nowrap;   /* "미사일·유도무기" 등 분류명 줄바꿈 방지 */
        overflow: hidden;
        text-overflow: ellipsis;   /* 칸을 넘는 이름은 … 표시 */
        min-width: 0;
    }

    /* TOP 5 / TOP 10 공통 표 헤더와 행 스타일 */
    .weapon-table-header {
        display: grid;
        gap: 6px;
        padding: 12px 8px;
        border-radius: 10px;
        background: rgba(100,160,255,.10);
        font-size: 13px;
        font-weight: 700;
    }
    /* TOP 5 / TOP 10 제목줄 가운데 정렬 */
    .weapon-table-header > span {
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        min-width: 0;
    }

    /* 최대 수입국 TOP 5: 4개 열 및 수입 비중 막대 */
    .weapon-top5-cols {
        grid-template-columns: 40px 1.3fr .8fr 1.2fr;
    }
    .weapon-top5-row {
        display: grid;
        gap: 6px;
        align-items: center;
        padding: 31px 8px;
        border-bottom: 1px solid rgba(128,128,128,.15);
        font-size: 13px;
    }
    .weapon-country-cell {
        display: flex;
        align-items: center;
        gap: 7px;
        min-width: 0;
        font-weight: 650;
    }
    .weapon-country-share {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }
    .weapon-share-track {
        width: 100%;
        height: 9px;
        border-radius: 5px;
        background: rgba(100,160,255,.15);
        overflow: hidden;
        display: block;
    }
    .weapon-share-fill {
        display: block;
        height: 100%;
        background: #5B9CF5;
        border-radius: 5px;
    }

    /* 수출 추천 TOP 10: 10개 행 높이 및 국가명 줄바꿈 */
    .weapon-recommend-list {
        display: flex;
        flex-direction: column;
    }
    .weapon-top10-cols {
        grid-template-columns: 42px minmax(0,1.4fr) minmax(95px,1fr);
    }
    .weapon-recommend-row {
        display: grid;
        gap: 6px;
        align-items: center;
        padding: 12px 8px;
        border-bottom: 1px solid rgba(128,128,128,.15);
        font-size: 13px;
        min-height: 78px;
        flex: 1 1 auto;
    }
    .weapon-top10-rank {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 30px;
    }
    .weapon-top10-empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
    }

    /* TOP 5 / TOP 10 표 내용 가운데 정렬 (메인 제외 화면 공통) */
    .weapon-top5-row > *,
    .weapon-recommend-row > * {
        justify-self: center;
        text-align: center;
    }
    /* 국기+국가명은 왼쪽 정렬 (01·02·04 공통) — 제목줄 '국가'도 왼쪽 */
    .weapon-top5-row > .weapon-country-cell,
    .weapon-recommend-row > .weapon-country-cell {
        justify-self: stretch;
        justify-content: flex-start;
        text-align: left;
        padding-left: 6px;
    }
    .weapon-table-header > span:nth-child(2) {
        justify-content: flex-start;
        padding-left: 6px;
    }
    /* 비중 막대·추천 점수 칸은 칸 너비를 그대로 써서 막대 길이 유지 */
    .weapon-top5-row > .weapon-country-share,
    .weapon-recommend-row > .weapon-top10-empty {
        justify-self: stretch;
    }
    .weapon-country-share {
        align-items: center;
    }
    .weapon-top10-empty span:first-child {
        font-weight: 650;
        opacity: .6;
    }
    /* 추천 점수: 숫자는 진하게, '점'은 작게 */
    .weapon-top10-score > span:first-child {
        font-weight: 750;
        opacity: 1;
        font-variant-numeric: tabular-nums;
    }
    .weapon-top10-score small {
        font-size: 11px;
        font-weight: 500;
        opacity: .6;
        margin-left: 1px;
    }

    /* 무기체계 TOP 3: 무기별 사진·메달·설명 카드 */
    .weapon-top3-card {
        position: relative;
        display: flex;
        align-items: stretch;
        gap: 0;
        padding: 0;
        margin-bottom: 12px;
        background: transparent;
        border: none;
        border-radius: 10px;
        box-shadow: none;
        min-height: 0;
    }

    /* 정사각형 사진 틀 유지. 원본 사진은 절대 자르지 않음(object-fit:contain) */
    .weapon-photo {
        width: 230px;
        max-width: 46%;
        aspect-ratio: 1/1;
        height: auto;
        box-sizing: border-box;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        background: rgba(100,160,255,.06);
        border-radius: 10px 0 0 10px;
        color: inherit;
        text-align: center;
    }
    .weapon-photo img {
        border-radius: 10px 0 0 10px !important;
    }
    .weapon-photo-missing { 
        font-size: 11px;
        line-height: 1.5;
        opacity: .7;
        overflow-wrap: anywhere;
        text-align: center;
    }
    .weapon-top3-medal {
        width: 24px;
        height: 24px;
        flex: 0 0 24px;

        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    /* 메달 이미지와 제목의 세로 위치 통일 */
    .weapon-top3-medal img {
        width: 24px !important;
        height: 24px !important;
        object-fit: contain;
        display: block;
    }

    /* 무기명 줄바꿈 방지 */
    .weapon-top3-name > span:last-child {
        white-space: nowrap;
    }

    .weapon-top3-info {
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 8px;
        flex: 1 1 0;
        min-width: 0;
        box-sizing: border-box;

        padding: 12px 10px;
        background: rgba(100,160,255,.10);
        border-radius: 0 10px 10px 0;
    }
    .weapon-top3-name {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;

        font-size: 16px;
        font-weight: 750;
        line-height: 24px;
        color: inherit; 
        white-space: nowrap;
        transform: translateY(-8px);
    }
    .weapon-top3-description {
        width: 100%;
        box-sizing: border-box;
        padding: 0 8px;
        font-size: 12px;
        font-weight: 400;
        line-height: 1.6;
        letter-spacing: -0.15px;
        color: inherit;
        opacity: .82;
        text-align: center;
        word-break: keep-all;
        overflow-wrap: anywhere;
    }
    .weapon-top3-tiv {
        font-size: 12px;
        color: inherit;
        line-height: 1.5;
        margin-top: 12px;
        text-align: center;
        transform: translateY(12px);
    }
    .weapon-top3-tiv strong {
        color: #358DEF;
        font-size: 15px;
        white-space: nowrap;
    }
    .weapon-rank-fallback {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        background: rgba(128,128,128,.15);
        color: inherit;
        font-size: 14px;
        font-weight: 800;
    }
    </style>
    """ + HELP_TOOLTIP_CSS,   # 도움말 말풍선 공통 CSS (01·02·04·05와 동일)
    unsafe_allow_html=True,
)

# ============================================================
# 1. 데이터 불러오기 및 최근 5년 TIV 집계
# ============================================================

# 1-1. 무기그룹 매핑표, 연도별 TIV, 국가명 매핑표 불러오기
# CSV는 캐시해 화면을 다시 그릴 때마다 읽지 않음 (파일이 바뀌면 자동 갱신, 속도 개선)
@st.cache_data(show_spinner=False)
def _read_csv_cached(path_text: str, modified_ns: int) -> pd.DataFrame:
    return pd.read_csv(path_text)


def _read_csv(path_text: str) -> pd.DataFrame:
    return _read_csv_cached(path_text, Path(path_text).stat().st_mtime_ns).copy()


weapon_groups = _read_csv(DATA_PROCESSED + "weapon_type_10group.csv")
tiv_df = _read_csv(DATA_PROCESSED + "tiv_delivery_yearly.csv")
country_map = _read_csv(DATA_MAPPING + "country_map_master.csv")
# 국가코드를 화면 표시용 한국어 국가명에 매핑하기 위한 딕셔너리
country_name_map = country_map.set_index("iso_a3")["country_name_ko"].to_dict()

# 1-2. 영어 무기그룹 코드 → 한국어 그룹명 연결
# 중복 행은 제거하고 그룹당 대표 이름만 사용
group_map = (weapon_groups[["weapon_type_group_en", "weapon_type_group"]]
             .dropna().drop_duplicates(subset=["weapon_type_group_en"])
             .set_index("weapon_type_group_en")["weapon_type_group"].to_dict())

# 1-3. 최근 5개년(2021~2025) 데이터만 사용
# 수입 TIV가 문자열이어도 계산되도록 숫자로 변환, 결측은 0 처리
tiv_5years = tiv_df.loc[tiv_df["year"].between(2021, 2025)].copy()
tiv_5years["tiv_per_year"] = pd.to_numeric(tiv_5years["tiv_per_year"], errors="coerce").fillna(0)

# 1-4. 무기그룹별 글로벌 수입 TIV 합계
# 값이 큰 그룹부터 내림차순 정렬하여 도넛 조각 순서에 반영
tiv_by_group = (tiv_5years.groupby("weapon_type_group_en")["tiv_per_year"]
                .sum().reindex(list(group_map), fill_value=0).sort_values(ascending=False))
# 무기 선택창과 도넛 차트에 동일한 정렬 순서 적용
group_list = tiv_by_group.index.tolist()
total_tiv = tiv_by_group.sum()

# ============================================================
# 2. 무기 선택 상태 공유 및 도넛 클릭 이벤트
# ============================================================

# 2-1. 선택창 / 도넛 / TOP 3 / TOP 5 / TOP 10 / 추이 차트가 같은 상태 사용
# 세션에 값이 없다면 미선택(None) 상태로 시작
if "selected_weapon" not in st.session_state:
    st.session_state.selected_weapon = None
if "weapon_select_radio" not in st.session_state:
    st.session_state.weapon_select_radio = None
# 도넛에서 선택한 값과 선택창에 표시되는 값이 달라지지 않도록 동기화
if st.session_state.weapon_select_radio != st.session_state.selected_weapon:
    st.session_state.weapon_select_radio = st.session_state.selected_weapon

# 2-2. 드롭다운에서 그룹을 바꾼 경우 세션 선택값 갱신

def on_weapon_radio_change():
    st.session_state.selected_weapon = st.session_state.weapon_select_radio

# 2-3. 도넛 조각 클릭 시 그룹 선택/선택 해제
# 같은 조각 재클릭 → None / 다른 조각 클릭 → 해당 그룹으로 즉시 전환

def on_donut_piece_click():
    result = st.session_state.get("weapon_donut_click")
    if result is None:
        return
    # v2 컴포넌트가 보낸 영문 그룹 ID(또는 한국어 라벨) 추출
    raw = result.get("weapon") if isinstance(result, dict) else getattr(result, "weapon", None)
    label_to_group = {label: code for code, label in group_map.items()}
    clicked = label_to_group.get(raw, raw)
    if clicked not in group_map:
        return
    # 이미 선택된 조각이면 선택 해제, 아니면 새 그룹 선택
    selection = None if clicked == st.session_state.selected_weapon else clicked
    st.session_state.selected_weapon = selection
    st.session_state.weapon_select_radio = selection

# 2-4. Streamlit 기본 Plotly 도넛에 실제 클릭 이벤트 연결
# 별도 iframe 차트를 재생성하지 않아 클릭할 때 깜빡임 최소화
# JS는 도넛 테두리/한국 수출 추이 값 색상의 다크·라이트 테마도 동기화
donut_click_bridge = st.components.v2.component(
    name="weapon_donut_click_bridge",
    html='<span class="weapon-chart-click-bridge" aria-hidden="true"></span>',
    css=".weapon-chart-click-bridge{display:block;height:0;width:0;overflow:hidden;}",
    js=r"""    export default function ({ data, setTriggerValue, parentElement }) {
        // 테마 변경 및 재실행 시 이벤트 중복 등록 방지
        const bridgeKey = "__kDefenseWeaponDonutClick";
        const previousHandler = window[bridgeKey];
        if (previousHandler) {
            document.removeEventListener(
                "click",
                previousHandler,
                true
            );
        }
        // --------------------------------------------
        // 도넛 경계선 색상 실시간 테마 동기화
        // --------------------------------------------
        function syncDonutTheme() {
            const themeElement = parentElement.querySelector(
                ".weapon-chart-click-bridge"
            );
            const chartElement = document.querySelector(
                ".st-key-weapon_tiv_chart"
            );
            if (!themeElement || !chartElement) return;
            // Streamlit v2 컴포넌트의 현재 테마 배경색
            const backgroundColor = getComputedStyle(themeElement)
                .getPropertyValue("--st-background-color")
                .trim();
            if (
                backgroundColor &&
                document.documentElement.style.getPropertyValue(
                    "--weapon-donut-border"
                ) !== backgroundColor
            ) {
                document.documentElement.style.setProperty(
                    "--weapon-donut-border",
                    backgroundColor
                );
            }
            // --st-background-color는 브라우저에서 대개 rgb() 또는 #HEX.
            // 어둠/밝음 판정은 UI의 실제 배경색으로 하고 Python 재실행을 요구하지 않음.
            const color = backgroundColor.toLowerCase();
            let dark = null;
            if (color.startsWith("#")) {
                const hex = color.slice(1);
                if (/^[0-9a-f]{3}$/.test(hex) || /^[0-9a-f]{6}$/.test(hex)) {
                    const x = hex.length === 3
                        ? hex.split("").map(c => parseInt(c + c, 16))
                        : [0, 2, 4].map(i => parseInt(hex.slice(i, i + 2), 16));
                    dark = (0.2126 * x[0] + 0.7152 * x[1] + 0.0722 * x[2]) < 135;
                }
            } else if (/^rgba?\(/.test(color)) {
                const parts = color.match(/[\d.]+%?/g) || [];
                const rgb = parts.slice(0, 3).map(v =>
                    v.endsWith("%") ? parseFloat(v) * 2.55 : parseFloat(v)
                );
                if (rgb.length === 3 && rgb.every(Number.isFinite)) {
                    dark = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) < 135;
                }
            } else if (color.startsWith("oklch(")) {
                const lightness = parseFloat(color.slice(6));
                if (Number.isFinite(lightness)) dark = lightness < 0.6;
            }
            if (dark !== null) {
                const root = document.documentElement.style;
                root.setProperty("--weapon-trend-label-color", dark ? "#D7EAFF" : "#1456AE");
                root.setProperty("--weapon-trend-label-halo", dark ? "#0E1117" : "#FFFFFF");
            }
        }
        // 테마 변경 후에도 자동 갱신
        syncDonutTheme();
        const donutThemeTimer = window.setInterval(
            syncDonutTheme,
            300
        );
        function onDocumentClick(event) {
            const target = event.target;
            if (!(target instanceof Element)) return;
            // 도넛 조각 클릭만 처리
            const slice = target.closest("g.slice");
            if (!slice) return;
            // 무기 도넛인지 확인
            const container = slice.closest(
                ".st-key-weapon_tiv_chart"
            );
            if (!container) return;
            const plot = slice.closest(".js-plotly-plot");
            if (!plot) return;
            // 실제 클릭한 조각의 데이터
            const datum = slice.__data__
                ?? slice.querySelector("path")?.__data__
                ?? null;
            const ids = data?.ids ?? [];
            const labels = data?.labels ?? [];
            let index = -1;
            if (typeof datum?.id === "string") {
                index = ids.indexOf(datum.id);
            }
            if (
                index < 0 &&
                typeof datum?.label === "string"
            ) {
                index = labels.indexOf(datum.label);
            }
            if (
                index < 0 &&
                Number.isInteger(datum?.i)
            ) {
                index = datum.i;
            }
            if (index < 0) {
                index = Array.from(
                    plot.querySelectorAll("g.slice")
                ).indexOf(slice);
            }
            if (
                index >= 0 &&
                index < ids.length
            ) {
                setTriggerValue("weapon", ids[index]);
            }
        }
        // 현재 클릭 이벤트 하나만 등록
        window[bridgeKey] = onDocumentClick;
        document.addEventListener(
            "click",
            onDocumentClick,
            true
        );
        // 컴포넌트가 제거될 때 이벤트 정리
        // 이전 인스턴스가 새 인스턴스의 이벤트를 지우지 않도록 보호
        return () => {
            window.clearInterval(donutThemeTimer);
            if (window[bridgeKey] === onDocumentClick) {
                document.removeEventListener(
                    "click",
                    onDocumentClick,
                    true
                );
                delete window[bridgeKey];
            }
        };
    }
    """,
)

# ============================================================
# 3. 도넛·TOP 5·TOP 10·TOP 3 계산 및 출력 함수
# ============================================================

# 반복되는 국가/순위/무기 카드 HTML은 위의 공통 함수와 CSS를 재사용
# 3-1. 선택된 무기그룹의 국가별 최근 5년 누적 수입 TIV
# TOP 5와 TOP 10에 동일한 집계 데이터를 전달
def _country_tiv(selected: str | None) -> pd.Series:
    return (tiv_5years.loc[tiv_5years["weapon_type_group_en"].eq(selected)]
            .groupby("recipient_iso_a3")["tiv_per_year"].sum().sort_values(ascending=False))

# 3-2. 도넛 차트 출력
#   - TIV 내림차순 시계방향, 10개 그룹 색상 중복 없음
#   - 선택 전후 도넛 크기 일정 / 선택 조각만 12px 바깥 이동
#   - 비중 3% 이상인 조각에만 숫자 표시
#   - 가운데 선택 무기명·비중과 하단 2줄 범례 표시

def _render_donut(selected: str | None) -> None:
    if total_tiv <= 0:
        st.warning("선택한 기간에 TIV 데이터가 없습니다.")
        return
    # 현재 그룹별 TIV 수치, 화면에 표시할 한국어 라벨, 선택 그룹 비중
    values = tiv_by_group.tolist()
    labels = [group_map[group] for group in group_list]
    percent = (tiv_by_group.loc[selected] / total_tiv * 100) if selected is not None else 0
    # pull=0으로 차트 반지름 고정하고 CSS로 선택 조각만 12px 이동
    if selected is not None:
        index = group_list.index(selected)
        center_angle = (sum(values[:index]) + values[index] / 2) / total_tiv * 360 - 90
        x = 12 * math.cos(math.radians(center_angle))
        y = 12 * math.sin(math.radians(center_angle))
        st.markdown(f"""<style>
        .st-key-weapon_tiv_chart .js-plotly-plot g.slice:nth-of-type({index + 1}) {{
            transform:translate({x:.2f}px,{y:.2f}px);
        }}</style>""", unsafe_allow_html=True)
    # 3% 미만인 매우 작은 조각은 차트 위 비중 라벨 생략
    pie_text = [f"{v / total_tiv * 100:.1f}%" if v / total_tiv >= .03 else "" for v in values]
    # 실제 Plotly Pie는 pull을 전부 0으로 고정하여 크기 변동 방지
    fig = go.Figure(go.Pie(
        labels=labels, values=values, ids=group_list, hole=.52,
        sort=False, direction="clockwise", rotation=0, pull=[0] * len(group_list),
        marker=dict(colors=PIE_COLORS, line=dict(
            color="#0E1117" if st.context.theme.type == "dark" else "#FFFFFF", width=2)),
        text=pie_text, textinfo="text", textposition="outside",
        textfont=dict(size=12), outsidetextfont=dict(size=12), automargin=True,
        showlegend=False, domain=dict(x=[.07, .93], y=[.07, .93]),
        hovertemplate="<b>%{label}</b><br>수입 TIV: %{value:,.2f}<br>비중: %{percent}<extra></extra>",
    ))
    # 도넛 중앙 문구: 미선택 안내 또는 선택 그룹의 비중
    if selected is None:
        center = "전체 무기<br><b>그룹을 선택하세요</b>"
    else:
        label = group_map[selected]
        center = f"{html.escape(label if len(label) <= 9 else '선택 무기')}<br><b>{percent:.1f}%</b>"
    fig.add_annotation(x=.5, y=.5, xref="paper", yref="paper", text=center,
                       showarrow=False, align="center", font=dict(size=14))
    fig.update_layout(
        height=320, uirevision="weapon_pie_stable", font=dict(size=12),
        margin=dict(l=8, r=8, t=10, b=10), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    # Streamlit 기본 테마 반영 및 도넛 조각 클릭값 연결
    st.plotly_chart(fig, use_container_width=True, theme="streamlit",
                    key="weapon_tiv_chart", config={"displayModeBar": False})
    donut_click_bridge(key="weapon_donut_click", data={"ids": group_list, "labels": labels},
                       on_weapon_change=on_donut_piece_click)
    # 범례: 4열 격자, 긴 이름은 … + 마우스 오버 시 전체 이름, 현재 선택한 그룹만 굵게 표시
    legend = []
    for i, group in enumerate(group_list):
        weight = 700 if selected == group else 400
        name = html.escape(group_map[group], quote=True)
        legend.append(
            f'<div class="weapon-legend-item" title="{name}"><span class="weapon-legend-dot" '
            f'style="background:{PIE_COLORS[i]}"></span><span class="weapon-legend-label" '
            f'style="font-weight:{weight}">{name}</span></div>'
        )
    st.html('<div class="weapon-donut-legend">' + "".join(legend) + "</div>")

# 3-3. 최대 수입국 TOP 5 HTML 출력
#   - 국기, 순위 아이콘, 국가별 수입 TIV, 전체에서 차지하는 비중
#   - 막대 길이는 전체 100% 대비 실제 비중으로 계산

def _render_top5(countries: pd.Series) -> None:
    top5 = countries.head(5)
    total = countries.sum()
    head = ('<div class="weapon-table-header weapon-top5-cols">'
            '<span>순위</span><span>국가</span><span>수입 TIV</span><span>비중</span></div>')
    rows = []
    # 상위 5개 국가를 HTML 행으로 생성
    for rank, (code, value) in enumerate(top5.items(), 1):
        # 국가별 비중은 선택 그룹 전체 수입 TIV 대비 비율
        share = value / total * 100 if total > 0 else 0
        bar = share
        country = html.escape(str(country_name_map.get(code, code)))
        rows.append(f'''
        <div class="weapon-top5-row weapon-top5-cols">
          {_rank_html(rank, size=30)}
          <span class="weapon-country-cell">{_flag_html(code, 27)}{country}</span>
          <span style="font-weight:700">{value:,.0f}</span>
          <span class="weapon-country-share"><span>{share:.1f}%</span>
            <span class="weapon-share-track"><span class="weapon-share-fill" style="width:{bar:.1f}%"></span></span>
          </span>
        </div>''')
    st.html(head + "".join(rows))

# 3-4. 수출 추천 TOP 10 HTML 출력
#   - src/dashboard_score/dashboard_score_weapon.py 결과 (components/export_score.py)
#   - rank → 순위, iso_a3 → 국기+국가명, final_score → 추천 점수(0~100점, 막대 길이)

def _render_top10(countries: list[dict]) -> None:
    head = ('<div class="weapon-recommend-list"><div class="weapon-table-header weapon-top10-cols">'
            '<span>순위</span><span>국가</span><span>추천 점수</span></div>')
    rows = []
    for item in countries:
        code = item["iso_a3"]
        rank = item["rank"]
        score = item["suitability"]
        country = html.escape(str(country_name_map.get(code, item["country"])))
        rank_html = (_rank_html(rank, size=28) if rank in RANK_IMAGES
                     else f'<span class="weapon-rank-fallback" style="width:28px;height:28px">{rank}</span>')
        rows.append(f'''
        <div class="weapon-recommend-row weapon-top10-cols">
          <span class="weapon-top10-rank">{rank_html}</span>
          <span class="weapon-country-cell">{_flag_html(code, 25)}
            <span style="min-width:0;overflow-wrap:anywhere">{country}</span></span>
          <span class="weapon-top10-empty weapon-top10-score">
            <span>{score:.1f}<small>점</small></span>
            <span class="weapon-share-track"><span class="weapon-share-fill" style="width:{max(0.0, min(score, 100.0)):.1f}%"></span></span>
          </span>
        </div>''')
    st.html(head + "".join(rows) + "</div>")

# 3-5. 전처리 완료된 무기그룹별 TOP 3 조회
def _get_top3(group: str, file_path: Path) -> pd.Series:
    data = _load_top3_orders(
        str(file_path),
        file_path.stat().st_mtime_ns
    )

    return (
        data.loc[data["weapon_type_group_en"].eq(group)]
        .sort_values("rank")
        .set_index("weapon")["tiv_order"]
    )

# 3-6. 무기체계 TOP 3 카드 HTML 출력
#   - 항상 정사각형 이미지 틀, 사진 전체 표시(object-fit:contain)
#   - 순위 메달, 모델명, 설명, 최근 5년 주문 TIV 표시
#   - 데이터의 무기명과 파일명을 분리하므로 CSV 이름은 변경하지 않음

def _render_top3(top3: pd.Series, group: str) -> None:
    cards = []
    for rank, (weapon, amount) in enumerate(top3.items(), 1):
        name = str(weapon)
        # 무기명은 영문 모델명 그대로 표시
        display = name
        # 등록된 30종 설명 우선 사용, 없는 무기는 기본 안내 표시
        description = WEAPON_DESCRIPTIONS.get((group, name.strip()), "무기체계 상세 설명 준비 중")
        cards.append(f'''
        <div class="weapon-top3-card">
          <div class="weapon-photo">{get_weapon_image_html(name, group)}</div>
          <div class="weapon-top3-info">
              <div class="weapon-top3-name">
                  <span class="weapon-top3-medal">{_rank_html(rank, size=24, shadow=True)}</span>
                  <span>{html.escape(display)}</span>
              </div>
            <div class="weapon-top3-description">{html.escape(description)}</div>
            <div class="weapon-top3-tiv">최근 5년(2021~2025) 주문 TIV:
              <strong>{amount:,.2f}</strong></div>
          </div>
        </div>''')
    st.html("".join(cards))

# ============================================================
# 4. 수입 추이 vs 한국 수출: Plotly 그래프 함수
# ============================================================

# 축 생략 여부에 따라 막대 구성만 분기하고, 한국 수출선은 공통 함수 사용
# 4-1. 한국 수출 TIV 꺾은선·마커·숫자 라벨 공통 생성
# Y축 중간 생략 시에는 값이 큰 라벨이 겹치지 않도록 위/아래 배치
def _add_korea_line(fig: go.Figure, years: list[str], values: list[float],
                    color: str, axis_broken: bool) -> None:
    peak = max(values + [0.0])
    positions = (["bottom center" if v >= peak * .65 else "top center" for v in values]
                 if axis_broken else "top center")
    fig.add_trace(go.Scatter(
        x=years, y=values, name="한국 수출 TIV", mode="lines+markers+text",
        line=dict(color="#2878E5", width=3.2),
        marker=dict(size=10, color="#2878E5", line=dict(color="white", width=1.5)),
        text=[f"{v:,.0f}" if v > 0 else "" for v in values],
        textposition=positions, textfont=dict(size=13, color=color), cliponaxis=False,
        hovertemplate="<b>%{x}년</b><br>한국 수출 TIV: %{y:,.2f}<extra></extra>",
    ))

# 4-2. 글로벌 수입이 한국 수출보다 매우 큰 경우 Y축 중간 생략
#   - 한국 수출선이 바닥에 눌려 보이지 않도록 하단 영역 별도 확보
#   - 생략구간 상단 수입 막대를 환산해 표시하며 hover는 원래 TIV 유지
#   - 곡선 2개로 축 중간 생략 표시, 눈금은 실제 TIV 숫자로 재표시

def _add_axis_break(fig: go.Figure, years: list[str], imports: list[float],
                    korea: list[float], label_color: str) -> None:
    max_import = max(imports + [0.0])
    max_korea = max(korea + [0.0])
    positive = [v for v in imports if v > 0]
    # 한국 수출값이 들어갈 아래쪽 Y축 영역
    lower_end = max(2.0, max_korea * 1.60)
    # 상단 막대는 실제 데이터가 시작되는 지점부터 다시 표시
    upper_imports = [v for v in positive if v > lower_end]
    upper_start = max(lower_end * 1.02, min(upper_imports, default=max_import) * .98)
    upper_start = min(upper_start, max_import * .995)
    upper_end, axis_unit = _axis_top(max_import)
    upper_display_size = lower_end * 2.1
    # 상단 실제 TIV를 표시 공간의 픽셀 높이로 변환하는 비율
    upper_scale = upper_display_size / max(upper_end - upper_start, .001)
    # 글로벌 수입 막대 아래 구간 (0 ~ lower_end)
    fig.add_trace(go.Bar(
        x=years, y=[min(v, lower_end) for v in imports], width=.52,
        marker_color="rgba(134,186,248,0.30)", name="글로벌 수입 TIV",
        legendgroup="global", showlegend=False, customdata=imports,
        hovertemplate="<b>%{x}년</b><br>글로벌 수입 TIV: %{customdata:,.2f}<extra></extra>",
    ))
    # 글로벌 수입 막대 위 구간 (실제 TIV 값은 hover/customdata로 보존)
    fig.add_trace(go.Bar(
        x=years, y=[max(0.0, v - upper_start) * upper_scale for v in imports],
        base=lower_end, width=.52, marker_color="#86BAF8", name="글로벌 수입 TIV",
        legendgroup="global", showlegend=True, customdata=imports,
        text=[f"{v:,.0f}" if v > upper_start else "" for v in imports],
        textposition="outside", textfont=dict(size=11), cliponaxis=False,
        hovertemplate="<b>%{x}년</b><br>글로벌 수입 TIV: %{customdata:,.2f}<extra></extra>",
    ))
    _add_korea_line(fig, years, korea, label_color, axis_broken=True)
    # 2줄 물결선으로 Y축 중간 생략 구간을 시각적으로 표시
    amplitude, separation, steps = lower_end * .026, lower_end * .05, 27
    for offset in (-separation, separation):
        wave_y = lower_end + offset
        segments = [f"M 0,{wave_y:.6f}"]
        for i in range(steps):
            center = (i + .5) / steps
            end = (i + 1) / steps
            control = wave_y + (amplitude if i % 2 == 0 else -amplitude)
            segments.append(f"Q {center:.5f},{control:.6f} {end:.5f},{wave_y:.6f}")
        fig.add_shape(type="path", path=" ".join(segments), xref="paper", yref="y",
                      line=dict(color="#D1D5DB", width=2), layer="below")
    # 표시 가능한 최대 4개 상단 눈금 + 원점(0)
    # 눈금 숫자는 환산된 막대 높이가 아니라 실제 TIV 값
    upper_tick_start = int(math.ceil(upper_start / axis_unit) * axis_unit)
    all_ticks = list(range(upper_tick_start, upper_end + 1, axis_unit))
    if not all_ticks or all_ticks[-1] != upper_end:
        all_ticks.append(upper_end)
    interval = max(1, math.ceil((len(all_ticks) - 1) / 3))
    upper_ticks = all_ticks[::interval]
    if upper_ticks[-1] != upper_end:
        upper_ticks.append(upper_end)
    fig.update_yaxes(
        title=None, range=[0, lower_end + upper_display_size * 1.07],
        tickmode="array", tickvals=[0] + [lower_end + (v - upper_start) * upper_scale for v in upper_ticks],
        ticktext=["0"] + [f"{v:,.0f}" for v in upper_ticks],
        gridcolor="rgba(128,128,128,0.13)", zeroline=False, fixedrange=True,
    )

# 4-3. 글로벌 수입과 한국 수출이 비슷할 때는 Y축을 생략하지 않음
#   - 정상 Y축에 글로벌 수입 막대 + 한국 수출선 모두 표시

def _add_normal_axis(fig: go.Figure, years: list[str], imports: list[float],
                     korea: list[float], label_color: str) -> None:
    fig.add_trace(go.Bar(
        x=years, y=imports, width=.52, marker_color="#86BAF8", name="글로벌 수입 TIV",
        text=[f"{v:,.0f}" if v > 0 else "" for v in imports],
        textposition="outside", textfont=dict(size=11), cliponaxis=False,
        hovertemplate="<b>%{x}년</b><br>글로벌 수입 TIV: %{y:,.2f}<extra></extra>",
    ))
    _add_korea_line(fig, years, korea, label_color, axis_broken=False)
    # 최대 5개 정도의 가독성 좋은 Y축 눈금 설정
    top, unit = _axis_top(max(imports + korea + [0.0]))
    step = max(unit, math.ceil(top / (4 * unit)) * unit)
    ticks = list(range(0, top + 1, step))
    if ticks[-1] != top:
        ticks.append(top)
    fig.update_yaxes(
        title=None, range=[0, top * 1.06], tickmode="array", tickvals=ticks,
        ticktext=[f"{v:,.0f}" for v in ticks],
        gridcolor="rgba(128,128,128,0.15)", zeroline=False, fixedrange=True,
    )

# 4-4. 선택 그룹의 글로벌 수입 vs 한국 수출 연도별 그래프 생성
# 2021~2025년 전체 연도를 표시하고 없는 연도의 합계는 0으로 채움

def _trend_chart(group: str) -> go.Figure:
    selected = tiv_5years.loc[tiv_5years["weapon_type_group_en"].eq(group)]
    global_yearly = selected.groupby("year")["tiv_per_year"].sum().reindex(YEARS, fill_value=0)
    # 한국 수출은 전체 무기그룹 거래 중 supplier_iso_a3 == 'KOR'만 추출
    korea_yearly = (selected.loc[selected["supplier_iso_a3"].eq("KOR")]
                    .groupby("year")["tiv_per_year"].sum().reindex(YEARS, fill_value=0))
    year_labels = [str(year) for year in YEARS]
    imports = [float(v) for v in global_yearly.values]
    korea = [float(v) for v in korea_yearly.values]
    peak_import = max(imports + [0.0])
    peak_korea = max(korea + [0.0])
    # 글로벌 최대 수입이 한국 최대 수출의 2배 이상일 때 중간축 생략
    use_break = bool([v for v in imports if v > 0]) and peak_import >= max(2.0, peak_korea * 2.0)
    label_color = "#CFE6FF" if st.context.theme.type == "dark" else "#1456AE"
    fig = go.Figure()
    if use_break:
        _add_axis_break(fig, year_labels, imports, korea, label_color)
    else:
        _add_normal_axis(fig, year_labels, imports, korea, label_color)
    # x축은 실제 수치축이 아닌 문자열 5개(2021~2025)로 고정
    fig.update_xaxes(
        type="category", categoryorder="array", categoryarray=year_labels,
        tickmode="array", tickvals=year_labels, showgrid=False,
        tickfont=dict(size=12), fixedrange=True,
    )
    fig.update_layout(
        height=455, margin=dict(l=18, r=12, t=34, b=26),
        legend=dict(orientation="h", yanchor="bottom", y=1.075,
                    xanchor="center", x=.48, font=dict(size=11)),
        hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", barmode="overlay", showlegend=True,
    )
    # 축 생략 중일 때만 그래프 우측 상단 안내문 추가
    if use_break:
        fig.add_annotation(
            x=1.0, y=1.015, xref="paper", yref="paper", xanchor="right", yanchor="bottom",
            text="Y축 중간 생략값: <b>≈</b>", showarrow=False,
            font=dict(size=11, color="#A4B3C5"),
        )
    return fig

# ============================================================
# 5. 대시보드 5개 패널 배치 및 화면 출력
# ============================================================

# 왼쪽(도넛 + 무기체계 TOP 3) / 가운데(추천 TOP 10) / 오른쪽(추이 + 수입국 TOP 5)
# Streamlit 컨테이너 위치만 예약한 뒤 아래에서 순서대로 내용 채움
# 열 비율: 수입 비중 +5% / 수출 추천 TOP 10 기본 / 추이·TOP 5 −5% (기본 1:1:1 대비, 도넛은 높이 320px 기준이라 크기 그대로)
left_col, middle_col, right_col = st.columns([1.05, 1.0, 0.95], gap="medium")
with left_col:
    left_top_slot = st.container()
    left_bottom_slot = st.container()
with middle_col:
    middle_tall_slot = st.container()
with right_col:
    right_top_slot = st.container()
    right_bottom_slot = st.container()

# ============================================================
# 5-1. 왼쪽 위: 무기그룹별 글로벌 수입 비중 (도넛)
# ============================================================

# 드롭다운에서 선택하면 모든 패널이 동일한 그룹으로 즉시 갱신
with left_top_slot:
    with st.container(border=True, key="weapon_donut_panel"):
        # 시안 A: 아이콘+제목 → 부제(기간) → 무기 선택창(기존 크기 220px) → 도넛
        # 제목은 다른 패널과 같은 _panel_heading 사용 (아이콘 28px, 제목 19px)
        st.html(_panel_heading(
            "무기체계별 글로벌 수입 비중",
            "images/03_weapon_images/material-swords.png", 28, "🛡️",
            gap_bottom=2,
        ) + '<div class="weapon-donut-heading"><small>최근 5년(2021~2025) TIV</small></div>')
        # 영문 그룹코드를 내부 상태로 보관하고, 화면에는 한국어 그룹명 출력
        st.selectbox(
            "무기체계", options=group_list, index=None, key="weapon_select_radio",
            on_change=on_weapon_radio_change, format_func=lambda code: group_map[code],
            placeholder="무기체계 선택", label_visibility="collapsed", width=220,
        )
        selected_weapon = st.session_state.selected_weapon
        _render_donut(selected_weapon)

# 5-1-1. TOP 5와 TOP 10의 국가별 합계 계산은 1회만 실행해 재사용
country_tiv = _country_tiv(selected_weapon)

# ============================================================
# 5-2. 오른쪽 아래: 최대 수입국 TOP 5
# ============================================================

# 선택 그룹의 최근 5년 누적 TIV 상위 국가·비중 표시
with right_bottom_slot:
    with st.container(border=True, key="weapon_top5_panel"):
        st.html(_panel_heading(
            "최대 수입국 TOP 5", "images/03_weapon_images/material-flag.png",
            28, "🌍", aside="최근 5년(2021~2025) TIV 누적",
        ))
        if selected_weapon is None:
            st.info("무기체계를 선택하면 최대 수입국 TOP 5가 표시됩니다.")
        elif country_tiv.empty:
            st.warning("선택한 무기체계의 수입국 데이터가 없습니다.")
        else:
            _render_top5(country_tiv)

# ============================================================
# 5-3. 오른쪽 위: 글로벌 수입 추이 vs 한국 수출
# ============================================================

# 선택된 무기그룹의 2021~2025년 TIV 막대와 한국 수출선 비교
with right_top_slot:
    with st.container(border=True, key="weapon_trend_panel"):
        st.html(_panel_heading(
            "수입 추이 vs 한국 수출", "images/common/etc/material-monitoring.png",
            24, "📈", gap_bottom=2,
        ))
        if selected_weapon is None:
            st.info("무기체계를 선택하면 연도별 수입 및 한국 수출 추이가 표시됩니다.")
        elif tiv_5years.loc[tiv_5years["weapon_type_group_en"].eq(selected_weapon)].empty:
            st.warning("선택한 무기체계의 연도별 TIV 데이터가 없습니다.")
        else:
            st.plotly_chart(
                _trend_chart(selected_weapon), width="stretch", theme="streamlit",
                key="weapon_tiv_trend_chart", config={"displayModeBar": False},
            )

# ============================================================
# 5-4. 가운데: 수출 추천 TOP 10 국가
# ============================================================

# 선택한 무기 그룹의 2026년 수출 추천 국가 (dashboard_score_weapon.py: 6개 지표 × 무기체계별 CRITIC 가중치)
with middle_tall_slot:
    with st.container(border=True, key="weapon_recommend_tall"):
        st.html(_panel_heading(
            "수출 추천 TOP 10 국가", "images/common/etc/material-thumb_up.png", 25, "📋",
            tooltip="2021~2025년 데이터로 6개 지표(HHI·국방비·무기 수요·협력 관계·GPI·신용도)"
                    "를 0~100점으로 바꾸고, 무기체계별 CRITIC 가중치를 곱해 추천 점수를 계산합니다.",
        ))
        if selected_weapon is None:
            st.info("무기체계를 선택하면 수출 추천 TOP 10 국가가 표시됩니다.")
        else:
            try:
                recommend_countries = weapon_top_countries(selected_weapon, n=10)
                recommend_error = None
            except Exception as exc:   # 파일 없음·스크립트 오류
                recommend_countries, recommend_error = [], exc
            if recommend_error is not None:
                st.warning(f"추천 점수를 불러오지 못했습니다: {recommend_error}")
            elif not recommend_countries:
                st.warning("선택한 무기체계의 추천 결과가 없습니다.")
            else:
                _render_top10(recommend_countries)

# ============================================================
# 5-5. 왼쪽 아래: 무기체계 TOP 3
# ============================================================

# 무기그룹별 최근 5년 주문 TIV 합계 TOP 3을 이미지 카드로 표시
# 주문 TIV 자료는 data/processed/arms_trade_98_countries_order_2021_2025.csv 사용
with left_bottom_slot:
    with st.container(border=True, key="weapon_top3_panel"):
        st.html(_panel_heading(
            "주요 무기 TOP 3", "images/common/etc/material-star.png", 25, "⭐",
            tooltip="일부 이미지는 AI 생성 참고 자료입니다. 자세한 사항은 이미지 출처 페이지를 참고해 주세요."
        ))
        if selected_weapon is None:
            st.info("무기체계를 선택하면 주요 무기 TOP 3이 표시됩니다.")
        else:
            st.caption(f"{group_map.get(selected_weapon, selected_weapon)} · 최근 5년(2021~2025) 주문 TIV")
            # 주문 기준 TOP 3 자료: 기존 파일 경로 유지
            arms_path = BASE_DIR / "data/processed/arms_trade_98_countries_order_2021_2025.csv"
            if not arms_path.is_file():
                st.error("무기 거래 파일을 찾을 수 없습니다: data/processed/arms_trade_98_countries_order_2021_2025.csv")
            else:
                top3 = _get_top3(selected_weapon, arms_path)
                if len(top3) < 3:
                    st.warning(f"현재 거래 파일({arms_path.name})에서는 모델명 확인 기준 "
                               f"상위 {len(top3)}개만 조회됩니다. 전체 거래 CSV의 누락 여부를 확인하세요.")
                if top3.empty:
                    st.warning("선택한 무기체계의 최근 5년(2021~2025) 무기별 TIV 데이터가 없습니다.")
                else:
                    _render_top3(top3, selected_weapon)

# ============================================================
# 6. 다섯 패널의 시작 위치·하단 높이 자동 정렬
# ============================================================

# 고정 높이/내부 스크롤을 만들지 않고 실제 브라우저 DOM 높이를 측정
# 그룹 변경·차트 재그리기·창 크기 조절 시 다시 정렬
# 왼쪽 TOP 3 / 오른쪽 TOP 5 / 가운데 TOP 10의 최종 아래쪽 선을 맞춤
weapon_layout_equalizer = st.components.v2.component(
    name="weapon_layout_equalizer",
    html='<span aria-hidden="true" style="display:none"></span>', css="",
    # 도움말 말풍선 위치·색 보정 JS(공통)를 앞에 붙임 (01·02·04·05와 동일)
    js=HELP_TOOLTIP_JS + r"""    export default function () {
        let timeoutIds = [];
        let disposed = false;
        const selectors = {
            donut: ".st-key-weapon_donut_panel",
            trend: ".st-key-weapon_trend_panel",
            top3: ".st-key-weapon_top3_panel",
            top5: ".st-key-weapon_top5_panel",
            recommend: ".st-key-weapon_recommend_tall"
        };
        // 6-1. 이전 그룹에서 적용된 카드 최소 높이를 초기화
        function resetRows(panel, rowSelector) {
            if (!panel) return;
            panel.querySelectorAll(rowSelector).forEach(node => {
                node.style.minHeight = "";
            });
        }
        // 6-2. 부족한 패널 높이는 각 행에 균등 배분
        function stretchRows(panel, rowSelector, extraHeight) {
            const rows = Array.from(panel.querySelectorAll(rowSelector));
            if (rows.length === 0 || extraHeight < 1) return;
            const increase = extraHeight / rows.length;
            rows.forEach(node => {
                const naturalHeight = node.getBoundingClientRect().height;
                node.style.minHeight = `${naturalHeight + increase}px`;
            });
        }
        // 6-3. 현재 브라우저 패널의 실제 위치를 측정해 높이 보정
        function synchronize() {
            if (disposed) return;
            const els = {};
            for (const [key, selector] of Object.entries(selectors)) {
                els[key] = document.querySelector(selector);
                if (!els[key]) return;
            }
            // 그룹을 바꿔도 이전 그룹의 임시 간격을 누적하지 않음
            for (const panel of Object.values(els)) {
                panel.style.minHeight = "";
                panel.style.marginTop = "";
            }
            // 상단 두 박스의 이전 높이 보정 초기화
            for (const panel of [els.donut, els.trend]) {
                panel.style.paddingBottom = "";
            }
            resetRows(els.top3, ".weapon-top3-card");
            resetRows(els.top5, ".weapon-top5-row");
            resetRows(els.recommend, ".weapon-recommend-row");
            // 왼쪽 1번과 오른쪽 3번 상단 카드의 하단 높이 일치
            const donutBottom = els.donut.getBoundingClientRect().bottom;
            const trendBottom = els.trend.getBoundingClientRect().bottom;
            const shorterPanel = donutBottom < trendBottom
                ? els.donut
                : els.trend;
            const heightDifference = Math.abs(donutBottom - trendBottom);
            if (heightDifference > 1) {
                const currentPadding =
                    parseFloat(getComputedStyle(shorterPanel).paddingBottom) || 0;
                shorterPanel.style.paddingBottom =
                    `${currentPadding + heightDifference}px`;
            }
            // 높이 보정 이후 실제 하단 위치 재측정
            const firstRowBottom = Math.max(
                els.donut.getBoundingClientRect().bottom,
                els.trend.getBoundingClientRect().bottom
            );
            // TOP 3 / TOP 5 둘째 줄을 상단 카드 아래 같은 위치에 배치
            const rowGap = 16;
            for (const panel of [els.top3, els.top5]) {
                const missing = firstRowBottom + rowGap -
                    panel.getBoundingClientRect().top;
                if (missing > 0) panel.style.marginTop = `${missing}px`;
            }
            // 세 패널의 최종 하단을 맞추기 위해 실측 높이 차이만큼 행 높이 배분
            // 실제 렌더링 결과를 기준으로 반복 보정합니다.
            // CSS grid/flex의 자동 높이 재계산 때문에 한 번만 보정하면
            // 화면 배율에 따라 몇 px 차이가 남는 문제를 방지합니다.
            for (let pass = 0; pass < 4; pass++) {
                const finalBottom = Math.max(
                    els.top3.getBoundingClientRect().bottom,
                    els.top5.getBoundingClientRect().bottom,
                    els.recommend.getBoundingClientRect().bottom
                );
                const delta3 = finalBottom - els.top3.getBoundingClientRect().bottom;
                const delta5 = finalBottom - els.top5.getBoundingClientRect().bottom;
                const delta10 = finalBottom - els.recommend.getBoundingClientRect().bottom;
                if (Math.max(delta3, delta5, delta10) < 0.6) break;
                stretchRows(els.top3, ".weapon-top3-card", delta3);
                stretchRows(els.top5, ".weapon-top5-row", delta5);
                stretchRows(els.recommend, ".weapon-recommend-row", delta10);
            }
        }
        let pending = null;
        // 6-4. 화면이 바뀌면 다음 그리기 직전(requestAnimationFrame)에 바로 재측정
        //      (예전 180ms 지연 → 표가 늘어나는 모습이 보이던 문제 개선)
        function schedule() {
            if (disposed || pending !== null) return;
            pending = requestAnimationFrame(() => {
                pending = null;
                synchronize();
            });
        }
        // 6-5. Streamlit이 차트와 표를 다시 그린 뒤에도 높이 재측정
        const observer = new MutationObserver(schedule);
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        // 초기 정렬
        schedule();
        // 차트 렌더링 이후 추가 정렬
        timeoutIds.push(setTimeout(synchronize, 700));
        timeoutIds.push(setTimeout(synchronize, 1600));
        // 화면 크기가 바뀌어도 재정렬
        window.addEventListener("resize", schedule);
        return () => {
            disposed = true;
            observer.disconnect();
            if (pending !== null) {
                cancelAnimationFrame(pending);
            }
            for (const id of timeoutIds) {
                clearTimeout(id);
            }
            window.removeEventListener("resize", schedule);
        };
    }
    """,
)
weapon_layout_equalizer(key="weapon_layout_equalizer")
