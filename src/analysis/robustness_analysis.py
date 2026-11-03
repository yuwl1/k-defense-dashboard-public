# %%
# ============================================================
# 1. 라이브러리 및 분석 설정
# ============================================================
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
from IPython.display import display

ROOT_DIR = Path(r"C:\Projects\k-defense-dashboard-public")
START_YEAR = 2021
END_YEAR = 2025
N_SIMULATIONS = 1000
RANDOM_SEED = 20261102
# 기존 가중치 대비 상대 변화율입니다. %p가 아닙니다.
# 예: 기본 20% → ±5%는 19~21%, ±10%는 18~22%
WEIGHT_CHANGE_RATES = [0.05, 0.10, 0.20, 0.30]

# 5·10·20·30%는 작은 변경부터 큰 변경까지 살펴보기 위한 실험 조건입니다.
# 통계적으로 보장된 기준이나 신뢰구간이 아닙니다.
# 전체 범위는 기존값과 무관하게 각 가중치 0~100%, 합계 100%인 조합 공간입니다.

SCENARIO_LABELS = {
    "relative_5pct": "기존값 대비 ±5%",
    "relative_10pct": "기존값 대비 ±10%",
    "relative_20pct": "기존값 대비 ±20%",
    "relative_30pct": "기존값 대비 ±30%",
    "global_dirichlet_1": "전체 범위"
}
TOP_N_LIST = [5, 10, 20]

pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 160)


# %%
# ============================================================
# 2. 공통 계산 함수
# ============================================================

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def draw_bounded_weights(baseline_weights, change_rate, count, rng):
    """각 지표의 상대 변화율과 가중치 합계 1을 동시에 만족하는 조합 추출."""
    baseline_weights = np.asarray(baseline_weights, dtype=float)
    lower = baseline_weights * (1 - change_rate)
    upper = baseline_weights * (1 + change_rate)

    # 5개 가중치를 범위 내에서 균등 추출하고 나머지 1개는 합계가 1이 되도록 결정.
    # 마지막 가중치도 범위 내인 조합만 채택합니다. 사후 재정규화는 하지 않습니다.
    # 이 방식은 범위와 합계 제약의 교집합에서 균등하게 추출합니다.
    balance_index = int(np.argmax(baseline_weights))
    free_indices = np.delete(np.arange(len(baseline_weights)), balance_index)
    accepted_batches = []
    accepted_count = 0

    while accepted_count < count:
        batch_size = max(256, 4 * (count - accepted_count))
        free_weights = rng.uniform(
            lower[free_indices],
            upper[free_indices],
            size=(batch_size, len(free_indices))
        )
        balance_weights = 1.0 - free_weights.sum(axis=1)
        valid = (
            (balance_weights >= lower[balance_index])
            & (balance_weights <= upper[balance_index])
        )

        batch = np.empty((int(valid.sum()), len(baseline_weights)))
        batch[:, free_indices] = free_weights[valid]
        batch[:, balance_index] = balance_weights[valid]
        accepted_batches.append(batch)
        accepted_count += len(batch)

    draws = np.concatenate(accepted_batches)[:count]
    assert np.allclose(draws.sum(axis=1), 1.0, atol=1e-12)
    assert np.all(draws >= lower - 1e-12)
    assert np.all(draws <= upper + 1e-12)
    return draws


def ranks(values):
    # Spearman 계산에 사용할 순위. 동점은 평균순위로 처리합니다.
    return pd.Series(values).rank(ascending=False, method="average").to_numpy()


def correlation(category_std, transaction_std):
    if np.std(category_std) == 0 or np.std(transaction_std) == 0:
        return float("nan")
    return float(np.corrcoef(category_std, transaction_std)[0, 1])


def order(values, countries):
    # 정확히 N개를 선택. 동점은 ISO 코드 오름차순으로 결정.
    return np.lexsort((np.asarray(countries), -np.asarray(values)))


def compare(baseline_scores, candidate, countries):
    baseline_ranks, candidate_ranks = ranks(baseline_scores), ranks(candidate)
    baseline_order, candidate_order = order(baseline_scores, countries), order(candidate, countries)
    result = {"spearman_all": correlation(baseline_ranks, candidate_ranks),
              "spearman_baseline_top10": correlation(baseline_ranks[baseline_order[:10]], candidate_ranks[baseline_order[:10]])}
    for n in TOP_N_LIST:
        result[f"overlap_top{n}"] = len(set(baseline_order[:n]) & set(candidate_order[:n])) / n
    return result


def percentile(strength_vector):
    if strength_vector.nunique() <= 1:
        return strength_vector * 0
    # 동점 평균순위, 최솟값=0 최댓값=1로 재조정.
    r = strength_vector.rank(method="average")
    return (r - r.min()) / (r.max() - r.min())




# %%
# ============================================================
# 3. 데이터 불러오기 및 기존 점수 확인
# ============================================================

model_path = ROOT_DIR / "src/dashboard_score/dashboard_score.py"
strength_path = ROOT_DIR / "components/company_weapons.py"
model = load_module(model_path, "robustness_dashboard")
definitions = load_module(strength_path, "robustness_strength")
data_path = ROOT_DIR / "data/processed/final_score.csv"
df = model.load_final_score(data_path)
assert not df.duplicated(["iso_a3", "year"]).any()
baseline, weights, weight_summary = model.run_2026_prediction_detail(df)
groups = definitions.WEAPON_GROUPS
share_cols = [g + "_category_score" for g in groups]
period = df.loc[df.year.between(START_YEAR, END_YEAR)].copy()
# 10개 분류가 모두 결측인 무거래 연도만 0으로 처리. 부분 결측은 중단.
assert period.groupby("iso_a3").year.nunique().eq(END_YEAR - START_YEAR + 1).all()
assert ((period[share_cols].isna().sum(axis=1) == 0) |
        (period[share_cols].isna().sum(axis=1) == len(groups))).all()
shares = period[share_cols].fillna(0).to_numpy(float)
assert np.isfinite(shares).all() and (shares >= 0).all()
totals = shares.sum(axis=1)
assert np.all(np.isclose(totals, 0) | np.isclose(totals, 1))
names_df = pd.read_csv(ROOT_DIR / "data/mapping/country_map_master.csv")
names = names_df.set_index("iso_a3").country_name_ko.to_dict()

print("=== 분석 대상 확인 ===")
print(f"국가 수: {df['iso_a3'].nunique()}개국")
print(f"분석 기간: {START_YEAR}~{END_YEAR}")
print(f"기업 수: {len(baseline)}개")
print("\n=== 기존 기업별 CRITIC 가중치 ===")
display(weight_summary)


# %%
# ============================================================
# 4. 무작위 가중치 생성 및 민감도 실험
# ============================================================

# ±5%, ±10%, ±20%, ±30%: 기존값의 0.95~1.05배 / 0.90~1.10배 /
# 0.80~1.20배 / 0.70~1.30배로 제한합니다. %p가 아닌 상대 변화율입니다.
# 6개 가중치의 합은 매번 100%이며, 합계 조정 후 범위를 벗어나지 않습니다.
# 전체 범위: 각 가중치 0~100%, 합계 100%인 조합 공간에서 균등 추출.
# Dirichlet(1,...,1)을 사용하므로 정확한 0%·100%는 확률 0의 경계입니다.
# 6개 기업 × 5개 시나리오 × 1,000회 = 총 30,000회.
# 지표 점수는 고정하고 최종 6개 지표 가중치만 바꿉니다.

weight_bound_records = []

# 예시의 기본값은 20%입니다. 실제 실험은 각 기업·지표의 기본 가중치를 사용합니다.
weight_condition_table = pd.DataFrame([
    {
        "실험": f"기존값 대비 ±{rate:.0%}",
        "하한 계산": f"기존값 × {1-rate:.2f}",
        "상한 계산": f"기존값 × {1+rate:.2f}",
        "기본 20%일 때": f"{0.2*(1-rate):.0%}~{0.2*(1+rate):.0%}"
    }
    for rate in WEIGHT_CHANGE_RATES
] + [{
    "실험": "전체 범위",
    "하한 계산": "0%",
    "상한 계산": "100%",
    "기본 20%일 때": "기존값과 무관; 6개 합계 100%"
}])
display(weight_condition_table)

weight_records = []
inclusion_result = []
weight_summary_records = []
base_rows = []

rng = np.random.default_rng(RANDOM_SEED)
global_draws = rng.dirichlet(
    np.ones(len(model.SCORE_COLUMNS)),
    N_SIMULATIONS
)

for company, company_config in model.COMPANY_CONFIG.items():
    baseline_table = baseline[company].sort_index()
    countries = baseline_table.index.to_numpy()
    assert len(countries) >= 20
    assert np.isfinite(baseline_table[model.SCORE_COLUMNS].to_numpy()).all()
    baseline_weights = weights[company].reindex(model.SCORE_COLUMNS).to_numpy()
    assert np.isfinite(baseline_weights).all() and (baseline_weights > 0).all() and np.isclose(baseline_weights.sum(), 1)
    indicator_values = baseline_table[model.SCORE_COLUMNS].to_numpy()
    baseline_scores = baseline_table.final_score.to_numpy()
    assert np.allclose(indicator_values @ baseline_weights, baseline_scores, atol=1e-10)
    for iso, row in baseline_table.iterrows():
        base_rows.append({"company": company, "iso_a3": iso, "country": names.get(iso, iso), **row.to_dict()})
    base_top = set(order(baseline_scores, countries)[:10])
    # 범위 제한 실험 네 가지와 전체 범위 실험을 구분
    scenarios = {}

    for change_rate in WEIGHT_CHANGE_RATES:
        scenario = f"relative_{change_rate * 100:.0f}pct"
        scenarios[scenario] = draw_bounded_weights(
            baseline_weights, change_rate, N_SIMULATIONS, rng
        )

        # 기본값·설정 범위·실제로 뽑힌 최솟값/최댓값을 확인하는 표
        for index, indicator in enumerate(model.SCORE_COLUMNS):
            weight_bound_records.append({
                "기업": company,
                "실험": SCENARIO_LABELS[scenario],
                "지표": indicator,
                "기본 가중치": baseline_weights[index],
                "허용 최솟값": baseline_weights[index] * (1 - change_rate),
                "허용 최댓값": baseline_weights[index] * (1 + change_rate),
                "추출 최솟값": scenarios[scenario][:, index].min(),
                "추출 최댓값": scenarios[scenario][:, index].max()
            })

    # 기업 간 비교를 위해 전역 실험에서는 동일한 추출 가중치를 사용
    scenarios["global_dirichlet_1"] = global_draws

    for scenario, draws in scenarios.items():
        counts = np.zeros(len(countries), dtype=int)
        scenario_rows = []

        for i, draw in enumerate(draws, 1):
            # 최종 점수 = 6개 지표 점수 × 이번 회차 가중치
            scores = indicator_values @ draw

            row = {
                "company": company,
                "scenario": scenario,
                "trial": i,
                **compare(baseline_scores, scores, countries),
                **dict(zip(model.SCORE_COLUMNS, map(float, draw)))
            }

            weight_records.append(row)
            scenario_rows.append(row)
            counts[order(scores, countries)[:10]] += 1

        # 국가별로 1,000회 중 Top 10에 포함된 비율 계산
        for j, iso in enumerate(countries):
            inclusion_result.append({
                "company": company,
                "scenario": scenario,
                "iso_a3": iso,
                "country": names.get(iso, iso),
                "baseline_top10": j in base_top,
                "top10_frequency": counts[j] / N_SIMULATIONS
            })

        trial_df = pd.DataFrame(scenario_rows)
        summary = {"company": company, "scenario": scenario}

        metrics = [
            "spearman_all",
            "spearman_baseline_top10",
            "overlap_top5",
            "overlap_top10",
            "overlap_top20"
        ]

        for metric in metrics:
            statistics = {
                "mean": trial_df[metric].mean(),
                "median": trial_df[metric].median(),
                "p05": trial_df[metric].quantile(0.05),
                "p95": trial_df[metric].quantile(0.95),
                "min": trial_df[metric].min()
            }

            for label, value in statistics.items():
                summary[f"{metric}_{label}"] = value

        weight_summary_records.append(summary)  


weight_trials = pd.DataFrame(weight_records)
weight_summary_result = pd.DataFrame(weight_summary_records)
top10_inclusion = pd.DataFrame(inclusion_result)
weight_bounds = pd.DataFrame(weight_bound_records)

print("=== 지표별 가중치 설정 범위 및 추출 범위 ===")
display(
    weight_bounds.style.format({
        column: "{:.3%}" for column in [
            "기본 가중치", "허용 최솟값", "허용 최댓값", "추출 최솟값", "추출 최댓값"
        ]
    }).hide(axis="index")
)

print(f"가중치 실험 완료: {len(weight_trials):,}회")


# %%
# ============================================================
# 5. 가중치 민감도 결과 확인
# ============================================================

# 겹침 비율 = 기준 Top N과 실험 Top N의 교집합 / N
# 전체 국가 상관과 기준 Top 10 국가들 내부의 순위 상관을 따로 봅니다.
# 하위 5%는 실험 분포의 분위수이며 신뢰구간이 아닙니다.

summary_columns = {
    "company": "기업명",
    "spearman_all_mean": "전체 순위 상관 평균",
    "spearman_baseline_top10_mean": "기준 Top 10 내부 상관 평균",
    "overlap_top5_mean": "Top 5 유지율",
    "overlap_top10_mean": "Top 10 유지율",
    "overlap_top10_p05": "Top 10 유지율 하위 5%",
    "overlap_top20_mean": "Top 20 유지율"
}

for scenario, title in SCENARIO_LABELS.items():
    print(f"=== {title} ===")
    display(
        weight_summary_result.loc[
            weight_summary_result["scenario"] == scenario,
            list(summary_columns)
        ]
        .rename(columns=summary_columns)
        .round(4)
    )


# %%
# ============================================================
# 6. 6개 지표 전체의 min-max 및 백분위 및 L2 벡터 정규화
# ============================================================

# 비교 대상: HHI / 국방비 / GPI / 한국 방산 거래 / 기업 매칭도 / 신용도
# 원자료의 집계·로그변환·복합지표 내부 결합은 기존 대시보드와 동일하게 유지합니다.
# 바꾸는 곳은 6개 복합지표를 최종적으로 같은 눈금으로 맞추는 단계입니다.
# 모든 원자료 열에 로그변환 없이 정규화를 적용하는 실험은 아닙니다.
# 기본 가중치는 기존 대시보드 계산값으로 고정하며, 새 CRITIC 가중치를 만들지 않습니다.
# 6개 중 HHI만 낮을수록 유리합니다. 나머지 방향은 기존 대시보드 정의를 유지합니다.
# GPI는 이 프로젝트에서 평화위협 지표로 사용하여 값이 높을수록 높은 점수를 줍니다.

INDICATOR_LABELS = {
    "hhi_score": "공급국 집중도 HHI",
    "defense_expenditure_score": "국방비 종합",
    "gpi_score": "GPI",
    "korea_arms_trade_score": "한국 방산 거래",
    "company_trade_score": "기업 매칭도",
    "fitch_score": "신용도"
}

METHOD_LABELS = {
    "minmax_all6": "6개 지표 min-max",
    "percentile_all6": "6개 지표 백분위",
    "vector_l2_all6": "6개 지표 L2 벡터 정규화"
}


def combine_by_std(components):
    """기존 대시보드와 같은 표준편차 비중으로 복합지표 구성요소 결합."""
    components = pd.concat(components, axis=1)
    standard_deviations = components.std()

    if standard_deviations.sum() == 0:
        return pd.Series(0.0, index=components.index)

    internal_weights = standard_deviations / standard_deviations.sum()
    return components.dot(internal_weights)


def normalize_all_six(indicators, method):
    """각 지표 열을 98개국에 걸쳐 정규화. 국가 행의 6개 값을 나누는 것이 아님."""
    normalized = pd.DataFrame(index=indicators.index)

    for column in model.SCORE_COLUMNS:
        values = indicators[column]

        if method == "minmax":
            if column == "hhi_score":
                # HHI만 (최댓값 - 값) / (최댓값 - 최솟값)
                normalized[column] = model.max_min_normalize(values)
            else:
                normalized[column] = model.min_max_normalize(values)

        elif method == "percentile":
            # HHI는 낮은 원래 값이 높은 순위 점수를 받도록 한 번만 반전
            direction_adjusted = -values if column == "hhi_score" else values
            normalized[column] = percentile(direction_adjusted)

        elif method == "vector_l2":
            # HHI의 이론적 범위 0~1을 이용해 1-HHI로 유리한 방향을 먼저 맞춤.
            # 이 단계에서는 min-max를 먼저 적용하지 않습니다.
            if column == "hhi_score":
                assert values.between(0, 1).all()
                direction_adjusted = 1.0 - values
            else:
                direction_adjusted = values

            # 지표마다 모든 국가의 값 제곱합에 루트를 씌운 공통 분모를 구함.
            # 예: 한 지표에서 A국=3, B국=4라면 분모=sqrt(3²+4²)=5,
            # 변환값은 0.6, 0.8. 국가 간 비율 3:4는 그대로 유지됩니다.
            # 각 지표 열의 제곱합은 1이 되지만 최댓값이 반드시 1인 것은 아닙니다.
            denominator = np.sqrt(direction_adjusted.pow(2).sum())
            if denominator > 0:
                normalized[column] = direction_adjusted / denominator
            else:
                normalized[column] = 0.0

            expected_norm = 1.0 if denominator > 0 else 0.0
            assert np.isclose(normalized[column].pow(2).sum(), expected_norm)

        else:
            raise ValueError(f"지원하지 않는 정규화 방식: {method}")

    assert np.isfinite(normalized.to_numpy()).all()
    assert (normalized.to_numpy() >= -1e-12).all()
    assert (normalized.to_numpy() <= 1 + 1e-12).all()
    return normalized


# ------------------------------------------------------------
# 6-1. 최종 정규화 직전의 공통 복합지표 구성
# ------------------------------------------------------------

country_index = next(iter(baseline.values())).sort_index().index
latest = df[df["year"] == END_YEAR].set_index("iso_a3").reindex(country_index)

defense_data = period.groupby("iso_a3").agg(
    total_milex=("military_expenditure_usd", lambda values: values.sum(skipna=False)),
    avg_pct=("military_expenditure_gdp_pct", lambda values: values.mean(skipna=False)),
    avg_tiv=("tiv_total_1y", "mean")
).reindex(country_index).fillna(0.0)

positive_milex = defense_data.loc[defense_data["total_milex"] > 0, "total_milex"]
positive_pct = defense_data.loc[defense_data["avg_pct"] > 0, "avg_pct"]

milex_component = model.min_max_normalize(
    model.gii_log_transform(positive_milex, 1e-7)
).reindex(country_index).fillna(0.0)

pct_component = model.min_max_normalize(
    model.gii_log_transform(positive_pct, 1.0)
).reindex(country_index).fillna(0.0)

tiv_component = model.min_max_normalize(
    model.gii_log_transform(defense_data["avg_tiv"], 1e-2)
).reindex(country_index).fillna(0.0)

defense_composite = combine_by_std([milex_component, pct_component, tiv_component])

korea_data = period.groupby("iso_a3").agg(
    tiv_sum=("tiv_korea", "sum"),
    import_mean=("import_from_south_korea", "mean")
).reindex(country_index)

korea_tiv_component = model.min_max_normalize(
    model.gii_log_transform(korea_data["tiv_sum"], 10)
)
korea_composite = combine_by_std([korea_tiv_component, korea_data["import_mean"]])

common_indicators = pd.DataFrame({
    "hhi_score": latest["hhi_5y"].fillna(1.0),
    "defense_expenditure_score": defense_composite,
    "gpi_score": latest["gpi_score_5y"],
    "korea_arms_trade_score": korea_composite,
    "fitch_score": latest["fitch_score"].fillna(0.0)
}, index=country_index)

# ------------------------------------------------------------
# 6-2. 기업 매칭도 구성 후 6개 지표 전체에 동일한 비교 방식 적용
# ------------------------------------------------------------

normalization_records = []
normalization_score_records = []
normalization_weight_records = []
validation_records = []
raw_indicator_tables = {}
normalized_indicator_tables = {}

for company, company_config in model.COMPANY_CONFIG.items():
    baseline_table = baseline[company].reindex(country_index)
    baseline_values = baseline_table["final_score"].to_numpy()

    company_data = (
        period.assign(category_filled=period[company_config["score_columns"][0]].fillna(0))
        .groupby("iso_a3")
        .agg(
            category_mean=("category_filled", "mean"),
            history=(company_config["hist_column"], "max")
        )
        .reindex(country_index)
    )

    category_component = model.min_max_normalize(
        model.gii_log_transform(company_data["category_mean"], 10)
    ).fillna(0.0)
    transaction_component = 0.7 + 0.3 * company_data["history"]

    indicators = common_indicators.copy()
    indicators["company_trade_score"] = combine_by_std([
        category_component, transaction_component
    ])
    indicators = indicators[model.SCORE_COLUMNS]
    raw_indicator_tables[company] = indicators

    minmax_table = normalize_all_six(indicators, "minmax")
    percentile_table = normalize_all_six(indicators, "percentile")
    vector_table = normalize_all_six(indicators, "vector_l2")
    normalized_indicator_tables[(company, "minmax_all6")] = minmax_table
    normalized_indicator_tables[(company, "percentile_all6")] = percentile_table
    normalized_indicator_tables[(company, "vector_l2_all6")] = vector_table

    # min-max는 기존 방식 재현용 대조군이므로 기존 6개 점수와 같아야 합니다.
    reproduction_error = np.max(np.abs(
        minmax_table.to_numpy() * 100
        - baseline_table[model.SCORE_COLUMNS].to_numpy()
    ))
    assert reproduction_error < 1e-8

    # HHI가 작은 국가부터 보면, 변환 후 점수는 큰 값부터 나와야 합니다.
    hhi_order = indicators["hhi_score"].sort_values().index
    for normalized in [minmax_table, percentile_table, vector_table]:
        assert np.all(np.diff(normalized.loc[hhi_order, "hhi_score"]) <= 1e-12)

    validation_records.append({
        "기업": company,
        "기존 6개 점수 최대 재현 오차": reproduction_error,
        "HHI 낮을수록 높은 점수": True
    })

    for method in METHOD_LABELS:
        normalized = normalized_indicator_tables[(company, method)]

        # 기본 가중치는 정규화 3개 방식에서 완전히 동일하게 고정합니다.
        for policy in ["fixed_baseline"]:
            candidate_weights = weights[company].reindex(model.SCORE_COLUMNS)

            assert np.isfinite(candidate_weights).all()
            assert np.isclose(candidate_weights.sum(), 1)

            # 3개 방식 모두 같은 가중합을 사용합니다. 기준국 비교는 없습니다.
            # 표시를 위해 100을 곱하지만 방식 간 점수 크기 자체는 직접 비교하지 않음.
            scores = normalized.dot(candidate_weights).to_numpy() * 100

            assert np.isfinite(scores).all()
            if method == "minmax_all6":
                assert np.allclose(scores, baseline_values, atol=1e-8)

            normalization_records.append({
                "company": company,
                "method": method,
                "weight_policy": policy,
                **compare(baseline_values, scores, country_index),
                "final_score_mean": scores.mean()
            })

            normalization_weight_records.append({
                "company": company,
                "method": method,
                "weight_policy": policy,
                **candidate_weights.to_dict()
            })

            selection_rank = np.empty(len(country_index), dtype=int)
            selection_rank[order(scores, country_index)] = np.arange(1, len(country_index) + 1)

            for index, iso in enumerate(country_index):
                normalization_score_records.append({
                    "company": company,
                    "method": method,
                    "weight_policy": policy,
                    "iso_a3": iso,
                    "country": names.get(iso, iso),
                    "selection_rank": selection_rank[index],
                    "final_score": scores[index]
                })

normalization_comparison = pd.DataFrame(normalization_records)
normalization_scores = pd.DataFrame(normalization_score_records)
normalization_weights = pd.DataFrame(normalization_weight_records)
normalization_validation = pd.DataFrame(validation_records)

print("=== 6개 지표 전체 비교 계산 완료 ===")
display(normalization_validation)


# %%
# ============================================================
# 7. 방식별 계산 의미 및 6개 지표 비교 결과
# ============================================================

# 설명은 표로만 표시합니다. 결과에 대한 장문 해석은 Word 문서에 작성합니다.
method_guide = pd.DataFrame([
    {
        "방식": "min-max",
        "무엇을 계산하나": "각 지표의 가장 낮은 값은 0, 가장 높은 값은 1로 변환",
        "HHI 처리": "낮은 원래 값에 1, 높은 원래 값에 0",
        "최종 계산": "6개 변환 점수 × 가중치의 합",
        "해석 주의": "기존 방식과 같아야 하는 재현 대조군"
    },
    {
        "방식": "백분위",
        "무엇을 계산하나": "각 지표의 국가 간 순서로 0~1 점수 부여; 동점은 평균순위",
        "HHI 처리": "낮은 원래 값이 높은 순위 점수를 받음",
        "최종 계산": "6개 순위 점수 × 가중치의 합",
        "해석 주의": "원래 값 사이의 간격보다 순서를 반영"
    },
    {
        "방식": "L2 벡터 정규화",
        "무엇을 계산하나": "지표별로 98개 국가의 값 제곱합에 루트를 씌운 수로 각 값을 나눔",
        "HHI 처리": "1-HHI로 방향을 맞춘 뒤 동일한 L2 나눗셈 적용",
        "최종 계산": "6개 변환 점수 × 가중치의 합",
        "해석 주의": "국가 간 비율 유지; 지표 열마다 제곱합 1; 최댓값이 꼭 1은 아님"
    }
])
display(method_guide)

comparison_columns = {
    "company": "기업명",
    "method": "계산 방식",
    "spearman_all": "전체 순위 상관",
    "overlap_top5": "Top 5 유지율",
    "overlap_top10": "Top 10 유지율",
    "overlap_top20": "Top 20 유지율"
}

for policy, title in [
    ("fixed_baseline", "최종 가중치 고정")
]:
    print(f"=== {title} ===")
    display(
        normalization_comparison.loc[
            normalization_comparison["weight_policy"] == policy,
            list(comparison_columns)
        ]
        .replace({"method": METHOD_LABELS})
        .rename(columns=comparison_columns)
        .round(4)
    )


# %%
# ============================================================
# 8. HHI 방향 처리 및 6개 지표 변환값 직접 확인
# ============================================================

CHECK_COMPANY = "현대로템"
raw_indicators = raw_indicator_tables[CHECK_COMPANY]
minmax_indicators = normalized_indicator_tables[(CHECK_COMPANY, "minmax_all6")]
percentile_indicators = normalized_indicator_tables[(CHECK_COMPANY, "percentile_all6")]
vector_indicators = normalized_indicator_tables[(CHECK_COMPANY, "vector_l2_all6")]

hhi_check = pd.DataFrame({
    "국가": [names.get(iso, iso) for iso in country_index],
    "원래 HHI": raw_indicators["hhi_score"],
    "min-max HHI 점수": minmax_indicators["hhi_score"],
    "백분위 HHI 점수": percentile_indicators["hhi_score"],
    "L2 벡터 HHI 점수": vector_indicators["hhi_score"]
}).sort_values("원래 HHI")

# 낮은 HHI 5개국과 높은 HHI 5개국을 나란히 확인
print("=== HHI: 원래 값이 낮을수록 높은 점수 ===")
display(pd.concat([hhi_check.head(5), hhi_check.tail(5)]).round(4))

for label, indicator_table in [
    ("최종 정규화 직전", raw_indicators),
    ("6개 지표 min-max", minmax_indicators),
    ("6개 지표 백분위", percentile_indicators),
    ("6개 지표 L2 벡터", vector_indicators)
]:
    print(f"=== {CHECK_COMPANY}: {label} / 앞 10개국 ===")
    display(indicator_table.rename(columns=INDICATOR_LABELS).head(10).round(4))


# %%
# ============================================================
# 9. 6개 지표 계산 방식별 Top 10 진입 및 이탈 국가
# ============================================================

changes = []

for company in model.COMPANY_CONFIG:
    company_scores = normalization_scores[normalization_scores["company"] == company]
    original_top10 = company_scores.loc[
        (company_scores["method"] == "minmax_all6")
        & (company_scores["weight_policy"] == "fixed_baseline")
        & (company_scores["selection_rank"] <= 10)
    ].sort_values("selection_rank")
    original_codes = set(original_top10["iso_a3"])

    for method in METHOD_LABELS:
        alternative_top10 = company_scores.loc[
            (company_scores["method"] == method)
            & (company_scores["weight_policy"] == "fixed_baseline")
            & (company_scores["selection_rank"] <= 10)
        ].sort_values("selection_rank")
        alternative_codes = set(alternative_top10["iso_a3"])

        entering = alternative_top10.loc[
            ~alternative_top10["iso_a3"].isin(original_codes), "country"
        ].tolist()
        leaving = original_top10.loc[
            ~original_top10["iso_a3"].isin(alternative_codes), "country"
        ].tolist()

        changes.append({
            "기업": company,
            "방식": method,
            "진입": ", ".join(entering) or "없음",
            "이탈": ", ".join(leaving) or "없음"
        })

display(pd.DataFrame(changes).replace({"방식": METHOD_LABELS}))


# %%
# ============================================================
# 10. 선택 기업의 국가별 Top 10 포함 빈도
# ============================================================
COMPANY = "한화에어로스페이스"  # 다른 기업명으로 바꿔 실행하세요.
INCLUSION_SCENARIO = "relative_10pct"  # relative_5pct / relative_10pct / relative_20pct / relative_30pct / global_dirichlet_1
print(f"=== {COMPANY}: {SCENARIO_LABELS[INCLUSION_SCENARIO]} ===")
inclusion_result = top10_inclusion
display(inclusion_result[(inclusion_result.company == COMPANY) & (inclusion_result.scenario == INCLUSION_SCENARIO)]
        .sort_values("top10_frequency", ascending=False).head(20))

# %%
# ============================================================
# 11. 회차별 상세 결과 확인
# ============================================================
display(weight_trials.head(10))


# %%
# ============================================================
# 12. 문서용 핵심 표 ① 기업별 가중치 민감도 요약
# ============================================================


# 다섯 시나리오의 Top 10 평균 유지율을 나란히 비교
report_weight_table = weight_summary_result.pivot(
    index="company",
    columns="scenario",
    values="overlap_top10_mean"
).reindex(model.COMPANY_CONFIG)

report_weight_table = report_weight_table[list(SCENARIO_LABELS)]
report_weight_table = report_weight_table.rename(columns=SCENARIO_LABELS)
report_weight_table = report_weight_table.reset_index().rename(columns={"company": "기업"})
report_weight_table.columns.name = None

print("=== 기업별 가중치 민감도 요약 ===")
display(
    report_weight_table.style
    .format({label: "{:.1%}" for label in SCENARIO_LABELS.values()})
    .hide(axis="index")
)


# %%
# ============================================================
# 13. 문서용 그림 ① 기업별 Top 10 유지율 비교
# ============================================================

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import PercentFormatter

# 기존 분석 파일과 같은 Windows 맑은 고딕 설정
font_path = Path(r"C:\Windows\Fonts\malgun.ttf")

if font_path.exists():
    font_manager.fontManager.addfont(str(font_path))
    font_name = font_manager.FontProperties(fname=str(font_path)).get_name()
    plt.rcParams["font.family"] = font_name

plt.rcParams["axes.unicode_minus"] = False

# 긴 기업명을 읽기 쉽도록 가로 막대그래프로 비교
company_positions = np.arange(len(report_weight_table))
bar_height = 0.15

fig, ax = plt.subplots(figsize=(12, 8))

for offset, column, color in [
    (-2 * bar_height, "기존값 대비 ±5%", "#1D4ED8"),
    (-bar_height, "기존값 대비 ±10%", "#38BDF8"),
    (0, "기존값 대비 ±20%", "#14B8A6"),
    (bar_height, "기존값 대비 ±30%", "#F59E0B"),
    (2 * bar_height, "전체 범위", "#94A3B8")
]:
    bars = ax.barh(
        company_positions + offset,
        report_weight_table[column],
        height=bar_height,
        label=column,
        color=color
    )

    ax.bar_label(
        bars,
        labels=[f"{value:.1%}" for value in report_weight_table[column]],
        padding=4,
        fontsize=8
    )

ax.set_yticks(company_positions)
ax.set_yticklabels(report_weight_table["기업"])
ax.invert_yaxis()
ax.set_xlim(0, 1.12)
ax.set_xticks(np.arange(0, 1.01, 0.2))
ax.xaxis.set_major_formatter(PercentFormatter(xmax=1))
ax.set_xlabel("기존 Top 10 평균 유지율")
ax.set_title("가중치 변경 범위에 따른 기업별 추천 국가 유지율", pad=16)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=3)
ax.grid(axis="x", alpha=0.2)
ax.set_axisbelow(True)

plt.tight_layout()
plt.show()


# %%
# ============================================================
# 14. 문서용 핵심 표 ② 정규화 방식 비교 요약
# ============================================================

# 기본 CRITIC 가중치를 고정하고 정규화 방법만 바꾼 결과를 사용
report_methods = list(METHOD_LABELS)

report_normalization = normalization_comparison.loc[
    (normalization_comparison["weight_policy"] == "fixed_baseline")
    & normalization_comparison["method"].isin(report_methods)
]

report_normalization_range = (
    report_normalization.groupby("method")["overlap_top10"]
    .agg(["min", "max"])
    .reindex(report_methods)
)

report_normalization_table = pd.DataFrame({
    "정규화 방식": [METHOD_LABELS[method] for method in report_methods],
    "기업별 기존 Top 10 유지율 범위": [
        f"{row['min']:.0%}~{row['max']:.0%}"
        for _, row in report_normalization_range.iterrows()
    ]
})

print("=== 6개 지표 계산 방식별 Top 10 유지율 범위 ===")
display(report_normalization_table.style.hide(axis="index"))


# %%
# ============================================================
# 15. 문서용 사례 표 ③ 현대로템 Top 10 진입·이탈 국가
# ============================================================

# 필요하면 기업명을 바꾸어 다른 기업의 사례 확인
CASE_COMPANY = "현대로템"

report_case_table = pd.DataFrame(changes)
report_case_table = report_case_table.loc[
    report_case_table["기업"] == CASE_COMPANY
].copy()

report_case_table = report_case_table.replace({"방식": METHOD_LABELS})
report_case_table = report_case_table.rename(columns={
    "방식": "변경 방식",
    "진입": "Top 10 진입 국가",
    "이탈": "Top 10 이탈 국가"
})

print(f"=== {CASE_COMPANY} Top 10 진입·이탈 국가 ===")
display(report_case_table.style.hide(axis="index"))


