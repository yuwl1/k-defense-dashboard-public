import streamlit as st
from pathlib import Path

# 공통 이미지 처리 함수
from components.icons import (
    make_image_mask,
    mask_icon_html
)


# ============================================================
# 1. 프로젝트 경로 및 이미지 설정
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MAP_PATH = (
    BASE_DIR / "images/common/etc/world_map.png"
)

CALENDAR_PATH = (
    BASE_DIR / "images/common/etc/material-calendar_month.png"
)


# ============================================================
# 1-1. 헤더 크기 설정 (단위: px)
# ============================================================
# 헤더 크기는 이 값들만 바꾸면 됨 (CSS 안의 숫자는 직접 수정하지 않기)

PAGE_PADDING_TOP = 58       # 페이지 위쪽 여백 (Streamlit 상단 툴바 약 60px 고려)
PAGE_PADDING_BOTTOM = 16    # 페이지 아래쪽 여백

HEADER_MIN_HEIGHT = 165     # 헤더 박스 최소 높이
HEADER_PADDING_Y = 20       # 헤더 박스 안쪽 위·아래 여백
HEADER_PADDING_X = 20       # 헤더 박스 안쪽 왼쪽·오른쪽 여백
HEADER_RADIUS = 15          # 헤더 박스 모서리 둥글기
HEADER_MARGIN_BOTTOM = 4    # 헤더 박스와 아래 내용 사이 간격

TITLE_FONT_SIZE = 44        # 제목 글자 크기 (예: 메인 대시보드)
TITLE_GAP = 12               # 제목과 설명 사이 간격
DESC_FONT_SIZE = 16         # 설명 글자 크기

CALENDAR_ICON_SIZE = 24     # 달력 아이콘 크기

# ============================================================
# 1-2. 최종 업데이트 날짜 (수동 관리)
# ============================================================

LAST_UPDATE_DATE = "2026. 10. 29."

# ============================================================
# 3. 공통 헤더 함수
# ============================================================

def render_header(title, description, page_file=None):

    # --------------------------------------------------------
    # 세계지도 이미지 마스크
    # --------------------------------------------------------

    map_base64 = make_image_mask(
        MAP_PATH,
        is_map=True
    )

    # --------------------------------------------------------
    # 달력 아이콘 HTML
    # --------------------------------------------------------

    calendar_html = mask_icon_html(
        CALENDAR_PATH,
        size=CALENDAR_ICON_SIZE
    )

    # --------------------------------------------------------
    # 라이트 / 다크모드 자동 대응 CSS
    # --------------------------------------------------------

    st.markdown(f"""
    <style>

    /* ================================================
       페이지 위쪽 여백
       - Streamlit 상단 툴바(약 60px)에 헤더가 가려지지 않도록
         모든 페이지 공통으로 여기서만 관리 (각 페이지에서 따로 줄이지 않기)
       - 기본값(96px)보다 줄여 1920x1080 화면에서 세로 공간 확보
    ================================================= */

    .block-container,
    [data-testid="stMainBlockContainer"] {{
        padding-top: {PAGE_PADDING_TOP}px !important;
        padding-bottom: {PAGE_PADDING_BOTTOM}px !important;
    }}

    /* ================================================
       상단 헤더 박스
    ================================================= */

    .st-key-header_box {{
        position: relative;
        overflow: hidden;
        isolation: isolate;

        background-color: transparent !important;
        background-image: none !important;

        color: inherit !important;

        border-radius: {HEADER_RADIUS}px;
        min-height: {HEADER_MIN_HEIGHT}px;
        padding: {HEADER_PADDING_Y}px {HEADER_PADDING_X}px !important;
        margin-bottom: {HEADER_MARGIN_BOTTOM}px;
        
        /* 제목·설명·업데이트 날짜를 헤더 박스 세로 가운데에 배치 */
        display: flex !important;
        justify-content: center !important;
    }}

    /* ================================================
       세계지도 배경
    ================================================= */

    .st-key-header_box::before {{
        content: "";
        position: absolute;
        inset: 0;
        z-index: 0;
        pointer-events: none;

        /* 현재 테마의 글씨 색상 사용 */
        background-color: currentColor;
        opacity: 0.35;

        /* 세계지도 마스크 */
        -webkit-mask-image:
            url("data:image/png;base64,{map_base64}");

        mask-image:
            url("data:image/png;base64,{map_base64}");

        -webkit-mask-position: center 35%;
        mask-position: right 35%;

        -webkit-mask-size: 80% auto;
        mask-size: 80% auto;

        -webkit-mask-repeat: no-repeat;
        mask-repeat: no-repeat;
    }}

    /* ================================================
       제목과 아이콘을 지도보다 앞에 표시
    ================================================= */

    .st-key-header_box > * {{
        position: relative;
        z-index: 1;
    }}

    /* ================================================
       헤더 글씨 자동 변경
    ================================================= */

    .st-key-header_box h1,
    .st-key-header_box p {{
        color: inherit !important;
    }}

    /* ================================================
       헤더 제목·설명 크기 (st.title 기본 여백이 커서 잘림 방지)
    ================================================= */

    .st-key-header_box h1 {{
        font-size: {TITLE_FONT_SIZE}px !important;
        line-height: 1.25 !important;
        padding: 0 0 {TITLE_GAP}px 0 !important;
        margin: 0 !important;
    }}

    .st-key-header_box p {{
        margin: 0 !important;
        font-size: {DESC_FONT_SIZE}px;
    }}

    </style>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------
    # 상단 제목 및 업데이트 날짜
    # --------------------------------------------------------

    with st.container(border=True, key="header_box"):

        header_col1, header_col2 = st.columns(
            [4, 1],
            vertical_alignment="center"
        )

        # 왼쪽: 제목과 설명
        with header_col1:

            st.title(title)

            st.write(description)

        # 오른쪽: 달력 아이콘과 마지막 업데이트 날짜
        # 아이콘과 글자를 한 줄(flex)로 묶어 세로 가운데를 정확히 맞춤
        with header_col2:

            if page_file is not None:

                date_text = f"최종 업데이트: {LAST_UPDATE_DATE}"

                st.html(f"""
                <div style="
                    display:flex;
                    align-items:center;
                    justify-content:flex-end;
                    width:100%;
                    gap:10px;
                    white-space:nowrap;
                ">
                    <span style="display:inline-flex; line-height:0;">
                        {calendar_html}
                    </span>
                    <span style="font-size:{DESC_FONT_SIZE}px; line-height:1;">
                        {date_text}
                    </span>
                </div>
                """)