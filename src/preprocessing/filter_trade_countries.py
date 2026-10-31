# %%
import re
import pandas as pd


# ============================================================
# 1. SIPRI 1950~2025 원본 데이터 불러오기
# ============================================================

DATA_RAW = "../../data/raw/"
DATA_PROCESSED = "../../data/processed/"

df = pd.read_csv(
    DATA_RAW + "sipri_trade_1950.csv",
    skiprows=11,
    encoding="latin-1"
)

# 원본 확인
print(
    f"원본 데이터 크기: {df.shape}"
    f"\n원본 컬럼: {df.columns.tolist()}"
    f"\n\n원본 상위 5행:\n{df.head()}"
    f"\n\n원본 결측치:\n{df.isna().sum()}"
)

# 데이터 타입 확인
df.info()


# ============================================================
# 2. SIPRI 컬럼명 정리
# ============================================================

# 스네이크 방식으로 열 이름 교체
df = df.rename(columns={
    "Recipient": "recipient",
    "Supplier": "supplier",
    "Year of order": "order_year",
    "Number ordered": "ordered_qty",
    "Weapon designation": "weapon",
    "Weapon description": "weapon_type",
    "Deliveries in the Year Range": "delivered_qty",
    "Year(s) of delivery": "delivery_years",
    "status": "status",
    "Comments": "comments",
    "SIPRI TIV per unit": "tiv_per_unit",
    "SIPRI TIV for total order": "tiv_order",
    "SIPRI TIV of delivered weapons": "tiv_delivered",
})

# ? 표시가 들어있는 컬럼명 변경
df = df.rename(columns={
    df.columns[3]: "order_year_uncertain",
    df.columns[5]: "ordered_qty_uncertain",
    df.columns[9]: "delivered_qty_uncertain"
})

# ? 여부를 True / False로 변경
for c in [
    "order_year_uncertain",
    "ordered_qty_uncertain",
    "delivered_qty_uncertain"
]:
    df[c] = df[c].eq("?")

print(
    f"컬럼 정리 후 상위 5행:\n{df.head()}"
    f"\n\n컬럼명:\n{df.columns.tolist()}"
)

# 데이터 타입 확인
df.info()


# ============================================================
# 3. 분석 대상 98개 국가만 추출
# ============================================================

country_df = pd.read_csv(
    "../../data/mapping/country_map_master.csv",
    keep_default_na=False,
    na_values=[""]
)

# 최종 국가맵의 국가명 사용
country_list = country_df["sipri_trade_country_name"]

# 수입국이 98개국 안에 있는 거래만 추출
# 수입국 South Korea는 제외
trade_98 = df[
    df["recipient"].isin(country_list) &
    (df["recipient"] != "South Korea")
].copy()

# 실제 거래가 없는 대상국 확인
missing_recipient = sorted(
    set(country_list.dropna().unique())
    - set(trade_98["recipient"].dropna().unique())
)

print(
    f"실제 수입국: {trade_98['recipient'].nunique()}개국"
    f"\n거래 데이터에 없는 대상국: {len(missing_recipient)}개국"
    f"\n{missing_recipient}"
)


# ============================================================
# 4. 완전히 동일한 중복 행 확인 및 제거
# ============================================================

duplicate_rows = trade_98[
    trade_98.duplicated(keep=False)
]

print(
    f"완전 중복 행: {len(duplicate_rows)}행"
    f"\n\n{duplicate_rows.to_string(index=False)}"
)

trade_98 = (
    trade_98
    .drop_duplicates()
    .copy()
)


# ============================================================
# 4-1. 검수 후 중복으로 판단한 거래 제거
# ============================================================

before_remove = len(trade_98)

remove_mask = (

    # 삭제 대상 1
    (
        (trade_98["recipient"] == "Peru") &
        (trade_98["supplier"] == "United States") &
        (trade_98["order_year"] == 2023) &
        (trade_98["weapon"] == "F-28") &
        (trade_98["ordered_qty"] == 2) &
        (trade_98["order_year_uncertain"] == True) &
        (trade_98["ordered_qty_uncertain"] == False) &
        (trade_98["delivery_years"] == "2024")
    )

    |

    # 삭제 대상 2
    (
        (trade_98["recipient"] == "Indonesia") &
        (trade_98["supplier"] == "Italy") &
        (trade_98["order_year"] == 2025) &
        (trade_98["weapon"] == "Super Rapid 76mm") &
        (trade_98["ordered_qty"] == 2) &
        (trade_98["order_year_uncertain"] == True)
    )

    |

    # 삭제 대상 3
    (
        (trade_98["recipient"] == "Iraq") &
        (trade_98["supplier"] == "United States") &
        (trade_98["order_year"] == 2013) &
        (trade_98["weapon"] == "F-404") &
        (trade_98["ordered_qty"] == 24) &
        (trade_98["order_year_uncertain"] == True)
    )

    |

    # 삭제 대상 4
    (
        (trade_98["recipient"] == "Israel") &
        (trade_98["supplier"] == "United States") &
        (trade_98["order_year"] == 2023) &
        (trade_98["weapon"] == "L-ATV") &
        (trade_98["ordered_qty"] == 75) &
        (trade_98["ordered_qty_uncertain"] == True) &
        (trade_98["delivery_years"] == "2024")
    )

    |

    # 삭제 대상 5~6
    (
        (trade_98["recipient"] == "Italy") &
        (trade_98["supplier"] == "Germany") &
        (trade_98["order_year"] == 2025) &
        (trade_98["weapon"] == "Lynx KF-41") &
        (trade_98["ordered_qty"].isna())
    )

    |

    # 삭제 대상 7
    (
        (trade_98["recipient"] == "Mexico") &
        (trade_98["supplier"] == "Canada") &
        (trade_98["order_year"] == 2014) &
        (trade_98["weapon"] == "aircraft engine") &
        (trade_98["ordered_qty"] == 4) &
        (trade_98["order_year_uncertain"] == True)
    )

    |

    # 삭제 대상 8
    (
        (trade_98["recipient"] == "Mexico") &
        (trade_98["supplier"] == "Spain") &
        (trade_98["order_year"] == 2014) &
        (trade_98["weapon"] == "C-295") &
        (trade_98["ordered_qty"] == 2) &
        (trade_98["order_year_uncertain"] == True)
    )

    |

    # 삭제 대상 9
    (
        (trade_98["recipient"] == "Pakistan") &
        (trade_98["supplier"] == "United States") &
        (trade_98["order_year"] == 2015) &
        (trade_98["weapon"] == "Cessna-208 Caravan") &
        (trade_98["ordered_qty"] == 2) &
        (trade_98["order_year_uncertain"] == False)
    )

    |

    # 삭제 대상 10
    (
        (trade_98["recipient"] == "Peru") &
        (trade_98["supplier"] == "United States") &
        (trade_98["order_year"] == 2020) &
        (trade_98["weapon"] == "F-28") &
        (trade_98["ordered_qty"] == 2) &
        (trade_98["order_year_uncertain"] == False)
    )
)

if remove_mask.sum() != 10:
    raise ValueError(
        f"삭제 대상이 10행이 아닙니다. "
        f"현재 {remove_mask.sum()}행이 잡혔습니다."
    )

trade_98 = trade_98[
    ~remove_mask
].copy()

after_remove = len(trade_98)

print(
    f"중복 제거 전: {before_remove}행"
    f"\n중복 삭제 대상: {remove_mask.sum()}행"
    f"\n중복 제거 후: {after_remove}행"
    f"\n실제 제거: {before_remove - after_remove}행"
    f"\n삭제 대상 수와 실제 삭제 수 일치: "
    f"{remove_mask.sum() == before_remove - after_remove}"
)


# ============================================================
# 5. 국가명 → ISO 정보 매핑
# ============================================================

# 98개 분석 대상 국가의
# SIPRI 국가명 → ISO_A3 매핑표 생성
iso3_map = (
    country_df
    .set_index("sipri_trade_country_name")["iso_a3"]
)


# ============================================================
# 5-1. 98개국 국가맵에 없는 수출국 확인
# ============================================================

# 실제 거래 데이터의 수출국 중
# 98개국 국가맵에 없는 수출국 이름 확인
missing_supplier = sorted(
    set(trade_98["supplier"].dropna().unique())
    - set(country_list.dropna().unique())
)

print(
    f"98개국 국가맵에 없는 수출국: {len(missing_supplier)}개"
    f"\n{missing_supplier}"
)


# ============================================================
# 5-2. 98개국 밖의 수출국 ISO_A3 보완
# ============================================================

supplier_iso_extra = {
    "Bahamas": "BHS",
    "Bosnia-Herzegovina": "BIH",
    "Brunei": "BRN",
    "Cyprus": "CYP",
    "Iran": "IRN",
    "Ireland": "IRL",
    "Latvia": "LVA",
    "Lithuania": "LTU",
    "Malta": "MLT",
    "North Macedonia": "MKD",
    "Slovenia": "SVN",
    "unknown supplier(s)": "unknown supplier(s)",
    "African Union**": "African Union"
}

# 기존 98개국 ISO 매핑을 dictionary로 복사
supplier_iso3_map = iso3_map.to_dict()

# 98개국 밖의 수출국 ISO 코드 추가
supplier_iso3_map.update(
    supplier_iso_extra
)


# ============================================================
# 5-3. 수입국 / 수출국 ISO_A3 추가
# ============================================================

# 수입국은 분석 대상 98개국 맵 기준으로 매핑
trade_98.insert(
    1,
    "recipient_iso_a3",
    trade_98["recipient"].map(iso3_map)
)

# 수출국은
# 98개국 맵 + 추가 수출국 ISO 맵 기준으로 매핑
trade_98.insert(
    3,
    "supplier_iso_a3",
    trade_98["supplier"].map(supplier_iso3_map)
)


# ============================================================
# 5-4. ISO_A3 매핑 결과 검수
# ============================================================

unmapped_supplier = (
    trade_98[
        trade_98["supplier_iso_a3"].isna()
    ]["supplier"]
    .value_counts(dropna=False)
)

unmapped_supplier = (
    unmapped_supplier
    .astype(str)
    + "행"
)

print(
    f"수입국 ISO 결측치: "
    f"{trade_98['recipient_iso_a3'].isna().sum()}개"
    f"\nISO_A3가 없는 수출국: {len(unmapped_supplier)}개"
    f"\n\n{unmapped_supplier}"
)

# ISO_A3 결측치가 원본의 몇 번째 행인지 확인
missing_supplier_rows = trade_98[
    trade_98["supplier_iso_a3"].isna()
].copy()

missing_supplier_rows["원본_csv_행"] = (
    missing_supplier_rows.index + 13
)

missing_supplier_check = missing_supplier_rows[
    ["원본_csv_행", "supplier", "weapon", "order_year"]
]

print(
    f"\nISO_A3 결측치 원본 위치:\n"
    f"{missing_supplier_check.to_string(index=False)}"
)


# ============================================================
# 5-5. SIPRI 원본 weapon_type 오타 수정
# ============================================================

trade_98["weapon_type"] = (
    trade_98["weapon_type"]
    .replace(
        "iinfantry fighting vehicle turret",
        "infantry fighting vehicle turret"
    )
)


# ============================================================
# 5-6. 전체 weapon_type 리스트 생성 및 저장
# ============================================================

# 아직 weapon_type을 삭제하기 전에
# 전체 분석 대상 데이터의 weapon_type 종류 저장
weapon_type_list = (
    trade_98[["weapon_type"]]
    .drop_duplicates()
    .reset_index(drop=True)
)

weapon_type_list.to_csv(
    DATA_PROCESSED + "weapon_type_list.csv",
    index=False,
    encoding="utf-8-sig"
)

print(
    f"weapon_type 종류 수: {len(weapon_type_list)}개"
)


# ============================================================
# 5-7. 불필요한 국가명 columns 삭제
#      및 order_year / order_year_uncertain 위치 이동
# ============================================================

# ISO 코드 매핑이 끝났으므로 기존 국가명 삭제
trade_98 = trade_98.drop(
    columns=[
        "recipient",
        "supplier"
    ]
)

# 기존 order_year 열 꺼내기
order_year = trade_98.pop(
    "order_year"
)

# recipient_iso_a3 위치 찾기
recipient_idx = trade_98.columns.get_loc(
    "recipient_iso_a3"
)

# recipient_iso_a3 바로 오른쪽에 order_year 추가
trade_98.insert(
    recipient_idx + 1,
    "order_year",
    order_year
)

# 기존 order_year_uncertain 열 꺼내기
order_year_uncertain = trade_98.pop(
    "order_year_uncertain"
)

# order_year 위치 찾기
order_year_idx = trade_98.columns.get_loc(
    "order_year"
)

# order_year 바로 오른쪽에 order_year_uncertain 추가
trade_98.insert(
    order_year_idx + 1,
    "order_year_uncertain",
    order_year_uncertain
)


# %%
# ============================================================
# 여기까지 처음 실행
# ============================================================
#
# weapon_type_list.csv 생성됨
#
# 1950~2025 전체 원본을 사용하므로
# 기존보다 새로운 weapon_type이 추가될 수 있음
#
# weapon_type_10group.py 실행 후
# 새 weapon_type까지 10개 그룹으로 매핑하고
# 아래 6번부터 다시 진행
# ============================================================


# ============================================================
# 6. weapon_type → 영어 10개 그룹으로 매핑
# ============================================================

weapon_type_10group = pd.read_csv(
    DATA_PROCESSED + "weapon_type_10group.csv",
    keep_default_na=False,
    na_values=[""]
)

weapon_type_map = (
    weapon_type_10group
    .set_index("weapon_type")["weapon_type_group_en"]
)

# 기존 weapon_type 위치
weapon_type_idx = trade_98.columns.get_loc(
    "weapon_type"
)

# weapon_type 바로 오른쪽에 10그룹 추가
trade_98.insert(
    weapon_type_idx + 1,
    "weapon_type_group_en",
    trade_98["weapon_type"].map(weapon_type_map)
)

# 미매핑 weapon_type 검수
missing_weapon_type = (
    trade_98[
        trade_98["weapon_type_group_en"].isna()
    ]["weapon_type"]
    .drop_duplicates()
)

print(
    f"10그룹 미매핑 weapon_type: "
    f"{len(missing_weapon_type)}개"
    f"\n{missing_weapon_type.to_string(index=False)}"
)


# ============================================================
# 7. 기존 SIPRI 세부 weapon_type 삭제
# ============================================================

trade_98 = trade_98.drop(
    columns=["weapon_type"]
)


# ============================================================
# 8. 정렬 및 최종 검수
# ============================================================

trade_98 = (
    trade_98
    .sort_values(
        by=[
            "recipient_iso_a3",
            "order_year"
        ]
    )
    .reset_index(drop=True)
)

# ISO 결측 행 수
iso_missing = (
    trade_98[
        [
            "recipient_iso_a3",
            "supplier_iso_a3"
        ]
    ]
    .isna()
    .sum()
    .astype(str)
    + "행"
)

# 10개 그룹별 행 수
group_count = (
    trade_98["weapon_type_group_en"]
    .value_counts()
    .astype(str)
    + "행"
)

print(
    f"수입국 수: "
    f"{trade_98['recipient_iso_a3'].nunique()}개국"

    f"\n전체 기간 거래 행 수: "
    f"{len(trade_98)}행"

    f"\n\nISO 결측 행 수:\n"
    f"{iso_missing}"

    f"\n\nweapon_type_group_en 결측 행 수: "
    f"{trade_98['weapon_type_group_en'].isna().sum()}행"

    f"\nweapon_type_group_en 종류 수: "
    f"{trade_98['weapon_type_group_en'].nunique()}개"

    f"\n\n10개 그룹별 행 수:\n"
    f"{group_count}"
)

print(trade_98.columns)


# ============================================================
# 9. 1950~2025 전체 98개국 전처리 데이터 저장
# ============================================================

trade_98.to_csv(
    DATA_RAW + "arms_trade_98_countries_all.csv",
    index=False,
    encoding="utf-8-sig"
)

print(
    f"전체 기간 전처리 데이터 저장 완료"
    f"\narms_trade_98_countries_all.csv"
    f"\n거래 행 수: {len(trade_98)}행"
)




# ============================================================
# 9-1. 주문연도 2021~2025 거래 추출 및 무기명 전처리
# ============================================================

# 주문연도 2021~2025, 주문 TIV가 양수인 유효 거래 추출
order_mask = (
    pd.to_numeric(trade_98["order_year"], errors="coerce").between(2021, 2025)
    & pd.to_numeric(trade_98["tiv_order"], errors="coerce").gt(0)
    & trade_98["weapon"].notna()
)

order_data = trade_98.loc[
    order_mask,
    ["weapon_type_group_en", "weapon", "tiv_order", "comments"]
].copy()

order_data["weapon"] = order_data["weapon"].astype(str).str.strip()
order_data["comments"] = order_data["comments"].fillna("")
order_data["tiv_order"] = pd.to_numeric(order_data["tiv_order"])


# ============================================================
# 9-2. comments에서 엔진 모델명 자동 식별
# ============================================================

# 특정 엔진 모델명은 미리 입력하지 않음
# 일반명으로 기록된 엔진 거래에만 comments 분석 적용
generic_engines = {
    "ship engine",
    "aircraft engine",
    "vehicle engine"
}

# 모델명 표기 차이를 비교하기 위한 정규화
# 예: MT-30, MT30, MT 30 → MT30
def model_key(name):
    return re.sub(r"[^A-Z0-9]", "", str(name).upper())


# 기존 weapon 열에 명시된 엔진 모델명을 자동으로 참고
known_engine_names = (
    trade_98.loc[
        trade_98["weapon_type_group_en"].eq("engines"),
        "weapon"
    ]
    .dropna()
    .astype(str)
    .str.strip()
    .value_counts()
)

engine_alias = {}

for name in known_engine_names.index:
    if name.lower() not in generic_engines:
        engine_alias.setdefault(model_key(name), name)


# 다른 무기그룹에 명시된 모델명을 엔진으로 잘못 식별하지 않도록 검수
other_weapon_keys = set(
    trade_98.loc[
        ~trade_98["weapon_type_group_en"].eq("engines"),
        "weapon"
    ]
    .dropna()
    .map(model_key)
)


# 알파벳과 숫자가 결합된 모델 식별 패턴
# 모델명을 지정하는 것이 아니라 표기 형태를 탐색
model_token = (
    r"(?-i:[A-Z]{1,8})[-/ ]?\d{1,6}"
    r"(?-i:[A-Z]{0,2})"
    r"(?:[-/](?-i:[A-Z0-9]{1,8})){0,2}"
)

# 모델명 뒤에 engine, gas turbine 등의 설명이 오는 경우
model_before = re.compile(
    rf"(?<![\w/-])(?P<model>{model_token})"
    r"(?:\s*\([^()]{1,30}\))?\s+"
    r"(?:(?:marine|naval|aircraft|ship|vehicle|diesel|gas|"
    r"turbofan|turboprop|turbojet)\s+){0,3}"
    r"(?:engines?|turbines?|turbofans?|turboprops?|turbojets?)\b",
    re.IGNORECASE
)

# engine, turbine 등의 설명 뒤에 모델명이 오는 경우
model_after = re.compile(
    rf"\b(?:engines?|turbines?|turbofans?|turboprops?|turbojets?)"
    rf"\s+(?:model\s+|type\s+)?(?P<model>{model_token})\b",
    re.IGNORECASE
)


def extract_engine_model(comment):

    if pd.isna(comment) or not str(comment).strip():
        return None

    candidates = {}

    # comments 전체에서 모델 후보 자동 탐색
    for pattern in (model_before, model_after):
        for match in pattern.finditer(str(comment)):
            model = match.group("model").strip()
            candidates.setdefault(model_key(model), model)

    # 모델을 찾지 못했거나 서로 다른 모델이 여러 개면 추측하지 않음
    if len(candidates) != 1:
        return None

    key, model = next(iter(candidates.items()))

    # 기존 weapon에 같은 모델이 있으면 정식 표기를 우선 사용
    if key in engine_alias:
        return engine_alias[key]

    # 다른 무기그룹 모델과 충돌하면 잘못된 식별 방지
    if key in other_weapon_keys:
        return None

    # 새로운 모델이면 comments에서 추출된 명칭 사용
    return re.sub(
        r"(?<=[A-Za-z])\s+(?=\d)",
        "-",
        model.upper()
    )


# 일반명 엔진 거래만 모델명 자동 추출
is_generic_engine = (
    order_data["weapon_type_group_en"].eq("engines")
    & order_data["weapon"].str.lower().isin(generic_engines)
)

# 기존 weapon에 모델명이 있던 행을 구분
order_data["_from_weapon"] = ~is_generic_engine

order_data.loc[is_generic_engine, "weapon"] = (
    order_data.loc[is_generic_engine, "comments"]
    .map(extract_engine_model)
)

# 자동 식별하지 못한 엔진 거래 확인용 자료
unresolved_engines = order_data.loc[
    is_generic_engine & order_data["weapon"].isna(),
    ["comments", "tiv_order"]
].copy()


# ============================================================
# 9-3. 일반명 제외 및 동일 모델명 통합
# ============================================================

# 기존 TOP 3에서 제외하던 일반명 규칙 유지
exclude_other = (
    order_data["weapon_type_group_en"].eq("other_systems_components")
    & order_data["weapon"].str.lower().eq("air refuel system")
)

order_data = order_data.loc[
    order_data["weapon"].notna()
    & order_data["weapon"].ne("")
    & ~exclude_other
].copy()

# 엔진 모델의 하이픈·공백 표기 차이 통합
order_data["_weapon_key"] = order_data["weapon"]

is_engine = order_data["weapon_type_group_en"].eq("engines")

order_data.loc[is_engine, "_weapon_key"] = (
    order_data.loc[is_engine, "weapon"].map(model_key)
)

# 기존 weapon에 있던 정식 모델명 우선
# comments 추출 모델끼리는 하이픈 표기를 우선
order_data["_has_hyphen"] = (
    order_data["weapon"].str.contains("-", regex=False)
)

display_names = (
    order_data
    .sort_values(
        ["_from_weapon", "_has_hyphen"],
        ascending=[False, False],
        kind="stable"
    )
    .drop_duplicates(["weapon_type_group_en", "_weapon_key"])
    [["weapon_type_group_en", "_weapon_key", "weapon"]]
)


# ============================================================
# 9-4. 무기그룹별 주문 TIV 합산 및 TOP 3 자동 선정
# ============================================================

order_top3_final = (
    order_data
    .groupby(
        ["weapon_type_group_en", "_weapon_key"],
        as_index=False
    )["tiv_order"]
    .sum()
    .merge(
        display_names,
        on=["weapon_type_group_en", "_weapon_key"],
        how="left"
    )
    .sort_values(
        ["weapon_type_group_en", "tiv_order", "weapon"],
        ascending=[True, False, True],
        kind="stable"
    )
)

# 각 무기그룹별 1~3위 순위 자동 부여
order_top3_final["rank"] = (
    order_top3_final
    .groupby("weapon_type_group_en")
    .cumcount() + 1
)

order_top3_final = (
    order_top3_final.loc[
        order_top3_final["rank"] <= 3,
        ["weapon_type_group_en", "rank", "weapon", "tiv_order"]
    ]
    .reset_index(drop=True)
)


# ============================================================
# 9-5. 전처리 완료 TOP 3 CSV 저장 및 검수
# ============================================================

order_top3_final.to_csv(
    DATA_PROCESSED + "arms_trade_98_countries_order_2021_2025.csv",
    index=False,
    encoding="utf-8-sig"
)

print(
    f"TOP 3 전처리 완료"
    f"\n주문연도: 2021~2025"
    f"\n무기그룹 수: {order_top3_final['weapon_type_group_en'].nunique()}개"
    f"\n최종 TOP 3 데이터: {len(order_top3_final)}행"
    f"\n모델 미식별 엔진 거래: {len(unresolved_engines)}행"
)

if not unresolved_engines.empty:
    print(
        "\n[모델 미식별 엔진 거래 - 주문 TIV 상위 15건]\n",
        unresolved_engines
        .sort_values("tiv_order", ascending=False)
        .head(15)
        .to_string(index=False)
    )

print(
    "\n[그룹별 최종 TOP 3]\n",
    order_top3_final.to_string(index=False)
)




# ============================================================
# 10. 인도연도 기준 2016~2025 거래 추출
# ============================================================

# delivery_years 예시
# "2014; 2015; 2016"
#
# 이 중 2016~2025 연도가 하나라도 존재하면
# 해당 거래를 분석용 데이터에 포함

delivery_mask = (
    trade_98["delivery_years"]
    .fillna("")
    .str.split(";")
    .apply(
        lambda years: any(
            2016 <= int(year.strip()) <= 2025
            for year in years
            if year.strip().isdigit()
        )
    )
)

trade_98_16_25 = (
    trade_98[
        delivery_mask
    ]
    .copy()
    .reset_index(drop=True)
)

print(
    f"전체 기간 거래: {len(trade_98)}행"
    f"\n인도연도 2016~2025 거래: "
    f"{len(trade_98_16_25)}행"
)


# ============================================================
# 11. 인도연도 2016~2025 분석용 CSV 저장
# ============================================================

trade_98_16_25.to_csv(
    DATA_PROCESSED + "arms_trade_98_countries.csv",
    index=False,
    encoding="utf-8-sig"
)

print(
    f"2016~2025 분석용 데이터 저장 완료"
    f"\narms_trade_98_countries.csv"
    f"\n거래 행 수: {len(trade_98_16_25)}행"
)

# %%