"""
대시보드 공통 화면 요소 (01_main, 03_weapon, 04_country 공통 / 02_company 제외)

- 카드 제목: 아이콘 28px (03_weapon 기준) + 아이콘-제목 간격 6px (01_main 기준)
  · 제목 글자 크기: 03_weapon, 04_country = 19px / 01_main은 화면 밀도 때문에 17px 유지
- 정보(ⓘ) 아이콘: 파란색 #2563eb (04_country '후보 적합도 구성 점수' 기준)
- 도움말(정보 아이콘에 마우스): 테두리 모양만 04_country, 나머지는 01_main 원래 도움말 느낌
- 무기체계 분류 색상: 03_weapon 도넛과 같은 색 (최근 5년 수입 TIV 순위별 색)
- 기업: 로고 이미지 미사용 (상표권 보호) — 화면마다 기업명 텍스트로 표시

여러 페이지에서 사용: from components.common_ui import ...
"""

import base64
import io
import re
from functools import lru_cache
from html import escape
from pathlib import Path

import pandas as pd

from components.icons import mask_icon_html


BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# 국기 썸네일 (속도 개선)
# ============================================================
# 원본 국기 PNG는 256px(약 15~40KB)라 표마다 여러 장을 HTML에 넣으면 화면이 무거워짐
# → 화면 표시 크기(22~30px)의 2배인 64px PNG로 줄여 캐시 (원본 파일은 그대로)
@lru_cache(maxsize=512)
def _flag_thumb(path_text, modified_ns, px):
    from PIL import Image
    with Image.open(path_text) as image:
        image = image.convert("RGBA")
        image.thumbnail((px, px), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def flag_thumb_base64(path, px=64):
    """국기 PNG → 작은 썸네일 base64 (파일이 없으면 None, 파일이 바뀌면 자동 갱신)"""
    path = Path(path)
    if not path.is_file():
        return None
    return _flag_thumb(str(path), path.stat().st_mtime_ns, px)


def loaded_mtime():
    """이 파일의 현재 수정 시각 (페이지에서 바뀌었는지 확인해 자동으로 다시 불러올 때 사용)"""
    return Path(__file__).stat().st_mtime_ns


LOADED_MTIME = loaded_mtime()   # 이 파일을 불러온 시점의 수정 시각

# ============================================================
# 1. 공통 크기·색상 설정 (여기만 바꾸면 세 화면에 같이 적용)
# ============================================================

TITLE_ICON_SIZE = 28            # 카드 제목 아이콘 크기 (px) - 03_weapon 기준
TITLE_ICON_GAP = 6              # 아이콘 ↔ 제목 글자 간격 (px) - 01_main 기준
TITLE_FONT_SIZE = 19            # 카드 제목 글자 크기 (px) - 03_weapon 기준 (01_main 제외)
TITLE_FONT_WEIGHT = 750         # 카드 제목 글자 굵기 - 03_weapon 기준

INFO_ICON_SIZE = 18             # 제목 옆 정보(ⓘ) 아이콘 크기 (px)
INFO_ICON_COLOR = "#2563eb"     # 정보(ⓘ) 아이콘 색 (파란색)
INFO_ICON_PATH = BASE_DIR / "images" / "01_main_images" / "info.png"



# ============================================================
# 2. 정보(ⓘ) 아이콘
# ============================================================

def info_icon_html(size=INFO_ICON_SIZE):
    """파란색 정보 아이콘 HTML (info.png 모양을 파란색으로 칠함, 파일이 없으면 ⓘ 글자)"""
    icon_html = mask_icon_html(INFO_ICON_PATH, size=size)

    if not icon_html:
        return (
            f'<span style="color:{INFO_ICON_COLOR}; font-size:{size}px; '
            f'font-weight:600; line-height:1;">ⓘ</span>'
        )

    # 여러 줄 HTML을 한 줄로 합쳐 마크다운 제목 안에서도 줄바꿈되지 않게 함
    icon_html = " ".join(icon_html.split())

    return (
        f'<span style="display:inline-flex; vertical-align:middle; margin-top:-3px; '
        f'color:{INFO_ICON_COLOR};">{icon_html}</span>'
    )


# ============================================================
# 4. 무기체계 분류 색상 (03_weapon·01_main과 동일)
# ============================================================

# 03_weapon.py PIE_COLORS와 같은 색 목록
# 최근 5년(2021~2025) 전 세계 수입 TIV가 큰 분류부터 순서대로 색을 붙임
WEAPON_COLOR_PALETTE = [
    "#1456AE", "#358DEF", "#32BDA0", "#FFC765", "#9274DC",
    "#F07869", "#59B85A", "#D49352", "#38B6CF", "#8290A8",
]
WEAPON_COLOR_FALLBACK = "#93A3B7"


@lru_cache(maxsize=4)
def _weapon_group_colors(tiv_mtime_ns, group_mtime_ns):
    processed = BASE_DIR / "data" / "processed"
    groups = pd.read_csv(processed / "weapon_type_10group.csv", encoding="utf-8-sig")
    tiv = pd.read_csv(processed / "tiv_delivery_yearly.csv", encoding="utf-8-sig")

    group_codes = list(dict.fromkeys(groups["weapon_type_group_en"].dropna()))
    tiv = tiv.loc[tiv["year"].between(2021, 2025)].copy()
    tiv["tiv_per_year"] = pd.to_numeric(tiv["tiv_per_year"], errors="coerce").fillna(0)

    # 03_weapon.py와 같은 계산: 분류별 합계를 큰 순서로 정렬
    ranking = (
        tiv.groupby("weapon_type_group_en")["tiv_per_year"].sum()
        .reindex(group_codes, fill_value=0)
        .sort_values(ascending=False)
        .index.tolist()
    )
    return {
        code: WEAPON_COLOR_PALETTE[i] if i < len(WEAPON_COLOR_PALETTE) else WEAPON_COLOR_FALLBACK
        for i, code in enumerate(ranking)
    }


def weapon_group_colors():
    """무기체계 영문 분류 코드 → 색상 {예: "artillery": "#1456AE"} (03_weapon 도넛과 동일)"""
    processed = BASE_DIR / "data" / "processed"
    return dict(_weapon_group_colors(
        (processed / "tiv_delivery_yearly.csv").stat().st_mtime_ns,
        (processed / "weapon_type_10group.csv").stat().st_mtime_ns,
    ))


# ============================================================
# 5. 도움말 말풍선 (정보 아이콘에 마우스를 올리면 표시)
# ============================================================
# - 테두리 모양만 04_country 기준 (1px 회색 테두리, 둥근 모서리 9px)
# - 나머지는 01_main 원래 도움말(브라우저 기본 말풍선) 느낌:
#   작은 글씨 12px, 좁은 여백, 그림자 거의 없음
# - 색: 밝은 모드 = 흰 배경·검은 글자 / 어두운 모드 = 어두운 배경·흰 글자 (화면 배경·글자색을 따라감)
#   배경색은 각 페이지의 테마 동기화 JS가 채우는 CSS 변수 사용
#   (01_main: --app-bg, 04_country: --di-country-donut-gap-color, 없으면 흰색)
# 사용법: 페이지에서 st.markdown(HELP_TOOLTIP_CSS, unsafe_allow_html=True)를 한 번 실행하고
#         제목 옆에 help_icon_html("설명")을 넣음

HELP_TOOLTIP_CSS = """
<style>
/* 말풍선은 position:fixed + 원래 자리(아이콘 아래)에 표시
   → 카드(높이 고정·스크롤 영역) 밖으로 나가도 잘리지 않고, 카드에 스크롤도 생기지 않음 */
.di-help { position:relative; display:inline-flex; align-items:center;
    vertical-align:middle; cursor:help; outline-offset:3px; }
.di-help-tip { position:fixed; align-self:flex-start;   /* 위치: 아이콘 왼쪽 위 기준 */
    margin-top:24px; margin-left:-6px;                   /* 아이콘 바로 아래로 */
    z-index:100000;
    width:max-content; max-width:560px; box-sizing:border-box;   /* 최대 너비 560px (기존 280px의 2배) */
    padding:5px 8px; border-radius:9px;                 /* 둥근 모서리: 04 기준 */
    border:1px solid rgba(128,128,128,.30);             /* 테두리: 04 기준 */
    /* 배경 = 현재 화면 배경색 + 회색 8% (밝은 모드: 연회색 / 어두운 모드: 짙은 회색)
       배경색 변수가 아직 없으면 투명 + 흐림 처리로 대신함 */
    background-color:transparent;   /* 실제 배경색은 HELP_TOOLTIP_JS가 띄울 때 카드 배경색으로 채움 */
    background-image:linear-gradient(rgba(128,128,128,.08), rgba(128,128,128,.08));
    -webkit-backdrop-filter:blur(12px); backdrop-filter:blur(12px);
    color:inherit;                                      /* 글자 = 현재 화면 글자색 */
    box-shadow:0 1px 3px rgba(0,0,0,.15);
    font-size:12px; font-weight:400; line-height:1.4; letter-spacing:normal;
    text-align:left; white-space:normal; word-break:keep-all;
    display:none;                                       /* 숨김 상태에서는 자리·스크롤 영향 없음 */
    pointer-events:none; }
.di-help:hover .di-help-tip,
.di-help:focus .di-help-tip,
.di-help:focus-within .di-help-tip { display:block; }
</style>
"""


def help_icon_html(text, size=INFO_ICON_SIZE, label="도움말"):
    """파란색 정보 아이콘 + 마우스를 올리면 나타나는 도움말 말풍선 HTML
    text: 설명 문구 (줄바꿈 \\n은 줄바꿈으로 표시, **글자**는 굵게 표시)"""
    tip = escape(str(text)).replace("\n", "<br>")
    # **글자** → 굵게
    tip = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", tip)
    # 물결표(~) 두 개 사이가 마크다운 취소선으로 바뀌지 않도록 글자 코드로 바꿈 (예: 1~3위 … 2021~2025)
    tip = tip.replace("~", "&#126;")
    return (
        f'<span class="di-help" tabindex="0" role="button" aria-label="{escape(label, quote=True)}">'
        f'{info_icon_html(size)}'
        f'<span class="di-help-tip" role="tooltip">{tip}</span>'
        f'</span>'
    )


# 도움말 말풍선 위치·색 보정 JS (01_main·04_country의 테마 동기화 컴포넌트 js 앞에 붙여 사용)
# - 위치: 아이콘 바로 아래, 화면 오른쪽·왼쪽·아래 끝을 넘지 않게 자동으로 밀어 넣음 → 잘리지 않음
# - 색: 말풍선을 띄울 때 실제 카드 배경색을 읽어 배경으로 사용 → 밝은/어두운 모드 자동 대응
HELP_TOOLTIP_JS = r"""
(function () {
  const KEY = "__diHelpTooltipV2";
  if (window[KEY]) return;
  window[KEY] = true;

  function cardBackground(el) {
    while (el && el !== document.documentElement) {
      const bg = getComputedStyle(el).backgroundColor;
      if (bg && bg !== "transparent" && !/rgba\([^)]*,\s*0\)$/.test(bg)) return bg;
      el = el.parentElement;
    }
    return getComputedStyle(document.body).backgroundColor || "#ffffff";
  }

  function place(help) {
    const tip = help.querySelector(".di-help-tip");
    if (!tip) return;
    tip.style.backgroundColor = cardBackground(help.parentElement);
    requestAnimationFrame(function () {
      const r = help.getBoundingClientRect();
      const w = tip.offsetWidth, h = tip.offsetHeight, gap = 6, edge = 8;
      let left = Math.min(Math.max(edge, r.left - 6), window.innerWidth - w - edge);
      let top = r.bottom + gap;
      if (top + h > window.innerHeight - edge) top = Math.max(edge, r.top - h - gap);
      tip.style.margin = "0";
      tip.style.left = left + "px";
      tip.style.top = top + "px";
    });
  }

  function onEnter(e) {
    const help = e.target && e.target.closest ? e.target.closest(".di-help") : null;
    if (help) place(help);
  }
  document.addEventListener("mouseover", onEnter, true);
  document.addEventListener("focusin", onEnter, true);
})();
"""

# ============================================================
# 6. KPI 큰 숫자 표기 (시안 5: 통화 기호·단위는 작게, 숫자는 크게)
# ============================================================
# 예) "2.71조 달러" → $2.71조 / "425.3억 달러" → $425.3억
#     "4.50%" → 4.50% (% 작게) / "TIV 14,895" → TIV(작게) 14,895
# 작은 글자 크기는 숫자 크기에 비례(em)라서 화면마다 숫자 크기가 달라도 같은 비율로 보임

_KPI_SMALL = "font-size:.5em; font-weight:700; opacity:.7;"


def kpi_value_html(value):
    """KPI 값 문자열 → 숫자는 그대로 크게, 통화 기호·단위·접두어는 작게 표시한 HTML"""
    text = str(value).strip()
    number = r"([+-]?[\d.,]+)"

    # 금액: "2.71조 달러", "425.3억 달러" → $ + 숫자 + 조/억
    match = re.fullmatch(number + r"\s*(조|억|만)?\s*달러", text)
    if match:
        unit = match.group(2) or ""
        return (
            f'<span style="{_KPI_SMALL} vertical-align:.55em; margin-right:.06em;">$</span>'
            f'<span>{escape(match.group(1))}</span>'
            + (f'<span style="{_KPI_SMALL} margin-left:.08em;">{escape(unit)}</span>' if unit else "")
        )

    # 비율: "4.50%", "0.7%p"
    match = re.fullmatch(number + r"\s*(%p|%)", text)
    if match:
        return (
            f'<span>{escape(match.group(1))}</span>'
            f'<span style="{_KPI_SMALL} margin-left:.06em;">{escape(match.group(2))}</span>'
        )

    # 접두어 + 숫자: "TIV 14,895"
    match = re.fullmatch(r"([A-Za-z가-힣]+)\s+" + number, text)
    if match:
        return (
            f'<span style="{_KPI_SMALL} margin-right:.15em;">{escape(match.group(1))}</span>'
            f'<span>{escape(match.group(2))}</span>'
        )

    return escape(text)
