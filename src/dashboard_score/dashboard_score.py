import numpy as np
import pandas as pd
from pathlib import Path

# ==========================================
# 0. 공통 정규화 및 변환 함수
# ==========================================
def min_max_normalize(s: pd.Series) -> pd.Series:
    """Benefit 지표: (x - min) / (max - min)."""
    s_min, s_max = s.min(), s.max()
    if pd.isna(s_min) or pd.isna(s_max) or s_max == s_min:
        return pd.Series(0.0, index=s.index)
    return (s - s_min) / (s_max - s_min)


def max_min_normalize(s: pd.Series) -> pd.Series:
    """Cost 지표(HHI 등): (max - x) / (max - min)."""
    s_min, s_max = s.min(), s.max()
    if pd.isna(s_min) or pd.isna(s_max) or s_max == s_min:
        return pd.Series(0.0, index=s.index)
    return (s_max - s) / (s_max - s_min)


def gii_log_transform(s: pd.Series, f: float) -> pd.Series:
    """GII 로그변환: ln(((max*f - 1)*(x-min))/(max-min) + 1)."""
    s_min, s_max = s.min(), s.max()
    if pd.isna(s_min) or pd.isna(s_max) or s_max == s_min:
        return pd.Series(0.0, index=s.index)
    scaled = ((f * s_max - 1.0) * (s - s_min)) / (s_max - s_min)
    return np.log(scaled + 1.0)


# 6개 지표 열 이름 (대시보드 가중치 커스텀도 이 열 이름으로 가중치를 넘김)
SCORE_COLUMNS = [
    "hhi_score",
    "defense_expenditure_score",
    "gpi_score",
    "korea_arms_trade_score",
    "company_trade_score",
    "fitch_score",
]


def critic_weights(df_indicators: pd.DataFrame) -> pd.Series:
    """CRITIC 가중치(w, 합계 1): 표준편차 × Σ(1 − 상관계수)를 합계로 나눔."""
    sigma = df_indicators.std()
    corr_matrix = df_indicators.corr(method="pearson")
    conflict = (1.0 - corr_matrix).sum(axis=1)
    C = sigma * conflict
    return C / C.sum()


def rescore(df_indicators: pd.DataFrame, weights) -> pd.DataFrame:
    """지표 점수 × 가중치로 final_score·rank 계산 (높은 점수 순 정렬).
    weights: {열 이름: 값} 또는 Series — 합계가 1(또는 100)이 아니어도 합계로 나눠 0~100점 유지.
    대시보드 '가중치 커스텀'에서 사용자 가중치로 다시 계산할 때도 이 함수를 사용."""
    w = pd.Series(weights, dtype=float).reindex(SCORE_COLUMNS).fillna(0.0)
    if w.sum() > 0:
        w = w / w.sum()
    res_df = df_indicators[SCORE_COLUMNS].copy()
    res_df["final_score"] = res_df.dot(w)
    res_df["rank"] = (
        res_df["final_score"].rank(ascending=False, method="min").astype(int)
    )
    return res_df.sort_values("final_score", ascending=False, kind="stable")


def compute_critic_score(df_indicators: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """주어진 지표 데이터프레임으로 CRITIC 가중치(w) 및 최종 점수/순위 산출."""
    w = critic_weights(df_indicators)
    return rescore(df_indicators, w), w


def round_to_100(w: pd.Series, decimals: int = 2) -> pd.Series:
    """가중치(합계 1)를 % 값으로 바꿔 합계가 정확히 100%가 되도록 소수점 decimals 자리로 맞춤.
    최대 잔여 반올림: 각 값을 내림한 뒤 모자란 만큼 버려진 소수점이 큰 항목부터 1단위씩 더함
    (버려진 소수점이 같으면 가중치가 큰 항목 우선). 출력 표시용이며 점수 계산은 원래 w를 사용.
    대시보드(components/weight_custom.py) 가중치 커스텀 기본값도 이 함수 결과를 그대로 사용."""
    unit = 10 ** decimals                                   # 0.01% 단위 → 100
    total = 100 * unit                                      # 100.00% → 10000
    scaled = w * total                                      # 예: 0.153631 → 1536.31
    floor = np.floor(scaled).astype(int)
    remain = int(round(total - floor.sum()))
    order = sorted(
        w.index,
        key=lambda k: (-round(float(scaled[k] - floor[k]), 6), -float(w[k])),
    )
    for k in order[:remain]:
        floor[k] += 1
    return floor / unit


# ==========================================
# 1. 기업 설정 및 데이터 로드
# ==========================================
COMPANY_CONFIG = {
    "한화에어로스페이스": {
        "code": "hanwha_aerospace",
        "score_columns": ["hanwha_aerospace_category_score"],
        "hist_column": "hanwha_aerospace_transaction_history",
    },
    "한화오션": {
        "code": "hanwha_ocean",
        "score_columns": ["hanwha_ocean_category_score"],
        "hist_column": "hanwha_ocean_transaction_history",
    },
    "현대로템": {
        "code": "hyundai_rotem",
        "score_columns": ["hyundai_rotem_category_score"],
        "hist_column": "hyundai_rotem_transaction_history",
    },
    "HD현대중공업": {
        "code": "hd_hyundai",
        "score_columns": ["hyundai_heavy_industries_category_score"],
        "hist_column": "hyundai_heavy_industries_transaction_history",
    },
    "LIG D&A": {
        "code": "lig_nex1",
        "score_columns": ["lig_category_score"],
        "hist_column": "lig_transaction_history",
    },
    "한국항공우주산업(KAI)": {
        "code": "kai",
        "score_columns": ["kai_category_score"],
        "hist_column": "kai_transaction_history",
    },
}

# 경로 설정 (프로젝트 디렉터리 구조에 맞게 조정 가능)
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / "processed"
data_path = DATA_DIR / "final_score.csv"

# # 만약 현재 작업 폴더에 final_score_1.csv가 있다면 우선 사용
# if not data_path.exists():
#     data_path = Path("final_score.csv")

def load_final_score(path: Path = data_path) -> pd.DataFrame:
    """final_score.csv 로드 (연도는 정수로 변환)."""
    df = pd.read_csv(path)
    df["year"] = pd.to_numeric(df["year"], errors="raise").astype(int)
    return df

START_YEAR = 2021
END_YEAR = 2025
TARGET_YEAR = 2026
TOP_N = 10


# ==========================================
# 2. 2021~2025 데이터 기반 2026 예측 실행
# ==========================================
def run_2026_prediction_detail(
    df: pd.DataFrame | None = None, verbose: bool = False
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.Series], pd.DataFrame]:
    """2026년 기업별 수출 유망국 산출.
    반환: (기업별 점수표, 기업별 CRITIC 가중치 w, 가중치 요약표)
    verbose=True면 터미널에 결과 출력 (대시보드는 False로 호출)."""
    if df is None:
        df = load_final_score()
    iso_index = df["iso_a3"].drop_duplicates().reset_index(drop=True)

    log = print if verbose else (lambda *args, **kwargs: None)   # verbose일 때만 터미널 출력

    df_period = df[df["year"].between(START_YEAR, END_YEAR)].copy()

    # ------------------------------------------
    # (1) 1번 지표: 공급국 집중도 HHI (Cost -> max_min 정규화)
    # ------------------------------------------
    hhi_series = (
        df[df["year"] == END_YEAR]
        .set_index("iso_a3")["hhi_5y"]
        .reindex(iso_index)
        .fillna(1.0)
    )
    hhi_5y_norm = max_min_normalize(hhi_series) * 100

    # ------------------------------------------
    # (2) 2번 지표: 국방비 종합 (총액, GDP 대비 비율, 연평균 TIV)
    # ------------------------------------------
    df_defense = (
        df_period.groupby("iso_a3")
        .agg(
            total_milex=("military_expenditure_usd", lambda x: x.sum(skipna=False)),
            avg_pct=("military_expenditure_gdp_pct", lambda x: x.mean(skipna=False)),
            avg_tiv=("tiv_total_1y", lambda x: x.mean()),
        )
        .reindex(iso_index)
        .fillna(0.0)
    )
    pos_milex = df_defense["total_milex"][df_defense["total_milex"] > 0]
    final_milex = (
        min_max_normalize(gii_log_transform(pos_milex, f=1e-7))
        .reindex(iso_index)
        .fillna(0.0)
    )

    pos_avg_pct = df_defense["avg_pct"][df_defense["avg_pct"] > 0]
    final_avg_pct = (
        min_max_normalize(gii_log_transform(pos_avg_pct, f=1.0))
        .reindex(iso_index)
        .fillna(0.0)
    )

    final_avg_tiv = (
        min_max_normalize(gii_log_transform(df_defense["avg_tiv"], f=1e-2))
        .reindex(iso_index)
        .fillna(0.0)
    )

    std_m1, std_m2, std_m3 = final_milex.std(), final_avg_pct.std(), final_avg_tiv.std()
    std_total = std_m1 + std_m2 + std_m3
    mil_score1 = (
        (std_m1 / std_total) * final_milex
        + (std_m2 / std_total) * final_avg_pct
        + (std_m3 / std_total) * final_avg_tiv
        if std_total > 0
        else pd.Series(0.0, index=iso_index)
    )
    final_mil_score = min_max_normalize(mil_score1) * 100

    # ------------------------------------------
    # (3) 3번 지표: 평화위협 지수 GPI
    # ------------------------------------------
    gpi_series = (
        df[df["year"] == END_YEAR]
        .set_index("iso_a3")["gpi_score_5y"]
        .reindex(iso_index)
    )
    gpi_norm = min_max_normalize(gpi_series) * 100

    # ------------------------------------------
    # (4) 4번 지표: 한국 전체 방산 거래 (G2G 국가 협력)
    # ------------------------------------------
    df_kor = (
        df_period.groupby("iso_a3")
        .agg(
            tiv_korea_sum=("tiv_korea", "sum"),
            import_from_korea=("import_from_south_korea", "mean"),
        )
        .reindex(iso_index)
    )
    norm_kor_tiv = min_max_normalize(
        gii_log_transform(df_kor["tiv_korea_sum"], f=10)
    )
    import_kor = df_kor["import_from_korea"]

    std_k1, std_k2 = norm_kor_tiv.std(), import_kor.std()
    std_k_total = std_k1 + std_k2
    transaction_with_korea = (
        min_max_normalize(
            (std_k1 / std_k_total) * norm_kor_tiv
            + (std_k2 / std_k_total) * import_kor
        ) * 100
        if std_k_total > 0
        else pd.Series(0.0, index=iso_index)
    )

    # ------------------------------------------
    # (6) 6번 지표: Fitch 신용등급 점수 (final_score_1.csv의 fitch_score 열)
    # ------------------------------------------
    fitch_series = (
        df[df["year"] == END_YEAR]
        .set_index("iso_a3")["fitch_score"]
        .reindex(iso_index)
        .fillna(0.0)  # 미평가/결측 국가는 D 등급 기본 점수(0.0) 부여
    )
    fitch_score_norm = min_max_normalize(fitch_series) * 100

    # ------------------------------------------
    # 기업별 (5)번 지표 산출 및 6개 지표 CRITIC 결합
    # ------------------------------------------
    company_results = {}
    company_weights = {}
    weight_records = []

    log("\n" + "=" * 105)
    log(f"=== [{START_YEAR}~{END_YEAR}년 데이터 기반 -> {TARGET_YEAR}년 기업별 수출 유망국 Top {TOP_N} 및 CRITIC 가중치] ===")
    log("=" * 105)

    for company_name, company_config in COMPANY_CONFIG.items():
        category_column = next(
            (name for name in company_config["score_columns"] if name in df.columns),
            None,
        )
        hist_col = company_config["hist_column"]

        # (5) 5번 지표: 기업 맞춤 적합도 (카테고리 소요 + 기업 거래 이력)
        df_company = (
            df_period.assign(score_filled=df_period[category_column].fillna(0.0))
            .groupby("iso_a3")
            .agg(
                category_mean=("score_filled", "mean"),
                company_tx_max=(hist_col, "max"),
            )
            .reindex(iso_index)
        )
        final_avg_category = (
            min_max_normalize(gii_log_transform(df_company["category_mean"], f=10))
            .reindex(iso_index)
            .fillna(0.0)
        )
        norm_comp_tx = 0.7 + 0.3 * df_company["company_tx_max"]

        std_c1, std_c2 = final_avg_category.std(), norm_comp_tx.std()
        std_c_total = std_c1 + std_c2
        company_category_score = (
            min_max_normalize(
                (std_c1 / std_c_total) * final_avg_category
                + (std_c2 / std_c_total) * norm_comp_tx
            ) * 100
            if std_c_total > 0
            else pd.Series(0.0, index=iso_index)
        )

        # 6개 지표 데이터프레임 구성
        df_6ind = pd.DataFrame(
            {
                "hhi_score": hhi_5y_norm,
                "defense_expenditure_score": final_mil_score,
                "gpi_score": gpi_norm,
                "korea_arms_trade_score": transaction_with_korea,
                "company_trade_score": company_category_score,
                "fitch_score": fitch_score_norm,
            },
            index=iso_index,
        )
        df_6ind.index.name = "iso_a3"

        df_scored, w = compute_critic_score(df_6ind)
        company_results[company_name] = df_scored
        company_weights[company_name] = w

        # 가중치 요약 레코드 저장
        w_row = {"기업명": company_name}
        w_pct = round_to_100(w)   # % 표시는 합계가 정확히 100.00%가 되도록 맞춤
        w_row.update({col: f"{val:.4f} ({w_pct[col]:.2f}%)" for col, val in w.items()})
        weight_records.append(w_row)

        # 터미널 출력: 기업별 가중치 w 및 Top 10 국가
        log(f"\n▶ [{company_name}] {TARGET_YEAR}년 추천 결과")
        log("  [6개 지표 CRITIC 가중치 (w)]")
        log("  " + " | ".join([f"{col}: {val:.4f} ({w_pct[col]:.2f}%)" for col, val in w.items()]))

        log(f"\n  [{TARGET_YEAR}년 수출 유망 국가 Top {TOP_N}]")
        display_cols = [
            "rank",
            "final_score",
            "hhi_score",
            "defense_expenditure_score",
            "gpi_score",
            "korea_arms_trade_score",
            "company_trade_score",
            "fitch_score",
        ]
        top10_df = df_scored.head(TOP_N)[display_cols].reset_index()
        log(top10_df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
        log("-" * 105)

    df_weights_summary = pd.DataFrame(weight_records)
    log("\n=== [기업별 6개 지표 CRITIC 가중치(w) 종합 요약] ===")
    log(df_weights_summary.to_string(index=False))
    log("=" * 105)

    return company_results, company_weights, df_weights_summary


def run_2026_prediction() -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """기존 호출 방식 유지: (기업별 점수표, 가중치 요약표) 반환 + 터미널 출력."""
    company_results, _, df_weights_summary = run_2026_prediction_detail(verbose=True)
    return company_results, df_weights_summary


if __name__ == "__main__":
    results_2026, weights_2026 = run_2026_prediction()