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


def gii_log_transform(s: pd.Series, f: float = 10.0) -> pd.Series:
    """
    GII 로그변환: ln(((max*f - 1)*(x-min))/(max-min) + 1).
    최댓값이 매우 작아 f * max <= 1.0이 되는 경우,
    순위 역전(음수 스케일링)을 방지하기 위해 f를 자동 보정합니다.
    """
    s_min, s_max = s.min(), s.max()
    if pd.isna(s_min) or pd.isna(s_max) or s_max == s_min:
        return pd.Series(0.0, index=s.index)
    
    # f * s_max가 1보다 작거나 같으면 로그 값이 음수가 되므로 보정
    # effective_f = max(f, 1e3 / s_max) if s_max > 0 else f
    effective_f = f
    scaled = ((effective_f * s_max - 1.0) * (s - s_min)) / (s_max - s_min)
    return np.log(scaled + 1.0)


def compute_critic_score(df_indicators: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """주어진 지표 데이터프레임으로 CRITIC 가중치(w) 및 최종 점수/순위 산출."""
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
    res_df = res_df.sort_values("final_score", ascending=False, kind="stable")
    return res_df, w


# ==========================================
# 1. 10대 무기 분류체계 설정 및 데이터 로드
# ==========================================
WEAPON_CONFIG = {
    "방공 시스템 (Air Defence)": "air_defence_systems_category_score",
    "항공기 및 무인기 (Aircraft & UAVs)": "aircraft_uavs_category_score",
    "장갑차량 (Armoured Vehicles)": "armoured_vehicles_category_score",
    "포병 및 화포 (Artillery)": "artillery_category_score",
    "엔진 (Engines)": "engines_category_score",
    "미사일 및 유도무기 (Missiles)": "missiles_guided_weapons_category_score",
    "해군 무기 (Naval Weapons)": "naval_weapons_category_score",
    "기타 시스템 및 부품 (Other Systems)": "other_systems_components_category_score",
    "센서, ISR 및 위성 (Sensors & ISR)": "sensors_isr_satellites_category_score",
    "함정 (Ships)": "ships_category_score",
}

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / "processed"
data_path = DATA_DIR / "final_score.csv"

if not data_path.exists():
    data_path = Path("final_score.csv")

df = pd.read_csv(data_path)
df["year"] = pd.to_numeric(df["year"], errors="raise").astype(int)

iso_index = df["iso_a3"].drop_duplicates().reset_index(drop=True)

START_YEAR = 2021
END_YEAR = 2025
TARGET_YEAR = 2026
TOP_N = 10

skew_and_kurt = []

# ==========================================
# 2. 2021~2025 데이터 기반 2026 예측 실행
# ==========================================
def run_2026_weapon_prediction() -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
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
        gii_log_transform(df_kor["tiv_korea_sum"], f=10.0)
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
    # (6) 6번 지표: Fitch 신용등급 점수 (0~100)
    # ------------------------------------------
    fitch_series = (
        df[df["year"] == END_YEAR]
        .set_index("iso_a3")["fitch_score"]
        .reindex(iso_index)
        .fillna(0.0)  # 미평가 국가는 0점 처리
    )
    fitch_score_norm = min_max_normalize(fitch_series) * 100

    # ------------------------------------------
    # 10대 무기 분류체계별 (5)번 지표 산출 및 CRITIC 결합
    # ------------------------------------------
    weapon_results = {}
    weight_records = []
    

    print("\n" + "=" * 110)
    print(f"=== [{START_YEAR}~{END_YEAR}년 데이터 기반 -> {TARGET_YEAR}년 10대 무기분류체계별 수출 유망국 Top {TOP_N} 및 CRITIC 가중치] ===")
    print("=" * 110)

    for weapon_name, col_name in WEAPON_CONFIG.items():
        # (5) 5번 지표: 무기 분류체계별 소요 점수 (5개년 평균 -> GII 로그변환 -> 정규화)
        df_weapon = (
            df_period.assign(score_filled=df_period[col_name].fillna(0.0))
            .groupby("iso_a3")["score_filled"]
            .mean()
            .reindex(iso_index)
            .fillna(0.0)
        )
        weapon_category_score = (
            min_max_normalize(gii_log_transform(df_weapon, f=1e3)) * 100
        )
        
        a, b = gii_log_transform(df_weapon, f=1e3).skew(), gii_log_transform(df_weapon, f=1e3).kurt()
        skew_and_kurt.append((a, b))

        # 6개 지표 결합
        df_6ind = pd.DataFrame(
            {
                "hhi_5y": hhi_5y_norm,
                "final_mil_score": final_mil_score,
                "gpi_score_5y": gpi_norm,
                "transaction_with_korea": transaction_with_korea,
                "weapon_category_score": weapon_category_score,
                "fitch_score": fitch_score_norm,
            },
            index=iso_index,
        )
        df_6ind.index.name = "iso_a3"

        df_scored, w = compute_critic_score(df_6ind)
        weapon_results[weapon_name] = df_scored

        w_row = {"무기 분류체계": weapon_name}
        w_row.update({col: f"{val:.4f} ({val * 100:.2f}%)" for col, val in w.items()})
        weight_records.append(w_row)

        print(f"\n▶ [{weapon_name}] {TARGET_YEAR}년 추천 결과")
        print("  [6개 지표 CRITIC 가중치 (w)]")
        print("  " + " | ".join([f"{col}: {val:.4f} ({val * 100:.2f}%)" for col, val in w.items()]))

        print(f"\n  [{TARGET_YEAR}년 수출 유망 국가 Top {TOP_N}]")
        display_cols = [
            "rank",
            "final_score",
            "hhi_5y",
            "final_mil_score",
            "gpi_score_5y",
            "transaction_with_korea",
            "weapon_category_score",
            "fitch_score",
        ]
        top10_df = df_scored.head(TOP_N)[display_cols].reset_index()
        print(top10_df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
        print("-" * 110)

    df_weights_summary = pd.DataFrame(weight_records)
    print("\n=== [10대 무기 분류체계별 6개 지표 CRITIC 가중치(w) 종합 요약] ===")
    print(df_weights_summary.to_string(index=False))
    print("=" * 110)

    return weapon_results, df_weights_summary



if __name__ == "__main__":
    results_2026, weights_2026 = run_2026_weapon_prediction()
    # print(skew_and_kurt)