import numpy as np
import pandas as pd
from pathlib import Path
from analysis.fitch_filter import get_fitch_excluded_countries

# ==========================================
# 0. 공통 정규화 함수 및 Fitch 점수 매핑
# ==========================================

FITCH_SCORE_MAP = {
        "AAA": 100.0, "AA+": 100, "AA": 100, "AA-": 100,
        "A+": 100, "A": 100, "A-": 100, "BBB+": 100, "BBB": 100.0, "BBB-": 87.5,
        "BB+": 75.0, "BB": 62.5, "BB-": 50.0, "B+": 37.5, "B": 25.0, "B-": 12.5, 
        "CCC+": 0.0,  "CCC": 0.0,  "CCC-": 0.0,
        "CC": 0.0,    "C": 0.0,
        "RD": 0.0,    "D": 0.0,    "WD": 0.0,
    }

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


# ==========================================
# 1. 기업 설정 및 데이터 로드
# ==========================================
COMPANY_CONFIG = {
    "한화에어로스페이스": {
        "code": "hanwha_aerospace",
        "trade_names": ["Hanwha Aerospace"],
        "score_columns": ["hanwha_aerospace_category_score"],
        "hist_column": "hanwha_aerospace_transaction_history",
    },
    "한화오션": {
        "code": "hanwha_ocean",
        "trade_names": ["Hanwha Ocean"],
        "score_columns": ["hanwha_ocean_category_score"],
        "hist_column": "hanwha_ocean_transaction_history",
    },
    "현대로템": {
        "code": "hyundai_rotem",
        "trade_names": ["Hyundai Rotem"],
        "score_columns": ["hyundai_rotem_category_score"],
        "hist_column": "hyundai_rotem_transaction_history",
    },
    "HD현대중공업": {
        "code": "hd_hyundai",
        "trade_names": ["HD Hyundai Heavy Industries", "Hyundai Heavy Industries"],
        "score_columns": [
            "hd_hyundai_category_score",
            "hyundai_heavy_industries_category_score",
        ],
        "hist_column": "hyundai_heavy_industries_transaction_history",
    },
    "LIG D&A": {
        "code": "lig_nex1",
        "trade_names": ["LIG Nex1", "LIG D&A"],
        "score_columns": ["lig_nex1_category_score", "lig_category_score"],
        "hist_column": "lig_transaction_history",
    },
    "한국항공우주산업(KAI)": {
        "code": "kai",
        "trade_names": ["KAI", "Korea Aerospace Industries"],
        "score_columns": [
            "kai_category_score",
            "korea_aerospace_industries_category_score",
        ],
        "hist_column": "kai_transaction_history",
    },
}

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / "processed"
data_path = DATA_DIR / "final_score_1.csv"
weapon_data_path = DATA_DIR / "korea_weapon_data.csv"
fitch_csv_path = DATA_DIR / "fitchrating.csv"

df = pd.read_csv(data_path)
df["year"] = pd.to_numeric(df["year"], errors="raise").astype(int)
df_weapon = pd.read_csv(weapon_data_path)

# Fitch 원본 데이터 로드 (6번째 지표 점수 계산용)
df_fitch_raw = pd.read_csv(fitch_csv_path, dtype=str)
df_fitch_raw["iso_a3"] = df_fitch_raw["iso_a3"].str.strip().str.upper()
df_fitch_raw["rating"] = df_fitch_raw["rating"].str.strip().str.upper()
df_fitch_raw["rating_action_date"] = pd.to_datetime(
    df_fitch_raw["rating_action_date"], errors="raise"
)

iso_index = df["iso_a3"].drop_duplicates().reset_index(drop=True)
END_YEARS = [2020, 2021, 2022, 2023, 2024]
TOP_N = 10


def get_fitch_score_series(prediction_year: int) -> pd.Series:
    """예측 연도 직전(prediction_year-01-01 이전) 최신 Fitch 등급을 점수로 변환 후 정규화."""
    cutoff = pd.Timestamp(year=prediction_year, month=1, day=1)
    sub = df_fitch_raw.loc[df_fitch_raw["rating_action_date"] < cutoff].copy()
    latest = (
        sub.sort_values("rating_action_date", kind="stable")
        .drop_duplicates(subset="iso_a3", keep="last")
    )
    
    # "D" 등급 점수(0.0)를 미평가/누락 국가의 기본 점수로 일원화
    default_fitch_score = FITCH_SCORE_MAP.get("D")
    
    score_map = {
        row["iso_a3"]: FITCH_SCORE_MAP.get(row["rating"], default_fitch_score)
        for _, row in latest.iterrows()
    }
    raw_scores = pd.Series(
        [score_map.get(iso, default_fitch_score) for iso in iso_index],  # 0.0 하드코딩 대신 default_fitch_score 사용
        index=iso_index,
        dtype=float,
    )
    return min_max_normalize(raw_scores)


def compute_critic_score(df_indicators: pd.DataFrame) -> pd.DataFrame:
    """주어진 지표 데이터프레임으로 CRITIC 가중치 및 최종 점수/순위 산출."""
    res_df = df_indicators.copy()
    sigma = res_df.std()
    corr_matrix = res_df.corr(method="pearson")
    conflict = (1.0 - corr_matrix).sum(axis=1)
    C = sigma * conflict
    w = C / C.sum()

    res_df["final_score"] = res_df.dot(w)
    res_df["rank"] = (
        res_df["final_score"].rank(ascending=False, method="min").astype(int)
    )
    return res_df.sort_values("final_score", ascending=False, kind="stable")


# ==========================================
# 2. 단일 기업 & 단일 연도 백테스팅 함수 (5지표 vs 6지표 비교)
# ==========================================
def run_single_backtest(company_name: str, end_year: int) -> dict:
    company_config = COMPANY_CONFIG[company_name]
    category_column = next(
        (name for name in company_config["score_columns"] if name in df.columns),
        None,
    )
    hist_col = company_config["hist_column"]
    start_year = end_year - 4
    target_year = end_year + 1

    df_period = df[df["year"].between(start_year, end_year)].copy()

    # (1) 공급국 집중도 HHI
    hhi_series = (
        df[df["year"] == end_year]
        .set_index("iso_a3")["hhi_5y"]
        .reindex(iso_index)
        .fillna(1.0)
    )
    hhi_5y_norm = max_min_normalize(hhi_series)

    # (2) 국방비
    df_defense = (
        df_period.groupby("iso_a3")
        .agg(
            total_milex=("military_expenditure_usd", lambda x: x.sum(skipna=False)),
            avg_pct=("military_expenditure_gdp_pct", lambda x: x.mean(skipna=False)),
            avg_tiv=('tiv_total_1y', lambda x: x.mean())
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
    # print(final_milex.skew(), final_milex.kurt())
    pos_avg_pct = df_defense["avg_pct"][df_defense["avg_pct"] > 0]
    final_avg_pct = (
        min_max_normalize(gii_log_transform(pos_avg_pct, f=1.0))
        .reindex(iso_index)
        .fillna(0.0)
    )
    # final_avg_pct = min_max_normalize(final_avg_pct).reindex(iso_index).fillna(0.0)
    # print(final_avg_pct.skew(), final_avg_pct.kurt())

    

    
    final_avg_tiv = (
        min_max_normalize(gii_log_transform(df_defense["avg_tiv"], f=1e-2))
        .reindex(iso_index)
        .fillna(0.0)
    )
    # final_avg_tiv = min_max_normalize(final_avg_tiv).reindex(iso_index).fillna(0.0)
    # print(df_defense['avg_tiv'].skew(), df_defense['avg_tiv'].kurt())
    # print(gii_log_transform(df_defense['avg_tiv'], f=1e-2).skew(), gii_log_transform(df_defense['avg_tiv'], f=1e-2).kurt())






    std_m1, std_m2, std_m3 = final_milex.std(), final_avg_pct.std(), final_avg_tiv.std()
    std_total = std_m1 + std_m2 + std_m3
    mil_score1 = (
        (std_m1 / std_total) * final_milex + (std_m2 / std_total) * final_avg_pct + (std_m3 / std_total) * final_avg_tiv
        if std_total > 0
        else pd.Series(0.0, index=iso_index)
    )
    final_mil_score = min_max_normalize(mil_score1)

    # (3) GPI
    gpi_series = (
        df[df["year"] == end_year]
        .set_index("iso_a3")["gpi_score_5y"]
        .reindex(iso_index)
    )
    gpi_norm = min_max_normalize(gpi_series)

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
        )
        if std_k_total > 0
        else pd.Series(0.0, index=iso_index)
    )

    # ------------------------------------------
    # (5) 5번 지표: 기업 맞춤 적합도 (카테고리 소요 + 기업 거래 이력)
    # ------------------------------------------
    df_company = (
        df_period.assign(score_filled=df_period[category_column].fillna(0.0))
        .groupby("iso_a3")
        .agg(
            category_mean=("score_filled", "mean"),
            company_tx_max=(hist_col, "max"),
        )
        .reindex(iso_index)
    )
    # norm_cat_score = min_max_normalize(df_company["category_mean"])
    # print(norm_cat_score.skew(), norm_cat_score.kurt())




    final_avg_category = (
        min_max_normalize(gii_log_transform(df_company["category_mean"], f=10))
        .reindex(iso_index)
        .fillna(0.0)
    )
    # print(final_avg_category.skew(), final_avg_category.kurt())




    norm_comp_tx = 0.7 + 0.3 * df_company["company_tx_max"]
    # print(norm_comp_tx.skew(), norm_comp_tx.kurt())

    # final_avg_comp = (
    #     min_max_normalize(gii_log_transform(df_company["company_tx_mean"], f=10))
    #     .reindex(iso_index)
    #     .fillna(0.0)
    # )
    # print(final_avg_comp.skew(), final_avg_comp.kurt())


    # [핵심] 0/1 이력을 0.5~1.0 스케일로 선형 변환 (0 -> 0.5, 1 -> 1.0)
    # 재정규화(min_max)를 태우지 않고 스케일 자체의 표준편차를 활용!
    # norm_comp_tx = 0.5 + 0.5 * min_max_normalize(df_company["company_tx_mean"])

    std_c1, std_c2 = final_avg_category.std(), norm_comp_tx.std()
    std_c_total = std_c1 + std_c2
    company_category_score = (
        min_max_normalize(
            (std_c1 / std_c_total) * final_avg_category
            + (std_c2 / std_c_total) * norm_comp_tx
        )
        if std_c_total > 0
        else pd.Series(0.0, index=iso_index)
    )

    # (6) 6번째 지표: Fitch 신용등급 점수 (0~1 정규화)
    fitch_score_norm = get_fitch_score_series(prediction_year=target_year)
    # print(fitch_score_norm.skew(), fitch_score_norm.kurt())



    # ------------------------------------------
    # 모델 A & B: 기존 5개 지표 기반 CRITIC
    # ------------------------------------------
    df_5ind = pd.DataFrame(
        {
            "hhi_5y": hhi_5y_norm,
            "final_mil_score": final_mil_score,
            "gpi_score_5y": gpi_norm,
            "transaction_with_korea": transaction_with_korea,
            "company_category_score": company_category_score,
        },
        index=iso_index,
    )
    df_5ind.index.name = "iso_a3"
    df_5_scored = compute_critic_score(df_5ind)

    # ------------------------------------------
    # 모델 C & D: 6개 지표(Fitch 점수 추가) 기반 CRITIC
    # ------------------------------------------
    df_6ind = df_5ind.copy()
    df_6ind["fitch_score"] = fitch_score_norm
    df_6_scored = compute_critic_score(df_6ind)

    # 하드 필터 제외 대상 국가 (B- 미만 및 미평가)
    excluded_ratings = get_fitch_excluded_countries(
        prediction_year=target_year, return_ratings=True
    )
    excluded_countries = set(excluded_ratings)

    # 각 모델별 Top 10 추출
    # [1] 5지표 (필터 전)
    top10_5_before = df_5_scored.head(TOP_N).index.tolist()

    # [2] 5지표 + 하드 필터
    df_5_filtered = df_5_scored.loc[~df_5_scored.index.isin(excluded_countries)].copy()
    df_5_filtered["recommend_rank"] = range(1, len(df_5_filtered) + 1)
    top10_5_after = df_5_filtered.head(TOP_N).index.tolist()

    # [3] 6지표 (필터 없이 점수만 반영)
    top10_6_before = df_6_scored.head(TOP_N).index.tolist()

    # [4] 6지표 + 하드 필터
    df_6_filtered = df_6_scored.loc[~df_6_scored.index.isin(excluded_countries)].copy()
    df_6_filtered["recommend_rank"] = range(1, len(df_6_filtered) + 1)
    top10_6_after = df_6_filtered.head(TOP_N).index.tolist()

    # 실제 수출 계약 국가 확인
    trade_names = company_config["trade_names"]
    actual_contracts = df_weapon[
        df_weapon["company"].astype(str).str.strip().isin(trade_names)
        & (pd.to_numeric(df_weapon["order_year"], errors="coerce") == target_year)
    ]
    actual_countries = (
        actual_contracts["recipient_iso_a3"].dropna().drop_duplicates().tolist()
    )

    return {
        "company": company_name,
        "target_year": target_year,
        "actual_countries": actual_countries,
        "m_5_before": [c for c in actual_countries if c in top10_5_before],
        "m_5_after": [c for c in actual_countries if c in top10_5_after],
        "df_5_scored": df_5_scored,        # [추가] 1) 5지표(필터전) 순위 참조용
        "m_6_before": [c for c in actual_countries if c in top10_6_before],
        "m_6_after": [c for c in actual_countries if c in top10_6_after],
        "df_5_filtered": df_5_filtered,
        "df_6_scored": df_6_scored,        # [추가] 3) 6지표(필터전) 순위 참조용
        "df_6_filtered": df_6_filtered,
    }


# ==========================================
# 3. 전체 백테스팅 실행 및 비교 요약 출력
# ==========================================
all_results = [
    run_single_backtest(comp, yr)
    for comp in COMPANY_CONFIG
    for yr in END_YEARS
]

summary_rows = []
for comp in COMPANY_CONFIG:
    c_res = [r for r in all_results if r["company"] == comp]
    tot = sum(len(r["actual_countries"]) for r in c_res)
    h_5_b = sum(len(r["m_5_before"]) for r in c_res)
    h_5_a = sum(len(r["m_5_after"]) for r in c_res)
    h_6_b = sum(len(r["m_6_before"]) for r in c_res)
    h_6_a = sum(len(r["m_6_after"]) for r in c_res)

    summary_rows.append({
        "기업명": comp,
        "계약건수": tot,
        "1) 5지표(필터전)": f"{h_5_b}/{tot} ({h_5_b/tot*100:4.1f}%)" if tot else "-",
        "2) 5지표+하드필터": f"{h_5_a}/{tot} ({h_5_a/tot*100:4.1f}%)" if tot else "-",
        "3) 6지표(필터전)": f"{h_6_b}/{tot} ({h_6_b/tot*100:4.1f}%)" if tot else "-",
        "4) 6지표+하드필터": f"{h_6_a}/{tot} ({h_6_a/tot*100:4.1f}%)" if tot else "-",
    })

print("\n" + "=" * 95)
print("=== [신용등급 6번째 지표 편입 전·후 백테스팅 비교 요약 (2021~2025 누적)] ===")
print("=" * 95)
print(pd.DataFrame(summary_rows).to_string(index=False))

g_tot = sum(len(r["actual_countries"]) for r in all_results)
for label, key in [
    ("1) 기존 5지표 (필터 전)         ", "m_5_before"),
    ("2) 기존 5지표 + Fitch 하드필터  ", "m_5_after"),
    ("3) 6지표(신용점수) (필터 전)    ", "m_6_before"),
    ("4) 6지표(신용점수) + 하드필터   ", "m_6_after"),
]:
    hits = sum(len(r[key]) for r in all_results)
    print(f"• {label}: {hits:2d} / {g_tot}건 적중 ({hits / g_tot * 100:5.1f}%)")
print("=" * 95)


# ==========================================
# 4. 신용등급(Fitch) vs 5개 지표 피어슨 상관계수 심층 분석
# ==========================================
print("\n" + "=" * 95)
print("=== [신용등급(Fitch) vs 타 5개 지표 간 피어슨 상관계수(r) 분석] ===")
print("=" * 95)

# 지표 매핑 딕셔너리
indicator_labels = {
    "hhi_5y": "1) HHI 집중도",
    "final_mil_score": "2) 국방비 종합",
    "gpi_score_5y": "3) 평화위협(GPI)",
    "transaction_with_korea": "4) 한국거래(G2G)",
    "company_category_score": "5) 기업적합도",
}
target_feats = list(indicator_labels.keys())

# 30회 실행 전체에서 상관계수 벡터 수집
corr_records = []
for r in all_results:
    comp = r["company"]
    yr = r["target_year"]
    df_feat = r["df_6_scored"][target_feats + ["fitch_score"]]
    corr_series = df_feat.corr(method="pearson")["fitch_score"].drop("fitch_score")
    
    row = {"기업명": comp, "추천연도": yr, "회차": f"[{yr-5}~{yr-1} -> {yr}년]"}
    for col, name in indicator_labels.items():
        row[name] = corr_series[col]
    corr_records.append(row)

df_all_corr = pd.DataFrame(corr_records)

# -------------------------------------------------------------
# [4-1] 공통 4대 거시 지표 vs Fitch 상관계수 (기업 무관, 연도별 100% 동일)
# -------------------------------------------------------------
macro_cols = ["1) HHI 집중도", "2) 국방비 종합", "3) 평화위협(GPI)", "4) 한국거래(G2G)"]
df_macro = df_all_corr.drop_duplicates(subset=["추천연도"])[["회차"] + macro_cols].copy()
for col in macro_cols:
    df_macro[col] = df_macro[col].apply(lambda v: f"{v:+.4f}")

print("\n[4-1. 공통 4대 거시 지표 vs Fitch 신용등급 상관계수 추이 (기업 공통)]")
print(df_macro.to_string(index=False))
print("-" * 95)

# -------------------------------------------------------------
# [4-2] 기업별 5번 지표(기업 맞춤 적합도) vs Fitch 상관계수 피벗 테이블
# -------------------------------------------------------------
pivot_cat = df_all_corr.pivot_table(
    index="기업명",
    columns="추천연도",
    values=indicator_labels["company_category_score"]
)
pivot_cat["평균(Mean)"] = pivot_cat.mean(axis=1)
pivot_cat_fmt = pivot_cat.apply(lambda col: col.map(lambda v: f"{v:+.4f}"))

print("\n[4-2. 기업별 5번 지표(기업 맞춤 적합도) vs Fitch 신용등급 상관계수 현황]")
print(pivot_cat_fmt.to_string())
print("-" * 95)

# -------------------------------------------------------------
# [4-3] 5개 지표 vs Fitch 상관계수 종합 통계 (30회 실행 누적 요약)
# -------------------------------------------------------------
stat_cols = list(indicator_labels.values())
stats_fitch = df_all_corr[stat_cols].agg(["mean", "std", "min", "max"]).T
stats_fitch.columns = ["평균(r)", "표준편차", "최소(r)", "최대(r)"]

def get_corr_direction(m: float) -> str:
    if m <= -0.70:
        return "강한 음(-)의 상관"
    elif m < -0.30:
        return "중간 정도 음(-)의 상관"
    elif m >= 0.70:
        return "강한 양(+)의 상관"
    elif m > 0.30:
        return "중간 정도 양(+)의 상관"
    return "약한 상관 / 독립"

stats_fitch["상관관계 방향"] = stats_fitch["평균(r)"].apply(get_corr_direction)
stats_fitch["평균(r)"] = stats_fitch["평균(r)"].apply(lambda v: f"{v:+.4f}")
stats_fitch["표준편차"] = stats_fitch["표준편차"].apply(lambda v: f"{v:.4f}")
stats_fitch["최소(r)"] = stats_fitch["최소(r)"].apply(lambda v: f"{v:+.4f}")
stats_fitch["최대(r)"] = stats_fitch["최대(r)"].apply(lambda v: f"{v:+.4f}")

print("\n[4-3. 5개 지표 vs Fitch 신용등급 상관계수 종합 요약 통계 (30회 누적)]")
print(stats_fitch.to_string())
print("=" * 95)

# ==========================================
# 5. 실제 계약 성사 국가들의 모델별 순위 분석 (산술 평균 및 중앙값)
# ==========================================
print("\n" + "=" * 95)
print("=== [실제 계약 성사 국가들의 모델별 추천 순위 분석 (산술 평균 및 중앙값)] ===")
print("=" * 95)

rank_records = []

for r in all_results:
    comp = r["company"]
    target_yr = r["target_year"]
    for c in r["actual_countries"]:
        # 1) 5지표 (필터 전): 전체 풀 내 순위 (rank)
        r_5_b = r["df_5_scored"].loc[c, "rank"] if c in r["df_5_scored"].index else np.nan

        # 2) 5지표 + 하드필터: 필터 통과 국가 내 추천 순위 (recommend_rank)
        r_5_a = (
            r["df_5_filtered"].loc[c, "recommend_rank"]
            if c in r["df_5_filtered"].index
            else np.nan
        )

        # 3) 6지표 (필터 전): 전체 풀 내 순위 (rank)
        r_6_b = r["df_6_scored"].loc[c, "rank"] if c in r["df_6_scored"].index else np.nan

        # 4) 6지표 + 하드필터: 필터 통과 국가 내 추천 순위 (recommend_rank)
        r_6_a = (
            r["df_6_filtered"].loc[c, "recommend_rank"]
            if c in r["df_6_filtered"].index
            else np.nan
        )

        rank_records.append({
            "기업명": comp,
            "계약연도": target_yr,
            "체결국가": c,
            "1) 5지표(필터전)": r_5_b,
            "2) 5지표+하드필터": r_5_a,
            "3) 6지표(필터전)": r_6_b,
            "4) 6지표+하드필터": r_6_a,
        })

df_ranks = pd.DataFrame(rank_records)

if df_ranks.empty:
    print("실제 계약 성사 데이터가 존재하지 않습니다.")
else:
    cases = [
        ("1) 기존 5지표 (필터 전)", "1) 5지표(필터전)"),
        ("2) 기존 5지표 + 하드필터", "2) 5지표+하드필터"),
        ("3) 6지표(신용점수) (필터 전)", "3) 6지표(필터전)"),
        ("4) 6지표(신용점수) + 하드필터", "4) 6지표+하드필터"),
    ]

    total_actual_cnt = len(df_ranks)
    stats_summary = []

    for label, col in cases:
        valid_series = df_ranks[col].dropna()
        valid_cnt = len(valid_series)
        excluded_cnt = total_actual_cnt - valid_cnt

        mean_rank = valid_series.mean()
        median_rank = valid_series.median()

        # 하드필터로 인해 제외된 실제 계약국이 있을 경우 표기
        note = f"{valid_cnt}/{total_actual_cnt}건"
        if excluded_cnt > 0:
            note += f" (하드필터 제외 {excluded_cnt}건)"

        stats_summary.append({
            "모델 구분": label,
            "유효 집계 건수": note,
            "산술 평균 순위": f"{mean_rank:6.2f}위" if not pd.isna(mean_rank) else "-",
            "중앙값(Median)": f"{median_rank:6.1f}위" if not pd.isna(median_rank) else "-",
        })

    # [1] 전체 종합 요약 출력
    print(pd.DataFrame(stats_summary).to_string(index=False))
    print("-" * 95)

    # [2] 기업별 평균 및 중앙값 비교 테이블
    comp_stats = []
    for comp in COMPANY_CONFIG:
        sub = df_ranks[df_ranks["기업명"] == comp]
        if sub.empty:
            continue
        
        comp_stats.append({
            "기업명": comp,
            "계약건수": len(sub),
            "5지표(전) 평균/중앙": f"{sub['1) 5지표(필터전)'].mean():.1f} / {sub['1) 5지표(필터전)'].median():.1f}",
            "5지표+필터 평균/중앙": f"{sub['2) 5지표+하드필터'].mean():.1f} / {sub['2) 5지표+하드필터'].median():.1f}",
            "6지표(전) 평균/중앙": f"{sub['3) 6지표(필터전)'].mean():.1f} / {sub['3) 6지표(필터전)'].median():.1f}",
            "6지표+필터 평균/중앙": f"{sub['4) 6지표+하드필터'].mean():.1f} / {sub['4) 6지표+하드필터'].median():.1f}",
        })

    if comp_stats:
        print("\n[기업별 실제 체결 국가 추천 순위 요약 (평균 / 중앙값)]")
        print(pd.DataFrame(comp_stats).to_string(index=False))
        print("-" * 95)

    # [3] 각 계약 건별 상세 순위 확인용 출력
    print("\n[상세 내역: 실제 계약 성사 건별 4가지 모델 추천 순위]")
    print(df_ranks.to_string(index=False))
    print("=" * 95)
    
# ==========================================
# 6. 실제 계약 성사 국가들의 모델별 Top 5 안착 비율 분석
# ==========================================
print("\n" + "=" * 95)
print("=== [실제 계약 성사 국가들의 모델별 Top 5 안착 비율 분석 (Hit Ratio @ Top 5)] ===")
print("=" * 95)

if not df_ranks.empty:
    total_contracts = len(df_ranks)
    top5_summary = []

    target_cases = [
        ("1) 기존 5지표 (필터 전)", "1) 5지표(필터전)"),
        ("2) 기존 5지표 + 하드필터", "2) 5지표+하드필터"),
        ("3) 6지표(신용점수) (필터 전)", "3) 6지표(필터전)"),
        ("4) 6지표(신용점수) + 하드필터", "4) 6지표+하드필터"),
    ]

    # [1] 전체 종합 요약 집계
    for label, col in target_cases:
        top5_cnt = int((df_ranks[col] <= 5).sum())
        ratio = (top5_cnt / total_contracts) * 100 if total_contracts > 0 else 0.0
        top5_summary.append({
            "모델 구분": label,
            "Top 5 안착 건수": f"{top5_cnt} / {total_contracts}건",
            "안착 비율 (%)": f"{ratio:5.1f}%",
        })

    print(pd.DataFrame(top5_summary).to_string(index=False))
    print("-" * 95)

    # # [2] 기업별 Top 5 안착 비율 비교 테이블
    # comp_top5_rows = []
    # for comp in COMPANY_CONFIG:
    #     sub = df_ranks[df_ranks["기업명"] == comp]
    #     if sub.empty:
    #         continue
    #     c_tot = len(sub)

    #     row = {"기업명": comp, "계약건수": c_tot}
    #     for _, col in target_cases:
    #         c_hits = int((sub[col] <= 5).sum())
    #         c_ratio = (c_hits / c_tot) * 100 if c_tot > 0 else 0.0
    #         row[col] = f"{c_hits}/{c_tot} ({c_ratio:4.1f}%)"
    #     comp_top5_rows.append(row)

    # if comp_top5_rows:
    #     print("\n[기업별 실제 체결 국가 Top 5 안착 요약]")
    #     print(pd.DataFrame(comp_top5_rows).to_string(index=False))
    #     print("-" * 95)

    # # [3] 터미널 한 줄 요약 출력
    # for item in top5_summary:
    #     print(f"• {item['모델 구분']:<28}: {item['Top 5 안착 건수']} 안착 ({item['안착 비율 (%)']})")
    # print("=" * 95)
    
# ==========================================
# 7. CRITIC 가중치 요약 분석 (종합 통계 / 기업별 / 연도별)
# ==========================================
print("\n" + "=" * 95)
print("=== [CRITIC 가중치(Weights) 심층 요약 분석] ===")
print("=" * 95)

def extract_critic_weights(df_scored: pd.DataFrame) -> pd.Series:
    """df_scored에서 지표 컬럼을 추출하여 원본 CRITIC 가중치(w)를 산출."""
    feature_cols = [c for c in df_scored.columns if c not in ["final_score", "rank", "recommend_rank"]]
    df_feat = df_scored[feature_cols]
    sigma = df_feat.std()
    corr = df_feat.corr(method="pearson")
    conflict = (1.0 - corr).sum(axis=1)
    c = sigma * conflict
    return c / c.sum()

weights_5_records = []
weights_6_records = []

for r in all_results:
    comp = r["company"]
    yr = r["target_year"]
    
    # 5지표 가중치 추출
    w_5 = extract_critic_weights(r["df_5_scored"])
    w_5_dict = w_5.to_dict()
    w_5_dict.update({"기업명": comp, "추천연도": yr})
    weights_5_records.append(w_5_dict)
    
    # 6지표 가중치 추출
    w_6 = extract_critic_weights(r["df_6_scored"])
    w_6_dict = w_6.to_dict()
    w_6_dict.update({"기업명": comp, "추천연도": yr})
    weights_6_records.append(w_6_dict)

df_w5 = pd.DataFrame(weights_5_records)
df_w6 = pd.DataFrame(weights_6_records)

# [1] 전체 30회 실행 종합 통계 (평균, 표준편차, Min, Max)
feat_w5 = [c for c in df_w5.columns if c not in ["기업명", "추천연도"]]
feat_w6 = [c for c in df_w6.columns if c not in ["기업명", "추천연도"]]

stat_w5 = df_w5[feat_w5].agg(["mean", "std", "min", "max"]).T
stat_w5.columns = ["평균(%)", "표준편차", "최소(%)", "최대(%)"]
stat_w5["평균(%)"] = (stat_w5["평균(%)"] * 100).round(2)
stat_w5["최소(%)"] = (stat_w5["최소(%)"] * 100).round(2)
stat_w5["최대(%)"] = (stat_w5["최대(%)"] * 100).round(2)
stat_w5["표준편차"] = stat_w5["표준편차"].round(4)

stat_w6 = df_w6[feat_w6].agg(["mean", "std", "min", "max"]).T
stat_w6.columns = ["평균(%)", "표준편차", "최소(%)", "최대(%)"]
stat_w6["평균(%)"] = (stat_w6["평균(%)"] * 100).round(2)
stat_w6["최소(%)"] = (stat_w6["최소(%)"] * 100).round(2)
stat_w6["최대(%)"] = (stat_w6["최대(%)"] * 100).round(2)
stat_w6["표준편차"] = stat_w6["표준편차"].round(4)

print("\n[1-1. 기존 5지표 모델: CRITIC 가중치 종합 통계 (30회 실행 누적)]")
print(stat_w5.to_string())

print("\n[1-2. 6지표 모델(신용등급 편입): CRITIC 가중치 종합 통계 (30회 실행 누적)]")
print(stat_w6.to_string())
print("-" * 95)

# [2] 기업별 평균 가중치 피벗 테이블 (6지표 기준)
comp_w6 = (df_w6.groupby("기업명")[feat_w6].mean() * 100).round(2)
print("\n[2. 기업별 6개 지표 평균 가중치 배분 현황 (%)]")
print(comp_w6.to_string())
print("-" * 95)

# [3] 연도별 평균 가중치 추이 피벗 테이블 (6지표 기준)
year_w6 = (df_w6.groupby("추천연도")[feat_w6].mean() * 100).round(2)
print("\n[3. 추천 연도별 6개 지표 평균 가중치 추이 (%)]")
print(year_w6.to_string())
print("=" * 95)


# ==========================================
# 8. 단일 지표 베이스라인 vs 종합 모델 백테스팅 비교 (성능 검증)
# ==========================================
print("\n" + "=" * 95)
print("=== [단일 지표 베이스라인(Naive Baseline) vs 종합 모델 벤치마크 비교] ===")
print("=" * 95)

# 단일 지표 순위 산출을 위한 백테스팅 루프
baseline_records = []

for end_year in END_YEARS:
    start_year = end_year - 4
    target_year = end_year + 1
    df_period = df[df["year"].between(start_year, end_year)].copy()

    # 단일 지표 1: 5개년 누적 국방비 USD
    s_milex = df_period.groupby("iso_a3")["military_expenditure_usd"].sum().reindex(iso_index).fillna(0.0)
    rk_milex = s_milex.rank(ascending=False, method="min").astype(int)

    # 단일 지표 2: 5개년 연평균 TIV 무기수입량
    s_tiv = df_period.groupby("iso_a3")["tiv_total_1y"].mean().reindex(iso_index).fillna(0.0)
    rk_tiv = s_tiv.rank(ascending=False, method="min").astype(int)

    # 단일 지표 3: 5개년 누적 대 한국 무기 수입 실적
    s_kor = df_period.groupby("iso_a3")["tiv_korea"].sum().reindex(iso_index).fillna(0.0)
    rk_kor = s_kor.rank(ascending=False, method="min").astype(int)

    for comp, conf in COMPANY_CONFIG.items():
        # 단일 지표 4: 기업별 카테고리 수입 실적
        cat_col = next((c for c in conf["score_columns"] if c in df.columns), None)
        if cat_col:
            s_cat = df_period.assign(filled=df_period[cat_col].fillna(0.0)).groupby("iso_a3")["filled"].mean().reindex(iso_index).fillna(0.0)
            rk_cat = s_cat.rank(ascending=False, method="min").astype(int)
        else:
            rk_cat = pd.Series(np.nan, index=iso_index)

        trade_names = conf["trade_names"]
        sub_weapon = df_weapon[
            df_weapon["company"].astype(str).str.strip().isin(trade_names)
            & (pd.to_numeric(df_weapon["order_year"], errors="coerce") == target_year)
        ]
        actual_countries = sub_weapon["recipient_iso_a3"].dropna().drop_duplicates().tolist()

        for c in actual_countries:
            baseline_records.append({
                "기업명": comp,
                "계약연도": target_year,
                "체결국가": c,
                "단순 국방비 총액 (Total Milex)": rk_milex.get(c, np.nan),
                "단순 무기 수입량 (Avg TIV)": rk_tiv.get(c, np.nan),
                "대 한국 거래 실적 (Korea TIV)": rk_kor.get(c, np.nan),
                "기업 카테고리 수입량 (Category Mean)": rk_cat.get(c, np.nan),
            })

df_baseline_ranks = pd.DataFrame(baseline_records)

# 종합 비교 테이블 생성 (단일 지표 4종 + 종합 모델 4종)
all_benchmarks = [
    # [1] 단일 지표 베이스라인
    ("단일: 단순 국방비 총액 (Total Milex)", df_baseline_ranks["단순 국방비 총액 (Total Milex)"]),
    ("단일: 단순 무기 수입량 (Avg TIV)", df_baseline_ranks["단순 무기 수입량 (Avg TIV)"]),
    ("단일: 대 한국 거래 실적 (Korea TIV)", df_baseline_ranks["대 한국 거래 실적 (Korea TIV)"]),
    ("단일: 기업 카테고리 수입량 (Category Mean)", df_baseline_ranks["기업 카테고리 수입량 (Category Mean)"]),
    # [2] 종합 모델 (df_ranks에서 참조)
    ("종합: 1) 기존 5지표 (필터 전)", df_ranks["1) 5지표(필터전)"]),
    ("종합: 2) 기존 5지표 + 하드필터", df_ranks["2) 5지표+하드필터"]),
    ("종합: 3) 6지표(신용점수) (필터 전)", df_ranks["3) 6지표(필터전)"]),
    ("종합: 4) 6지표(신용점수) + 하드필터", df_ranks["4) 6지표+하드필터"]),
]

bench_summary = []
tot_cnt = len(df_ranks)

for label, s_rank in all_benchmarks:
    valid_s = s_rank.dropna()
    top5_hits = int((s_rank <= 5).sum())
    top10_hits = int((s_rank <= 10).sum())
    mean_rk = valid_s.mean()
    med_rk = valid_s.median()

    bench_summary.append({
        "모델 / 지표 구분": label,
        "Top 5 안착률": f"{top5_hits:2d}/{tot_cnt} ({top5_hits/tot_cnt*100:5.1f}%)",
        "Top 10 안착률": f"{top10_hits:2d}/{tot_cnt} ({top10_hits/tot_cnt*100:5.1f}%)",
        "실제 체결국 평균순위": f"{mean_rk:6.2f}위" if not pd.isna(mean_rk) else "-",
        "중앙값 순위": f"{med_rk:5.1f}위" if not pd.isna(med_rk) else "-",
    })

print(pd.DataFrame(bench_summary).to_string(index=False))
print("=" * 95)

# # ==========================================
# # 9. 실제 거래 38건 대상 체결 국가별 Fitch 신용등급 및 평가 현황 심층 분석
# # ==========================================
# print("\n" + "=" * 105)
# print("=== [실제 거래 성사 38건: 체결 국가별 당시 Fitch 신용등급 및 평가 점수 책정 현황] ===")
# print("=" * 105)

# # 국가명 컬럼 탐색 (df 또는 df_weapon에 존재할 경우 매핑)
# name_map = {}
# for source_df in [df, df_weapon]:
#     for col in ["country", "country_name", "recipient_country", "recipient"]:
#         if col in source_df.columns:
#             iso_col = "iso_a3" if "iso_a3" in source_df.columns else "recipient_iso_a3"
#             if iso_col in source_df.columns:
#                 valid_pairs = source_df[[iso_col, col]].dropna().drop_duplicates()
#                 for _, row in valid_pairs.iterrows():
#                     name_map[str(row[iso_col]).strip().upper()] = str(row[col]).strip()
#             break
#     if name_map:
#         break

# investment_grades = {"AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-"}
# speculative_grades = {"BB+", "BB", "BB-", "B+", "B", "B-"}

# # 미평가 및 D등급 기본 점수 (10.0점)
# default_fitch_score = FITCH_SCORE_MAP.get("D")

# fitch_tx_records = []
# seq_no = 1

# for r in all_results:
#     comp = r["company"]
#     target_yr = r["target_year"]
#     actual_list = r["actual_countries"]
#     df_6_scored = r["df_6_scored"]

#     # 해당 연도 직전(1월 1일 기준) 유효 Fitch 데이터 및 하드필터 제외국 추출
#     cutoff = pd.Timestamp(year=target_yr, month=1, day=1)
#     sub_fitch = df_fitch_raw.loc[df_fitch_raw["rating_action_date"] < cutoff].copy()
#     latest_fitch = (
#         sub_fitch.sort_values("rating_action_date", kind="stable")
#         .drop_duplicates(subset="iso_a3", keep="last")
#         .set_index("iso_a3")["rating"]
#         .to_dict()
#     )
    
#     excluded_set = set(get_fitch_excluded_countries(prediction_year=target_yr, return_ratings=True))

#     for c in actual_list:
#         c_upper = str(c).strip().upper()
#         country_kr = name_map.get(c_upper, c_upper)
        
#         # 1) 당시 Fitch 문자 등급 확인
#         rating_str = latest_fitch.get(c_upper, "미평가(NR)")
        
#         # 2) 100점 만점 원점수 (미평가 시 D 등급 점수 10.0점 부여)
#         raw_score = FITCH_SCORE_MAP.get(rating_str, default_fitch_score)
        
#         # 3) 6지표 모델에 실제 반영된 0~1 min-max 정규화 점수
#         if c_upper in df_6_scored.index and "fitch_score" in df_6_scored.columns:
#             norm_score = df_6_scored.loc[c_upper, "fitch_score"]
#         else:
#             norm_score = raw_score / 100.0

#         # 4) 하드필터 통과 여부 및 판정 사유
#         is_excluded = c_upper in excluded_set
#         if is_excluded:
#             filter_status = "제외 (B- 미만/미평가)"
#         else:
#             filter_status = "통과"

#         # 5) 신용 구간 분류
#         if rating_str in investment_grades:
#             grade_group = "투자적격 (BBB- 이상)"
#         elif rating_str in speculative_grades:
#             grade_group = "투기등급 (BB+ ~ B-)"
#         elif rating_str == "미평가(NR)":
#             grade_group = "미평가 (NR)"
#         else:
#             grade_group = "초고위험/부도 (CCC 이하)"

#         fitch_tx_records.append({
#             "순번": seq_no,
#             "기업명": comp,
#             "계약연도": target_yr,
#             "국가코드": c_upper,
#             "국가명": country_kr,
#             "Fitch 등급": rating_str,
#             "원점수(100점)": f"{raw_score:5.1f}",
#             "정규화 점수": f"{norm_score:6.4f}",
#             "등급 구간": grade_group,
#             "하드필터": filter_status,
#         })
#         seq_no += 1

# df_fitch_tx = pd.DataFrame(fitch_tx_records)

# # -------------------------------------------------------------
# # [9-1] 38개 실제 거래 건별 신용등급 및 평가 점수 전체 명세 출력
# # -------------------------------------------------------------
# print("\n[9-1. 실제 방산 거래 38건 대상 Fitch 신용등급 및 산정 점수 상세 내역]")
# pd.set_option("display.max_rows", 100)
# pd.set_option("display.max_columns", 15)
# pd.set_option("display.width", 1000)
# print(df_fitch_tx.to_string(index=False))
# print("-" * 105)

# # -------------------------------------------------------------
# # [9-2] 실제 체결 국가들의 신용등급별 분포 (빈도수 및 점수)
# # -------------------------------------------------------------
# rating_dist = (
#     df_fitch_tx.groupby("Fitch 등급")
#     .agg(
#         거래건수=("순번", "count"),
#         배당_원점수=("원점수(100점)", "first"),
#         평균_정규화점수=("정규화 점수", lambda s: f"{s.astype(float).mean():.4f}"),
#         해당국가_예시=("국가코드", lambda s: ", ".join(sorted(set(s))[:5]))
#     )
#     .reset_index()
# )
# rating_dist["비율(%)"] = (rating_dist["거래건수"] / len(df_fitch_tx) * 100).round(1)
# rating_dist = rating_dist.sort_values(by="거래건수", ascending=False, kind="stable")

# print("\n[9-2. 38개 거래 성사 국가들의 Fitch 신용등급별 분포 현황]")
# print(rating_dist[["Fitch 등급", "거래건수", "비율(%)", "배당_원점수", "평균_정규화점수", "해당국가_예시"]].to_string(index=False))
# print("-" * 105)

# # -------------------------------------------------------------
# # [9-3] 등급 대분류 및 하드필터 제외 현황 요약 통계
# # -------------------------------------------------------------
# group_dist = (
#     df_fitch_tx.groupby("등급 구간")
#     .agg(
#         거래건수=("순번", "count"),
#         하드필터_제외건수=("하드필터", lambda s: (s.str.startswith("제외")).sum()),
#         평균_원점수=("원점수(100점)", lambda s: f"{s.astype(float).mean():.2f}"),
#         평균_정규화점수=("정규화 점수", lambda s: f"{s.astype(float).mean():.4f}")
#     )
#     .reset_index()
# )
# group_dist["비율(%)"] = (group_dist["거래건수"] / len(df_fitch_tx) * 100).round(1)

# print("\n[9-3. 신용등급 구간별 거래 건수 및 하드필터 제외 현황]")
# print(group_dist[["등급 구간", "거래건수", "비율(%)", "하드필터_제외건수", "평균_원점수", "평균_정규화점수"]].to_string(index=False))
# print("-" * 105)

# # -------------------------------------------------------------
# # [9-4] 기업별 실제 거래 국가의 신용등급 특성 요약
# # -------------------------------------------------------------
# comp_fitch_summary = (
#     df_fitch_tx.groupby("기업명")
#     .agg(
#         총거래건수=("순번", "count"),
#         투자적격건수=("등급 구간", lambda s: (s.str.startswith("투자적격")).sum()),
#         투기_미평가건수=("등급 구간", lambda s: (~s.str.startswith("투자적격")).sum()),
#         하드필터_제외건수=("하드필터", lambda s: (s.str.startswith("제외")).sum()),
#         평균_원점수=("원점수(100점)", lambda s: f"{s.astype(float).mean():.2f}"),
#         체결국_목록=("국가코드", lambda s: ", ".join(s))
#     )
#     .reset_index()
# )
# comp_fitch_summary["적격비율(%)"] = (comp_fitch_summary["투자적격건수"] / comp_fitch_summary["총거래건수"] * 100).round(1)

# print("\n[9-4. 방산기업별 체결 국가들의 신용등급 평가 요약]")
# print(comp_fitch_summary[["기업명", "총거래건수", "투자적격건수", "투기_미평가건수", "적격비율(%)", "하드필터_제외건수", "평균_원점수", "체결국_목록"]].to_string(index=False))
# print("=" * 105)