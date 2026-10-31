
"""Defense Insight: 공통 사이드바와 대시보드 페이지 (4개 분석 화면 + 데이터 출처)."""

import base64
from pathlib import Path

import streamlit as st


# ============================================================
# 1. 기본 설정
# ============================================================
ROOT_DIR = Path(__file__).resolve().parent
ICON_DIR = ROOT_DIR / "images" / "icon"
BACKGROUND_FILE = "sidebar-background.png"
APP_ICON = ICON_DIR / "material-security.png"   # Material Symbols "security" (Apache 2.0)

st.set_page_config(
    page_title="Defense Insight",
    page_icon=str(APP_ICON) if APP_ICON.is_file() else "🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 메뉴 이름 / 메뉴 제목 / 페이지 경로 / PNG 파일명 / 대체 아이콘
MENU = [
    ("main", "메인 대시보드", "pages/01_main.py", "material-home.png", ":material/home:"),
    ("company", "기업별 수출 기회 분석", "pages/02_company.py", "material-apartment.png", ":material/bar_chart:"),
    ("weapon", "무기체계별 수출국 추천", "pages/03_weapon.py", "material-swords.png", ":material/target:"),
    ("country", "국가별 상세 분석", "pages/04_country.py", "material-public.png", ":material/public:"),
    ("sources", "데이터 출처", "pages/05_sources.py", "material-description.png", ":material/description:"),
]


# ============================================================
# 2. 페이지 등록 및 현재 페이지 확인
# ============================================================
PAGES = {
    key: st.Page(path, title=title, default=(key == "main"))
    for key, title, path, _, _ in MENU
}

# 기존 Streamlit 메뉴는 숨기지만 4개 페이지 이동 기능은 유지
pg = st.navigation(list(PAGES.values()), position="hidden")
active_menu = next(
    (key for key, page in PAGES.items() if page.url_path == pg.url_path),
    "main",
)


# ============================================================
# 3. 이미지 불러오기 (파일이 바뀌면 캐시 자동 갱신)
# ============================================================
@st.cache_data(show_spinner=False)
def image_data_uri(file_path: str, modified_ns: int) -> str:
    """PNG/JPG 파일을 브라우저용 data URI로 변환."""
    path = Path(file_path)
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def get_image_uri(filename: str) -> str:
    """images/icon 폴더의 파일을 찾음. 없으면 빈 문자열 반환."""
    path = ICON_DIR / filename
    if not path.is_file():
        return ""
    return image_data_uri(str(path), path.stat().st_mtime_ns)


# ============================================================
# 4. 사이드바 CSS
# ============================================================
background_uri = get_image_uri(BACKGROUND_FILE)
background_layer = (
    'linear-gradient(180deg, rgba(7,26,52,.55) 0%, '
    'rgba(7,26,52,.12) 35%, rgba(7,26,52,.12) 75%, #081B35 100%), '
    f'url("{background_uri}") center center / cover no-repeat'
    if background_uri
    else "linear-gradient(160deg, #0E3D6A, #071A34)"
)

# 단일 CSS 문자열로 구성: 화면에 코드가 노출되는 오류 방지
css = """
/* ------------------------------------------------------------
   4-1. 사이드바 전체와 비행기·군함 배경
------------------------------------------------------------ */
section[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #071A34, #0B3159 55%, #071A34) !important;
    border-right: 1px solid rgba(154,201,252,.18);
}

section[data-testid="stSidebar"]::before {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: 70px;
    height: 59%;
    background: __BACKGROUND_LAYER__;
    pointer-events: none;
    z-index: 0;
}

section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    position: relative;
    z-index: 1;
    background: transparent !important;
}

/* ------------------------------------------------------------
   4-2. Streamlit 기본 접기 버튼 보존
   - 버튼의 높이, 위치, 클릭 이벤트를 덮어쓰지 않음
   - 디자인 요소만 버튼 아래 레이어로 배치
------------------------------------------------------------ */
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
    position: relative;
    z-index: 30;
}

section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    position: relative;
    z-index: 1;
    padding-top: 0 !important;
    padding-bottom: 115px !important;
}

/* ============================================================
   사이드바 접기 버튼 - 항상 흰색 표시
   ============================================================ */

/* 마우스를 올리지 않아도 버튼 자체를 표시 */
section[data-testid="stSidebar"]
[data-testid="stSidebarCollapseButton"] {
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    z-index: 100 !important;
}

/* 버튼 배경과 테두리 제거 */
section[data-testid="stSidebar"]
[data-testid="stSidebarCollapseButton"] button {
    visibility: visible !important;
    opacity: 1 !important;
    color: white !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* 화살표 아이콘을 항상 흰색으로 */
section[data-testid="stSidebar"]
[data-testid="stSidebarCollapseButton"] svg,
section[data-testid="stSidebar"]
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
section[data-testid="stSidebar"]
[data-testid="stSidebarCollapseButton"] .material-symbols-rounded {
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
    opacity: 1 !important;
    filter: brightness(0) invert(1) !important;
}

/* 마우스를 올려도 동일한 디자인 */
section[data-testid="stSidebar"]
[data-testid="stSidebarCollapseButton"] button:hover {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* ------------------------------------------------------------
   4-3. 로고 및 메뉴 제목
------------------------------------------------------------ */
.sidebar-brand {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 14px;
    margin: 0 2px 12px;
    padding: 0 0 17px;
    border-bottom: 1px solid rgba(184,217,254,.20);
}

/* Defense Insight 로고와 글씨만 위로 이동 */
.sidebar-brand img,
.sidebar-brand-title {
    transform: translateY(-30px);
}

.sidebar-brand img {
    width: 60px;
    height: 60px;
    flex-shrink: 0;
    object-fit: contain;
    filter: brightness(0) invert(1);   /* 검은 Material 아이콘 → 흰색 (메뉴 아이콘과 동일) */
}

.sidebar-brand-title {
    color: #F3F8FF;
    font-size: 29px;
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -.6px;
}

.sidebar-brand-title span {
    color: #6ABDFF;
}

.sidebar-nav-caption {
    margin: 0 0 12px 10px;
    color: #94BFEF;
    font-size: 11px;
    font-weight: 750;
    letter-spacing: 2px;
}

/* ------------------------------------------------------------
   4-4. 메뉴 카드, 글씨와 선택 상태
------------------------------------------------------------ */
section[data-testid="stSidebar"] [class*="st-key-sidebar_nav_"] {
    margin-bottom: 0 !important;
}

section[data-testid="stSidebar"] [class*="st-key-sidebar_nav_"] a {
    position: relative !important;
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
    width: 100% !important;
    min-height: 68px !important;
    padding: 11px 13px !important;
    box-sizing: border-box !important;
    border: 1px solid rgba(173,211,255,.10) !important;
    border-radius: 13px !important;
    background: rgba(255,255,255,.035) !important;
    color: #EEF6FF !important;
    text-decoration: none !important;
    transition: background .16s ease, box-shadow .16s ease !important;
}

section[data-testid="stSidebar"] [class*="st-key-sidebar_nav_"] a p {
    color: #EEF6FF !important;
    font-size: 17px !important;
    font-weight: 650 !important;
    line-height: 1.3 !important;
}

section[data-testid="stSidebar"] [class*="st-key-sidebar_nav_"] a:hover {
    background: rgba(51,132,235,.26) !important;
    border-color: rgba(143,200,255,.28) !important;
}

section[data-testid="stSidebar"] .st-key-sidebar_nav___ACTIVE__ a {
    background: linear-gradient(105deg, #1C7FEC, #1254A5) !important;
    border-color: rgba(167,221,255,.46) !important;
    box-shadow: 0 7px 18px rgba(0,0,0,.22) !important;
}

section[data-testid="stSidebar"] .st-key-sidebar_nav___ACTIVE__ a::after {
    content: "";
    position: absolute;
    top: 11px;
    bottom: 11px;
    left: 0;
    width: 4px;
    border-radius: 0 4px 4px 0;
    background: #A7E4FF;
}

/* ------------------------------------------------------------
   4-5. 최하단 문구
------------------------------------------------------------ */
section[data-testid="stSidebar"]::after {
    content: "데이터로 읽는 방산시장,\\A근거로 찾는 수출 기회.";
    position: absolute;
    left: 22px;
    right: 22px;
    bottom: 22px;
    z-index: 2;
    padding: 14px 0 0;
    border-top: 1px solid rgba(191,223,255,.28);
    color: #ECF5FF;
    font-size: 15px;
    font-weight: 650;
    line-height: 1.65;
    letter-spacing: -.2px;
    white-space: pre-line;
    text-align: center;
    pointer-events: none;
}
"""

css = css.replace("__BACKGROUND_LAYER__", background_layer)
css = css.replace("__ACTIVE__", active_menu)


# ------------------------------------------------------------
# 4-6. 원하는 PNG 메뉴 아이콘을 CSS 안에 추가
# ------------------------------------------------------------
icon_css = []

for key, _, _, filename, _ in MENU:
    icon_uri = get_image_uri(filename)

    if not icon_uri:
        continue

    icon_css.append(f"""
    section[data-testid="stSidebar"] .st-key-sidebar_nav_{key} a::before {{
        content: "";
        display: block;
        width: 34px;
        height: 34px;
        flex: 0 0 34px;
        background: url("{icon_uri}") center / contain no-repeat;
        filter: brightness(0) invert(1);
    }}
    """)

# 스타일 태그를 한 번만 사용하고 CSS를 직접 적용
st.html("<style>" + css + "\n" + "\n".join(icon_css) + "</style>")


# ============================================================
# 5. 사이드바 화면 구성
# ============================================================
with st.sidebar:
    logo_uri = get_image_uri("material-security.png")
    logo_html = (
        f'<img src="{logo_uri}" alt="Defense Insight 로고">'
        if logo_uri else ""
    )

    st.html(f"""
        <div class="sidebar-brand">
            {logo_html}
            <div class="sidebar-brand-title">
                Defense<br><span>Insight</span>
            </div>
        </div>
        <div class="sidebar-nav-caption">DASHBOARD MENU</div>
    """)

    for key, title, _, filename, fallback_icon in MENU:
        # PNG 파일이 없으면 Streamlit 기본 아이콘으로 대체
        menu_icon = None if get_image_uri(filename) else fallback_icon

        with st.container(key=f"sidebar_nav_{key}"):
            st.page_link(
                PAGES[key],
                label=title,
                icon=menu_icon,
                use_container_width=True,
            )


# ============================================================
# 6. 현재 선택한 페이지 실행
# ============================================================
pg.run()
