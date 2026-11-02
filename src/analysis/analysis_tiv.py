# %%
import numpy as np
import pandas as pd

OFFICIAL = "../../data/analysis/tiv_supplier_official_clean.csv"
MINE = "../../data/processed/tiv_recipient.csv"

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

# %%
yr = cmp.groupby(["recipient_iso_a3", "year"])[["tiv_per_year", "tiv_official"]].sum()
m = yr["tiv_per_year"].unstack(fill_value=0)      # 행: 수입국, 열: 연도 (균등배분)
o = yr["tiv_official"].unstack(fill_value=0)      # 행: 수입국, 열: 연도 (SIPRI)

rows = []
for end in range(2020, 2026):                      # 5년 창을 굴리며 합산
    cols = list(range(end - 4, end + 1))
    rows.append(pd.DataFrame({
        "end": end,
        "mine": m[cols].sum(axis=1),
        "official": o[cols].sum(axis=1),
    }))
w = pd.concat(rows)
w = w[w["official"] > 0]
w["rel_err"] = (w["mine"] - w["official"]).abs() / w["official"]

print(w["rel_err"].describe().round(3))
print((w["rel_err"] <= 0.10).mean())               # 10% 이내 비율 (0.908)
# %%
# 2) 5년 합계 오차가 큰 국가 (국가별 평균, 상위 6개)
print(w["rel_err"].groupby(level=0).mean().sort_values(ascending=False).head(6).round(3))
# 기대값: POL 0.124, SVK 0.113, AUS 0.077, IRQ 0.077, PER 0.060, QAT 0.056

# 3) 1년 HHI 절대오차
errs = []
for (r, y), g in cmp.groupby(["recipient_iso_a3", "year"]):
    errs.append(abs(hhi(g, "tiv_per_year", [y]) - hhi(g, "tiv_official", [y])))
e1 = pd.Series(errs).dropna()           # 양쪽 모두 거래가 있는 수입국·연도만 남음
print(len(e1), e1.mean().round(3), e1.median().round(3), e1.quantile(0.9).round(3), e1.max().round(3))
# 기대값: 196, 0.034, 0.022, 0.080, 0.333

# 4) 한국 공급 TIV
k = cmp[cmp["supplier_iso_a3"] == "KOR"]
print(round(k["tiv_official"].sum(), 1), round(k["tiv_per_year"].sum(), 1))   # 6688.0, 6650.9
kk = k[k["tiv_official"] > 0]
print(((kk["tiv_per_year"] - kk["tiv_official"]).abs().sum() / kk["tiv_official"].sum()).round(3))  # 0.284
# %%
master = pd.read_csv("../../data/mapping/country_map_master.csv")
name_map = master.set_index("iso_a3")["country_name_ko"].to_dict()

tbl = res[["total_ratio", "year_rel_err", "cell_wape",
           "hhi5_abs_err_mean", "hhi5_abs_err_max", "rank_corr"]].round(3).copy()
tbl.insert(0, "국가", tbl.index.map(lambda x: name_map.get(x, x)))
tbl["종합합격"] = res.filter(like="_ok").all(axis=1)      # 4개 기준 모두 통과해야 True
tbl = tbl.rename(columns={
    "total_ratio": "총량 비율", "year_rel_err": "연도별 상대오차",
    "cell_wape": "칸 단위 오차(WAPE)", "hhi5_abs_err_mean": "5년 HHI 오차(평균)",
    "hhi5_abs_err_max": "5년 HHI 오차(최대)", "rank_corr": "공급국 순위 상관"})

print(tbl.iloc[:, 1:7].agg(["mean", "median"]).round(3))   # 평균·중앙값 행
print(tbl["종합합격"].sum(), "/ 20")
tbl.to_csv("../../data/analysis/tiv_validation_table.csv", encoding="utf-8-sig")
# %%
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"      # 맥은 "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

def panel(ax, x, title, lines=(), bins=10, xlabel=""):
    """히스토그램 한 칸을 그린다.
    들어오는 값: ax(그릴 칸), x(오차 값들), title(제목), lines(합격 기준선 위치), bins(막대 수), xlabel(가로축 이름)
    돌려주는 값: 없음 (그 칸에 그림이 그려짐)
    """
    ax.hist(x, bins=bins, edgecolor="white")
    for v in lines:
        ax.axvline(v, color="red", ls="--")
    ax.set_title(title); ax.set_xlabel(xlabel); ax.set_ylabel("국가 수")

fig, axes = plt.subplots(2, 2, figsize=(11, 8))
panel(axes[0, 0], res["total_ratio"], "총량 비율 (균등배분 ÷ SIPRI)", lines=[0.98, 1.02], xlabel="비율")
panel(axes[0, 1], res["year_rel_err"], "연도별 상대오차", lines=[0.10], xlabel="상대오차")
panel(axes[1, 0], res["hhi5_abs_err_mean"], "5년 HHI 절대오차(평균)", lines=[0.03], xlabel="절대오차")
panel(axes[1, 1], w["rel_err"], "5년 합계 상대오차(사후 확인)", lines=[0.10], bins=15, xlabel="상대오차")
axes[1, 1].set_ylabel("국가·기간 수")
plt.tight_layout()
plt.savefig("../../data/analysis/tiv_validation_dist_2.png", dpi=150)