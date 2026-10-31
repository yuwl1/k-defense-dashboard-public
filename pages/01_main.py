import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import base64
from pathlib import Path
from html import escape

from components.header import render_header
from components.icons import mask_icon_html   # 검은 아이콘 → 테마 글자색
# common_ui.py를 고치면 Streamlit을 다시 시작하지 않아도 새로고침만으로 반영되도록,
# 파일 수정 시각이 바뀌었을 때만 다시 불러옴 (바뀌지 않았으면 그대로 사용)
import importlib
import components.common_ui as _common_ui
if _common_ui.loaded_mtime() != _common_ui.LOADED_MTIME:
    _common_ui = importlib.reload(_common_ui)
from components.common_ui import (            # 03_weapon·04_country와 같은 공통 화면 요소
    TITLE_ICON_SIZE, TITLE_ICON_GAP, INFO_ICON_SIZE, info_icon_html,
    HELP_TOOLTIP_CSS, HELP_TOOLTIP_JS, help_icon_html,
    kpi_value_html,   # KPI 숫자 크게·단위 작게 (시안 5)
    flag_thumb_base64,   # 국기 썸네일 (속도 개선)
)
from components.company_weapons import COMPANIES, get_company_weapons
# export_score.py를 고치면 Streamlit을 다시 시작하지 않아도 새로고침만으로 반영
# (예전 버전이 메모리에 남아 ImportError가 나는 것 방지 — common_ui와 같은 방식)
import components.export_score as _export_score
if getattr(_export_score, "LOADED_MTIME", None) != _export_score.Path(_export_score.__file__).stat().st_mtime_ns:
    _export_score = importlib.reload(_export_score)
from components.export_score import top_countries   # dashboard_score.py 결과 (02_company와 공통)

# ============================================================
# 공통 상단 헤더
# ============================================================

render_header(
    title="메인 대시보드",
    description=(
        "글로벌 방산시장 핵심 지표와 기업별 추천 현황을 한눈에 확인합니다."
    ),
    page_file=__file__
)

# =========================================================
# 1. 기본 설정
# =========================================================

# Streamlit 파일이 pages 폴더에 있어도 프로젝트 루트 기준
# images / data 폴더를 사용할 수 있도록 설정
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = (
    CURRENT_DIR.parent
    if CURRENT_DIR.name == "pages"
    else CURRENT_DIR
)

DATA_DIR = ROOT_DIR / "data"
DATA_FOLDERS = [
    DATA_DIR / "processed",
    DATA_DIR / "mapping",
]

IMAGE_DIR = ROOT_DIR / "images"
MAIN_ICON_DIR = IMAGE_DIR / "01_main_images"      # 메인 화면 아이콘 (Material Symbols)

# 아이콘 크기 (px)
# 카드 제목 아이콘 크기(28px)·간격(15px), 정보 아이콘(파란색 18px)은 components/common_ui.py에서 공통 관리
ICON_OPACITY = 0.6          # 아이콘 진하기: 글자색(검정/흰색)을 이 비율로 흐리게 → 회색으로 보임 (1 = 원래 색)
DELTA_ICON_SIZE = 16        # 증감 표시(상승·하락) 아이콘

# 아이콘 색상: 01_main_images의 검은 아이콘을 components/icons.py의 mask_icon_html로 그려
# 다른 페이지와 같이 화면 글자색(밝은 모드 검정, 어두운 모드 흰색)을 자동으로 따라감

# 기업명 칸 최대 너비 (px) - 로고 이미지는 상표권 보호를 위해 사용하지 않고 기업명 텍스트로 표시
NAME_COL_WIDTH = 230

# 국기 이미지 폴더 (03_weapon.py는 images/common, 02_company.py는 images/flags 사용)
# 두 폴더와 대문자·소문자 파일명(USA.png / usa.png)을 모두 찾음
FLAG_IMAGE_DIRS = [
    IMAGE_DIR / "common" / "country",
]

# 분석 기간
FIRST_YEAR = 2016
LATEST_YEAR = 2025
RECENT_YEARS = list(range(LATEST_YEAR - 4, LATEST_YEAR + 1))     # 2021~2025
PREVIOUS_YEARS = list(range(LATEST_YEAR - 9, LATEST_YEAR - 4))   # 2016~2020

# 기간 표기 통일: "최근 5년(2021~2025)" / 수치는 "TIV 14,895"
RECENT_LABEL = f"최근 5년({RECENT_YEARS[0]}~{LATEST_YEAR})"
TEN_YEAR_LABEL = f"최근 10년({FIRST_YEAR}~{LATEST_YEAR})"

# 분석 제외국: 기준국(한국), 북한, 대러 수출통제 대상
EXCLUDED_ISO = {"KOR", "PRK"}
RESTRICTED_ISO = {"RUS", "BLR"}

# 기업명: 코드 → components/company_weapons.py의 COMPANIES 사용

# 기업별 설정
# - data_name: korea_weapon_data.csv의 company 값
# - weapon_groups: weapon_type_10group.csv의 weapon_type_group_en (후보국 계산용)
COMPANY_INFO = {
    "한화에어로스페이스": {
        "data_name": "Hanwha Aerospace",
        "weapon_groups": ["artillery", "armoured_vehicles"],
    },
    "한화오션": {
        "data_name": "Hanwha Ocean",
        "weapon_groups": ["ships", "naval_weapons"],
    },
    "현대로템": {
        "data_name": "Hyundai Rotem",
        "weapon_groups": ["armoured_vehicles"],
    },
    "HD현대중공업": {
        "data_name": "HD Hyundai Heavy Industries",
        "weapon_groups": ["ships", "naval_weapons"],
    },
    "LIG D&A": {
        "data_name": "LIG Nex1",      # 데이터에는 옛 사명으로 기록됨
        "weapon_groups": [
            "missiles_guided_weapons",
            "air_defence_systems",
            "sensors_isr_satellites",
        ],
    },
    "한국항공우주산업(KAI)": {
        "data_name": "KAI",
        "weapon_groups": ["aircraft_uavs"],
    },
}

# 기업별 주요 품목 개수 (korea_weapon_data.csv 기준, load_company_products에서 사용)
PRODUCT_COUNT = 3

# 주요 무기체계 표시 개수 (주요 → 보조 순서) - None이면 개수 제한 없이 전부 표시
WEAPON_GROUP_COUNT = None

# 도넛 차트에 따로 표시할 분류 수 (나머지는 '기타')
DONUT_TOP_N = 5

# 무기 그룹별 색상 10개 (03_weapon.py의 pie_colors와 동일)
# 최근 5년 TIV 내림차순 순서대로 적용 → 03_weapon.py 도넛과 같은 그룹이 같은 색
WEAPON_COLORS = [
    "#1456AE",
    "#358DEF",
    "#32BDA0",
    "#FFC765",
    "#9274DC",
    "#F07869",
    "#59B85A",
    "#D49352",
    "#38B6CF",
    "#8290A8",
]
OTHER_COLOR = "#B8C2D3"     # '기타' 색상

# 1920 x 1080 화면 기준 높이(px) — 한 화면에 스크롤 없이 들어오도록 설정
# 세로 배분(브라우저 표시 영역 약 880px 기준):
#   위 여백 58 + 헤더 100 + KPI 228 + 아래 카드 450 + 사이 간격 ≈ 890
KPI_CARD_HEIGHT = 228       # KPI 카드 4개
BOTTOM_CARD_HEIGHT = 450    # 기업별 후보국 표 / 무기 수입 규모
KPI_BODY_HEIGHT = 150       # KPI 카드 본문(수치 영역) 높이
HEADER_GAP_ADJUST = -30     # 이 페이지에서만 헤더 아래 간격 조절 (음수 = 위로 당김, px)
SPARK_OFFSET_Y = -20        # KPI 막대그래프 세로 위치 (음수 = 아래로 이동, px)
TABLE_HEIGHT_OFFSET = 100    # 기업 표: 카드 높이에서 제목·여백을 뺀 값 (표가 넘치면 키우기)
DONUT_HEIGHT = 160
MAP_HEIGHT = 300
MAP_CENTER_LON = 127.8      # 세계지도 가운데 경도 (대한민국 중심, 0이면 유럽 중심 기본 지도)
MAP_CARD_EXTRA = 140        # 지도 카드의 제목줄 + 범례 + 안쪽 여백 높이
BOTTOM_CARD_HEIGHT = MAP_HEIGHT + MAP_CARD_EXTRA   # 기업 표 / 지도 카드 공통 높이

# 세계지도 경계선 파일(topojson) 위치
# 1) static/topojson/world_110m.json 이 있으면 로컬 파일 사용 (인터넷 차단 환경)
# 2) 없으면 jsDelivr CDN 사용 (Plotly 기본 CDN이 막힌 환경 대비)
LOCAL_TOPOJSON = ROOT_DIR / "static" / "topojson" / "world_110m.json"
TOPOJSON_URL = (
    "/app/static/topojson/"
    if LOCAL_TOPOJSON.is_file()
    else "https://cdn.jsdelivr.net/npm/plotly.js@2.35.2/dist/topojson/"
)

# 무기 수입 규모 지도: 원 크기 구간
BUBBLE_BINS = [
    (0, 1000, "1,000 미만", 10),
    (1000, 5000, "1,000 - 5,000", 22),
    (5000, float("inf"), "5,000 이상", 38),
]


# =========================================================
# 2. 데이터 불러오기
# =========================================================

def find_data_file(file_name):
    """data/processed, data/mapping 순서로 파일을 찾음"""
    for folder in DATA_FOLDERS:
        path = folder / file_name
        if path.is_file():
            return path

    raise FileNotFoundError(
        f"{file_name} 파일을 찾지 못했습니다: "
        f"{', '.join(str(f) for f in DATA_FOLDERS)}"
    )


@st.cache_data
def load_data(file_name):
    return pd.read_csv(
        find_data_file(file_name),
        encoding="utf-8-sig"
    )


@st.cache_data
def load_master():
    """국가 마스터: iso_a3 -> 한글 국가명"""
    master = load_data("country_map_master.csv")

    master["is_target"] = (
        ~master["iso_a3"].isin(EXCLUDED_ISO)
    )

    return master


@st.cache_data
def load_milex():
    """국방비(USD), GDP 대비 비중 / 0은 결측 처리"""
    milex = load_data("military_expenditure.csv").rename(columns={
        "military_expenditure_usd": "milex_usd",
        "military_expenditure_gdp_pct": "milex_gdp_pct",
    })

    milex[["milex_usd", "milex_gdp_pct"]] = (
        milex[["milex_usd", "milex_gdp_pct"]].replace(0, np.nan)
    )

    return milex


@st.cache_data
def load_tiv():
    """도입국 × 연도 × 공급국 × 무기분류별 인도 TIV"""
    tiv = load_data("tiv_delivery_yearly.csv").rename(columns={
        "recipient_iso_a3": "recipient",
        "supplier_iso_a3": "supplier",
        "weapon_type_group_en": "group",
        "tiv_per_year": "tiv",
    })

    tiv["year"] = tiv["year"].astype(int)

    return tiv


@st.cache_data
def load_tiv_weapon_group():
    """도입국 × 연도별 무기분류 TIV (tiv_weapon_group.csv, 03_weapon과 같은 원천)
    가로형(<분류>_tiv 열 10개)을 세로형(recipient, year, group, tiv)으로 변환"""
    wide = load_data("tiv_weapon_group.csv")
    value_columns = [c for c in wide.columns if c.endswith("_tiv")]
    long = wide.melt(
        id_vars=["recipient_iso_a3", "year"],
        value_vars=value_columns,
        var_name="group",
        value_name="tiv",
    ).rename(columns={"recipient_iso_a3": "recipient"})
    long["group"] = long["group"].str.removesuffix("_tiv")
    long["year"] = long["year"].astype(int)
    long["tiv"] = pd.to_numeric(long["tiv"], errors="coerce").fillna(0)
    return long


@st.cache_data
def load_weapon_groups():
    """weapon_type_10group.csv -> {영문 분류 코드: 한글 분류명}"""
    groups = load_data("weapon_type_10group.csv")
    groups = groups.drop_duplicates(subset="weapon_type_group_en")

    return dict(zip(
        groups["weapon_type_group_en"],
        groups["weapon_type_group"]
    ))


# =========================================================
# 2-1. 1920 x 1080 화면용 여백·글자 크기 조정
# =========================================================

st.markdown(
    """
    <style>
    /* 본문 너비 제한 없음 → 다른 페이지처럼 화면 너비에 맞춰 늘어남 */

    /* 메인 페이지에서만 헤더 아래 간격 줄이기
       (이 CSS는 메인 페이지에서만 들어가므로 다른 페이지 헤더에는 영향 없음) */
    .st-key-header_box {margin-bottom: __HEADER_GAP__px !important;}
    h4 {font-size: 17px !important; padding: 0 0 5px 0 !important;}
    hr {margin: 6px 0 !important;}

    /* 도넛 조각 사이 여백 = 현재 화면 배경색 (--app-bg는 아래 테마 동기화가 채움) */
    .st-key-kpi_weapon_group_chart g.slice path.surface {
        stroke: var(--app-bg, #ffffff) !important;
        stroke-width: 2px !important;
    }

    /* 기업 표: 표가 들어 있는 요소가 카드의 남은 높이를 모두 차지 → 행이 균등하게 늘어나 아래 여백 없음 */
    .st-key-company_card [data-testid="stElementContainer"]:has(.company-grid) {
        flex: 1 1 auto !important;
        min-height: 0;
        display: flex;
        flex-direction: column;
    }
    .st-key-company_card [data-testid="stElementContainer"]:has(.company-grid) > div,
    .st-key-company_card [data-testid="stHtml"]:has(.company-grid) {
        flex: 1 1 auto;
        height: 100%;
    }

    /* 지도 위 국가명 글씨 = 현재 테마 글씨색 */
    .st-key-main_tiv_bubble_map g.textpoint text {
        fill: var(--app-text, #0f2747) !important;
    }
    
    /* 지도 아래 TIV 규모 범례를 위로 이동 */
    .st-key-main_tiv_bubble_map {
        margin-bottom: -40px !important;
    }
    </style>
    """.replace("__HEADER_GAP__", str(HEADER_GAP_ADJUST)) + HELP_TOOLTIP_CSS,   # 도움말 말풍선 공통 CSS
    unsafe_allow_html=True
)


# =========================================================
# 2-2. 밝은/어두운 테마 실시간 동기화
# =========================================================
# 브라우저에서 현재 화면의 배경색·글씨색을 읽어 CSS 변수(--app-bg, --app-text)로 저장.
# 테마를 바꾸면 페이지를 다시 실행하지 않아도 0.5초 안에 도넛 여백·지도 글씨색이 바뀜.
# (03_weapon.py와 같은 st.components.v2 사용, Streamlit 1.51 이상)

if hasattr(getattr(st, "components", None), "v2"):

    theme_sync = st.components.v2.component(
        name="main_theme_sync",
        html='<span class="main-theme-sync" aria-hidden="true"></span>',
        css=".main-theme-sync {display:block; width:0; height:0; overflow:hidden;}",
        # 도움말 말풍선 위치·색 보정 JS(공통)를 앞에 붙임
        js=HELP_TOOLTIP_JS + """
        export default function () {

            function applyTheme() {
                const app = document.querySelector(".stApp") || document.body;
                const style = getComputedStyle(app);

                let background = style.backgroundColor;
                if (!background || background === "rgba(0, 0, 0, 0)" || background === "transparent") {
                    background = getComputedStyle(document.body).backgroundColor;
                }

                const root = document.documentElement.style;
                root.setProperty("--app-bg", background);
                root.setProperty("--app-text", style.color);

                // 카드 제목 아이콘 색: 밝은 모드 = 검정, 어두운 모드 = 흰색 (배경 밝기로 판단)
                const rgb = (background.match(/[\\d.]+/g) || [255, 255, 255]).map(Number);
                const brightness = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2];
                root.setProperty("--main-icon-color", brightness < 128 ? "#ffffff" : "#000000");

            }

            applyTheme();

            // 이전 타이머 정리 후 하나만 동작
            const timerKey = "__kDefenseMainThemeSync";
            if (window[timerKey]) {
                clearInterval(window[timerKey]);
            }

            const timer = setInterval(applyTheme, 500);
            window[timerKey] = timer;

            return () => {
                if (window[timerKey] === timer) {
                    clearInterval(timer);
                    delete window[timerKey];
                }
            };
        }
        """,
    )

    theme_sync(key="main_theme_sync")

@st.cache_data
def load_company_products():
    """
    korea_weapon_data.csv → {기업 데이터명: [(짧은 이름, 전체 이름), ...]}
    신품(New) 수출 계약의 TIV 합계(tiv_order)가 큰 무기 순서
    전체 이름은 마우스를 올렸을 때 말풍선으로 표시
    """
    deals = load_data("korea_weapon_data.csv")
    deals = deals[deals["status"] == "New"].copy()

    # 무기명 앞부분만 사용: 첫 번째 띄어쓰기 앞까지
    # 예) "K-9 Thunder 155mm" → "K-9", "T-50 Golden Eagle" → "T-50"
    # 앞부분이 같은 무기(K-9 Thunder 155mm / K-9)는 하나로 합침
    deals["weapon_short"] = (
        deals["weapon"].astype(str).str.strip().str.split().str[0]
    )

    products = {}

    for company, group in deals.groupby("company"):
        top_shorts = (
            group.groupby("weapon_short")["tiv_order"]
            .sum()
            .sort_values(ascending=False)
            .head(PRODUCT_COUNT)
            .index
            .tolist()
        )

        items = []
        for short in top_shorts:
            # 같은 짧은 이름으로 합쳐진 전체 이름들 (계약 TIV 큰 순서)
            full_names = (
                group[group["weapon_short"] == short]
                .groupby("weapon")["tiv_order"]
                .sum()
                .sort_values(ascending=False)
                .index
                .tolist()
            )
            items.append((short, " / ".join(full_names)))

        products[company] = items

    return products


master = load_master()
name_ko = dict(zip(master["iso_a3"], master["country_name_ko"]))
targets = master.loc[master["is_target"], "iso_a3"].tolist()

milex = load_milex()
milex = milex[milex["iso_a3"].isin(targets)]

tiv = load_tiv()
tiv = tiv[tiv["recipient"].isin(targets)]
recent = tiv[tiv["year"].isin(RECENT_YEARS)]

# 무기체계별 거래 비중(도넛)은 03_weapon과 같은 tiv_weapon_group.csv 사용
tiv_group = load_tiv_weapon_group()
recent_group = tiv_group[
    tiv_group["recipient"].isin(targets) & tiv_group["year"].isin(RECENT_YEARS)
]

group_ko = load_weapon_groups()
company_products = load_company_products()


# =========================================================
# 3. 화면 표시 함수
# =========================================================

def format_usd(value):
    """USD -> '2.64조 달러' / '188억 달러'"""
    if pd.isna(value):
        return "—"

    if value >= 1e12:
        return f"{value / 1e12:,.2f}조 달러"

    return f"{value / 1e8:,.0f}억 달러"


def icon_img(name, size, fallback=""):
    """
    01_main_images/<name>.png 검은 아이콘 → 테마 글자색 아이콘 HTML
    (components/icons.py의 mask_icon_html 사용, 파일이 없으면 fallback 글자 표시)
    """
    icon_html = mask_icon_html(MAIN_ICON_DIR / f"{name}.png", size=size)

    if not icon_html:
        return fallback

    # mask_icon_html 결과는 여러 줄이라 '#### 제목' 마크다운 안에서 줄바꿈되지 않게 한 줄로 합침
    icon_html = " ".join(icon_html.split())

    return (
        f'<span style="display:inline-flex; vertical-align:middle; '
        f'margin-top:-3px; opacity:{ICON_OPACITY};">{icon_html}</span>'
    )


def info_icon(text):
    """제목 옆 파란색 정보 아이콘 + 마우스를 올리면 도움말 말풍선 (공통 help_icon_html)
    말풍선 테두리는 04_country와 같은 모양 (CSS: HELP_TOOLTIP_CSS)"""
    return help_icon_html(text, size=INFO_ICON_SIZE)


def title_icon_html(name):
    """
    카드 제목 아이콘: 원형 배경 없이 아이콘만 표시
    밝은 모드 = 검은색(이미지 그대로), 어두운 모드 = 흰색
    (--main-icon-color는 아래 테마 동기화 JS가 채움, 없으면 화면 글씨색)
    """
    icon_html = mask_icon_html(MAIN_ICON_DIR / f"{name}.png", size=TITLE_ICON_SIZE)

    if not icon_html:
        return ""

    icon_html = " ".join(icon_html.split())

    return (
        f'<span style="display:inline-flex; flex-shrink:0; vertical-align:middle; '
        f'margin:-4px {TITLE_ICON_GAP}px 0 0; color:var(--main-icon-color, currentColor);">'
        f'{icon_html}</span>'
    )


def card_title(icon, title, tooltip):
    """icon: 01_main_images 폴더의 아이콘 파일 이름 (확장자 제외)"""
    st.markdown(
        f"#### {title_icon_html(icon)}{title} {info_icon(tooltip)}",
        unsafe_allow_html=True
    )


def spark_bars_html(values, width=90, height=44):
    """
    작은 막대그래프 (마지막 해 강조) — 카드 오른쪽 아래에 표시.
    st.html이 <svg>를 걸러내 그래프가 사라지는 경우가 있어 일반 <div> 막대로 그림.
    """
    values = [float(v) for v in values]
    top = max(values) if values and max(values) > 0 else 1

    # Python 3.11은 f-string {} 안에 '#'을 쓸 수 없어 색상을 미리 변수로 계산
    bar_list = []

    for i, value in enumerate(values):
        bar_height = max(2, value / top * height)
        bar_color = "#2563eb" if i == len(values) - 1 else "#9ec2f2"

        bar_list.append(
            f'''<div style="
            flex:1;
            height:{bar_height:.0f}px;
            background:{bar_color};
            border-radius:2px 2px 0 0;
        "></div>'''
        )

    bars = "".join(bar_list)

    return f'''<div style="
        display:flex;
        align-items:flex-end;
        gap:4px;
        width:{width}px;
        height:{height}px;
    ">{bars}</div>'''


def kpi_body_html(label, value, delta, spark_values):
    """
    KPI 카드 본문: 텍스트는 가운데, 막대그래프는 오른쪽 아래에 작게.
    delta: 증감률(소수) 또는 None, 문구는 ' 전년 대비' 등과 함께 튜플로 전달
    """
    delta_html = ""

    if delta is not None:
        rate, text = delta
        is_up = rate >= 0

        # Python 3.11 호환: 색상·화살표를 f-string 밖에서 결정
        delta_color = "#21c354" if is_up else "#ff4b4b"
        delta_background = "rgba(33,195,84,0.15)" if is_up else "rgba(255,75,75,0.15)"
        arrow = icon_img(
            "trending_up" if is_up else "trending_down",
            DELTA_ICON_SIZE,
            fallback="▲" if is_up else "▼",
        )

        delta_html = f"""
        <span style="
            display:inline-flex;
            align-items:center;
            gap:4px;
            padding:3px 10px;
            border-radius:999px;
            font-size:13px;
            font-weight:600;
            color:{delta_color};
            background:{delta_background};
        ">{arrow} {abs(rate):.1%} {escape(text)}</span>
        """

    return f"""
    <div style="position:relative; min-height:{KPI_BODY_HEIGHT}px;
                display:flex; flex-direction:column;
                align-items:center; justify-content:center;
                text-align:center; gap:8px; padding-bottom:18px;">

        <div style="font-size:13px; opacity:0.75;">{escape(label)}</div>

        <div style="font-size:clamp(22px, 1.8vw, 34px); font-weight:800; line-height:1.1;
                    white-space:nowrap;">{kpi_value_html(value)}</div>

        {delta_html}

        <div style="position:absolute; right:0; bottom:{SPARK_OFFSET_Y}px;">
            {spark_bars_html(spark_values)}
        </div>
    </div>
    """


def find_flag_path(iso_a3):
    """국기 파일 찾기: images/flags, images/common/country × USA.png, usa.png"""
    code = str(iso_a3)

    for folder in FLAG_IMAGE_DIRS:
        for name in [code.upper(), code.lower()]:
            path = folder / f"{name}.png"
            if path.is_file():
                return path

    return None


def flag_base64(iso_a3):
    path = find_flag_path(iso_a3)

    if path is None:
        return None

    return flag_thumb_base64(path)   # 64px 썸네일 (원본 256px 대신, 속도 개선)


def flag_html(iso_a3, size=22):
    """03_weapon.py와 같은 원형 국기 <img>, 파일이 없으면 빈 문자열"""
    encoded = flag_base64(iso_a3)

    if encoded is None:
        return ""

    return f"""<img src="data:image/png;base64,{encoded}"
        style="width:{size}px; height:{size}px; border-radius:50%;
               object-fit:cover; flex-shrink:0; vertical-align:middle;">"""


def country_html(iso_a3, size=22, font_size=14, bold=False):
    """국기 + 한글 국가명"""
    name = escape(str(name_ko.get(iso_a3, iso_a3)))
    weight = 700 if bold else 500

    return f"""<span style="display:inline-flex; align-items:center; gap:6px;
        font-size:{font_size}px; font-weight:{weight}; white-space:nowrap;">
        {flag_html(iso_a3, size)}{name}</span>"""


def get_top_countries(company, n=3):
    """
    추천 후보국 1~n위: src/dashboard_score/dashboard_score.py 결과
    (02_company '2026년 수출 유망 국가 TOP 10'의 기본 결과와 같은 순서)

    스크립트를 실행할 수 없을 때만 예전 임시 기준
    (기업 무기분류의 최근 5년 도입 TIV 상위국, 수출통제국 제외)으로 표시.
    """
    try:
        result = top_countries(company, n)
        if result:
            return [row["iso_a3"] for row in result]
    except Exception:
        pass

    groups = COMPANY_INFO[company]["weapon_groups"]

    by_country = (
        recent[
            recent["group"].isin(groups)
            & ~recent["recipient"].isin(RESTRICTED_ISO)
        ]
        .groupby("recipient")["tiv"]
        .sum()
        .sort_values(ascending=False)
    )

    return by_country.head(n).index.tolist()


# =========================================================
# 4. KPI 카드 4개
# =========================================================

kpi_columns = st.columns(
    [1, 1, 1, 1.3],
    gap="medium"
)


# ---------------------------------------------------------
# 4-1. 대상국 전체 국방비
# ---------------------------------------------------------

with kpi_columns[0]:

    with st.container(border=True, height=KPI_CARD_HEIGHT):

        card_title(
            "account_balance",
            "대상국 전체 국방비",
            "분석 대상국(한국·북한 제외)의 국방비 합계입니다. "
            "전년 대비는 두 해 모두 자료가 있는 국가끼리 비교합니다."
        )

        y1, y0 = LATEST_YEAR, LATEST_YEAR - 1

        total_latest = milex.loc[
            milex["year"] == y1, "milex_usd"
        ].sum()

        both_years = (
            milex.pivot(index="iso_a3", columns="year", values="milex_usd")
            [[y0, y1]]
            .dropna()
        )

        yoy = both_years[y1].sum() / both_years[y0].sum() - 1

        milex_by_year = (
            milex[milex["year"].isin(RECENT_YEARS)]
            .groupby("year")["milex_usd"]
            .sum()
        )

        # 텍스트 가운데 + 오른쪽 아래 작은 막대그래프
        st.html(kpi_body_html(
            label=f"{y1}년 기준",
            value=format_usd(total_latest),
            delta=(yoy, "전년 대비"),
            spark_values=milex_by_year.tolist(),
        ))


# ---------------------------------------------------------
# 4-2. 대상국 총 TIV
# ---------------------------------------------------------

with kpi_columns[1]:

    with st.container(border=True, height=KPI_CARD_HEIGHT):

        card_title(
            "sync_alt",
            "대상국 전체 총 TIV",
            f"SIPRI TIV(무기 이전 물량 지표)의 {RECENT_LABEL} 인도분 합계입니다. "
            "TIV는 계약 금액(달러)이 아닙니다."
        )

        tiv_by_year = (
            recent.groupby("year")["tiv"]
            .sum()
            .reindex(RECENT_YEARS, fill_value=0)
        )

        previous_total = tiv[
            tiv["year"].isin(PREVIOUS_YEARS)
        ]["tiv"].sum()

        change = (
            tiv_by_year.sum() / previous_total - 1
            if previous_total
            else None
        )

        st.html(kpi_body_html(
            label=f"{RECENT_LABEL} 누적",
            value=f"TIV {tiv_by_year.sum():,.0f}",
            delta=(change, "직전 5년 대비") if change is not None else None,
            spark_values=tiv_by_year.tolist(),
        ))


# ---------------------------------------------------------
# 4-3. 최대 수입국
# ---------------------------------------------------------

with kpi_columns[2]:

    with st.container(border=True, height=KPI_CARD_HEIGHT):

        card_title(
            "emoji_events",
            "최대 수입국",
            f"{RECENT_LABEL} 인도 TIV 합계가 가장 큰 대상국입니다."
        )

        tiv_by_country = (
            recent.groupby("recipient")["tiv"]
            .sum()
            .sort_values(ascending=False)
        )

        top_iso = tiv_by_country.index[0]
        second_iso = tiv_by_country.index[1]

        # 긴 국가명(예: 남아프리카공화국)도 카드 안에 들어가도록 글자 크기 조절
        top_name_size = 32 if len(str(name_ko.get(top_iso, ""))) <= 5 else 25
        top_country = country_html(top_iso, size=56, font_size=top_name_size, bold=True)
        second_country = country_html(second_iso, size=18, font_size=13)

        # 1위 국기·국가명·TIV를 카드 가운데에 배치
        st.html(f"""
        <div style="
            display:flex;
            flex-direction:column;
            align-items:center;
            justify-content:center;
            text-align:center;
            gap:10px;
            min-height:{KPI_BODY_HEIGHT}px;
        ">
            <div>
                {top_country}
            </div>

            <div style="font-size:15px;">
                {RECENT_LABEL}
                <b style="font-size:20px; margin-left:4px;">TIV {tiv_by_country.iloc[0]:,.0f}</b>
            </div>

            <div style="font-size:13px; opacity:0.7;
                        display:flex; align-items:center; gap:6px;">
                2위 {second_country}
                · TIV {tiv_by_country.iloc[1]:,.0f}
            </div>
        </div>
        """)


# ---------------------------------------------------------
# 4-4. 무기체계별 거래 비중
# ---------------------------------------------------------

with kpi_columns[3]:

    with st.container(border=True, height=KPI_CARD_HEIGHT):

        card_title(
            "donut_large",
            "무기체계별 거래 비중",
            f"{RECENT_LABEL} TIV 기준입니다. 상위 {DONUT_TOP_N}개 분류 외에는 '기타'로 묶었고, "
            "색상은 무기체계별 수출국 추천 화면과 같습니다."
        )

        # 03_weapon.py와 같은 방식: 10개 분류 전체를 TIV 내림차순으로 정렬해
        # pie_colors(WEAPON_COLORS)를 순서대로 적용 → 두 화면의 분류별 색상 일치
        tiv_by_group = (
            recent_group.groupby("group")["tiv"]
            .sum()
            .reindex(list(group_ko), fill_value=0)
            .sort_values(ascending=False)
        )

        # 상위 5개 분류 + 나머지 '기타'
        # 상위 분류 색상은 03_weapon.py와 같은 순서(1~5위 색)
        top_groups = tiv_by_group.head(DONUT_TOP_N)
        other_total = float(tiv_by_group.iloc[DONUT_TOP_N:].sum())

        labels = [group_ko.get(group, group) for group in top_groups.index]
        values = [float(v) for v in top_groups.values]
        colors = WEAPON_COLORS[:len(top_groups)]

        if other_total > 0:
            labels.append("기타")
            values.append(other_total)
            colors.append(OTHER_COLOR)

        total_value = sum(values)
        shares = [value / total_value * 100 for value in values]

        # 조각 바깥 비중 표기 (3% 미만은 생략, 03_weapon.py와 동일 기준)
        pie_text = [
            f"{share:.1f}%" if share >= 3 else ""
            for share in shares
        ]

        # 왼쪽 도넛 / 오른쪽 범례 (gap으로 간격 확보)
        chart_column, legend_column = st.columns(
            [1.35, 1],
            gap="small",
            vertical_alignment="center"
        )

        with chart_column:

            fig = go.Figure(go.Pie(
                labels=labels,
                values=values,
                hole=0.5,
                sort=False,
                direction="clockwise",
                rotation=0,
                marker=dict(
                    colors=colors,
                    # 조각 사이 여백(2px). 색은 위 CSS가 현재 화면 배경색으로 바꿔 줌
                    line=dict(color="#ffffff", width=2),
                ),
                text=pie_text,
                textinfo="text",
                textposition="outside",
                textfont=dict(size=11),
                automargin=True,
                showlegend=False,
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "TIV %{value:,.0f}<br>"
                    "비중 %{percent}<extra></extra>"
                ),
            ))

            # 도넛 가운데 총 TIV
            fig.add_annotation(
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                text=f"총 TIV<br><b>{total_value:,.0f}</b>",
                showarrow=False,
                font=dict(size=12),
            )

            fig.update_layout(
                height=DONUT_HEIGHT,
                margin=dict(l=0, r=0, t=6, b=6),
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )

            # theme="streamlit": 밝은/어두운 모드 글씨색 자동 대응
            st.plotly_chart(
                fig,
                theme="streamlit",
                key="kpi_weapon_group_chart",
                config={"displayModeBar": False}
            )

        # 03_weapon.py와 같은 원형 점 범례 (이름 + 비중)
        with legend_column:

            legend_items = "".join(f"""
                <div style="display:flex; align-items:center; gap:6px; min-width:0;">
                    <span style="width:10px; height:10px; flex-shrink:0;
                                 border-radius:50%; background-color:{color};"></span>
                    <span style="font-size:12.5px; line-height:1.3; color:inherit;
                                 white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                        {escape(label)}
                    </span>
                    <span style="font-size:12.5px; font-weight:700; margin-left:auto;
                                 padding-left:6px; color:inherit;">
                        {share:.1f}%
                    </span>
                </div>
                """ for label, share, color in zip(labels, shares, colors))

            st.html(f"""
            <div style="display:flex; flex-direction:column; gap:6px;
                        padding-left:4px; width:100%;">
                {legend_items}
            </div>
            """)


# =========================================================
# 5. 기업별 추천 후보국 + 무기 수입 규모
# =========================================================

# 표(왼쪽)를 넓히고 지도(오른쪽)를 줄여 국가명이 잘리지 않게 함
left_column, right_column = st.columns(
    [1.4, 1],
    gap="medium"
)


# ---------------------------------------------------------
# 5-1. 기업별 주요 무기체계 및 추천 후보국
# ---------------------------------------------------------

with left_column:

    with st.container(border=True, height=BOTTOM_CARD_HEIGHT, key="company_card"):

        card_title(
            "recommend",
            "기업별 주요 무기체계 및 추천 후보국",
            "**주요 무기체계** 기업이 강점을 가진 무기체계 (파란 칩: 주력 · 회색 칩: 보조)\n"
            "**추천 후보국** 2026년 수출 유망 국가 1~3위\n"
            "**산정 기준** 2021~2025년 데이터의 6개 지표(HHI·국방비·무기 매칭도·협력 관계·GPI·신용도)를 "
            "0~100점으로 바꾸고 기업별 CRITIC 가중치를 곱함. 기업별 수출 기회 화면 TOP 10 기본 순위와 같음."
        )

        # -------------------------------------------------
        # 표 전체를 하나의 CSS 그리드로 그림 (화면 크기에 따라 유연하게)
        # - 열: 기업명 | 주요 무기체계 | 추천 후보국 1·2·3위 (5칸)
        #   한 그리드 안이라 제목줄과 모든 행의 세로 정렬이 항상 맞음
        # - 행: 제목줄 + 기업 6행이 카드 남은 높이를 똑같이 나눠 채움 (아래 여백 없음)
        #   내용이 넘치는 좁은 화면에서는 행이 늘어나고 카드 안에서 스크롤
        # - 넓은 화면: 기업명·무기체계 칸이 최대 너비까지 커지고 남는 폭은 후보국 3칸이 균등 분배
        # - 좁은 화면: 로고·무기체계 칸이 먼저 줄어듦 (칩은 줄바꿈, 국가명은 한 줄 유지)
        # -------------------------------------------------
        NAME_COL_MIN_WIDTH = 100         # 좁은 화면에서 기업명 칸이 줄어드는 최소 너비 (px)
        WEAPON_COL_MAX = 270         # 주요 무기체계 칸 최대 너비 (px) - 줄이면 칩이 더 줄바꿈됨
        WEAPON_COL_MIN = 170         # 주요 무기체계 칸 최소 너비 (px) - 좁은 화면에서 칩이 한 줄에 2개 이상 들어가도록
        HEADER_ROW_HEIGHT = 36       # 제목줄 높이 (px)

        def company_cell_html(company, code):
            """
            기업명 칸: 기업명 텍스트만 표시 (로고 미사용 - 상표권 문제 방지, 시안 C)
            칸이 좁으면 말줄임(…) + 마우스를 올리면 전체 기업명 말풍선
            """
            return (
                f'<span title="{escape(company, quote=True)}" style="'
                f'display:block; width:100%; text-align:center; '
                f'font-weight:700; font-size:14px; '
                f'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">'
                f'{escape(company)}</span>'
            )

        # 칸 공통 스타일
        line = "border-bottom:1px solid rgba(128,128,128,0.18);"
        cell_style = "display:flex; align-items:center; min-width:0; padding:4px 8px; font-size:13px;"
        header_style = (
            "display:flex; align-items:center; justify-content:center; padding:0 8px; "
            "font-size:13px; font-weight:700; "
            "background:rgba(100,160,255,0.10); white-space:nowrap;"
        )

        # 제목줄 (03_weapon.py TOP 5 표와 같은 연한 파란 배경, 양 끝만 둥글게)
        cells_html = (
            f'<div style="{header_style} border-radius:10px 0 0 10px;">기업명</div>'
            f'<div style="{header_style}">주요 무기체계</div>'
            f'<div style="{header_style} grid-column:span 3; border-radius:0 10px 10px 0;">추천 후보국</div>'
        )

        for index, (company, code) in enumerate(COMPANIES.items()):

            info = COMPANY_INFO[company]
            top_countries = get_top_countries(company)

            border = line if index < len(COMPANIES) - 1 else ""

            # 추천 후보국 1·2·3위를 각각 별도 칸에 넣음 → 모든 행의 국가가 세로로 같은 위치
            # 국가명은 줄바꿈하지 않음 → 칸이 좁아지면 로고·무기체계 칸이 먼저 줄어듦
            country_cells = [
                f'<span style="display:flex; align-items:center; gap:6px;">'
                f'<span style="flex-shrink:0; display:flex;">{flag_html(iso, 20)}</span>'
                f'<span style="font-size:13px; font-weight:500; line-height:1.2; white-space:nowrap;">'
                f'{escape(str(name_ko.get(iso, iso)))}</span>'
                f'</span>'
                for iso in top_countries
            ]
            country_cells += [""] * (3 - len(country_cells))   # 3개 미만이면 빈칸

            # 주요(1.0) 무기체계는 파란 칩, 보조(0.5)는 회색 음영 칩 + 한 단계 연한 글자 (전체 표시)
            # title 속성 → 마우스를 올리면 영문 분류명 말풍선 표시
            products_html = "".join(
                f'<span title="{escape(en, quote=True)}" '
                f'style="white-space:nowrap; cursor:help; '
                f'padding:1px 6px; border-radius:6px; '
                + (
                    'background:rgba(100,160,255,0.14);">'
                    if level == "primary"
                    # 보조 칩: 회색 음영을 진하게(0.18→0.32), 글자도 덜 흐리게(0.75→0.85) → 카드 배경과 구분
                    else 'background:rgba(128,128,128,0.32); opacity:0.85;">'
                )
                + f'{escape(ko)}</span>'
                for en, ko, level in get_company_weapons(code, WEAPON_GROUP_COUNT)
            ) or "—"

            cells_html += (
                # 기업명 칸: align-items:stretch → 로고 상자가 칸 높이를 꽉 채움
                f'<div style="{cell_style} {border}">{company_cell_html(company, code)}</div>'
                f'<div style="{cell_style} {border}">'
                f'<div style="display:flex; flex-wrap:wrap; gap:3px; '
                f'font-size:11.5px; line-height:1.3; opacity:0.9;">{products_html}</div>'
                f'</div>'
                + "".join(
                    f'<div style="{cell_style} {border} padding-right:12px;">{cell}</div>'
                    for cell in country_cells
                )
            )

        # 표 최소 높이 = 카드 높이 - (카드 제목 + 카드 안쪽 여백)
        # 실제 높이는 아래 CSS(.st-key-company_card)가 카드 남은 높이에 맞춰 늘려 줌
        table_height = BOTTOM_CARD_HEIGHT - TABLE_HEIGHT_OFFSET

        st.html(f"""
        <div class="company-grid" style="
            display:grid;
            grid-template-columns:
                minmax({NAME_COL_MIN_WIDTH + 16}px, {NAME_COL_WIDTH + 16}px)
                minmax({WEAPON_COL_MIN}px, {WEAPON_COL_MAX}px)
                repeat(3, minmax(max-content, 1fr));
            grid-template-rows: {HEADER_ROW_HEIGHT}px repeat({len(COMPANIES)}, 1fr);
            min-height:{table_height}px;
            height:100%;
            margin-top:6px;
        ">
            {cells_html}
        </div>
        """)


# ---------------------------------------------------------
# 5-2. 무기 수입 규모 (세계 지도)
# ---------------------------------------------------------

with right_column:

    with st.container(border=True, height=BOTTOM_CARD_HEIGHT):

        title_column, period_column = st.columns(
            [1.5, 1],
            vertical_alignment="top"     # "center" → "top": 왼쪽 카드 제목과 같은 높이
        )

        with title_column:
            card_title(
                "bubble_chart",
                "무기 수입 규모",
                "원 크기는 선택한 기간의 무기 도입 TIV 구간입니다. "
                "원에 마우스를 올리면 국가명과 TIV가 보입니다."
            )

        with period_column:

            periods = {
                RECENT_LABEL: RECENT_YEARS,
                TEN_YEAR_LABEL: PREVIOUS_YEARS + RECENT_YEARS,
            }

            for year in reversed(RECENT_YEARS):
                periods[f"{year}년"] = [year]

            period = st.selectbox(
                "기간",
                list(periods),
                key="main_map_period",
                label_visibility="collapsed",
            )

        map_data = (
            tiv[tiv["year"].isin(periods[period])]
            .groupby("recipient")["tiv"]
            .sum()
            .reset_index()
        )

        map_data = map_data[map_data["tiv"] > 0]
        map_data["country"] = map_data["recipient"].map(name_ko)

        # TIV 구간별 원 크기
        map_data["size"] = 0
        for low, high, _, size in BUBBLE_BINS:
            in_bin = (map_data["tiv"] >= low) & (map_data["tiv"] < high)
            map_data.loc[in_bin, "size"] = size

        # Plotly 6 + 일부 Streamlit 버전에서 numpy 배열이 그려지지 않는 문제가 있어
        # 모든 값을 파이썬 list로 넘김
        # TIV 정보만 표시: 원 크기 = TIV 구간, 색은 한 가지, 국가명 글씨 없음 (마우스를 올리면 표시)
        fig = go.Figure(go.Scattergeo(
            locations=map_data["recipient"].tolist(),
            locationmode="ISO-3",
            mode="markers",
            marker=dict(
                size=map_data["size"].astype(int).tolist(),
                color="#2563eb",
                opacity=0.75,
                line=dict(color="white", width=1),
            ),
            customdata=map_data[["country", "tiv"]].values.tolist(),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "TIV %{customdata[1]:,.0f}<extra></extra>"
            ),
        ))

        # 밝은 지도: 육지·국경·바다 색을 모두 직접 지정
        # (showland=True가 없으면 landcolor가 적용되지 않아 육지가 검게 보일 수 있음)
        fig.update_geos(
            projection_type="natural earth",
            projection_rotation=dict(lon=MAP_CENTER_LON),   # 지도 중심 경도 = 대한민국
            showframe=False,
            showcoastlines=False,
            showland=True,
            landcolor="#dbe7f7",
            showcountries=True,
            countrycolor="#ffffff",
            countrywidth=0.6,
            showocean=True,
            oceancolor="rgba(0,0,0,0)",   # 바다는 카드 배경색 그대로
            showlakes=False,
            bgcolor="rgba(0,0,0,0)",
            lataxis_range=[-58, 85],
        )

        fig.update_layout(
            height=MAP_HEIGHT,
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
            template="plotly_white",       # 어두운 기본 템플릿이 섞이지 않도록 밝은 템플릿 고정
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        # theme=None: Streamlit 테마가 지도 색을 덮어쓰지 않도록 위에서 지정한 색 그대로 사용
        st.plotly_chart(
            fig,
            theme=None,
            key="main_tiv_bubble_map",
            config={
                "displayModeBar": False,
                "topojsonURL": TOPOJSON_URL,   # 세계지도 경계선 파일 위치
            }
        )

        # 원 크기 범례
        legend_columns = st.columns(len(BUBBLE_BINS) + 1)

        with legend_columns[0]:
            # "TIV 규모" 아래 줄에 기간 표시 (마크다운 줄바꿈: 끝에 공백 2칸 + \n)
            st.caption(f"**TIV 규모**  \n{period}")

        for column, (_, _, label, size) in zip(legend_columns[1:], BUBBLE_BINS):
            with column:
                dot = size // 2 + 6
                st.markdown(
                    f'<span style="display:inline-block;width:{dot}px;height:{dot}px;'
                    f'border-radius:50%;background:#2563eb;opacity:.75;'
                    f'vertical-align:middle;margin-right:6px"></span>'
                    f'<span style="font-size:14px">{label}</span>',
                    unsafe_allow_html=True
                )