"""
Defense Insight | 국가별 상세 분석 (실제 CSV 연동 버전)

- 실행: 프로젝트 루트에서 python -m streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path
import base64
import math
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.header import render_header
from components.icons import mask_icon_html
import importlib
# export_score.py를 고치면 Streamlit을 다시 시작하지 않아도 새로고침만으로 반영
# (예전 버전이 메모리에 남아 ImportError가 나는 것 방지 — common_ui와 같은 방식)
import components.export_score as _export_score
if getattr(_export_score, "LOADED_MTIME", None) != _export_score.Path(_export_score.__file__).stat().st_mtime_ns:
    _export_score = importlib.reload(_export_score)
from components.export_score import country_score, neighbor_countries   # dashboard_score.py 결과 (01·02와 공통)
# weight_custom.py(가중치 커스텀 공용 부품)도 고치면 새로고침만으로 반영
import components.weight_custom as _weight_custom
if getattr(_weight_custom, "LOADED_MTIME", None) != _weight_custom.loaded_mtime():
    _weight_custom = importlib.reload(_weight_custom)
from components.weight_custom import (   # 가중치 커스텀 공용 부품 (02·04 공통, 상태 공유)
    TOTAL, WEIGHT_NAMES, DEFAULT_WEIGHTS,
    init_weight_state, render_weight_popover, custom_weights, is_default_weights, weight_summary,
    applied_weights, is_customized,
)
# common_ui.py를 고치면 Streamlit을 다시 시작하지 않아도 새로고침만으로 반영되도록,
# 파일 수정 시각이 바뀌었을 때만 다시 불러옴 (바뀌지 않았으면 그대로 사용)
import importlib
import components.common_ui as _common_ui
if _common_ui.loaded_mtime() != _common_ui.LOADED_MTIME:
    _common_ui = importlib.reload(_common_ui)
from components.common_ui import (   # 01_main·03_weapon과 같은 공통 화면 요소
    TITLE_ICON_SIZE, TITLE_ICON_GAP, TITLE_FONT_SIZE, TITLE_FONT_WEIGHT,
    INFO_ICON_SIZE, info_icon_html,
    weapon_group_colors, WEAPON_COLOR_FALLBACK,
    HELP_TOOLTIP_CSS, HELP_TOOLTIP_JS, help_icon_html,
    flag_thumb_base64,   # 국기 썸네일 (속도 개선)
    kpi_value_html,   # KPI 숫자 크게·단위 작게 (시안 5)
)
from components.company_weapons import (
    COMPANIES,            # 한글 표시명 -> 기업 코드
    WEAPON_GROUP_KO,      # 무기체계 영문 분류 -> 공식 한글 분류명 (10개)
)


ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
MAPPING = ROOT / "data" / "mapping" / "country_map_master.csv"
FLAG_DIR = ROOT / "images" / "common" / "country"
COMMON_DIR = ROOT / "images" / "common" / "etc" # 국기·순위 아이콘 (프로젝트에 이미 존재)
LIGHT_ICON_DIR = ROOT / "images" / "04_country_images" / "icons"  # 사용자가 넣은 검은색 PNG
EMPTY = "—"
REFERENCE_YEAR = 2025
TIV_START_YEAR = 2021

# 기업명과 무기체계 분류의 유일한 기준은 components/company_weapons.py입니다.
# 아래 두 매핑은 기존 CSV의 '영문 기업명' 및 '예전 점수 열 접두어'를
# 공통 기업 코드에 연결하는 호환용 매핑이며 화면 표시명으로 사용하지 않습니다.
TRANSACTION_COMPANY_NAMES = {
    "hanwha_aerospace": "Hanwha Aerospace",
    "hanwha_ocean": "Hanwha Ocean",
    "hyundai_rotem": "Hyundai Rotem",
    "hd_hyundai": "HD Hyundai Heavy Industries",
    "lig_nex1": "LIG Nex1",
    "kai": "KAI",
}
COMPANY_METRIC_PREFIX = {
    "hanwha_aerospace": "hanwha_aerospace",
    "hanwha_ocean": "hanwha_ocean",
    "hyundai_rotem": "hyundai_rotem",
    "hd_hyundai": "hyundai_heavy_industries",
    "lig_nex1": "lig",
    "kai": "kai",
}
TRANSACTION_TO_DISPLAY_NAME = {
    TRANSACTION_COMPANY_NAMES[code]: display_name
    for display_name, code in COMPANIES.items()
    if code in TRANSACTION_COMPANY_NAMES
}

DEFAULT_COUNTRY_NAMES = {"POL": "폴란드", "KOR": "대한민국", "USA": "미국", "ARE": "아랍에미리트"}
DEFAULT_FLAGS = {"POL": "🇵🇱", "KOR": "🇰🇷", "USA": "🇺🇸", "ARE": "🇦🇪"}
RADAR_LABELS = ["HHI", "국방비", "무기 매칭도", "협력 관계", "GPI", "신용도"]


# images/common에 이미 보관된 순위 아이콘 파일명
RANK_ICON_FILES = {
    1: "rank-1.png",
    2: "rank-2.png",
    3: "rank-3.png",
    4: "rank-4.png",
    5: "rank-5.png",
}


# 업로드된 카드 아이콘 8개(24×24 PNG)를 코드에 포함했습니다.
# 아이콘 경로를 따로 관리하지 않아도 pages/04_country.py 하나로 실행됩니다.
CARD_ICON_PNG = {
    "bar_chart": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAbklEQVR4AeyRUQrAMAhDu93D+x/Mg2wIFcR8pIXto5CC1Gpq4HmPn48MKOBlRO7+1KCTp2DZYOq3LxlQZICoLjJyOoEIwIDot9syGLGnGp2hEHUi8BYiQNILgMjMrhr5odYiZ/Xsg0E2vrrPN3gBAAD//2cu5h4AAAAGSURBVAMADIMwMZFfR8YAAAAASUVORK5CYII="),
    "donut_large": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAACI0lEQVR4AcSUOU4rQRCGPXb6TuA1eUv0nvTYI4hYIrZbgAQBEhwCJAKQ4BZsEUsEETsSRCyJ1xOQ2sNXlv/WDMwIG4GwulxVf1fV393TXcnEF/++n6BYLHaXy+VHxNdmzUZukX5hcTp2B9Vq9T8F/GQyeUnyT+T1+AtwajGlUmkQO3JEElQqlY1Go3EdmREBep53TM5uxFTiDQErWvN9fyYYzC4mcrmcJ8xsYsbkm8YfJ3fb7KCECFjFbybnEI0LK5bJZPYESOfz+QObo/ChMPQkxzWCdiNEQPC9m0kkrijQF/AjTYhGmdhBmoPjOmgarT9HUKvVultYU1G8p2m08UfsVDCMmzcs3xHU6/VVgeglpKPBd3JHk0qltpTsCADcVWNFK/gdDb7TkRI46h+ygwTCPqxZmCdRkU8lUNGg/lQC3oEvEUmQ4EQgQYuy29W0FndzuKrPynMEfPkFgehlpKNBa3EPjhs5rWRHkE6nrwSaZhfW5Mx8V4gNtYhCoeBulCOwKmztj+mWWJs+b9mxitZgL3dSAVxRe9lyw80um80+MLOOaPSyOp/zHRcgTeFRm2NR7oExt0PrcEeFHyYwgHs8T9Km2RLOd9eKyTebmH35pvH3yA21DMNDR2SACTuZ5el3md2OcCxD5ExExUYSWCBP/4YVeazemt6TYa/kDn/AYjgWd8XBQiOWQFHcCGvbv6yQMLORf8iZsDj9LkFcYrv4CwAAAP//VXflAgAAAAZJREFUAwDEgsYxYYKtIwAAAABJRU5ErkJggg=="),
    "finance_mode": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABYElEQVR4AcxRSU7DQBD02AcOgKII5eJVfggS9/AH7vyAD/ADeAB/CFcufMTbBRCKgsQBWTZVKGPNDHbGUpRNLnVNz3RVd8d1dvw7ToOiKFoJ2wKOcwJb1+r94SeQu2ZUOxvLDz/B2E6H3u13Au5ZYqijvrysUaN8t98JpKsZm6a5NHM8CyEWjFEUgYp3chPWCeq6niZJ8sqoFkNxEYbhNXNYzUfbtjNyE1aDNE2XeZ77jLLYEP9E/gJwOAmjCqtBVVW3EKyyLLuThbJzGC+RmwKdOE0I5oheA8/zTnlJcez/gdx13Xus4oWcAF/BeEKuCvKs4p8BxX3f/1bFIXSzLrqC8FtZll84nwNd5+R90Az6xFE0x0qegBNwfjP8oWckmzrnPaEZmJ3jwRwiz4gOpvgBFxBf8UzOaINmoK4FhZ04ePfFcTwZK84izSAIgkcWr/HXOR9tA81gG6Gh2p0b/AIAAP//65NBAgAAAAZJREFUAwAoOKUxezIQAQAAAABJRU5ErkJggg=="),
    "language": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAACgklEQVR4AcSUPXITQRCFZ/VzBlToB8kBjkiMA98CV+GM3IRQZUc4BUcmgAwOQGQFcAmT2BERVUayfgrdQVot7+uaWY9WEnZgl13ztl+/7umeaa235O757+EbTCaTjeFweCZkBZwRu2kAa28wHo+3KDidTi9VZEcorh1i5JBbDAZ/ZQNt+jKfz899UpplWd/zv7LAeS2V78hlD7yIpQaDweBISfsCa6/ZbFaSJGnjiD8GcDTxiviewNrX3g+QGAsNRqNRQxvfkzCbzToq0NWmA3zhlxCWcWLkkEtAe9/1+/0teMBCA39tp8TDTqdjYxE/IVljeIEFgYcYueKHxMrlchgtrssb6PRPpZQF5nuimdpbgw9KpdJl0OBoIGg6nB0EzdeCXjdQwjdT7uAR18pvoLrPBaeZJgE66S6arv8jaMGiESMnaFg0wWrJXt8ApwjN2t4e6T2huEyLcopx8+MbmBA/dMrE+5m3sTEtyoljOf9vA81yQKZsuAmuIWiylmPiikfc4Cfx8FZg5XcF1i5+DIn2+8h2C7okZ7UgeYNqtfoK4S4Q18ob1Gq1Pypu3xbN9YA3AkizlabpBj6Am6gHPmCPXFu+lvG8AZ6SbNaa68der2dc+lvB6T/0OxZE3GLksoeYXtv8FTWfR0Cj0RiJfxZcpVLpabYvdbpP+MIzISzjxMgh1we+1uv1C8/NLNwARZve6DTHcOFUBWayV4LTx20C4MKVj52K83k51t7X8BhLDQi2Wq0jzTlcle/TE3SN8BGAC2jEHLnskba0VjYgq91uX+hEqpdsyl/4QspnnSu4SQ65CKuwtkFI1u/yW0W2hfwb5fk2sZC3zt7YYN3G2+r/AAAA//8qAWoUAAAABklEQVQDAHE5QkD6yB6fAAAAAElFTkSuQmCC"),
    "paid": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAACtUlEQVR4AcSVO4sTURzFZ2LSrM2KhUnIC0H9AKZYdHHFR6Ol2Kio2Nm5hV/CRu1sBGXFSkELLUTBFSU26awElTwgSaXNpshrPL8h//FmkmzSyC738H+fc+/NTTbh/ee/vRdot9uHG41GRQhiqFBbdAFzT9BqtTYg7Pf7P0SyJsTXGjV66I0XLZ4pUK/XnwwGg4/jpq7v++fy+bzvIgiCDdX/CB69zODHMSWgxvsivEEjJCLdn8vlPhCzW4BfKBQ+qXaAHmJmmMV3MSHAUdV4hwYN+5DgAxHfxQL5oSA+PfTiMwsHvmFCgKNSGI1G61hDs9kcyL8n2DojkcACrM0YBzkQCYjkKAmhWywWv8iGq1arresa9olgk50C7fQ6RYlcwoLxTBff4fIiAZE8pyhcFqKVTCaPEEjgFRboM9lCSHhJ7CCcdbj+CajpuOBp6C3WkM1mn+FL6JdOcw1/HpzZkIu+6AQEs6Dr6Gv3ZWqJRGJL18IX7j3xMlgoAInut6rdScvnCvjAzyKkuz5IfTcsJWAEuvsXEkpJ6QQ5newbdje4Al9p1JflFNagXV7UbncsxkqogpVQGmtwZkMu8pFAKpW6SkJDr7EGvYgr8lck8lg2XJ1O51DoeF5vbENjs8ZFMhJIp9M/SQirzk54VaGw8rckwgcc9Hq9tmJvOByWsGA8s4rvcE08U09P8TQN2sk21qB793Xf4U8IOZ3qEblSqdQiBjZjHORAdAKCTCazreGn+OxW7/4kPtBLeogF+v25jQX00IvPLBz4hgkBkhq+qcYH+Hr3nzW8I1wgZtcAX8Tnlf9NDzEzzOK7mBKgqMZN56gryr0RWXj/ZkX8TvnwzullRvHUmilAF0dlt7rbY4qrQnxVqdFDb7xo8VwBa9Cb/y6SsjDxH01xmZr1zbMLBeYNLpv/CwAA//8r/7vcAAAABklEQVQDAPofVUD505FhAAAAAElFTkSuQmCC"),
    "hexagon": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABuklEQVR4nL3VsY8NURQG8N9780qJRCRUCnRbIFmiUVDpiIJWYvcPkCglKo1EolISpYqCRoPEkpAIkahIdovVSTYahN2nmDvZM3fnjjeIL7mZmXvO+c5375x7LrOjwiiNakDcbzEuEFbJ9scYYRK+j+ExnuFEmJ8k30GIivfjFqbZuIN9hZgixkHNdlzBl0T4GRdxCWtpbg2XsS3EF7ctLvM8PgS1N7En2PfidrC/x7kCV0v5PJZC4EMcCX4T7f9yHE+D/yPMJa7WSpqPhvwNzgR7U6LRv9nzERbwMcU+yThbS3qJnzgUFPeVYhUSHU2xryJnV3CjtkqKNnoSrAffb+nZ8u9Tt95ji5gm37hlMyUYimnX5L9M0In/niAuc0jHLPrmCUbqKthQ/7jeo2/zgDYFUay4/KC9xulgzztmfiecxbsUu9QlvlFyGM9tHv37OJgliq1iHg+C/4vEsaVVNKqa5wUsp6AfuI5dwXc3bqhP7hQrWMw4OhHb9Q5cxddEsqruOYv4lOa+4xp2BuKZKjPu7xzu2nrh3MOB4Be3bibkV+ZJdSN7i1MZ8eArMyIv1XFh/q9RFd578Qsve11KfMj1EgAAAABJRU5ErkJggg=="),
    "pentagon": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABz0lEQVR4AcxTPUvDQBhO0hILxYpDUEmbP2Fxd3DwRzgpLrq6OOnk4qaLCE6C+FNEh46FUkqbEsVF0E0p8XmO3nFtL+m1UGi5p/e+l+fjXtJ6zoI/yxUQx/Eb8DrL0FYTdDqdTRinMN4G6qxbrVaAeuqaGgCz+2Kx+E4n13V/sBNOqVT6xLNb9LkrNwAGvPURHWB+Xq1WK7VarZKm6RnPgJMhB6V5GQMgOgVoLlQwXgGuRIOvKIqu0fsoxSIXOBbN2NdEQL/f/wDnBuB6xI1xefeXjQ4c/vEZzh4Arrter5ew0KECcIMdANOnGyR4nhfB4IB1HsA5xPsIyUHoFj2SJKmzJ1QAmhfAAakBkRuGYczeBkEQJNSA2wCcwWCgfsp6wAUfYoQv7nNCaoUXPVQAbnDJA2AXmHcJreblqADdsdvtruu9TZ2lGQ8QoxUKhWcbU52Ddyc1wkM+GwmQo+E97EmC7Y4AoZEeUjcSIA+5t9vtNe42yOOaAsSIvu8/2ZiTo3GFlmcSEwHaiPuSZLELrqZVkokA9QRFs9lcxZa7pnGyAsSo5XL5m3/9PJAzvIHQDGu1GQNMoypFRpGlMQbQAwJ3FlBjQmaAiTzP2cID/gEAAP//sxLBZQAAAAZJREFUAwBG/a0x/3ZOkgAAAABJRU5ErkJggg=="),
    "format_list_bulleted": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAqUlEQVR4AexUwQnAIAxsu4e72MnrLg7SnmBCEkFbqz/F4BGTOziDxzZ5LYGmwcqiGKNH3Dl8s/tFgRJA/YWgzTgLknDzJIJ0WoGUGxpW4BTsjJ1z+5cQHJsSAElAEFmQhb1YCfSS1PqUAB5zTVHhlrIItzw5EouHpwGonujlrQRAtKaIrSGgLEKS/x+JMb7N/0fWoJe3FeCLUcAKrCkqnLUWFQV/E9MFHgAAAP//wtKOTwAAAAZJREFUAwCrWMYxgtn6kAAAAABJRU5ErkJggg=="),
    "switch_access_shortcut_add": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABNElEQVR4AcSVMW7CMBiF4yrqWHWqFLXJ1Ct07hGQ2omLMLAzcACuwAFY2BlZWWFJwsTECcx76M+AEfgZhEA8PVux3+ffjpWX7MG/5wOapvGXpBT//ArKsnSdlBWHY+QKsE17m9y5da+bBGjbdoiYNyhDNe90VRLAez+ywC9z2aKAuq57lrbH6rfWli0KcM5NLK1vzm06HnzXv+ZRACZ/Qgyd0y8JL8HxvoTPFUA4J6l/NyBcedi/GxArRwGsGYKV/dND4c06OfCwrwD+LHRqnmRRAFa0ssRX3Ikfa58Zxp1U0g2IAjgQN/mXjjuxpKdIAlRVtUDoBspwFp6uSgIwDFvwTacIgQZsxyQDGASIw3bN2IbGUPSfBGAatquX5/kH2tJ3IRmA4Kwoih2qkb4LNwEIUXUAAAD//6PC4ZoAAAAGSURBVAMA6SpoMdQ1R38AAAAASUVORK5CYII="),
    "description": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAApUlEQVR4AeyVUQ6AIAiGy3t4lzpZ3ayu4jxIUVsbUxCmlj7UokyBzz90muHl63uA934COyRzzq0a8ZSCTRVozKKBUIA7v7V25Ox2gIdRQFgAxKtuCVIMuGaRglQBpCDVAA/kemPLAlDFx0lxOwuAE0jt9gBpR/evgCoo7utfwV+DdvtA+vfhOLeaKAUz56zoj2IjAKzxHYw9zYSxPZxEBAgdSr9PAAAA//9Kj2+BAAAABklEQVQDAHuysjFLq6qNAAAAAElFTkSuQmCC"),
}


def card_icon_html(icon_key: str, size: int = 30) -> str:
    """브라우저의 실제 테마 글자색으로 아이콘을 표시합니다.

    images/04_country_images/icons/<name>_black.png를 우선 사용합니다.
    일부 파일이 누락되거나 폴더 안에 한 단계 더 들어 있어도 찾아보고,
    없으면 원본 내장 아이콘을 마스크로 사용합니다. 밝은 회색으로 되돌아가지 않습니다.
    """
    filename = f"{icon_key}_black.png"
    path = LIGHT_ICON_DIR / filename
    if not path.is_file():
        # ZIP을 기존 폴더 안에 풀 때 생기는 하위 폴더도 지원합니다.
        path = next((p for p in LIGHT_ICON_DIR.glob(f"**/{filename}") if p.is_file()), None)
    try:
        icon_bytes = path.read_bytes() if path is not None and path.is_file() else CARD_ICON_PNG[icon_key]
    except OSError:
        icon_bytes = CARD_ICON_PNG[icon_key]
    encoded = base64.b64encode(icon_bytes).decode("ascii")
    return (
        f'<span class="di-theme-icon" role="img" aria-label="{escape(icon_key)}" '
        f'style="width:{size}px;height:{size}px;'
        f'--di-icon-src:url(\'data:image/png;base64,{encoded}\');"></span>'
    )


render_header(
    title="국가별 상세 분석",
    description="선택한 국가의 핵심 지표와 한국 기업의 수출 기회를 상세히 분석합니다.",
    page_file=__file__,
)

def source_path(*names: str) -> Path | None:
    """기존 팀 파일명과 첨부 CSV 파일명을 함께 지원합니다."""
    for name in names:
        candidate = PROCESSED / name
        if candidate.is_file():
            return candidate
    return None


@st.cache_data(show_spinner=False)
def read_csv(path_str: str, stamp: int) -> pd.DataFrame:
    """파일 변경 시 캐시 갱신. 누락값 문자열 'NaN'은 결측치로 취급."""
    return pd.read_csv(path_str, encoding="utf-8-sig", low_memory=False)


def get_table(*file_names: str) -> pd.DataFrame:
    path = source_path(*file_names)
    if path is None:
        return pd.DataFrame()
    try:
        df = read_csv(str(path), path.stat().st_mtime_ns).copy()
        for col in ("iso_a3", "recipient_iso_a3", "supplier_iso_a3"):
            if col in df.columns:
                df[col] = df[col].astype("string").str.strip().str.upper()
        if "year" in df.columns:
            df["year"] = pd.to_numeric(df["year"], errors="coerce")
        return df
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        st.warning(f"{path.name} 파일을 읽지 못했습니다: {exc}")
        return pd.DataFrame()



def flag_file(iso_a3: str) -> Path | None:
    """images/common의 ISO 대문자 국기를 우선 표시. 이전 flags 경로도 호환."""
    code = str(iso_a3).strip().upper()
    candidates = (
        COMMON_DIR / f"{code}.png",
        FLAG_DIR / f"{code.lower()}.png",
        FLAG_DIR / f"{code}.png",
    )
    return next((path for path in candidates if path.is_file()), None)


def flag_widget(iso_a3: str, width: int = 30) -> None:
    """국기 PNG가 없는 경우에도 오류 없이 코드/대체 아이콘을 표시."""
    path = flag_file(iso_a3)
    if path is not None:
        st.image(str(path), width=width)
    else:
        st.write("🌐")


def rank_icon_html(rank: int, size: int = 30) -> str:
    """순위 아이콘 (03_weapon과 동일)
    1~3위: 트로피 원본 색 / 4위 이후: 마스크 → 다크 모드에서도 테마 글자색(흰색)으로 표시"""
    file_name = RANK_ICON_FILES.get(rank)
    path = COMMON_DIR / file_name if file_name else None
    if path is None or not path.is_file():
        return f"<strong>{rank}</strong>"
    if rank > 3:
        return " ".join(mask_icon_html(path, size=size).split())
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return (f'<img src="data:image/png;base64,{encoded}" alt="{rank}위" '
            f'style="width:{size}px;height:{size}px;object-fit:contain;display:block;">')


def flag_icon_html(iso_a3: str, size: int = 27) -> str:
    """원형 국기 HTML (03_weapon과 동일)"""
    path = flag_file(iso_a3)
    if path is None:
        return ""
    encoded = flag_thumb_base64(path)   # 64px 썸네일 (원본 256px 대신, 속도 개선)
    return (f'<img src="data:image/png;base64,{encoded}" alt="" '
            f'style="width:{size}px;height:{size}px;border-radius:50%;'
            'object-fit:cover;flex-shrink:0;">')


# 주요 공급국 표: 03_weapon '최대 수입국 TOP 5'와 같은 형식
SUPPLIER_TABLE_CSS = """
<style>
.country-table-header {
    display:grid; gap:6px; padding:12px 8px; border-radius:10px;
    background:rgba(100,160,255,.10); font-size:13px; font-weight:700;
}
.country-table-header > span {
    display:flex; align-items:center; justify-content:center; text-align:center; min-width:0;
}
.country-table-header > span:nth-child(2) { justify-content:flex-start; padding-left:6px; }
.country-supplier-cols { grid-template-columns:40px 150px 52px minmax(0,1fr); }   /* A안: 국가 열 150px 고정 (가장 긴 공급국명 '남아프리카공화국' 한 줄) */
.country-supplier-row {
    display:grid; gap:6px; align-items:center; padding:16px 8px;
    border-bottom:1px solid rgba(128,128,128,.15); font-size:13px; box-sizing:border-box;
}
.country-supplier-row:last-child { border-bottom:none; }
.country-supplier-row > * { justify-self:center; text-align:center; }
.country-supplier-row > .country-supplier-cell {
    justify-self:stretch; display:flex; align-items:center; justify-content:flex-start;
    gap:7px; min-width:0; padding-left:6px; font-weight:650; text-align:left;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;   /* 국가명 줄바꿈 금지 */
}
.country-supplier-row > .country-supplier-share {
    justify-self:stretch; display:flex; flex-direction:column; align-items:center; gap:5px;
}
.country-share-track {
    width:100%; height:9px; border-radius:5px; background:rgba(100,160,255,.15);
    overflow:hidden; display:block;
}
.country-share-fill { display:block; height:100%; background:#5B9CF5; border-radius:5px; }
</style>
"""


def full_country_names() -> dict[str, str]:
    """95개국 밖의 공급국(KOR 포함)도 한국어 국가명으로 표시."""
    if not MAPPING.is_file():
        return {}
    try:
        master = read_csv(str(MAPPING), MAPPING.stat().st_mtime_ns)
        if not {"iso_a3", "country_name_ko"}.issubset(master.columns):
            return {}
        return {
            str(row.iso_a3).strip().upper(): str(row.country_name_ko).strip()
            for row in master[["iso_a3", "country_name_ko"]].dropna().itertuples(index=False)
        }
    except (OSError, UnicodeError, pd.errors.ParserError):
        return {}


def numeric(df: pd.DataFrame, column: str) -> pd.Series:
    if df.empty or column not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[column], errors="coerce")


def as_number(value) -> float | None:
    try:
        val = float(value)
        return val if math.isfinite(val) else None
    except (ValueError, TypeError):
        return None


def fmt(value, digits: int = 1, suffix: str = "") -> str:
    n = as_number(value)
    return EMPTY if n is None else f"{n:,.{digits}f}{suffix}"


def country_rows(df: pd.DataFrame, iso: str, iso_field: str = "iso_a3") -> pd.DataFrame:
    return df.loc[df[iso_field].eq(iso)].copy() if not df.empty and iso_field in df.columns else pd.DataFrame()


def latest_record(df: pd.DataFrame, iso: str, latest: int = REFERENCE_YEAR) -> pd.Series | None:
    rows = country_rows(df, iso)
    if rows.empty or "year" not in rows:
        return None
    rows = rows.loc[rows["year"].eq(latest)]
    return rows.iloc[0] if not rows.empty else None


def fetch_country_names() -> dict[str, str]:
    """country_map_master.csv를 기준으로 분석 국가 목록 생성."""

    if not MAPPING.is_file():
        st.error(f"국가 마스터 파일을 찾을 수 없습니다: {MAPPING}")
        st.stop()

    try:
        master = read_csv(str(MAPPING), MAPPING.stat().st_mtime_ns)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        st.error(f"국가 마스터를 읽지 못했습니다: {exc}")
        st.stop()

    countries = {}

    for row in master.to_dict("records"):
        code = str(row.get("iso_a3", "")).strip().upper()

        # 대한민국과 쿠바는 분석 대상에서 제외
        if code in {"", "NAN", "KOR", "CUB"}:
            continue

        name = row.get("country_name_ko")

        countries[code] = (
            str(name).strip()
            if pd.notna(name) and str(name).strip()
            else DEFAULT_COUNTRY_NAMES.get(code, code)
        )

    if not countries:
        st.error("분석 대상 국가 목록이 비어 있습니다.")
        st.stop()

    return dict(
        sorted(
            countries.items(),
            key=lambda item: (item[0] != "POL", item[1])
        )
    )
    """최종 평가의 95개국을 기준으로 선택 목록을 만듭니다.

    final_score_1.csv / final_score.csv의 iso_a3를 우선 사용합니다.
    평가 파일이 없는 개발 환경에서는 97개국 마스터에서 CUB, KOR을
    제외한 95개국만 표시합니다. 한국(KOR)은 거래 기록의 공급국으로는 유지합니다.
    """
    master_names: dict[str, str] = {}
    if MAPPING.is_file():
        try:
            master = read_csv(str(MAPPING), MAPPING.stat().st_mtime_ns)
            for row in master.to_dict("records"):
                code = str(row.get("iso_a3", "")).strip().upper()
                if code and code != "NAN":
                    name = row.get("country_name_ko")
                    master_names[code] = (
                        str(name).strip()
                        if pd.notna(name) and str(name).strip()
                        else DEFAULT_COUNTRY_NAMES.get(code, code)
                    )
        except (OSError, UnicodeError, pd.errors.ParserError) as exc:
            st.warning(f"국가 마스터를 읽지 못했습니다: {exc}")

    # 95개국 최종 평가 파일을 기준 목록으로 사용합니다.
    evaluation = get_table("final_score_1.csv", "final_score.csv")
    if not evaluation.empty and "iso_a3" in evaluation.columns:
        evaluation_codes = set(evaluation["iso_a3"].dropna().astype(str).str.strip().str.upper())
        evaluation_codes.discard("CUB")
        evaluation_codes.discard("KOR")
        evaluation_codes.discard("NAN")
        if len(evaluation_codes) != 95:
                    st.warning(f"최종 평가 CSV의 분석 국가 수가 예상한 95개국과 다릅니다: {len(evaluation_codes)}개국")
        countries = {code: master_names.get(code, DEFAULT_COUNTRY_NAMES.get(code, code))
                     for code in evaluation_codes}
    else:
        # 프로젝트에 최종 평가 파일이 아직 배치되지 않았을 때의 기본 목록
        countries = {code: name for code, name in master_names.items()
                     if code not in {"CUB", "KOR"}}
        if not countries:
            st.error("95개국 선택 목록을 만들 수 없습니다. final_score.csv 또는 국가 마스터 파일을 확인해 주세요.")
            st.stop()
        if len(countries) != 95:
            st.warning(f"국가 마스터 기반 분석 대상이 예상한 95개국과 다릅니다: {len(countries)}개국")

    return dict(sorted(countries.items(), key=lambda item: (item[0] != "POL", item[1])))


def radar_figure(values: dict | None) -> go.Figure:
    """후보 적합도 구성 점수 6개 축 (dashboard_score.py의 0~100점 지표)"""
    fig = go.Figure()
    if values:
        r = [values.get(label) for label in RADAR_LABELS]
        fig.add_trace(go.Scatterpolar(
            r=r + r[:1], theta=RADAR_LABELS + RADAR_LABELS[:1],
            mode="lines+markers", fill="toself",
            line=dict(color="#5B9CF5", width=2), fillcolor="rgba(91,156,245,0.25)",
            marker=dict(size=7, color="#5B9CF5"),
            hovertemplate="%{theta}: %{r:.1f}점<extra></extra>", showlegend=False,
        ))
    else:
        fig.add_trace(go.Scatterpolar(
            r=[None] * len(RADAR_LABELS), theta=RADAR_LABELS,
            mode="lines", showlegend=False, hoverinfo="skip",
        ))
    # 축 이름 아래에 점수를 굵게 표시 (마우스를 올리지 않아도 바로 읽힘)
    tick_text = ([f"{label}<br><b>{values[label]:.1f}</b>" if values.get(label) is not None else label
                  for label in RADAR_LABELS] if values else RADAR_LABELS)
    grid_color = "rgba(128,128,128,0.28)"   # 밝은·어두운 모드 공통으로 옅은 격자
    fig.update_layout(
        polar=dict(
            gridshape="linear",
            bgcolor="rgba(91,156,245,0.04)",   # 흰 배경 대신 카드 색에 가까운 투명 배경
            radialaxis=dict(range=[0, 100], showticklabels=False, ticks="", showline=False,
                            gridcolor=grid_color),
            angularaxis=dict(categoryorder="array", categoryarray=RADAR_LABELS,
                             tickmode="array", tickvals=RADAR_LABELS, ticktext=tick_text,
                             tickfont=dict(size=13), direction="clockwise", rotation=90,
                             gridcolor=grid_color, linecolor=grid_color),
        ),
        margin=dict(l=58, r=58, t=58, b=48), height=308,   # 위 여백을 늘려 차트를 아래로 · 아래쪽 축 이름+점수 두 줄 공간 확보
        paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
    )
    if not values:
        fig.add_annotation(x=0.5, y=0.5, xref="paper", yref="paper",
                           text="점수 데이터 준비 중", showarrow=False)
    return fig


def blank_plot(message: str, height: int = 250) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        height=height, margin=dict(l=15, r=15, t=10, b=15),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        annotations=[dict(text=message, x=0.5, y=0.5,
                          xref="paper", yref="paper", showarrow=False)],
    )
    return fig


def get_budget_data(milex: pd.DataFrame, iso: str) -> tuple[pd.DataFrame, pd.Series | None, float | None]:
    rows = country_rows(milex, iso)
    if rows.empty:
        return rows, None, None
    rows = rows.loc[rows["year"].between(2015, REFERENCE_YEAR)].sort_values("year")
    rows["military_expenditure_usd"] = numeric(rows, "military_expenditure_usd")
    rows["military_expenditure_gdp_pct"] = numeric(rows, "military_expenditure_gdp_pct")
    now = latest_record(rows, iso)
    # '최근 5년 증가율': 2020년 대비 2025년 누적 증가율 (CAGR 아님).
    old = rows.loc[rows["year"].eq(REFERENCE_YEAR - 5), "military_expenditure_usd"].dropna()
    current = as_number(now.get("military_expenditure_usd")) if now is not None else None
    before = as_number(old.iloc[0]) if not old.empty else None
    growth = (current / before - 1) * 100 if current is not None and before and before > 0 else None
    return rows, now, growth


def get_tiv_data(groups: pd.DataFrame, iso: str) -> tuple[float | None, dict[str, float] | None]:
    """공통 무기체계 10개 분류를 사용하여 최근 5년 도입 TIV 집계."""
    rows = country_rows(groups, iso, "recipient_iso_a3")
    if rows.empty:
        return None, None
    rows = rows.loc[rows["year"].between(TIV_START_YEAR, REFERENCE_YEAR)]
    if rows.empty:
        return None, None

    result: dict[str, float] = {}
    for group_en, group_ko in WEAPON_GROUP_KO.items():
        col = f"{group_en}_tiv"
        if col in rows.columns:
            result[group_ko] = float(numeric(rows, col).fillna(0).sum())
    if not result:
        return None, None
    return sum(result.values()), result


def get_suppliers(supplier_df: pd.DataFrame, iso: str) -> pd.DataFrame:
    rows = country_rows(supplier_df, iso, "recipient_iso_a3")
    if rows.empty or "tiv_per_year" not in rows.columns:
        return pd.DataFrame()
    rows = rows.loc[rows["year"].between(TIV_START_YEAR, REFERENCE_YEAR)].copy()
    rows["tiv_per_year"] = numeric(rows, "tiv_per_year")
    rows = rows.dropna(subset=["tiv_per_year", "supplier_iso_a3"])
    if rows.empty:
        return pd.DataFrame()
    out = rows.groupby("supplier_iso_a3", as_index=False)["tiv_per_year"].sum()
    out = out.loc[out["tiv_per_year"] > 0].sort_values("tiv_per_year", ascending=False)
    total = out["tiv_per_year"].sum()
    out["share_pct"] = out["tiv_per_year"] / total * 100 if total > 0 else 0
    return out


def get_orders(orders: pd.DataFrame, iso: str) -> pd.DataFrame:
    rows = country_rows(orders, iso, "recipient_iso_a3")
    if rows.empty:
        return pd.DataFrame()
    rows = rows.loc[rows["supplier_iso_a3"].eq("KOR")].copy()
    if rows.empty:
        return pd.DataFrame()
    rows["order_year_num"] = pd.to_numeric(rows["order_year"], errors="coerce")
    rows = rows.sort_values("order_year_num", ascending=False, kind="stable")

    def order_year_display(row) -> str:
        year = as_number(row.get("order_year_num"))
        label = str(int(year)) if year is not None else EMPTY
        return label + "*" if str(row.get("order_year_uncertain", "")).lower() == "true" else label

    def qty_display(row) -> str:
        qty = as_number(row.get("ordered_qty"))
        if qty is None:
            return EMPTY
        label = f"{qty:,.0f}" if qty.is_integer() else f"{qty:,.1f}"
        return label + "*" if str(row.get("ordered_qty_uncertain", "")).lower() == "true" else label

    return pd.DataFrame({
        "주문연도": rows.apply(order_year_display, axis=1),
        "기업명": rows["company"].map(TRANSACTION_TO_DISPLAY_NAME).fillna(rows["company"]),
        "무기명": rows["weapon"].fillna(EMPTY),
        "인도연도": rows["delivery_years"].fillna(EMPTY).replace("", EMPTY),
        "주문수량": rows.apply(qty_display, axis=1),
    }).reset_index(drop=True)


def get_gpi(gpi: pd.DataFrame, iso: str) -> tuple[float | None, float | None, float | None]:
    row = latest_record(gpi, iso)
    if row is None:
        return None, None, None
    score = as_number(row.get("score"))
    average = as_number(row.get("gpi_10yr_avg"))
    change = as_number(row.get("gpi_change"))
    return score, average, change


def stat_title(icon_key: str, label: str, suffix: str = "", tooltip: str | None = None) -> None:
    """카드 제목: 아이콘 + 제목 (+ 파란색 정보 아이콘)

    크기·간격은 components/common_ui.py 공통값 사용 (03_weapon 기준)
    - 아이콘 28px, 아이콘-제목 간격 6px(01_main 기준), 제목 19px / 굵기 750
    - tooltip이 있으면 제목 옆 파란색 정보 아이콘에 마우스를 올렸을 때 설명 표시
    """
    info_html = ""
    if tooltip is not None:
        # 설명은 카드 제목 옆 정보 아이콘에만 나타나도록 하여 하단 공간을 차지하지 않습니다.
        # 말풍선: 01_main과 같은 공통 도움말 (테두리 모양은 04 기준, 글자·크기는 main 기준)
        info_html = help_icon_html(tooltip, size=INFO_ICON_SIZE, label=f"{label} 설명")
    st.markdown(
        f'<div class="di-card-title" style="gap:{TITLE_ICON_GAP}px;">'
        f'{card_icon_html(icon_key, size=TITLE_ICON_SIZE)}'
        f'<span style="font-size:{TITLE_FONT_SIZE}px; font-weight:{TITLE_FONT_WEIGHT}; '
        f'line-height:1.2;">{escape(label)}</span>'
        f'{info_html}</div>',
        unsafe_allow_html=True,
    )
    if suffix:
        st.caption(suffix)


# 테마 전환 시 서버 측 st.context.theme.type 값이 잠시 이전 상태일 수 있어
# CSS 변수를 브라우저의 실제 카드 배경색과 동기화하는 작은 컴포넌트를 사용합니다.
# 도넛의 크기/범례/라벨/데이터는 전혀 수정하지 않습니다.
donut_gap_theme_sync = st.components.v2.component(
    name="country_donut_gap_theme_sync",
    html='<span class="di-country-gap-sync" aria-hidden="true"></span>',
    css=".di-country-gap-sync{display:block;width:0;height:0;overflow:hidden;}",
    # 도움말 말풍선 위치·색 보정 JS(공통)를 앞에 붙임
    js=HELP_TOOLTIP_JS + r"""
export default function () {
  function syncActualBackground() {
    const chart = document.querySelector('.st-key-weapon_donut');
    if (!chart) return;
    // 차트를 둘러싼 카드부터 최상위 앱까지 실제 칠해진 배경을 탐색합니다.
    let el = chart;
    while (el && el !== document.documentElement) {
      const bg = window.getComputedStyle(el).backgroundColor;
      if (bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)' &&
          bg !== 'rgba(0,0,0,0)') {
        document.documentElement.style.setProperty('--di-country-donut-gap-color', bg);
        return;
      }
      el = el.parentElement;
    }
  }
  syncActualBackground();
  const timer = window.setInterval(syncActualBackground, 400);
  return () => window.clearInterval(timer);
}
""",
)

# 이 스타일은 핵심 지표 3개와 거래 이력 표 머리글에만 적용합니다.
st.markdown("""
<style>
/* 도넛 조각 사이 간격: 브라우저에 실제 적용된 배경색만 사용합니다.
   기존 --background-color 와 st.context.theme.type 은 전환 중 오래된 색상을 유지할 수 있습니다. */
.st-key-weapon_donut .js-plotly-plot g.slice path {
    stroke: var(--di-country-donut-gap-color, #FFFFFF) !important;
    stroke-width: 2px !important;
    stroke-linejoin: round !important;
}
/* 아이콘 소스는 PNG 알파(모양)만 사용하고 색은 화면의 실제 테마 색으로 지정합니다.
   Streamlit 서버의 st.context.theme에 의존하지 않아 테마 전환 즉시 적용됩니다. */
.di-theme-icon {
    display:inline-block;
    flex-shrink:0;
    vertical-align:middle;
    background-color:var(--text-color, currentColor);
    -webkit-mask-image:var(--di-icon-src);
    mask-image:var(--di-icon-src);
    -webkit-mask-repeat:no-repeat;
    mask-repeat:no-repeat;
    -webkit-mask-position:center;
    mask-position:center;
    -webkit-mask-size:contain;
    mask-size:contain;
}
.di-kpi { position:relative; min-height:278px; display:flex; flex-direction:column;
          width:100%; color:inherit; }
.di-kpi-title { display:flex; align-items:center; gap:7px; font-size:15px;   /* 지표 카드 제목: 15px 고정 (A안) */
                font-weight:700; line-height:1.3; }
.di-kpi-title .di-theme-icon { width:24px; height:24px; flex-shrink:0; }
.di-kpi-body { display:flex; flex-direction:column; align-items:center;
               gap:8px; padding:10px 0 8px; }   /* 1안: 숫자를 위로 올리고 아래쪽은 5년 막대 */
.di-kpi-period { font-size:12px; opacity:.72; text-align:center; }
.di-kpi-value { font-size:clamp(24px,1.95vw,36px); font-weight:800; line-height:1.13;
                letter-spacing:-.045em; text-align:center; overflow-wrap:anywhere;
                max-width:100%; }
.di-kpi-badge { display:inline-block; padding:3px 10px; border-radius:999px;   /* 크기·굵기: 01_main과 동일 */
                background:rgba(33,195,84,.15); color:#21c354;   /* 증가: 01_main과 같은 초록 */
                font-weight:600; font-size:13px; text-align:center; }
.di-kpi-badge.down { background:rgba(255,75,75,.15); color:#ff4b4b; }   /* 감소: 01_main과 같은 빨강 */
.di-kpi-badge.neutral { background:rgba(133,150,170,.18);
                        color:inherit; opacity:.82; }
/* 1안: 카드 아래쪽 빈 공간에 연도·값이 붙은 5년 막대 */
.di-kpi-spark { margin-top:auto; display:flex; align-items:flex-end; justify-content:flex-end; gap:4px;   /* 오른쪽 정렬 · 간격 4px */
                border-top:1px solid rgba(128,128,128,.15); padding-top:10px; }
.di-kpi-spark .di-spark-col { flex:0 0 28px; display:flex; flex-direction:column; align-items:center; min-width:0; }   /* 막대 폭 28px */
.di-kpi-spark .di-spark-val { font-size:10.5px; opacity:.75; margin-bottom:3px; white-space:nowrap;
                              font-variant-numeric:tabular-nums; }
.di-kpi-spark .di-spark-bar { display:block; width:100%; background:#a4c6f3;
                              border-radius:2px 2px 0 0; }
.di-kpi-spark .di-spark-col:last-child .di-spark-bar { background:#376bff; }
.di-kpi-spark .di-spark-year { font-size:11px; opacity:.6; margin-top:4px; }
/* 카드 제목 공통: 아이콘 + 제목 + 정보 아이콘 한 줄 (크기·간격은 common_ui 공통값) */
.di-card-title { display:flex; align-items:center; flex-wrap:wrap;
    min-height:36px; margin-bottom:6px; }
/* 후보 적합도 카드: 정보 아이콘에 마우스를 올리거나 키보드로 초점을 맞추면 설명 표시 */
.di-radar-title { display:inline-flex; align-items:center; gap:8px;
    font-size:1.3rem; font-weight:700; line-height:1.35; }
.di-radar-info { position:relative; display:inline-flex; align-items:center;
    justify-content:center; flex-shrink:0; cursor:help; outline-offset:3px;
    color:#2563eb; font-size:20px; font-weight:600; line-height:1; z-index:5; }
.di-radar-tooltip { display:block; position:absolute; top:calc(100% + 12px);
    right:0; width:310px; max-width:min(310px, 80vw);
    padding:12px 14px; border-radius:9px;
    border:1px solid rgba(128,128,128,.30);
    background:var(--secondary-background-color, var(--background-color, #ffffff));
    color:var(--text-color, #1c1c1c); box-shadow:0 8px 24px rgba(0,0,0,.18);
    font-size:13px; font-weight:400; line-height:1.6; text-align:left;
    opacity:0; visibility:hidden; pointer-events:none;
    z-index:1000; transition:opacity .15s ease; }
.di-radar-info:hover .di-radar-tooltip,
.di-radar-info:focus .di-radar-tooltip,
.di-radar-info:focus-within .di-radar-tooltip {
    opacity:1; visibility:visible;
}
/* 레이더 도형만 약간 내려 카드의 세로 중앙에 가깝게 배치합니다.
   Plotly 영역 크기, 카드 제목, 툴팁 및 다른 그래프는 변경하지 않습니다. */
.st-key-country_radar {
    transform: translateY(0);   /* 아래쪽 축 이름·점수(협력 관계)가 잘리지 않도록 내리지 않음 */
}
/* 도넛 차트만 하단 설명 제거로 확보된 공간 쪽으로 18px 내립니다. */
.st-key-weapon_donut { transform: translateY(18px); }
/* 거래 이력 카드: 행 목록만 스크롤되고 제목·헤더·주석은 고정됩니다. */
.st-key-country_trade_history_card { min-height:370px; }
.di-trade-header { display:grid;
    grid-template-columns:1.15fr 2.4fr 2.95fr 1.4fr 1.3fr;
    column-gap:12px; align-items:center; border-radius:10px;
    /* 표 제목행: 01_main·03_weapon과 같은 연한 파란 배경 (밝은·어두운 모드 공통) */
    background:rgba(100,160,255,.10); color:inherit; padding:11px 12px; font-size:13px;
    font-weight:700; margin-bottom:8px; }
.di-trade-header > span {
    min-width: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# 도움말 말풍선 공통 CSS (01_main과 동일, components/common_ui.py)
st.markdown(HELP_TOOLTIP_CSS, unsafe_allow_html=True)


def _metric_badge(delta: float | None, *, suffix: str = "%", note: str = "전년 대비") -> tuple[str, str]:
    """비교값이 없으면 변화율을 만들어내지 않습니다."""
    if delta is None:
        return "비교 자료 없음", "neutral"
    if abs(delta) < 1e-10:
        return f"0.0{suffix} {escape(note)}", "neutral"
    arrow = "▲" if delta > 0 else "▼"
    tone = "up" if delta > 0 else "down"
    return f"{arrow} {abs(delta):.1f}{suffix} {escape(note)}", tone


def _spark_markup(values: list[float | None], years: list[int], value_format: str = "{:,.0f}") -> str:
    """원자료의 관측값만으로 5년 막대를 그립니다 (막대 위 값, 아래 연도). 결측 연도는 '—'로 둡니다."""
    valid = [v for v in values if v is not None and math.isfinite(v)]
    if len(valid) < 2:
        return ""
    max_v = max(valid)
    if max_v <= 0:
        return ""
    cols = []
    for value, year in zip(values, years):
        if value is None or not math.isfinite(value):
            label, bar = "—", '<span class="di-spark-bar" style="height:0px"></span>'
        else:
            label = value_format.format(value)
            height = 6 + round(62 * max(0, value) / max_v)
            bar = f'<span class="di-spark-bar" style="height:{height}px" title="{year}: {value:,.2f}"></span>'
        cols.append(f'<div class="di-spark-col"><span class="di-spark-val">{label}</span>{bar}'
                    f'<span class="di-spark-year">{str(year)[-2:]}</span></div>')
    return '<div class="di-kpi-spark" aria-label="최근 5년 값 추이">' + ''.join(cols) + '</div>'


def metric_with_icon(icon_key: str, label: str, value: str, period: str,
                     badge: str = "", badge_tone: str = "neutral",
                     spark_values: list[float | None] | None = None,
                     spark_years: list[int] | None = None,
                     spark_format: str = "{:,.0f}") -> None:
    """샘플과 같이 중앙 수치, 증감 배지, 우측 하단 미니 막대를 표시."""
    icon_html = card_icon_html(icon_key, size=24)
    badge_class = ' ' + badge_tone if badge_tone != 'up' else ''
    badge_html = f'<div class="di-kpi-badge{badge_class}">{escape(badge)}</div>' if badge else ''
    spark = _spark_markup(spark_values or [], spark_years or [], spark_format)
    st.markdown(
        '<div class="di-kpi">'
        f'<div class="di-kpi-title">{icon_html}<span>{escape(label)}</span></div>'
        '<div class="di-kpi-body">'
        f'<div class="di-kpi-period">{escape(period)}</div>'
        f'<div class="di-kpi-value">{kpi_value_html(value)}</div>'
        f'{badge_html}</div>{spark}</div>',
        unsafe_allow_html=True,
    )


def render_trade_history_table(df: pd.DataFrame) -> None:
    headers = ["주문연도", "기업명", "무기명", "인도연도", "주문수량"]
    widths = [1.15, 2.4, 2.95, 1.4, 1.3]
    # 예시처럼 다섯 개 열 제목을 한 개의 짙은 바탕색 행 안에 배치합니다.
    st.markdown(
        '<div class="di-trade-header">'
        + ''.join(f'<span>{escape(label)}</span>' for label in headers)
        + '</div>',
        unsafe_allow_html=True,
    )

    # 거래 기록 행만 지정된 높이(215px) 안에서 스크롤 (제목·헤더는 고정)
    # 속도 개선: 행마다 Streamlit 열·글 요소(행당 6개)를 만들지 않고 HTML 표 한 번으로 그림
    cols_css = " ".join(f"{w}fr" for w in widths)
    cell = "padding:0.35rem 0; text-align:center; min-width:0; overflow-wrap:anywhere;"
    rows_html = []
    for idx, (_, row) in enumerate(df.iterrows()):
        border = "border-bottom:1px solid rgba(128,128,128,0.15);" if idx < len(df) - 1 else ""
        rows_html.append(
            f'<div style="display:grid; grid-template-columns:{cols_css}; column-gap:12px; '
            f'align-items:center; padding:0.15rem 0.4rem; {border}">'
            f'<div style="{cell}">{escape(str(row.get("주문연도", EMPTY)))}</div>'
            f'<div style="{cell} font-weight:600;">{escape(str(row.get("기업명", EMPTY)))}</div>'
            f'<div style="{cell}">{escape(str(row.get("무기명", EMPTY)))}</div>'
            f'<div style="{cell}">{escape(str(row.get("인도연도", EMPTY)))}</div>'
            f'<div style="{cell}">{escape(str(row.get("주문수량", EMPTY)))}</div>'
            '</div>'
        )
    st.html(
        '<div style="max-height:215px; overflow-y:auto; overflow-x:hidden; font-size:14px;">'
        + "".join(rows_html) + '</div>'
    )


# ============================================================
# 1. 데이터 로딩: 프로젝트 내 원본 CSV는 읽기 전용으로 사용
# ============================================================
country_names = fetch_country_names()
supplier_country_names = full_country_names()
milex = get_table("military_expenditure.csv")
gpi = get_table("gpi_overall_2016_2025.csv", "gpi_overall_2016_2025(2).csv")
orders = get_table("korea_weapon_data.csv")
tiv_weapon = get_table("tiv_weapon_group.csv")
tiv_supplier = get_table("tiv_recipient.csv")
final_inputs = get_table("final_score_1.csv", "final_score.csv")
fitch = get_table("fitchrating.csv")

# 02_company 'TOP 10'에서 국가를 눌러 넘어온 경우: 그 기업·국가를 선택한 상태로 표시
_jump = st.session_state.pop("country_jump", None)
if _jump:
    if _jump.get("company") in COMPANIES:
        st.session_state.country_detail_company = _jump["company"]
    if _jump.get("iso") in country_names:
        st.session_state.country_detail_country = country_names[_jump["iso"]]

if "country_detail_company" not in st.session_state:
    preferred = st.session_state.get("export_company")
    # 다른 페이지가 이전 LIG 표시명을 세션에 남긴 경우 신규 표시명으로 연결
    if preferred == "LIG넥스원":
        preferred = "LIG D&A" if "LIG D&A" in COMPANIES else preferred
    st.session_state.country_detail_company = preferred if preferred in COMPANIES else next(iter(COMPANIES))
if st.session_state.country_detail_company not in COMPANIES:
    st.session_state.country_detail_company = next(iter(COMPANIES))
if "country_detail_country" not in st.session_state or st.session_state.country_detail_country not in country_names.values():
    st.session_state.country_detail_country = country_names.get("POL", next(iter(country_names.values())))

# ============================================================
# 2. 선택 영역: 기존 가로 레이아웃 유지
# ============================================================
with st.container(border=True):
    company_label, company_select, between, country_label, country_select, space = st.columns(
        [0.7, 2.4, 0.55, 0.75, 1.85, 4.0], gap="small", vertical_alignment="center"
    )
    with company_label:
        st.markdown("**선택 기업**")
    with company_select:
        company = st.selectbox("기업 선택", list(COMPANIES),
                               key="country_detail_company", label_visibility="collapsed")
    with country_label:
        st.markdown("**분석 국가**")
    with country_select:
        country = st.selectbox("국가 선택", list(country_names.values()),
                               key="country_detail_country", label_visibility="collapsed")

country_iso = next(code for code, name in country_names.items() if name == country)
budget_rows, budget_latest, budget_growth = get_budget_data(milex, country_iso)
tiv_total, tiv_groups = get_tiv_data(tiv_weapon, country_iso)
suppliers = get_suppliers(tiv_supplier, country_iso)
trade_history = get_orders(orders, country_iso)
gpi_latest, gpi_avg, gpi_change = get_gpi(gpi, country_iso)
gpi_peace = (5 - gpi_latest) / 4 * 100 if gpi_latest is not None else None
final_row = latest_record(final_inputs, country_iso)

# 수출 후보 순위·추천 점수·6개 지표 점수: src/dashboard_score/dashboard_score.py 결과
# (02_company '2026년 수출 유망 국가 TOP 10'과 같은 기준)
#   - 가중치 기본값: 기업별 CRITIC 가중치 / '가중치 커스텀'에서 바꾸면 그 가중치로 순위·점수 재계산
#   - 가중치 상태는 02_company와 공유 (어느 화면에서 바꿔도 같이 반영)
init_weight_state(company)   # 기업별 가중치 (02_company와 공유)
try:
    score_info = country_score(company, country_iso, custom_weights(company))
    neighbors = neighbor_countries(company, country_iso, custom_weights(company))   # 앞뒤 순위 국가
    score_error = None
except Exception as error:   # 스크립트 오류가 나도 화면은 유지
    score_info, neighbors, score_error = None, [], str(error)

# ============================================================
# 3. 첫 번째 행: 국가 개요 | 거래 이력
# ============================================================
# 국가 개요 카드: 순위·점수 + 순위 주변 국가 (C안). 버튼이 잘리지 않도록 거래 이력 카드를 조금 줄임
left_overview, right_history = st.columns([1.45, 1.55], gap="small")   # 거래 이력 카드를 줄여 국가명(최대 8자)이 한 줄에 들어가게

OVERVIEW_CSS = """
<style>
/* 순위·점수 숫자: 숫자와 한글(위·점)을 같은 한글 글꼴로 그려 크기를 맞춤 (2안)
   웹 글꼴을 못 불러오면 맑은 고딕(Windows)·애플 SD 고딕(Mac)으로 표시 */
@import url("https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@500;800&display=swap");
.ov-kpis { display:grid; grid-template-columns:1fr 1px 1fr; align-items:center; margin:10px 0 4px; }
.ov-sep { align-self:stretch; background:rgba(128,128,128,.28); }
.ov-k { text-align:center; padding:4px 6px; min-width:0; }
.ov-l { display:inline-flex; align-items:center; gap:4px; font-size:13px; font-weight:600; opacity:.7; }
.ov-v { font-size:38px; font-weight:800; line-height:1.15; margin-top:4px;
        font-family:"Noto Sans KR", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
        font-variant-numeric:tabular-nums; white-space:nowrap; }
.ov-v small { font-size:17px; font-weight:500; opacity:.6; margin-left:2px; }
.ov-near { margin-top:12px; }
.ov-row { display:grid; grid-template-columns:48px minmax(0,1fr) 72px; align-items:center; gap:8px;
          padding:7px 6px; font-size:14px; opacity:.6; font-variant-numeric:tabular-nums; }
.ov-row.me { opacity:1; font-weight:800; }
.ov-row .cn { display:flex; align-items:center; gap:8px; min-width:0; white-space:nowrap;
              overflow:hidden; text-overflow:ellipsis; }
.ov-row > span:last-child { text-align:right; }
/* 순위 주변 국가를 누르면 그 국가로 바뀜 */
.ov-row.ov-link { cursor:pointer; border-radius:6px; }
.ov-row.ov-link:hover { opacity:1; background:rgba(91,156,245,.10); }
.ov-row.ov-link:hover .cn { color:#5B9CF5; }
</style>
"""

# 순위 주변 국가 클릭 → 그 국가 선택 (02 TOP 10 클릭과 같은 country_jump 방식)
def on_near_country_click():
    result = st.session_state.get("country_near_click")
    iso = result.get("country") if isinstance(result, dict) else getattr(result, "country", None)
    if iso:
        st.session_state.country_jump = {"company": st.session_state.get("country_detail_company"),
                                         "iso": str(iso)}


near_click_bridge = st.components.v2.component(
    name="country_near_click_bridge",
    html='<span class="country-near-click-bridge" aria-hidden="true"></span>',
    css=".country-near-click-bridge{display:block;width:0;height:0;overflow:hidden;}",
    js=r"""
    export default function ({ setTriggerValue }) {
        const KEY = "__kDefenseNearCountryClick";
        if (window[KEY]) {
            document.removeEventListener("click", window[KEY], true);
            document.removeEventListener("keydown", window[KEY], true);
        }
        function handler(event) {
            if (event.type === "keydown" && event.key !== "Enter") return;
            const target = event.target;
            const row = target && target.closest ? target.closest(".ov-near .ov-link") : null;
            if (!row) return;
            const iso = row.getAttribute("data-iso");
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

with left_overview:
    # 우측 거래 이력 카드의 실제 높이에 맞춰 같은 행에서 자연스럽게 늘어납니다.
    with st.container(border=True, height="stretch", key="country_overview_card"):
        # 국가명은 글자 크기 그대로 한 줄 표시 (줄바꿈 금지)
        st.html("<style>.st-key-country_overview_card h2 { white-space:nowrap; }</style>")
        flag_area, country_area, weight_area = st.columns([0.8, 3.0, 1.5], vertical_alignment="center")
        with flag_area:
            flag_widget(country_iso, width=85)
        with country_area:
            st.header(country)
        with weight_area:
            # 가중치 커스텀 (02_company와 같은 버튼·기능·상태 공유)
            render_weight_popover(company)

        # 수출 후보 순위 | 후보 적합도 점수 (가운데 정렬, 세로 구분선)
        rank_text = (f'{score_info["rank"]}위<small>/ {score_info["total"]}</small>'
                     if score_info else EMPTY)
        score_text = f'{score_info["score"]:.1f}<small>점</small>' if score_info else EMPTY
        # 순위 주변 국가: 순위 · 국기+국가명 · 점수 (선택 국가는 진하게)
        near_rows = "".join(
            (f'<div class="ov-row me">' if row["is_target"] else
             f'<div class="ov-row ov-link" data-iso="{escape(str(row["iso_a3"]), quote=True)}" '
             f'title="{escape(str(row["country"]), quote=True)} 선택" role="link" tabindex="0">')
            + f'<span>{row["rank"]}위</span>'
            f'<span class="cn">{flag_icon_html(row["iso_a3"], 22)}{escape(str(row["country"]))}</span>'
            f'<span>{row["suitability"]:.1f}점</span></div>'
            for row in neighbors
        )
        st.html(
            OVERVIEW_CSS
            + '<div class="ov-kpis">'
            + f'<div class="ov-k"><div class="ov-l">{escape(company)} 수출 후보 순위</div>'
            + f'<div class="ov-v">{rank_text}</div></div>'
            + '<div class="ov-sep"></div>'
            + '<div class="ov-k"><div class="ov-l">후보 적합도 점수</div>'
            + f'<div class="ov-v">{score_text}</div></div>'
            + '</div>'
            + (f'<div class="ov-near">{near_rows}</div>' if near_rows else "")
        )
        near_click_bridge(key="country_near_click", on_country_change=on_near_country_click)
        if score_error:
            st.caption(f"점수를 불러오지 못했습니다: {score_error}")
        if gpi_latest is not None:
            st.caption(f"GPI 2025: {gpi_latest:.3f} · 평화 점수: {gpi_peace:.1f}/100")
        if not fitch.empty and "rating_action_date" in fitch:
            country_fitch = country_rows(fitch, country_iso)
            if not country_fitch.empty:
                last = country_fitch.sort_values("rating_action_date").iloc[-1]
                st.caption(f"Fitch 최근 기록: {last['rating']} ({last['rating_action_date']})")

with right_history:
    # 카드 전체의 스크롤은 비활성화하고, 표 데이터 행에만 스크롤을 둡니다.
    # 왼쪽 국가 개요 카드와 같은 높이로 늘어나도록 height="stretch"
    with st.container(border=True, key="country_trade_history_card", height="stretch"):
        stat_title("description", "한국 기업과의 거래 이력")
        if trade_history.empty:
            st.info("연결된 한국 기업 거래 기록이 없습니다. 기록 부재와 거래 부재는 동일하지 않습니다.")
        else:
            render_trade_history_table(trade_history)
            st.caption(f"총 {len(trade_history)}건 · * 표시: 주문연도 또는 주문수량이 불확실한 기록 · 복수 인도연도는 원자료 그대로 표시")

# ============================================================
# 4. 두 번째 행: 레이더 | 핵심 지표
# ============================================================
left_radar, right_metrics = st.columns([0.91, 1.89], gap="small")
with left_radar:
    # 옆 핵심 지표 카드와 같은 높이를 사용하되 내부 스크롤은 만들지 않습니다.
    with st.container(border=True, height="stretch"):
        # 6개 축 = dashboard_score.py의 지표 점수(0~100점, 98개국 중 상대 위치)
        #   HHI→hhi_5y · 국방비→final_mil_score · 무기 매칭도→company_category_score
        #   협력 관계→transaction_with_korea · GPI→gpi_score_5y · 신용도→fitch_score
        radar_values = score_info["indicators"] if score_info else None
        if radar_values:
            radar_notes = [
                "각 지표를 98개국 기준 0~100점으로 바꾼 값입니다.",
                " · ".join(f"{name} {radar_values[name]:.1f}" for name in RADAR_LABELS),
                "HHI는 공급국이 다양할수록, GPI는 지수가 높을수록(안보 수요) 점수가 높습니다.",
            ]
        else:
            radar_notes = ["점수 데이터를 불러오지 못했습니다."]
        stat_title("hexagon", "후보 적합도 구성 점수 (6개)", tooltip="\n".join(radar_notes))
        st.plotly_chart(radar_figure(radar_values), use_container_width=True,
                        config={"displayModeBar": False}, key="country_radar")

with right_metrics:
    # 레이더 카드 높이에 맞춰 자동 확장합니다. 고정 높이로 인한 스크롤은 없습니다.
    with st.container(border=True, height="stretch"):
        stat_title("format_list_bulleted", "핵심 지표")
        metric_cols = st.columns(3, gap="small")
        expense = as_number(budget_latest.get("military_expenditure_usd")) if budget_latest is not None else None
        share = as_number(budget_latest.get("military_expenditure_gdp_pct")) if budget_latest is not None else None
        # 실제 연도별 값을 이용해 증감 배지 및 미니 막대 추이를 만듭니다.
        spark_years = list(range(REFERENCE_YEAR - 4, REFERENCE_YEAR + 1))
        budget_index = budget_rows.set_index("year") if not budget_rows.empty else pd.DataFrame()

        def annual_series(column: str, multiplier: float = 1.0) -> list[float | None]:
            if budget_index.empty or column not in budget_index:
                return [None] * len(spark_years)
            return [
                as_number(budget_index.loc[year, column]) * multiplier
                if year in budget_index.index and as_number(budget_index.loc[year, column]) is not None
                else None
                for year in spark_years
            ]

        expense_spark = annual_series("military_expenditure_usd", 1e-8)
        share_spark = annual_series("military_expenditure_gdp_pct")

        def previous_value(column: str) -> float | None:
            if budget_index.empty or column not in budget_index or REFERENCE_YEAR - 1 not in budget_index.index:
                return None
            return as_number(budget_index.loc[REFERENCE_YEAR - 1, column])

        last_expense = previous_value("military_expenditure_usd")
        last_share = previous_value("military_expenditure_gdp_pct")
        expense_delta = (expense / last_expense - 1) * 100 if expense is not None and last_expense is not None and last_expense > 0 else None
        share_delta = share - last_share if share is not None and last_share is not None else None
        expense_badge, expense_tone = _metric_badge(expense_delta)
        share_badge, share_tone = _metric_badge(share_delta, suffix="%p")

        # TIV는 현재 5개 연도 값으로 시각화합니다. 5년 전 기간도 관측된
        # 경우에만 전기 5년 대비 증감률을 보여줍니다.
        tiv_rows = country_rows(tiv_weapon, country_iso, "recipient_iso_a3")
        tiv_columns = [f"{g}_tiv" for g in WEAPON_GROUP_KO if f"{g}_tiv" in tiv_rows]
        if tiv_columns and not tiv_rows.empty:
            tiv_rows = tiv_rows.copy()
            tiv_rows["annual_total"] = tiv_rows[tiv_columns].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1)
            annual_tiv = tiv_rows.groupby("year")["annual_total"].sum(min_count=1)
            tiv_spark = [as_number(annual_tiv.loc[y]) if y in annual_tiv.index else None for y in spark_years]
            prior_years = set(range(REFERENCE_YEAR - 9, REFERENCE_YEAR - 4))
            if prior_years.issubset(set(annual_tiv.index)) and tiv_total is not None:
                prior_total = float(annual_tiv.loc[sorted(prior_years)].sum(min_count=1))
                tiv_delta = (tiv_total / prior_total - 1) * 100 if math.isfinite(prior_total) and prior_total > 0 else None
            else:
                tiv_delta = None
        else:
            tiv_spark, tiv_delta = [None] * len(spark_years), None
        tiv_badge, tiv_tone = _metric_badge(tiv_delta, note="직전 5년 대비")

        metric_info = [
            ("paid", "국방비", f"{expense / 1e8:,.1f}억 달러" if expense is not None else EMPTY,
             "2025년 기준", expense_badge, expense_tone, expense_spark, "{:,.0f}"),
            ("donut_large", "GDP 대비 국방비", fmt(share, 2, "%"),
             "2025년 기준", share_badge, share_tone, share_spark, "{:.1f}"),
            ("switch_access_shortcut_add", "무기 도입 TIV", fmt(tiv_total, 1),
             "최근 5년(2021~2025) 누적", tiv_badge, tiv_tone, tiv_spark, "{:,.0f}"),
        ]
        for col, (icon_key, title, value, period, badge, tone, spark_vals, spark_fmt) in zip(metric_cols, metric_info):
            with col:
                with st.container(border=True, height=320):
                    metric_with_icon(icon_key, title, value, period,
                                     badge, tone, spark_vals, spark_years, spark_fmt)

# ============================================================
# 5. 세 번째 행: 국방비 추이 | 무기 도입 비중 | 주요 공급국
# ============================================================
bottom_left, bottom_center, bottom_right = st.columns([1.25, 1.2, 0.98], gap="small")
with bottom_left:
    with st.container(border=True, height="stretch"):
        stat_title("bar_chart", "연도별 국방비 추이", "국방비: 억 달러 · GDP 대비 국방비: %",
                   tooltip="결측 연도는 임의로 0 처리하거나 보간하지 않습니다.")
        # 최근 5년(2021~2025년), 막대: 국방비 / 선: GDP 대비 국방비
        values = (budget_rows.loc[budget_rows["year"].between(TIV_START_YEAR, REFERENCE_YEAR)].copy()
                  if not budget_rows.empty else pd.DataFrame())
        if values.empty or (values["military_expenditure_usd"].isna().all()
                            and values["military_expenditure_gdp_pct"].isna().all()):
            st.plotly_chart(blank_plot("해당 국가의 국방비 자료 없음"), use_container_width=True,
                            config={"displayModeBar": False}, key="budget_empty")
        else:
            values = values.sort_values("year")
            years = values["year"].astype(int).astype(str)
            budget = values["military_expenditure_usd"] / 1e8
            gdp_pct = values["military_expenditure_gdp_pct"]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=years, y=budget,
                name="국방비 (억 달러)", marker_color="#71B6F6",
                text=budget.map(lambda v: f"{v:,.0f}" if pd.notna(v) else ""),
                # 선그래프와 겹치지 않도록 막대 안쪽 중앙에 값을 표기합니다.
                textposition="inside", insidetextanchor="middle",
                textfont=dict(color="#103A65", size=12),
                hovertemplate="%{x}년 국방비: %{y:,.1f}억 달러<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=years, y=gdp_pct, yaxis="y2", mode="lines+markers",
                name="GDP 대비 국방비 (%)",
                line=dict(color="#E64747", width=2.5),
                marker=dict(size=8, color="#E64747"),
                connectgaps=False,
                hovertemplate="%{x}년 GDP 대비 국방비: %{y:.2f}%<extra></extra>",
            ))
            fig.update_layout(
                height=255, margin=dict(l=12, r=14, t=38, b=15),   # 주요 공급국 3개 행·도넛과 높이를 맞춰 하단 여백 없앰
                xaxis=dict(title=None, type="category", fixedrange=True),
                yaxis=dict(title="억 달러", rangemode="tozero", showgrid=True, fixedrange=True),
                yaxis2=dict(title="%", overlaying="y", side="right", rangemode="tozero", showgrid=False, fixedrange=True),
                legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                hovermode="x unified", bargap=0.35, dragmode=False,
            )
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False, "scrollZoom": False,
                                    "doubleClick": False}, key="budget_chart")

with bottom_center:
    with st.container(border=True, height="stretch"):
        # 제목 앞에 임시로 넣었던 8px 공백을 제거해 위쪽에 정렬합니다.
        stat_title("donut_large", "무기체계별 도입 비중", "최근 5년(2021~2025) · TIV 기준")

        if not tiv_groups or tiv_total is None or tiv_total <= 0:
            # 원자료에 해당 국가의 TIV 기록이 없으면 0%로 꾸며서 표현하지 않습니다.
            st.info("2021~2025년 무기체계별 TIV 자료가 없습니다.")
        else:
            # 공통 10개 무기체계 분류는 그대로 사용하고, 표시만 예시 카드 스타일로 맞춥니다.
            donut_data = pd.DataFrame(
                [(name, value) for name, value in tiv_groups.items() if value > 0],
                columns=["무기체계", "TIV"],
            ).sort_values("TIV", ascending=False, kind="stable").reset_index(drop=True)

            # 01_main과 같은 방식: 상위 5개 분류 + 나머지는 '기타'로 묶음
            DONUT_TOP_N = 5
            OTHER_LABEL, OTHER_COLOR = "기타", "#B8C2D3"   # 01_main OTHER_COLOR와 동일
            if len(donut_data) > DONUT_TOP_N:
                other_tiv = float(donut_data["TIV"].iloc[DONUT_TOP_N:].sum())
                donut_data = pd.concat(
                    [donut_data.head(DONUT_TOP_N),
                     pd.DataFrame([{"무기체계": OTHER_LABEL, "TIV": other_tiv}])],
                    ignore_index=True,
                )
            donut_data["비중(%)"] = donut_data["TIV"] / tiv_total * 100

            # 무기체계 색상: 03_weapon·01_main 도넛과 같은 색 (components/common_ui.py)
            # 국가가 바뀌어도 같은 무기체계는 항상 같은 색입니다.
            group_colors = weapon_group_colors()
            weapon_colors = {
                group_ko: group_colors.get(group_en, WEAPON_COLOR_FALLBACK)
                for group_en, group_ko in WEAPON_GROUP_KO.items()
            }
            weapon_colors[OTHER_LABEL] = OTHER_COLOR
            fallback_color = WEAPON_COLOR_FALLBACK
            chart_colors = [weapon_colors.get(name, fallback_color)
                            for name in donut_data["무기체계"]]
            donut_pct_labels = [
                f"{pct:.1f}%" if pct >= 3 else ""   # 3% 미만 생략 (01_main과 동일)
                for pct in donut_data["비중(%)"]
            ]

            # 왼쪽 도넛 / 오른쪽 범례 비율: 01_main과 동일
            chart_col, legend_col = st.columns(
                [1.35, 1], gap="small", vertical_alignment="center"
            )
            with chart_col:
                donut_fig = go.Figure(go.Pie(
                    labels=donut_data["무기체계"].tolist(),
                    values=donut_data["TIV"].tolist(),
                    hole=0.5,   # 도넛 두께: 01_main과 동일
                    sort=False,
                    direction="clockwise",
                    # 조각을 밀어내지 않고, 배경색과 같은 얇은 경계로만 간격을 만듭니다.
                    # 비중이 작은 조각도 도넛 바깥으로 튀어나오지 않습니다.
                    pull=[0] * len(donut_data),
                    marker=dict(
                        colors=chart_colors,
                        line=dict(width=0),  # 간격 색상은 브라우저 CSS에서만 처리
                    ),
                    text=donut_pct_labels,
                    textinfo="text",
                    textposition="outside",
                    textfont=dict(size=11),
                    automargin=True,
                    showlegend=False,
                    hovertemplate="<b>%{label}</b><br>TIV %{value:,.0f}<br>비중 %{percent}<extra></extra>",
                ))
                donut_fig.update_layout(
                    height=235,
                    margin=dict(l=8, r=8, t=12, b=12),
                    paper_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    annotations=[dict(
                        x=0.5, y=0.5, xref="paper", yref="paper",
                        text=f"총 TIV<br><b>{tiv_total:,.0f}</b>",
                        showarrow=False,
                        align="center",
                        font=dict(size=12),
                    )],
                )
                st.plotly_chart(
                    donut_fig, use_container_width=True, theme="streamlit",
                    config={"displayModeBar": False}, key="weapon_donut",
                )
                # 현재 화면에 칠해진 실제 배경색을 도넛 간격으로 사용합니다.
                # Streamlit 설정에서 라이트/다크를 전환해도 JS가 즉시 색상을 갱신합니다.
                donut_gap_theme_sync(key="country_donut_gap_theme_sync")

            with legend_col:
                # 범례: 01_main과 같은 원형 점 + 분류명 + 비중(굵게)
                legend_rows = []
                for _, record in donut_data.iterrows():
                    category = str(record["무기체계"])
                    color = weapon_colors.get(category, fallback_color)
                    pct = float(record["비중(%)"])
                    legend_rows.append(
                        '<div style="display:flex; align-items:center; gap:6px; min-width:0;">'
                        f'<span style="width:10px; height:10px; flex-shrink:0; border-radius:50%; '
                        f'background-color:{color};"></span>'
                        '<span style="font-size:12.5px; line-height:1.3; color:inherit; '
                        'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">'
                        f'{escape(category)}</span>'
                        '<span style="font-size:12.5px; font-weight:700; margin-left:auto; '
                        f'padding-left:6px; color:inherit;">{pct:.1f}%</span></div>'
                    )
                st.html(
                    '<div style="display:flex; flex-direction:column; gap:6px; '
                    'padding-left:4px; width:100%;">' + "".join(legend_rows) + '</div>'
                )

            # 도넛 중앙의 총 TIV와 범례는 기존대로 유지합니다.

with bottom_right:
    # 공급국 상위 3개국만 표시 (국방비 추이·도넛 카드와 같은 높이)
    with st.container(border=True, height="stretch"):
        stat_title("language", "주요 공급국", "최근 5년(2021~2025) · TIV 기준",
                   tooltip="비중은 해당 국가의 전체 무기 도입 TIV를 분모로 계산합니다.")
        if suppliers.empty:
            st.info("집계된 공급국 데이터가 없습니다.")
        else:
            # 03_weapon 'TOP 5'와 같은 HTML 표 (순위 / 국가 / TIV / 비중) — 상위 3개국
            top_suppliers = suppliers.head(3)
            top_value = float(top_suppliers["tiv_per_year"].iloc[0])
            head = ('<div class="country-table-header country-supplier-cols">'
                    '<span>순위</span><span>국가</span><span>TIV</span><span>비중</span></div>')
            rows = []
            for index, (_, row) in enumerate(top_suppliers.iterrows(), 1):
                supplier_iso = str(row["supplier_iso_a3"])
                name = escape(str(supplier_country_names.get(
                    supplier_iso,
                    country_names.get(supplier_iso, DEFAULT_COUNTRY_NAMES.get(supplier_iso, supplier_iso))
                )))
                value = float(row["tiv_per_year"])
                share = float(row["share_pct"])
                # 막대 길이 = 비중 (전체 100% 기준)
                bar = max(0.0, min(share, 100.0))
                rows.append(
                    '<div class="country-supplier-row country-supplier-cols">'
                    f'<span>{rank_icon_html(index, 30)}</span>'
                    f'<span class="country-supplier-cell">{flag_icon_html(supplier_iso, 27)}{name}</span>'
                    f'<span style="font-weight:700">{value:,.0f}</span>'
                    f'<span class="country-supplier-share"><span>{share:.1f}%</span>'
                    f'<span class="country-share-track"><span class="country-share-fill" '
                    f'style="width:{bar:.1f}%"></span></span></span></div>'
                )
            st.html(SUPPLIER_TABLE_CSS + head + "".join(rows))
