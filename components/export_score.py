"""수출 유망 국가 점수 — 화면 연결용 (01_main·02_company·04_country 공통)

계산은 모두 src/dashboard_score/dashboard_score.py에서 함 (이 파일은 계산식을 갖지 않음)
- run_2026_prediction_detail() : 기업별 6개 지표 점수, final_score, rank, CRITIC 가중치
- rescore()                    : 사용자 가중치로 점수·순위 다시 계산
- round_to_100()               : 가중치 % 표시 (합계 정확히 100.00%)

이 파일이 하는 일
- 스크립트 결과를 Streamlit 캐시에 저장 (스크립트나 final_score.csv가 바뀌면 자동으로 다시 계산)
- 화면 지표 이름(HHI·국방비 …) ↔ 스크립트 열 이름 연결, 국가명(한글) 붙이기
- 03_weapon: src/dashboard_score/dashboard_score_weapon.py 결과(무기 그룹별 TOP 10)도 같은 방식으로 연결

사용: from components.export_score import top_countries, country_score, critic_weights_pct
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
SCORE_SCRIPT = ROOT / "src" / "dashboard_score" / "dashboard_score.py"
WEAPON_SCRIPT = ROOT / "src" / "dashboard_score" / "dashboard_score_weapon.py"
SCORE_DATA = ROOT / "data" / "processed" / "final_score.csv"
COUNTRY_MAP = ROOT / "data" / "mapping" / "country_map_master.csv"

# 화면의 지표 이름 → dashboard_score.py의 지표 열 이름 (02 가중치 커스텀 순서와 같음)
INDICATOR_COLUMNS = {
    "HHI": "hhi_score",
    "국방비": "defense_expenditure_score",
    "무기 매칭도": "company_trade_score",
    "협력 관계": "korea_arms_trade_score",
    "GPI": "gpi_score",
    "신용도": "fitch_score",
}


def loaded_mtime() -> int:
    """이 파일의 현재 수정 시각 — 페이지에서 LOADED_MTIME과 비교해 바뀌었으면 다시 불러옴"""
    return Path(__file__).stat().st_mtime_ns


LOADED_MTIME = loaded_mtime()


def _mtimes() -> tuple[int, int]:
    if not SCORE_SCRIPT.is_file():
        raise FileNotFoundError("점수 계산 파일을 찾을 수 없습니다.")
    if not SCORE_DATA.is_file():
        raise FileNotFoundError("점수 데이터 파일을 찾을 수 없습니다.")
    return SCORE_SCRIPT.stat().st_mtime_ns, SCORE_DATA.stat().st_mtime_ns


@st.cache_resource(show_spinner=False)
def _score_module(script_mtime: int):
    """dashboard_score.py 모듈 (스크립트가 바뀌면 새로 불러옴)"""
    spec = importlib.util.spec_from_file_location("dashboard_score", SCORE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def score_module():
    return _score_module(_mtimes()[0])


@st.cache_data(show_spinner=False)
def _run_score_script(script_mtime: int, data_mtime: int) -> tuple[dict, dict]:
    """스크립트 실행 결과 ({기업명: 점수표(iso_a3 열 포함)}, {기업명: CRITIC 가중치 Series})"""
    module = _score_module(script_mtime)
    results, weights, _ = module.run_2026_prediction_detail(verbose=False)
    return (
        {company: scored.reset_index() for company, scored in results.items()},
        weights,
    )


@st.cache_data(show_spinner=False)
def _country_names(map_mtime: int) -> dict:
    if not COUNTRY_MAP.is_file():
        return {}
    master = pd.read_csv(COUNTRY_MAP, encoding="utf-8-sig")
    return dict(zip(master["iso_a3"], master["country_name_ko"]))


def load_scores() -> dict:
    """기업별 점수표. 파일이 없거나 스크립트 오류면 예외 발생"""
    return _run_score_script(*_mtimes())[0]


def _scored_table(company: str, weights: dict | None) -> pd.DataFrame | None:
    """기업 점수표 (weights가 있으면 dashboard_score.rescore로 다시 계산)"""
    scores = load_scores().get(company)
    if scores is None or scores.empty:
        return None
    if not weights:
        return scores
    column_weights = {INDICATOR_COLUMNS[name]: value for name, value in weights.items()
                      if name in INDICATOR_COLUMNS}
    if sum(float(v) for v in column_weights.values()) <= 0:
        return scores
    rescored = score_module().rescore(scores.set_index("iso_a3"), column_weights)
    return rescored.reset_index()


def critic_weights_pct(company: str) -> dict:
    """기업의 CRITIC 가중치 % (dashboard_score.round_to_100 결과, 합계 정확히 100.00)
    → 가중치 커스텀 기본값. 스크립트 터미널 출력의 %와 같은 값"""
    weights = _run_score_script(*_mtimes())[1].get(company)
    if weights is None:
        return {}
    pct = score_module().round_to_100(weights)
    return {name: float(pct[col]) for name, col in INDICATOR_COLUMNS.items()}


def top_countries(company: str, n: int = 10, weights: dict | None = None) -> list[dict]:
    """기업의 수출 유망 국가 상위 n개 → [{iso_a3, country, rank, suitability}, ...]

    weights=None : dashboard_score.py 결과(CRITIC 가중치) 그대로
    weights={지표 이름: 비율} : 같은 6개 지표 점수에 사용자 가중치를 곱해 다시 계산
    """
    table = _scored_table(company, weights)
    if table is None:
        return []
    names = _country_names(COUNTRY_MAP.stat().st_mtime_ns if COUNTRY_MAP.is_file() else 0)
    return [
        {
            "iso_a3": str(row["iso_a3"]),
            "country": names.get(row["iso_a3"], row["iso_a3"]),
            "rank": int(row["rank"]),
            "suitability": float(row["final_score"]),
        }
        for _, row in table.head(n).iterrows()
    ]


def country_score(company: str, iso_a3: str, weights: dict | None = None) -> dict | None:
    """한 국가의 기업별 수출 유망 순위·추천 점수·6개 지표 점수 (04_country 국가 개요·레이더용)

    반환: {"rank", "total", "score", "indicators": {지표 이름: 0~100점}} — 국가가 없으면 None
    """
    table = _scored_table(company, weights)
    if table is None:
        return None
    row = table.loc[table["iso_a3"] == iso_a3]
    if row.empty:
        return None
    row = row.iloc[0]
    return {
        "rank": int(row["rank"]),
        "total": int(len(table)),
        "score": float(row["final_score"]),
        "indicators": {name: float(row[col]) for name, col in INDICATOR_COLUMNS.items()},
    }


def neighbor_countries(company: str, iso_a3: str, weights: dict | None = None, span: int = 1) -> list[dict]:
    """선택 국가와 앞뒤 순위 국가 (04_country 국가 개요 '순위 주변 국가')
    → [{iso_a3, country, rank, suitability, is_target}, ...] 순위 순서 (기본: 앞뒤 1개씩)"""
    table = _scored_table(company, weights)
    if table is None:
        return []
    table = table.reset_index(drop=True)            # 점수 높은 순으로 정렬된 상태
    hits = table.index[table["iso_a3"] == iso_a3]
    if len(hits) == 0:
        return []
    pos = int(hits[0])
    start, end = max(0, pos - span), min(len(table), pos + span + 1)
    names = _country_names(COUNTRY_MAP.stat().st_mtime_ns if COUNTRY_MAP.is_file() else 0)
    return [
        {
            "iso_a3": str(row["iso_a3"]),
            "country": names.get(row["iso_a3"], row["iso_a3"]),
            "rank": int(row["rank"]),
            "suitability": float(row["final_score"]),
            "is_target": str(row["iso_a3"]) == iso_a3,
        }
        for _, row in table.iloc[start:end].iterrows()
    ]


# ------------------------------------------------------------
# 03_weapon: 무기 그룹별 수출 추천 TOP 10 (dashboard_score_weapon.py 결과)
# ------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _run_weapon_script(script_mtime: int, data_mtime: int) -> dict:
    """{무기 그룹 코드(예: artillery): 점수표(iso_a3·final_score·rank 포함)}
    스크립트 열 이름 '<코드>_category_score'에서 코드를 꺼내 03 화면의 무기 그룹 코드와 연결"""
    spec = importlib.util.spec_from_file_location("dashboard_score_weapon", WEAPON_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    # 스크립트의 터미널 출력(print)은 화면에 보이지 않게 숨김
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(module)
        results, _ = module.run_2026_weapon_prediction()
    code_of = {name: col.removesuffix("_category_score") for name, col in module.WEAPON_CONFIG.items()}
    return {code_of[name]: scored.reset_index() for name, scored in results.items() if name in code_of}


def weapon_top_countries(group_code: str, n: int = 10) -> list[dict]:
    """무기 그룹의 수출 추천 국가 상위 n개 → [{iso_a3, country, rank, suitability}, ...]
    파일이 없거나 스크립트 오류면 예외 발생"""
    if not WEAPON_SCRIPT.is_file():
        raise FileNotFoundError("무기 그룹 점수 계산 파일을 찾을 수 없습니다.")
    if not SCORE_DATA.is_file():
        raise FileNotFoundError("점수 데이터 파일을 찾을 수 없습니다.")
    table = _run_weapon_script(WEAPON_SCRIPT.stat().st_mtime_ns, SCORE_DATA.stat().st_mtime_ns).get(group_code)
    if table is None or table.empty:
        return []
    names = _country_names(COUNTRY_MAP.stat().st_mtime_ns if COUNTRY_MAP.is_file() else 0)
    return [
        {
            "iso_a3": str(row["iso_a3"]),
            "country": names.get(row["iso_a3"], row["iso_a3"]),
            "rank": int(row["rank"]),
            "suitability": float(row["final_score"]),
        }
        for _, row in table.head(n).iterrows()
    ]
