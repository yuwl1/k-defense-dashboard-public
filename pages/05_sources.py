"""데이터 출처 화면 (시안 A: 한 페이지 표 중심)

내용은 아래 두 CSV에서 읽어 옴 → 출처를 고칠 때는 코드 대신 CSV만 수정
- data/sources/data_sources.csv  : 원천 데이터 목록
- images/**/credits.csv          : 이미지·아이콘·로고 출처 (이미지가 있는 폴더마다 하나씩, 화면에서 자동으로 합침)
"""

import importlib
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from components.header import render_header
from components.icons import mask_icon_html   # 검은 아이콘 → 테마 글자색

# common_ui.py를 고치면 새로고침만으로 반영 (다른 화면과 동일)
import components.common_ui as _common_ui
if _common_ui.loaded_mtime() != _common_ui.LOADED_MTIME:
    _common_ui = importlib.reload(_common_ui)
from components.common_ui import (            # 다른 화면과 같은 제목·도움말 스타일
    TITLE_ICON_SIZE, TITLE_ICON_GAP, TITLE_FONT_SIZE, TITLE_FONT_WEIGHT,
    HELP_TOOLTIP_CSS, HELP_TOOLTIP_JS, help_icon_html,
)


# ============================================================
# 공통 상단 헤더
# ============================================================
render_header(
    title="데이터 출처",
    description="대시보드에 사용한 데이터·이미지의 출처, 가공 기준, 이용 조건을 안내합니다.",
    page_file=__file__,
)


# ============================================================
# 1. 기본 설정
# ============================================================
ROOT_DIR = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT_DIR / "data" / "sources"
DATA_SOURCES_CSV = SOURCE_DIR / "data_sources.csv"
IMAGE_ROOT = ROOT_DIR / "images"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}   # 출처 누락 검사 대상

# 카드 제목 아이콘 (Material Symbols, 04_country와 같은 파일 사용)
ICON_DIR = ROOT_DIR / "images" / "04_country_images" / "icons"
MAIN_ICON_DIR = ROOT_DIR / "images" / "01_main_images"
ICONS = {
    "data": ICON_DIR / "description_black.png",
    "rule": ICON_DIR / "format_list_bulleted_black.png",
    "score": ICON_DIR / "hexagon_black.png",
    "caution": MAIN_ICON_DIR / "info.png",
    "image": ICON_DIR / "language_black.png",
}

# 분석 기간 (01_main과 동일)
LATEST_YEAR = 2025
RECENT_LABEL = f"최근 5년({LATEST_YEAR - 4}~{LATEST_YEAR})"

# 문의처 (팀 정보로 바꾸기)
CONTACT_TEXT = "K-방산 수출 후보국 대시보드 팀 · AI 교육 팀프로젝트 (비상업적 교육 목적)"

# 이용조건 배지 색: ok = 초록(출처 표기 등 이용 가능), check = 주황(약관 확인 필요), info = 파랑
CHIP_CLASS = {"ok": "ok", "check": "check", "info": "info"}


# ============================================================
# 2. 데이터 불러오기
# ============================================================
@st.cache_data(show_spinner=False)
def read_csv(path_text: str, modified_ns: int) -> pd.DataFrame:
    """CSV를 문자열로 읽음 (빈 칸은 빈 문자열). 파일이 바뀌면 캐시 자동 갱신."""
    return pd.read_csv(path_text, dtype=str, encoding="utf-8-sig").fillna("")


def load_table(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    return read_csv(str(path), path.stat().st_mtime_ns)


data_sources = load_table(DATA_SOURCES_CSV)
def load_image_credits():
    """images 아래 모든 폴더의 credits.csv를 합침 (폴더 열 자동 추가)"""
    frames = []
    for path in sorted(IMAGE_ROOT.rglob("credits.csv")):
        df = load_table(path)
        df["폴더"] = path.parent.relative_to(IMAGE_ROOT).as_posix()
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def find_missing_credits(credits: pd.DataFrame):
    """images 폴더의 이미지 중 credits.csv에 파일명이 없는 것 (폴더/파일명 목록)
    파일명 칸에 여러 파일을 적을 때는 ';'로 구분 (예: kai.png; kai_off.png)"""
    covered = set()
    for _, r in credits.iterrows():
        for name in str(r.get("파일명", "")).split(";"):
            if name.strip():
                covered.add(f'{r["폴더"]}/{name.strip()}')
    missing = []
    for path in sorted(IMAGE_ROOT.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            key = path.relative_to(IMAGE_ROOT).as_posix()
            if key not in covered:
                missing.append(key)
    return missing

image_credits = load_image_credits()

# ============================================================
# 3. 화면 요소 HTML
# ============================================================
def title_html(icon_key: str, text: str, tooltip: str = "") -> str:
    """카드 제목: 아이콘 28px + 19px 굵은 제목 (+ 파란 정보 아이콘)"""
    icon = " ".join(mask_icon_html(ICONS[icon_key], size=TITLE_ICON_SIZE).split())
    help_html = help_icon_html(tooltip) if tooltip else ""
    return (
        f'<div class="src-title" style="gap:{TITLE_ICON_GAP}px;">'
        f'<span class="src-title-icon">{icon}</span>'
        f'<span style="font-size:{TITLE_FONT_SIZE}px; font-weight:{TITLE_FONT_WEIGHT};">{escape(text)}</span>'
        f'{help_html}</div>'
    )


def chip(text: str, kind: str = "info") -> str:
    if not text:
        return '<span class="src-muted">-</span>'
    return f'<span class="src-chip {CHIP_CLASS.get(kind, "info")}">{escape(text)}</span>'


def link(url: str, label: str = "바로가기") -> str:
    if not url:
        return '<span class="src-muted">-</span>'
    return (f'<a class="src-link" href="{escape(url, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(label)} ↗</a>')


def table_html(headers, rows, left_cols=()) -> str:
    """제목행 파란 음영 표 (04_country 테이블 제목행과 같은 색)"""
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = ""
    for row in rows:
        cells = "".join(
            f'<td class="{"l" if i in left_cols else ""}">{cell}</td>'
            for i, cell in enumerate(row)
        )
        body += f"<tr>{cells}</tr>"
    return f'<div class="src-table-wrap"><table class="src-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def bullet_html(items) -> str:
    return '<ul class="src-list">' + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


# ============================================================
# 4. 스타일
# ============================================================
st.markdown(
    """
<style>
.src-title { display:flex; align-items:center; margin:2px 0 10px 0; line-height:1.3; }
.src-title-icon { display:inline-flex; margin-top:-4px; color:var(--main-icon-color, currentColor); }

.src-table-wrap { width:100%; overflow-x:auto; }
.src-table { width:100%; border-collapse:separate; border-spacing:0; font-size:13.5px; }
.src-table th { background:rgba(100,160,255,.10); font-weight:700; padding:9px 10px;
                text-align:center; white-space:nowrap; border:none; }
.src-table th:first-child { border-radius:10px 0 0 10px; }
.src-table th:last-child  { border-radius:0 10px 10px 0; }
.src-table td { padding:8px 10px; text-align:center; vertical-align:middle;
                border:none; border-bottom:1px solid rgba(128,128,128,.18); }
.src-table td.l { text-align:left; }
.src-table tr:last-child td { border-bottom:none; }
.src-table .src-sub { display:block; font-size:12px; opacity:.65; margin-top:2px; }

.src-chip { display:inline-block; padding:2px 9px; border-radius:10px; font-size:12px;
            font-weight:700; white-space:nowrap; }
.src-chip.ok    { color:#21c354; background:rgba(33,195,84,.15); }
.src-chip.check { color:#e8a317; background:rgba(255,170,0,.16); }
.src-chip.info  { color:#3b82f6; background:rgba(100,160,255,.15); }

.src-link { color:#2563eb !important; text-decoration:none; font-weight:600; white-space:nowrap; }
.src-link:hover { text-decoration:underline; }
.src-muted { opacity:.5; }
.src-folder { border:1px solid rgba(128,128,128,.25); border-radius:8px; margin:0 0 8px 0; }
.src-folder > summary { cursor:pointer; padding:9px 14px; font-size:14px; font-weight:600;
                        list-style:none; display:flex; align-items:center; gap:8px; }
.src-folder > summary::-webkit-details-marker { display:none; }
.src-folder > summary::before { content:"›"; display:inline-block; font-size:18px; line-height:1;
                                transition:transform .15s; }
.src-folder[open] > summary::before { transform:rotate(90deg); }
.src-folder[open] > summary { border-bottom:1px solid rgba(128,128,128,.18); }
.src-folder .src-table-wrap { padding:8px 10px 10px; box-sizing:border-box; }
.src-cut { display:inline-block; max-width:320px; overflow:hidden; text-overflow:ellipsis;
           white-space:nowrap; vertical-align:middle; }
           
.src-list { margin:0; padding-left:18px; font-size:14px; line-height:1.75; }
.src-list b { font-weight:700; }

.src-footer { font-size:12.5px; opacity:.6; text-align:right; margin-top:4px; }
</style>
"""
    + HELP_TOOLTIP_CSS,
    unsafe_allow_html=True,
)

# 도움말 말풍선 위치·색 보정 + 제목 아이콘 색(밝은 모드 검정 / 어두운 모드 흰색)
if hasattr(getattr(st, "components", None), "v2"):
    sources_theme_sync = st.components.v2.component(
        name="sources_theme_sync",
        html='<span class="sources-theme-sync" aria-hidden="true"></span>',
        css=".sources-theme-sync {display:block; width:0; height:0; overflow:hidden;}",
        js=HELP_TOOLTIP_JS + """
        export default function () {
            function applyTheme() {
                const app = document.querySelector(".stApp") || document.body;
                let bg = getComputedStyle(app).backgroundColor;
                if (!bg || bg === "rgba(0, 0, 0, 0)" || bg === "transparent") {
                    bg = getComputedStyle(document.body).backgroundColor;
                }
                const rgb = (bg.match(/[\\d.]+/g) || [255, 255, 255]).map(Number);
                const brightness = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2];
                document.documentElement.style.setProperty(
                    "--main-icon-color", brightness < 128 ? "#ffffff" : "#000000");
            }
            applyTheme();
            const key = "__kDefenseSourcesThemeSync";
            if (window[key]) clearInterval(window[key]);
            const timer = setInterval(applyTheme, 500);
            window[key] = timer;
            return () => {
                if (window[key] === timer) { clearInterval(timer); delete window[key]; }
            };
        }
        """,
    )
    sources_theme_sync(key="sources_theme_sync")


# ============================================================
# 5. ① 원천 데이터
# ============================================================
with st.container(border=True):
    st.markdown(
        title_html(
            "data", "원천 데이터",
            "Fitch 등급 원본과 KOTRA 국가정보 원문은 재배포 제한·저작권 때문에 "
            "공개 저장소에 포함하지 않으며, 가공 결과(점수·국가 목록)만 사용합니다.",
        ),
        unsafe_allow_html=True,
    )

    if data_sources.empty:
        st.info("data/sources/data_sources.csv 파일이 없습니다.")
    else:
        rows = [
            [
                f'<b>{escape(r["데이터"])}</b><span class="src-sub">{escape(r["내용"])}</span>',
                escape(r["제공기관"]),
                escape(r["기간"]),
                escape(r["사용화면"]),
                chip(r["이용조건"], r["조건구분"]),
                link(r["링크"]),
            ]
            for _, r in data_sources.iterrows()
        ]
        st.markdown(
            table_html(
                ["데이터", "제공기관", "기간", "사용 화면", "이용조건", "링크"],
                rows, left_cols=(0,),
            ),
            unsafe_allow_html=True,
        )


# ============================================================
# 6. ② 용어·가공 기준 / ③ 후보국 산정 방법 / ④ 해석 시 주의
# ============================================================
col_rule, col_score, col_caution = st.columns(3)

with col_rule:
    with st.container(border=True, height="stretch"):
        st.markdown(title_html("rule", "용어·가공 기준"), unsafe_allow_html=True)
        st.markdown(bullet_html([
            "<b>TIV</b>(Trend Indicator Value): SIPRI가 무기의 군사적 능력을 기준으로 매긴 "
            "추세지표값으로, <b>금액(달러)이 아님</b>",
            f"무기 이전은 <b>인도(Delivery) 연도</b> 기준, 기본 기간은 <b>{RECENT_LABEL}</b> 누적",
            "국가명은 <b>country_map_master.csv</b>(ISO A3) 기준으로 통일",
            "무기체계는 SIPRI 분류를 <b>10개 그룹</b>(weapon_type_10group.csv)으로 재분류",
            "국방비는 SIPRI <b>2024년 불변 달러</b> 기준. SIPRI 값이 없는 연도(UAE·카타르·우즈베키스탄 등)는 "
            "World Bank 명목 GDP × 국방비 비중으로 보완하고 GDP 디플레이터로 2024년 달러 환산",
            "Fitch 등급·KOTRA 국가정보 원문은 <b>공개 저장소에 포함하지 않음</b> "
            "(등급은 점수로 변환해 반영, KOTRA는 국가 목록만 사용)",
        ]), unsafe_allow_html=True)

with col_score:
    with st.container(border=True, height="stretch"):
        st.markdown(title_html("score", "후보국 산정 방법"), unsafe_allow_html=True)
        st.markdown(bullet_html([
            "<b>6개 지표</b>를 98개국 기준 0~100점으로 바꾸고 <b>CRITIC 가중치</b>(지표별 변동성·상관관계로 자동 계산)를 곱해 "
            "추천 점수 산출 (2021~2025년 데이터 → 2026년 순위)",
            "<b>HHI</b>: 공급국 집중도 — 공급국이 다양할수록 신규 진입 여지가 커 높은 점수",
            "<b>국방비</b>: 국방비 규모·GDP 대비 비중·연평균 무기 도입 TIV 종합",
            "<b>무기 매칭도·협력 관계</b>: 기업 강점 무기체계 수요, 한국·기업과의 거래 이력",
            "<b>GPI·신용도</b>: GPI 평화지수, 국가 신용등급(Fitch 등급을 0~100점으로 변환)",
            # "<b>순위 해석</b>: 한국은 분석에서 제외. 북한(UN 무기 금수조치)·러시아·벨라루스(대러 수출통제)는 "
            # "순위에는 포함되지만 <b>수출 대상에서는 제외</b>하고 해석",
        ]), unsafe_allow_html=True)

with col_caution:
    with st.container(border=True, height="stretch"):
        st.markdown(title_html("caution", "해석 시 주의"), unsafe_allow_html=True)
        st.markdown(bullet_html([
            "공개 데이터 기반으로 <b>비공개·미확인 계약은 반영되지 않음</b>",
            "데이터마다 <b>기준 시점이 다름</b> (SIPRI·GPI 2025년까지, Fitch 2025-09 등급까지 · 2026-10-01 공시 파일)",
            "TIV는 거래 규모 비교용 지표로, 실제 계약 금액과 다름",
            "후보국 순위는 <b>참고용</b>이며 정책·투자 판단의 근거가 아님",
            "AI 생성 이미지는 실제 장비와 차이가 있을 수 있음",
        ]), unsafe_allow_html=True)


# ============================================================
# 7. ⑤ 이미지·아이콘·로고 출처
# ============================================================
def license_kind(text: str) -> str:
    """라이선스 문구로 배지 색 결정"""
    if not text or "확인" in text:
        return "check"
    if "상표" in text or "AI" in text:
        return "check"
    return "ok"


def summary_rows(df: pd.DataFrame):
    """구분별 요약 (건수, 대표 저작자, 라이선스 종류)"""
    rows = []
    for group, part in df.groupby("구분", sort=False):
        # 라이선스는 많이 쓰인 순서로 최대 4종 표시
        licenses = [x for x in part["라이선스"].value_counts().index if x]
        authors = [x for x in part["저작자"].unique() if x]
        missing = int(((part["라이선스"] == "") | (part["저작자"] == "")).sum())

        if len(authors) > 2:
            author_text = f"작성자 {len(authors)}명 (아래 상세)"
        else:
            author_text = ", ".join(authors) or "-"

        chips = " ".join(chip(x, license_kind(x)) for x in licenses[:4])
        if len(licenses) > 4:
            chips += f' <span class="src-muted">외 {len(licenses) - 4}종</span>'
        status = (chip(f"확인 필요 {missing}건", "check") if missing
                  else chip("완료", "ok"))
        change = next((x for x in part["변경사항"] if x), "-")
        rows.append([
            f"<b>{escape(group)}</b>",
            f'<span style="white-space:nowrap;">{len(part)}건</span>',
            escape(author_text),
            chips or chip("", "check"),
            escape(change) if len(part) == 1 or group.startswith("아이콘 (Material") else "항목별 상세 참고",
            status,
        ])
    return rows


with st.container(border=True):
    st.markdown(
        title_html(
            "image", "이미지·아이콘·로고 출처",
            "구분별 요약입니다. 항목별 저작자·라이선스·원본 링크는 아래 '상세 목록'에서 확인하세요.\n"
            "'확인 필요'는 저작자 또는 라이선스가 아직 비어 있는 항목 수입니다.",
        ),
        unsafe_allow_html=True,
    )

    if image_credits.empty:
        st.info("images 폴더에 credits.csv 파일이 없습니다.")
    else:
        st.markdown(
            table_html(
                ["구분", "수량", "저작자/제공", "라이선스", "변경 내용", "상태"],
                summary_rows(image_credits), left_cols=(0, 2),
            ),
            unsafe_allow_html=True,
        )

        st.write("")

        def cut(text):   # 칸 너비를 넘으면 … 표시, 마우스를 올리면 전체 내용 말풍선
            return f'<span class="src-cut" title="{escape(text, quote=True)}">{escape(text) or "-"}</span>'

        # 상세 목록: 바깥 펼침 하나("상세 목록") 안에 이미지 폴더별 펼침
        # (Streamlit 펼침은 겹칠 수 없어서 안쪽은 HTML <details>로 표시)
        folder_groups = list(image_credits.groupby("폴더", sort=True))
        with st.expander(f"상세 목록 ({len(folder_groups)}개 폴더 · {len(image_credits)}건)"):
            for folder, part in folder_groups:
                rows = [
                    [cut(r["파일명"]), cut(r["항목"]), cut(r["저작자"]),
                     chip(r["라이선스"], license_kind(r["라이선스"])),
                     cut(r["변경사항"]), link(r["원본링크"])]
                    for _, r in part.iterrows()
                ]
                st.markdown(
                    f'<details class="src-folder"><summary>images/{escape(folder)} '
                    f'<span class="src-muted">({len(part)}건)</span></summary>'
                    + table_html(["파일명", "항목", "저작자/제공", "라이선스", "변경 내용", "원본"], rows)
                    + "</details>",
                    unsafe_allow_html=True,
                )

        # 출처 누락 검사: 폴더에는 있는데 credits.csv에 없는 이미지
        missing = find_missing_credits(image_credits)
        if missing:
            with st.expander(f"⚠️ 출처 누락 이미지 ({len(missing)}건) — 해당 폴더의 credits.csv에 추가 필요"):
                st.markdown(
                    table_html(["폴더", "파일명"],
                               [[escape("images/" + m.rsplit("/", 1)[0]), escape(m.rsplit("/", 1)[1])]
                                for m in missing]),
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(chip("모든 이미지 출처 등록 완료", "ok"), unsafe_allow_html=True)

        st.caption(
            "기업은 상표권 보호를 위해 로고 이미지 없이 기업명 텍스트로만 표시합니다. "
            "본 대시보드는 언급된 기업과 제휴·후원 관계가 없습니다. "
            "미 국방부(DVIDS) 이미지 사용은 미 국방부의 보증·후원을 의미하지 않습니다."
        )


# ============================================================
# 8. 하단 안내
# ============================================================
st.markdown(f'<div class="src-footer">{escape(CONTACT_TEXT)}</div>', unsafe_allow_html=True)
