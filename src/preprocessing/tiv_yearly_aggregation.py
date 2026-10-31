# %%
import pandas as pd

DATA = "../../data/processed/"
df = pd.read_csv(DATA + "arms_trade_98_countries.csv")

df = df[
    [
        "recipient_iso_a3",
        "supplier_iso_a3",
        "weapon_type_group_en",
        "delivery_years",
        "tiv_delivered"
    ]
].copy()


# ============================================================
# 1. delivery_years 기준 연도별 TIV 계산
# ============================================================

# delivery_years 결측치 제외
d = df.dropna(subset=["delivery_years"]).copy()

# ; 기준으로 연도 쪼개기
# 예: "2018; 2019" → [2018, 2019]
d["year_list"] = (
    d["delivery_years"]
    .str.split(";")
    .apply(
        lambda s: [
            int(x)
            for x in s
            if x.strip().isdigit()
        ]
    )
)

# 인도 연도 수
d["n_years"] = d["year_list"].apply(len)

# 연도가 정상적으로 추출된 행만 사용
d = d[
    d["n_years"] > 0
].copy()

# TIV를 인도 연도 수로 균등 분할
d["tiv_per_year"] = (
    d["tiv_delivered"]
    / d["n_years"]
)

# 연도별로 행 펼치기
e = d.explode("year_list")

e["year"] = e["year_list"].astype(int)

# 분석기간 2016~2025만 남기기
e = e[
    e["year"].between(2016, 2025)
].copy()

# 수입국 + 연도 + 수출국 + 무기그룹별 TIV 합계
yearly = (
    e.groupby(
        [
            "recipient_iso_a3",
            "year",
            "supplier_iso_a3",
            "weapon_type_group_en"
        ]
    )["tiv_per_year"]
    .sum()
    .reset_index()
)

# 저장할 때만 소수점 둘째 자리 반올림
yearly.round(2).to_csv(
    DATA + "tiv_delivery_yearly.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 2. 국가별 · 연도별 · 수출국별 TIV
# ============================================================

tiv_recipient = (
    yearly
    .groupby(
        [
            "recipient_iso_a3",
            "year",
            "supplier_iso_a3"
        ]
    )["tiv_per_year"]
    .sum()
    .reset_index()
)

tiv_recipient.to_csv(
    DATA + "tiv_recipient.csv",
    index=False,
    encoding="utf-8-sig"
)

print(tiv_recipient.head())


# ============================================================
# 3. 국가별 · 연도별 무기 10개 그룹 TIV
# ============================================================

tiv_weapon_group = (
    yearly
    .groupby(
        [
            "recipient_iso_a3",
            "year",
            "weapon_type_group_en"
        ]
    )["tiv_per_year"]
    .sum()
    .reset_index()
)

# 무기 그룹을 가로 컬럼으로 펼치기
tiv_weapon_group = (
    tiv_weapon_group
    .pivot(
        index=[
            "recipient_iso_a3",
            "year"
        ],
        columns="weapon_type_group_en",
        values="tiv_per_year"
    )
    .fillna(0)
    .reset_index()
)

# 무기그룹 컬럼 뒤에 _tiv 붙이기
tiv_weapon_group = tiv_weapon_group.rename(
    columns={
        "air_defence_systems": "air_defence_systems_tiv",
        "aircraft_uavs": "aircraft_uavs_tiv",
        "armoured_vehicles": "armoured_vehicles_tiv",
        "artillery": "artillery_tiv",
        "engines": "engines_tiv",
        "missiles_guided_weapons": "missiles_guided_weapons_tiv",
        "naval_weapons": "naval_weapons_tiv",
        "other_systems_components": "other_systems_components_tiv",
        "sensors_isr_satellites": "sensors_isr_satellites_tiv",
        "ships": "ships_tiv"
    }
)


tiv_weapon_group.to_csv(
    DATA + "tiv_weapon_group.csv",
    index=False,
    encoding="utf-8-sig"
)

print(tiv_weapon_group.head())

# %%