# %%
import pandas as pd

gpi=pd.read_csv("../../data/processed/gpi_overall.csv")
me=pd.read_csv("../../data/processed/military_expenditure.csv")
tiv_r=pd.read_csv("../../data/processed/tiv_recipient.csv")
tiv_wg=pd.read_csv("../../data/processed/tiv_weapon_group_order_year.csv")
th=pd.read_csv("../../data/processed/transaction_history.csv")
fitch=pd.read_csv("../../data/processed/fitch_rating_yearly.csv")

# %%
YEARS = list(range(2016, 2026))
KOREA = "KOR"
 
GROUPS = [
    "air_defence_systems", "aircraft_uavs", "armoured_vehicles", "artillery",
    "engines", "missiles_guided_weapons", "naval_weapons",
    "other_systems_components", "sensors_isr_satellites", "ships",
]
TIV_COLS = [f"{g}_tiv" for g in GROUPS]

COMPANIES=["hanwha_aerospace", "hanwha_ocean", "hyundai_rotem", "hyundai_heavy_industries", "kai", "lig"]

KWD_YEARS_COL="order_year"

WINDOW=5
OUT_PATH = "../../data/processed/final_score.csv"
# %%
# th(거래 이력 파일)에서 '최초 거래 연도'가 들어 있는 열 이름.
#   {final_score에 만들 열 이름 : th의 열 이름}
FIRST_YEAR_COLS = {
    "import_from_south_korea": "the_initial_year_of_south_korea's_defense_exports",
    **{f"{c}_transaction_history":
    f"the_initial_year_of_{c}'s_defense_exports" for c in COMPANIES},
}

print(FIRST_YEAR_COLS)
 
# 국가 코드 열 이름을 iso_a3로 통일
tiv_r = tiv_r.rename(columns={"recipient_iso_a3": "iso_a3"})
tiv_wg = tiv_wg.rename(columns={"recipient_iso_a3": "iso_a3"})

# %%
strength = pd.DataFrame(0.0, index=list(COMPANIES+GROUPS), columns=GROUPS)
strength.loc["hanwha_aerospace", ["artillery", "armoured_vehicles"]] = 1.0
strength.loc["hanwha_aerospace", ["air_defence_systems", "missiles_guided_weapons", "engines"]] = 0.5
strength.loc["hanwha_ocean", ["ships"]] = 1.0
strength.loc["hyundai_rotem", ["armoured_vehicles"]] = 1.0
strength.loc["hyundai_heavy_industries", ["ships"]] = 1.0
strength.loc["kai", ["aircraft_uavs"]] = 1.0
strength.loc["kai", ["sensors_isr_satellites"]] = 0.5
strength.loc["lig", ["missiles_guided_weapons", "air_defence_systems"]] = 1.0
strength.loc["lig", ["sensors_isr_satellites", "naval_weapons"]] = 0.5
for w in GROUPS:
	strength.loc[f"{w}",[f"{w}"]]=1.0
# %%
def calc_hhi(df, keys):
    """keys 단위로 묶어서 계산
 
    df   : tiv_recipient 형태 (supplier_iso_a3, tiv_per_year 열 필요)
    keys : 묶음 기준 열 이름 리스트
    반환 : keys + ['hhi'] 열을 가진 DataFrame (인도가 없는 묶음은 행이 없음)
    """
    t = (df[df["tiv_per_year"] > 0]
         .groupby(keys + ["supplier_iso_a3"], as_index=False)["tiv_per_year"].sum())
    total = t.groupby(keys)["tiv_per_year"].transform("sum")
    t["share_sq"] = (t["tiv_per_year"] / total) ** 2
    return (t.groupby(keys, as_index=False)["share_sq"].sum()
             .rename(columns={"share_sq": "hhi"}))
 
 
def calc_hhi_rolling(df, years, window):
    """각 연도 y마다 (y-window+1 ~ y) 구간의 TIV를 합산한 뒤 HHI를 계산
 
    df     : tiv_recipient 형태 (iso_a3, year, supplier_iso_a3, tiv_per_year)
    years  : HHI를 만들 연도 목록
    window : 구간 길이(년)
    반환   : iso_a3, year, hhi_{window}y 열의 DataFrame
             (구간이 데이터 시작 연도 앞으로 걸치는 해는 행이 없음 → 나중에 NaN)
    """
    first_data_year = df["year"].min()
    parts = []
    for y in years:
        start = y - window + 1
        if start < first_data_year:
            continue
        sub = df[df["year"].between(start, y)]
        h = calc_hhi(sub, ["iso_a3"])
        h["year"] = y
        parts.append(h)
    out = pd.concat(parts, ignore_index=True)
    return out.rename(columns={"hhi": f"hhi_{window}y"})


def calc_gpi_rolling(df, years, window):
    """각 연도 y마다 (y-window+1 ~ y) 구간의 GPI 점수를 평균한 뒤 반환
 
    df     : gpi_overall 형태 (iso_a3, year, score)
    years  : GPI를 만들 연도 목록
    window : 구간 길이(년)
    반환   : iso_a3, year, gpi_score_{window}y 열의 DataFrame
             (구간이 데이터 시작 연도 앞으로 걸치는 해는 행이 없음 → 나중에 NaN)
    """
    first_data_year = df["year"].min()
    parts = []
    for y in years:
        start = y - window + 1
        if start < first_data_year:
            continue
        sub = df[df["year"].between(start, y)]
        g = sub.groupby("iso_a3", as_index=False)["score"].mean()
        g["year"] = y
        parts.append(g)
    out = pd.concat(parts, ignore_index=True)
    return out.rename(columns={"score": f"gpi_score_{window}y"})

 
def calc_category_scores(df, strength, keys):
    """무기분류 점수 = Σ (국가의 무기그룹별 TIV 비중 × 그룹별 강점).
 
    df       : tiv_weapon_group 형태 ({그룹}_tiv 열 10개 필요)
    strength : 무기그룹 강점표 (행=기업, 무기 키, 열=GROUPS)
    keys     : 묶음 기준 열 이름 리스트
    반환     : keys + 기업, 무기 '{기업&무기}_category_score' 열 (TIV 합이 0이면 NaN)
    """
    t = df.groupby(keys, as_index=False)[TIV_COLS].sum()
    total = t[TIV_COLS].sum(axis=1)
    share = t[TIV_COLS].div(total.where(total > 0), axis=0)
    share.columns = GROUPS
    out = t[keys].copy()
    for c in COMPANIES+GROUPS:
        w = strength.loc[c, GROUPS]
        out[f"{c}_category_score"] = share.mul(w, axis=1).sum(axis=1, min_count=1)
    return out
 
 
def first_year_flag(grid, first_year_by_country):
    """최초 거래 연도 이후(그 해 포함)는 1, 이전이거나 거래 없음은 0.
 
    grid                  : iso_a3, year 열을 가진 표
    first_year_by_country : 국가코드 -> 최초 거래 연도 (Series). 0이나 빈 값은 '거래 없음'
    반환                  : grid와 같은 길이의 0/1 Series
    """
    first = pd.to_numeric(grid["iso_a3"].map(first_year_by_country), errors="coerce")
    first = first.where(first > 0)          # 0은 '거래 없음'이므로 NaN 처리 (그대로 두면 모든 해가 1이 됨)
    return (grid["year"] >= first).astype(int)
 
 
# %% [5] final_score 만들기 (국가 × 연도) -------------------------------------
countries = sorted(th["iso_a3"].unique())
print("국가 수:", len(countries))          # 98개가 맞는지 확인
 
final = pd.MultiIndex.from_product(
    [countries, YEARS], names=["iso_a3", "year"]).to_frame(index=False)
 
# hhi_1y : 한 해만의 공급국 집중도 (인도가 없는 해는 NaN)
hhi_1y = calc_hhi(tiv_r, ["iso_a3", "year"]).rename(columns={"hhi": "hhi_1y"})
final = final.merge(hhi_1y, on=["iso_a3", "year"], how="left")
 
# hhi_5y : 최근 5년 합산 HHI (2016~2019는 구간이 모자라 NaN)
hhi_5y = calc_hhi_rolling(tiv_r, YEARS, WINDOW)
final = final.merge(hhi_5y, on=["iso_a3", "year"], how="left")
 
# military_expenditure
final = final.merge(
    me[["iso_a3", "year", "military_expenditure_usd", "military_expenditure_gdp_pct"]],
    on=["iso_a3", "year"], how="left")

# tiv_total_1y
tiv_total_1y = (tiv_r.groupby(["iso_a3", "year"], as_index=False)["tiv_per_year"].sum()
                .rename(columns={"tiv_per_year": "tiv_total_1y"}))
final = final.merge(tiv_total_1y, on=["iso_a3", "year"], how="left")
final["tiv_total_1y"] = final["tiv_total_1y"].fillna(0)      # 인도 없음 = 0

# tiv_total_5y
final = final.sort_values(["iso_a3", "year"])
final["tiv_total_5y"] = (final.groupby("iso_a3")["tiv_total_1y"]
                         .rolling(5, min_periods=5).mean()
                         .reset_index(level=0, drop=True))
 
# gpi_score_1y = score (국가별 값, 연도와 무관)
gpi_latest = (gpi[["iso_a3", "year", "score"]]
              .rename(columns={"score": "gpi_score_1y"}))
final = final.merge(gpi_latest, on=["iso_a3", "year"], how="left")

# gpi_score_5y
gpi_5y = calc_gpi_rolling(gpi, YEARS, WINDOW)
final = final.merge(gpi_5y, on=["iso_a3", "year"], how="left")

# tiv_korea : 한국(KOR)이 그 나라에 그 해 인도한 TIV (없으면 0)
tiv_korea = (tiv_r[tiv_r["supplier_iso_a3"] == KOREA]
             .groupby(["iso_a3", "year"], as_index=False)["tiv_per_year"].sum()
             .rename(columns={"tiv_per_year": "tiv_korea"}))
final = final.merge(tiv_korea, on=["iso_a3", "year"], how="left")
final["tiv_korea"] = final["tiv_korea"].fillna(0)
 
# category_score (한 해 기준)
cs = calc_category_scores(tiv_wg, strength, ["iso_a3", "year"])
final = final.merge(cs, on=["iso_a3", "year"], how="left")

# 거래 이력 0/1 : th의 '최초 거래 연도'를 기준으로 (이전 0, 그 해 포함 이후 1)
first_years = th.set_index("iso_a3")
for out_col, src_col in FIRST_YEAR_COLS.items():
    first = pd.to_numeric(first_years[src_col], errors="coerce")   # 숫자가 아니면 NaN
    final[out_col] = first_year_flag(final, first)

# fitch_rating : fitch_rating_yearly.csv의 rating를 그대로 가져옴
final = final.merge(fitch[["iso_a3", "year", "rating"]], on=["iso_a3", "year"], how="left")
final.rename(columns={"rating": "fitch_score"}, inplace=True)
 
# %% [6] 열 순서 정리, 점검, 저장 ---------------------------------------------
ordered = ["iso_a3", "year", "hhi_1y", f"hhi_{WINDOW}y",
           "military_expenditure_usd", "military_expenditure_gdp_pct", "tiv_total_1y", "tiv_total_5y",
           "gpi_score_1y",f"gpi_score_{WINDOW}y", "fitch_score", "tiv_korea", "import_from_south_korea"]
for comp in COMPANIES:
    ordered += [f"{comp}_transaction_history", f"{comp}_category_score"]
for wg in GROUPS:
    ordered += [f"{wg}_category_score"]
final = final[ordered]
 
assert not final.duplicated(["iso_a3", "year"]).any(), "iso_a3, year 중복 있음"
print(final.shape)            # (국가 수 x 10, 21)
print(final.isna().sum())     # 열별 빈 값 개수 확인
 
final.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
# %%
# military_expenditure_usd 열이 NaN인 국가-연도 확인
na_me = (final[final["military_expenditure_usd"].isna()]
         .groupby("iso_a3").size().sort_values(ascending=False))
print(na_me)