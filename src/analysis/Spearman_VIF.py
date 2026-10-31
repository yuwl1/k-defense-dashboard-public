# %% [1] 라이브러리 및 데이터 불러오기

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
from matplotlib import font_manager
from IPython.display import display
from statsmodels.stats.outliers_influence import variance_inflation_factor


# ============================================================
# 한글 폰트 설정 (Windows)
# ============================================================

font_path = Path(r"C:\Windows\Fonts\malgun.ttf")

if not font_path.exists():
    raise FileNotFoundError(f"한글 폰트를 찾을 수 없습니다: {font_path}")

font_manager.fontManager.addfont(str(font_path))

font_name = font_manager.FontProperties(
    fname=str(font_path)
).get_name()

plt.rcParams["font.family"] = font_name
plt.rcParams["axes.unicode_minus"] = False

print(f"적용된 폰트: {font_name}")


# ============================================================
# 데이터 불러오기
# ============================================================

FILE_PATH = "../../data/processed/final_score.csv"

START_YEAR = 2021
END_YEAR = 2025

df = pd.read_csv(FILE_PATH, encoding="utf-8-sig")

print(f"원본 데이터: {df.shape}")
print(f"국가 수: {df['iso_a3'].nunique()}")
print(f"분석 기간: {START_YEAR}~{END_YEAR}")


# %% [2] 국가별 5개년 집계

period = df[
    df["year"].between(START_YEAR, END_YEAR)
].copy()

country_sum = period.groupby("iso_a3", as_index=False).agg(
    defense_usd=(
        "military_expenditure_usd",
        lambda s: s.sum(min_count=5)
    ),
    defense_gdp_pct=(
        "military_expenditure_gdp_pct",
        lambda s: s.mean() if s.count() == 5 else np.nan
    ),
    import_tiv=(
        "tiv_total_1y",
        lambda s: s.sum(min_count=5)
    ),
    korea_tiv=(
        "tiv_korea",
        lambda s: s.sum(min_count=5)
    )
)

last_year = df[df["year"] == END_YEAR][
    ["iso_a3", "hhi_5y", "gpi_score_5y", "fitch_score"]
].rename(columns={
    "hhi_5y": "HHI",
    "gpi_score_5y": "GPI",
    "fitch_score": "Fitch"
})

country = country_sum.merge(
    last_year,
    on="iso_a3",
    validate="one_to_one"
)

cols = [
    "HHI",
    "defense_usd",
    "defense_gdp_pct",
    "GPI",
    "import_tiv",
    "korea_tiv",
    "Fitch"
]


# ============================================================
# 출력용 한국어 지표명
# ============================================================

korean_labels = {
    "HHI": "공급국 집중도(HHI)",
    "defense_usd": "국방비 지출액",
    "defense_gdp_pct": "GDP 대비 국방비 비중",
    "GPI": "평화지수(GPI)",
    "import_tiv": "전체 수입 TIV",
    "korea_tiv": "한국 TIV",
    "Fitch": "국가 신용등급(Fitch)"
}

print(f"집계 국가: {len(country)}개국")

display(
    country[["iso_a3"] + cols]
    .rename(columns=korean_labels)
    .head(10)
)

print("=== 지표별 결측 수 ===")

display(
    country[cols]
    .isna()
    .sum()
    .rename(index=korean_labels)
    .to_frame("결측 수")
)


# %% [3] Spearman 상관계수

# 지표 쌍별 결측 제외(Pairwise deletion)
corr = country[cols].corr(method="spearman")

print("=== Spearman 상관계수 행렬 ===")

display(
    corr.rename(
        index=korean_labels,
        columns=korean_labels
    ).round(3)
)


# %% [4] Spearman 지표 쌍별 분석 국가 수(N)

# 값이 존재하면 1, 결측이면 0
valid = country[cols].notna().astype(int)

# 지표 쌍별로 두 지표 모두 값이 존재하는 국가 수 계산
n_matrix = valid.T @ valid

print("=== Spearman 지표 쌍별 분석 국가 수(N) ===")

display(
    n_matrix.rename(
        index=korean_labels,
        columns=korean_labels
    )
)


# %% [5] 21개 지표 쌍 상관계수 및 국가 수

results = []

for i, a in enumerate(cols):
    for b in cols[i + 1:]:

        results.append({
            "지표1": a,
            "지표2": b,
            "N": int(n_matrix.loc[a, b]),
            "Spearman rho": corr.loc[a, b]
        })

result_df = pd.DataFrame(results)

# 상관계수 절댓값이 큰 순서로 정렬
result_df = result_df.sort_values(
    "Spearman rho",
    key=lambda x: x.abs(),
    ascending=False
).reset_index(drop=True)

print("=== 21개 지표 쌍 상관분석 ===")

display(
    result_df.replace({
        "지표1": korean_labels,
        "지표2": korean_labels
    }).style.format({
        "Spearman rho": "{:.3f}"
    })
)


# %% [6] Spearman 상관 히트맵

fig, ax = plt.subplots(figsize=(11, 8))

im = ax.imshow(
    corr,
    cmap="coolwarm",
    vmin=-1,
    vmax=1
)

ax.set_xticks(range(len(cols)))
ax.set_yticks(range(len(cols)))

labels = [korean_labels[c] for c in cols]

ax.set_xticklabels(
    labels,
    rotation=45,
    ha="right"
)

ax.set_yticklabels(labels)

for i in range(len(cols)):
    for j in range(len(cols)):

        value = corr.iloc[i, j]

        ax.text(
            j, i,
            f"{value:.2f}\n(N={n_matrix.iloc[i, j]})",
            ha="center",
            va="center",
            color="white" if abs(value) >= 0.65 else "black"
        )

fig.colorbar(
    im,
    ax=ax,
    label="Spearman 상관계수"
)

ax.set_title(
    f"Spearman 상관관계 히트맵 ({START_YEAR}~{END_YEAR})",
    fontsize=14,
    pad=15
)

plt.tight_layout()
plt.show()


# %% [7] VIF 다중공선성 분석

# 7개 지표 모두 존재하는 국가만 사용
vif_data = country[cols].dropna().copy()

# 표준화: 수치 안정성 확보
vif_scaled = (
    vif_data - vif_data.mean()
) / vif_data.std(ddof=0)

vif_result = pd.DataFrame({
    "지표": cols,
    "VIF": [
        variance_inflation_factor(
            vif_scaled.values, i
        )
        for i in range(len(cols))
    ]
})

vif_result["판정"] = np.select(
    [
        vif_result["VIF"] >= 10,
        vif_result["VIF"] >= 5
    ],
    [
        "높음",
        "주의"
    ],
    default="낮음"
)

vif_result = vif_result.sort_values(
    "VIF",
    ascending=False
)

print("=== VIF 다중공선성 분석 ===")
print(f"VIF 분석 국가: {len(vif_data)}개국")

display(
    vif_result.replace({
        "지표": korean_labels
    }).round(3)
)
# %%
