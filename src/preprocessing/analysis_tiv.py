# %%
import numpy as np
import pandas as pd

OFFICIAL = "../../data/analysis/tiv_supplier_official_clean.csv"
MINE = "../../data/processed/tiv_recipient.csv"

EXCLUDE = ["UNK"]
KEYS = ["recipient_iso_a3", "year", "supplier_iso_a3"]

off = pd.read_csv(OFFICIAL)
mine = pd.read_csv(MINE)

mine["supplier_iso_a3"] = mine["supplier_iso_a3"].replace(
    {"unknown supplier(s)": "UNK"}
)

# 합격 기준 (결과 보기 전에 고정)
CRITERIA = {"total_ratio": (0.98, 1.02), "year_rel_err": (0, 0.10),
            "hhi5_abs_err_mean": (0, 0.03), "rank_corr": (0.90, 1.0)}

# ---------- 1) 두 표 맞대기 ----------
mine = mine[KEYS + ["tiv_per_year"]]
mine = mine[mine["year"].between(2016, 2025)]

cmp = mine.merge(off[KEYS + ["tiv_official"]], on=KEYS, how="outer")
cmp[["tiv_per_year", "tiv_official"]] = cmp[["tiv_per_year", "tiv_official"]].fillna(0)
cmp = cmp[~cmp["supplier_iso_a3"].isin(EXCLUDE)]
cmp = cmp[cmp["recipient_iso_a3"].isin(off["recipient_iso_a3"].unique())]  # 20개국만

# ---------- 2) 계산용 함수 ----------
def hhi(g, col, years):
    """공급국 점유율 제곱합(HHI, 0~1)을 구한다.
    들어오는 값: g(한 수입국의 표), col(TIV 열 이름), years(계산에 쓸 연도 목록)
    돌려주는 값: HHI 숫자 하나 (해당 기간 거래가 없으면 NaN)
    """
    s = g[g["year"].isin(years)].groupby("supplier_iso_a3")[col].sum()
    total = s.sum()
    if total == 0:
        return np.nan
    return ((s / total) ** 2).sum()


def validate_one(g):
    """한 수입국의 균등배분 vs SIPRI 비교 지표 6개를 계산한다.
    들어오는 값: g(한 수입국의 비교 표: tiv_per_year, tiv_official 열 포함)
    돌려주는 값: 지표 6개가 담긴 Series
    """
    m, o = g["tiv_per_year"], g["tiv_official"]
    total_ratio = m.sum() / o.sum()
    cell_wape = (m - o).abs().sum() / o.sum()

    yr = g.groupby("year")[["tiv_per_year", "tiv_official"]].sum()
    yr = yr[yr["tiv_official"] > 0]
    year_err = ((yr["tiv_per_year"] - yr["tiv_official"]).abs() / yr["tiv_official"]).mean()

    errs = []
    for end in range(2020, 2026):                       # 5년 창을 굴리며 비교
        win = list(range(end - 4, end + 1))
        errs.append(abs(hhi(g, "tiv_per_year", win) - hhi(g, "tiv_official", win)))

    sup = g.groupby("supplier_iso_a3")[["tiv_per_year", "tiv_official"]].sum()
    sup = sup[(sup > 0).any(axis=1)]                    # 양쪽 다 0인 공급국 제외
    rank_corr = sup["tiv_per_year"].rank().corr(sup["tiv_official"].rank())

    return pd.Series({
        "total_ratio": total_ratio, "year_rel_err": year_err, "cell_wape": cell_wape,
        "hhi5_abs_err_mean": np.nanmean(errs), "hhi5_abs_err_max": np.nanmax(errs),
        "rank_corr": rank_corr,
    })


# ---------- 3) 20개국 실행 + 합격 판정 ----------
res = pd.DataFrame({r: validate_one(g) for r, g in cmp.groupby("recipient_iso_a3")}).T

for col, (lo, hi) in CRITERIA.items():
    res[col + "_ok"] = res[col].between(lo, hi)
print(res.round(3))
print(res.filter(like="_ok").mean())        # 지표별 합격 국가 비율
res.to_csv("../../data/analysis/tiv_validation_result.csv", encoding="utf-8-sig")

# ---------- 4) 오차 분포 그래프 ----------
import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 3, figsize=(12, 3.5))
for ax, col in zip(axes, ["year_rel_err", "hhi5_abs_err_mean", "rank_corr"]):
    ax.hist(res[col], bins=10)
    ax.set_title(col)
plt.tight_layout()
plt.savefig("../../data/analysis/tiv_validation_dist.png", dpi=150)