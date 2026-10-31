# %% 주문연도 기준 tiv_weapon_group 만들기 ---------------------------------------
# 입력 : arms_trade_98_countries  (필요한 열: recipient_iso_a3, order_year,
#                                  weapon_type_group_en, tiv_order, status)
# 출력 : recipient_iso_a3, year, {무기그룹}_tiv 10개  (year = 주문 연도)
import os
from pathlib import Path

import numpy as np
import pandas as pd

GROUPS = [
    "air_defence_systems", "aircraft_uavs", "armoured_vehicles", "artillery",
    "engines", "missiles_guided_weapons", "naval_weapons",
    "other_systems_components", "sensors_isr_satellites", "ships",
]

YEAR_MIN, YEAR_MAX = 2016, 2025     # 포함할 주문 연도 범위
ONLY_NEW = False                    # True면 신품(New)만 집계
OUT_PATH = "../../data/processed/tiv_weapon_group_order_year.csv"
arms_trade_98_countries = pd.read_csv("../../data/processed/arms_trade_98_countries.csv", encoding="utf-8-sig")


def make_tiv_weapon_group_order(arms, year_min, year_max, only_new=False):
    """주문연도 x 수입국 x 무기그룹별 주문 TIV(tiv_order) 합계를 가로 표로 만든다.

    arms      : arms_trade_98_countries 형태의 거래 목록
    year_min, year_max : 포함할 주문 연도 범위 (양 끝 포함)
    only_new  : True면 status가 'New'인 거래만 사용
    반환      : recipient_iso_a3, year, {그룹}_tiv 10개 열의 DataFrame
                (주문이 없는 그룹은 0, 주문이 하나도 없는 수입국-연도는 행이 없음)
    """
    df = arms[arms["order_year"].between(year_min, year_max)]
    if only_new:
        df = df[df["status"] == "New"]

    # 그룹 값 점검: 빈 값이나 정의되지 않은 값이 있으면 멈추고 알려줌
    assert df["weapon_type_group_en"].notna().all(), "weapon_type_group_en이 빈 행이 있어요"
    unknown = set(df["weapon_type_group_en"].unique()) - set(GROUPS)
    assert not unknown, f"정의되지 않은 무기 그룹 값: {unknown}"

    wide = df.pivot_table(index=["recipient_iso_a3", "order_year"],
                          columns="weapon_type_group_en",
                          values="tiv_order", aggfunc="sum", fill_value=0)
    wide = wide.reindex(columns=GROUPS, fill_value=0)      # 10개 그룹을 항상 같은 순서로
    wide.columns = [f"{g}_tiv" for g in GROUPS]
    out = wide.reset_index().rename(columns={"order_year": "year"})

    # 합계가 원본과 같은지, 중복이 없는지 점검
    assert np.isclose(out[[f"{g}_tiv" for g in GROUPS]].to_numpy().sum(),
                      df["tiv_order"].sum()), "집계 후 TIV 합계가 원본과 달라요"
    assert not out.duplicated(["recipient_iso_a3", "year"]).any(), "수입국-연도 중복"
    return out


tiv_weapon_group_order = make_tiv_weapon_group_order(
    arms_trade_98_countries, YEAR_MIN, YEAR_MAX, ONLY_NEW)

win = arms_trade_98_countries["order_year"].between(YEAR_MIN, YEAR_MAX)
print(tiv_weapon_group_order.shape)
print("주문연도 범위:", tiv_weapon_group_order["year"].min(), "~", tiv_weapon_group_order["year"].max())
print("tiv_order가 0인 거래 비율:", round((arms_trade_98_countries.loc[win, "tiv_order"] == 0).mean(), 3))

# %% 저장 (같은 이름이면 덮어쓰기) ---------------------------------------------
out = Path(OUT_PATH)
out.parent.mkdir(parents=True, exist_ok=True)

tmp = out.with_name(out.name + ".tmp")
tiv_weapon_group_order.to_csv(tmp, index=False, encoding="utf-8-sig")
os.replace(tmp, out)

print("저장 위치:", out.resolve())