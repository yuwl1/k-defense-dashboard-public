
# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from IPython.display import display
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests


# ============================================================
# 1. 원본 데이터 불러오기
# ============================================================

DATA_PATH = "../../data/processed/final_score.csv"

df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

print("=== 원본 데이터 확인 ===")
print(f"전체 행 수: {len(df)}")
print(f"국가 수: {df['iso_a3'].nunique()}")
print(f"연도: {df['year'].min()}~{df['year'].max()}")

display(df.head())


# %%
# ============================================================
# 2. 2021~2025년 국가별 데이터 생성
# ============================================================

df_5y = df[df["year"].between(2021, 2025)].copy()

# 2025년 기준 최근 5년 HHI, GPI 사용
latest = (
    df_5y[df_5y["year"] == 2025]
    [
        [
            "iso_a3",
            "hhi_5y",
            "gpi_score_5y",
            "import_from_south_korea"
        ]
    ]
    .set_index("iso_a3")
)

# GDP 대비 국방비 비중은 5년 평균
gdp_avg = (
    df_5y.groupby("iso_a3")[
        "military_expenditure_gdp_pct"
    ]
    .mean()
    .rename("gdp_pct_5y_avg")
)

country = latest.join(gdp_avg).reset_index()

# 98개국 확인
assert len(country) == 98

print("=== 분석 대상 확인 ===")
print(f"전체 국가: {len(country)}개국")

group_counts = (
    country["import_from_south_korea"]
    .value_counts()
    .rename(index={1: "거래 경험 있음", 0: "거래 경험 없음"})
    .to_frame("국가 수")
)

display(group_counts)

print("\n=== 국가별 분석 데이터 ===")
display(country.head(10))


# %%
# ============================================================
# 3. Mann-Whitney U 검정
# ============================================================

metrics = {
    "HHI": "hhi_5y",
    "GDP 대비 국방비 비중": "gdp_pct_5y_avg",
    "GPI": "gpi_score_5y"
}

results = []
plot_data = {}
missing_results = []

for name, col in metrics.items():

    # 결측 국가 확인
    missing = country.loc[
        country[col].isna(), "iso_a3"
    ].tolist()

    missing_results.append({
        "지표": name,
        "결측 국가 수": len(missing),
        "결측 국가": ", ".join(missing) if missing else "없음"
    })

    # 해당 지표의 결측치만 제거
    valid = country.dropna(subset=[col])

    # 한국 거래 경험 있음
    yes = valid.loc[
        valid["import_from_south_korea"] == 1,
        col
    ].to_numpy(dtype=float)

    # 한국 거래 경험 없음
    no = valid.loc[
        valid["import_from_south_korea"] == 0,
        col
    ].to_numpy(dtype=float)

    # Mann-Whitney U 양측검정
    u, p = mannwhitneyu(
        yes,
        no,
        alternative="two-sided",
        method="asymptotic"
    )

    # Cliff's delta 효과크기
    cliff_delta = 2 * u / (len(yes) * len(no)) - 1

    results.append({
        "지표": name,
        "거래 있음 N": len(yes),
        "거래 없음 N": len(no),
        "거래 있음 중앙값": np.median(yes),
        "거래 없음 중앙값": np.median(no),
        "U통계량": u,
        "p값": p,
        "Cliff's delta": cliff_delta
    })

    plot_data[name] = (yes, no)

result_df = pd.DataFrame(results)

# BH 다중비교 보정
result_df["BH 보정 p값"] = multipletests(
    result_df["p값"],
    method="fdr_bh"
)[1]

result_df["판단"] = np.where(
    result_df["BH 보정 p값"] < 0.05,
    "유의함",
    "유의하지 않음"
)


# %%
# ============================================================
# 4. 최종 검정 결과 출력
# ============================================================

print("=== Mann-Whitney U 검정 결과 ===")

display(result_df.round(4))

print("\n=== 지표별 결측 국가 확인 ===")

missing_df = pd.DataFrame(missing_results)
display(missing_df)



# %%
# ============================================================
# 5. 효과크기 및 결과 해석 출력
# ============================================================

for _, row in result_df.iterrows():

    print(f"\n[{row['지표']}]")
    print(f"거래 경험 있음: {row['거래 있음 N']}개국")
    print(f"거래 경험 없음: {row['거래 없음 N']}개국")

    print(
        f"중앙값: {row['거래 있음 중앙값']:.4f}"
        f" vs {row['거래 없음 중앙값']:.4f}"
    )

    print(f"p값: {row['p값']:.4f}")
    print(f"BH 보정 p값: {row['BH 보정 p값']:.4f}")

    cliff_delta = row["Cliff's delta"]
    print(f"Cliff's delta: {cliff_delta:.4f}")

    print(f"판단: {row['판단']}")


# %%
# ============================================================
# 6. 지표별 Boxplot 시각화
# ============================================================

english_names = {
    "HHI": "HHI",
    "GDP 대비 국방비 비중": "Military Expenditure (% GDP)",
    "GPI": "GPI"
}

for name, (yes, no) in plot_data.items():

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.boxplot(
        [yes, no],
        showmeans=True,
        showfliers=True
    )

    ax.set_xticks(
        [1, 2],
        [
            f"Trade: Yes (n={len(yes)})",
            f"Trade: No (n={len(no)})"
        ]
    )

    row = result_df[result_df["지표"] == name].iloc[0]

    ax.set_title(
        f"{english_names[name]}\n"
        f"p={row['p값']:.4f}, "
        f"BH p={row['BH 보정 p값']:.4f}"
    )

    ax.set_ylabel(english_names[name])
    ax.grid(axis="y", alpha=0.2)

    plt.tight_layout()
    plt.show()
    plt.close(fig)

# %%
