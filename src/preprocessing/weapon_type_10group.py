# %%
import pandas as pd

DATA = "../../data/processed/"


# ============================================================
# 1. 전체 weapon_type 리스트 불러오기
# ============================================================

weapon_type_10group = pd.read_csv(
    DATA + "weapon_type_list.csv"
)


# ============================================================
# 2. 한국어 / 영어 10개 대분류 확인
# ============================================================

weapon_type_group = [
    "센서·감시정찰(ISR)·위성",
    "방공체계",
    "미사일·유도무기",
    "항공기·무인기",
    "함정",
    "해군용 무기체계",
    "엔진·추진체계",
    "기갑차량",
    "기타 체계·구성품",
    "포병체계"
]

print(weapon_type_group)


weapon_type_group_en = [
    "Sensors / ISR / Satellites",
    "Air defence systems",
    "Missiles & guided weapons",
    "Aircraft & UAVs",
    "Ships",
    "Naval weapons",
    "Engines",
    "Armoured vehicles",
    "Other systems/components",
    "Artillery"
]

print(weapon_type_group_en)


# ============================================================
# 3. 206개 weapon_type → 한국어 / 영어 10개 대분류 매핑
# ============================================================

weapon_type_map = {

    "air-search radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "self-propelled air-defence system": ["방공체계", "Air defence systems"],

    "surface-to-air missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "helicopter": ["항공기·무인기", "Aircraft & UAVs"],

    "anti-ship/land-attack missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "anti-tank/air-to-surface missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "frigate": ["함정", "Ships"],

    "naval gun": ["해군용 무기체계", "Naval weapons"],

    "aircraft engine": ["엔진·추진체계", "Engines"],

    "air/sea-search radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "anti-submarine helicopter": ["항공기·무인기", "Aircraft & UAVs"],

    "fire-control radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "gas turbine": ["엔진·추진체계", "Engines"],

    "armoured personnel carrier": ["기갑차량", "Armoured vehicles"],

    "ship engine": ["엔진·추진체계", "Engines"],

    "anti-submarine sonar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "surface-to-surface missile launcher": ["미사일·유도무기", "Missiles & guided weapons"],

    "transport helicopter": ["항공기·무인기", "Aircraft & UAVs"],

    "anti-submarine torpedo": ["미사일·유도무기", "Missiles & guided weapons"],

    "anti-tank missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "surface-to-air missile system": ["방공체계", "Air defence systems"],

    "armed drone": ["항공기·무인기", "Aircraft & UAVs"],

    "reconnaissance drone": ["항공기·무인기", "Aircraft & UAVs"],

    "combat helicopter": ["항공기·무인기", "Aircraft & UAVs"],

    "surface-to-surface missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "anti-ship torpedo": ["미사일·유도무기", "Missiles & guided weapons"],

    "anti-ship/anti-submarine torpedo": ["미사일·유도무기", "Missiles & guided weapons"],

    "submarine": ["함정", "Ships"],

    "tank": ["기갑차량", "Armoured vehicles"],

    "infantry fighting vehicle turret": ["기타 체계·구성품", "Other systems/components"],

    "minehunter": ["함정", "Ships"],

    "fighter/ground-attack aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "multiple rocket launcher": ["포병체계", "Artillery"],

    "fire-support vehicle": ["기갑차량", "Armoured vehicles"],

    "mortar": ["포병체계", "Artillery"],

    "self-propelled mortar": ["포병체계", "Artillery"],

    "transport aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "air-search system": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "patrol boat": ["함정", "Ships"],

    "long-range air-to-air missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "short-range air-to-air missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "coastal defence system": ["미사일·유도무기", "Missiles & guided weapons"],

    "anti-ship missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "artillery locating radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "mobile surface-to-air missile system": ["방공체계", "Air defence systems"],

    "replenishment ship": ["함정", "Ships"],

    "turbofan": ["엔진·추진체계", "Engines"],

    "light aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "signals intelligence system": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "light transport aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "towed gun": ["포병체계", "Artillery"],

    "light helicopter": ["항공기·무인기", "Aircraft & UAVs"],

    "turbojet": ["엔진·추진체계", "Engines"],

    "(armed) trainer aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "patrol ship": ["함정", "Ships"],

    "air-search/fire-control radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "portable surface-to-air missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "maritime patrol aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "guided bomb": ["미사일·유도무기", "Missiles & guided weapons"],

    "naval surface-to-air missile system": ["해군용 무기체계", "Naval weapons"],

    "destroyer": ["함정", "Ships"],

    "guided glide bomb": ["미사일·유도무기", "Missiles & guided weapons"],

    "amphibious assault ship": ["함정", "Ships"],

    "fighter/ground-attack/electronic warfare aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "guided shell": ["미사일·유도무기", "Missiles & guided weapons"],

    "training ship": ["함정", "Ships"],

    "anti-submarine aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "signals intelligence aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "trainer aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "air refuel system": ["기타 체계·구성품", "Other systems/components"],

    "armoured recovery vehicle": ["기갑차량", "Armoured vehicles"],

    "heavy transport aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "anti-radar missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "air-to-surface missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "trainer/combat aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "infantry fighting vehicle": ["기갑차량", "Armoured vehicles"],

    "self-propelled gun": ["포병체계", "Artillery"],

    "armoured supply vehicle": ["기갑차량", "Armoured vehicles"],

    "vehicle engine": ["엔진·추진체계", "Engines"],

    "armoured engineer vehicle": ["기갑차량", "Armoured vehicles"],

    "armoured bridgelayer": ["기갑차량", "Armoured vehicles"],

    "combat helicopter radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "submarine sonar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "guided rocket": ["미사일·유도무기", "Missiles & guided weapons"],

    "nuclear submarine": ["함정", "Ships"],

    "anti-ballistic missile missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "landing ship": ["함정", "Ships"],

    "anti-aircraft gun": ["방공체계", "Air defence systems"],

    "mortar turret": ["포병체계", "Artillery"],

    "aircraft electro-optical/radar system": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "air-to-surface/surface-to-surface missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "missile boat": ["함정", "Ships"],

    "loitering munition": ["미사일·유도무기", "Missiles & guided weapons"],

    "tank destroyer": ["기갑차량", "Armoured vehicles"],

    "surveillance satellite": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "air-to-surface/anti-ship missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "combat aircraft radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "aircraft electro-optical system": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "corvette": ["함정", "Ships"],

    "maritime patrol aircraft radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "multi-function radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "guided rocket/air-to-surface missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "landing craft": ["함정", "Ships"],

    "turboprop": ["엔진·추진체계", "Engines"],

    "ground surveillance radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "armoured reconnaissance vehicle": ["기갑차량", "Armoured vehicles"],

    "(armed) transport helicopter": ["항공기·무인기", "Aircraft & UAVs"],

    "aircraft reconnaissance system": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "anti-ship helicopter": ["항공기·무인기", "Aircraft & UAVs"],

    "self-propelled anti-aircraft gun": ["방공체계", "Air defence systems"],

    "support ship": ["함정", "Ships"],

    "(armed) light helicopter": ["항공기·무인기", "Aircraft & UAVs"],

    "minehunter/minesweeper": ["함정", "Ships"],

    "electro-optical system": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "armoured engineer/recovery vehicle": ["기갑차량", "Armoured vehicles"],

    "tank chassis": ["기갑차량", "Armoured vehicles"],

    "cargo ship": ["함정", "Ships"],

    "ground surveillance aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "tanker/transport aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "light/trainer aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "air/sea-search/fire-control radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "airborne early-warning aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "anti-ship/anti-radar missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "sea-search radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "ground-attack aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "transport ship": ["함정", "Ships"],

    "patrol ship/transport ship": ["함정", "Ships"],

    "tug": ["함정", "Ships"],

    "anti-ballistic missile system": ["방공체계", "Air defence systems"],

    "airborne early-warning radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "one-way attack drone": ["미사일·유도무기", "Missiles & guided weapons"],

    "armed reconnaissance drone": ["항공기·무인기", "Aircraft & UAVs"],

    "patrol boat/transport craft": ["함정", "Ships"],

    "maritime patrol drone": ["항공기·무인기", "Aircraft & UAVs"],

    "anti-submarine rocket launcher": ["해군용 무기체계", "Naval weapons"],

    "reconnaissance/signals intelligence system": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "anti-submarine/ship torpedo": ["미사일·유도무기", "Missiles & guided weapons"],

    "anti-ship/air-to-ground/surface-to-air missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "anti-aircraft gun system": ["방공체계", "Air defence systems"],

    "tank turret": ["기타 체계·구성품", "Other systems/components"],

    "electro-optical fire-control system": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "anti-ship/air-to surface/surface-to-surface missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "aircraft carrier": ["함정", "Ships"],

    "electronic warfare aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "transport aircraft/helicopter": ["항공기·무인기", "Aircraft & UAVs"],

    "anti-aircraft gun/surface-to-air missile system": ["방공체계", "Air defence systems"],

    "patrol ship/training ship": ["함정", "Ships"],

    "fighter aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "replenishment tanker": ["함정", "Ships"],

    "signals intelligence ship": ["함정", "Ships"],

    "patrol ship/frigate": ["함정", "Ships"],

    "self-propelled gun chassis": ["포병체계", "Artillery"],

    "ground-surveillance radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "amphibious assault ship/frigate": ["함정", "Ships"],

    "midget submarine": ["함정", "Ships"],

    "(armed) reconnaissance drone": ["항공기·무인기", "Aircraft & UAVs"],

    "reconnaissance satellite": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "reconnaissance aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "light tank": ["기갑차량", "Armoured vehicles"],

    "armoured reconnaissance/fire-support vehicle": ["기갑차량", "Armoured vehicles"],

    "multi-role radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],
    
    "armed UGV": ["기갑차량", "Armoured vehicles"],
    # armed UGV는 무장 무인지상차량으로,
    # Type X가 궤도형 무인 전투차량이므로 기갑차량으로 분류
    
    "bomber aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "minesweeper": ["함정", "Ships"],

    "torpedo boat": ["함정", "Ships"],

    "height-finding radar": ["센서·감시정찰(ISR)·위성", "Sensors / ISR / Satellites"],

    "(armed) maritime patrol aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "self-propelled gun turret": ["기타 체계·구성품", "Other systems/components"],

    "cruiser": ["함정", "Ships"],

    "tanker": ["함정", "Ships"],

    "anti-submarine mortar": ["해군용 무기체계", "Naval weapons"],

    "heavy transport helicopter": ["항공기·무인기", "Aircraft & UAVs"],

    "helicopter turret": ["기타 체계·구성품", "Other systems/components"],

    "anti-submarine missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "patrol ship/tug": ["함정", "Ships"],

    "anti-radar/air-to-surface missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "tank destroyer turret": ["기타 체계·구성품", "Other systems/components"],

    "land-attack missile": ["미사일·유도무기", "Missiles & guided weapons"],

    "icebreaker": ["함정", "Ships"],

    "frigate/landing ship": ["함정", "Ships"],

    "minelayer": ["함정", "Ships"],

    "airborne early-warning helicopter": ["항공기·무인기", "Aircraft & UAVs"],

    "naval mine/torpedo": ["해군용 무기체계", "Naval weapons"],

    "airborne early-warning/ground surveillance aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "anti-aircraft gun turret": ["기타 체계·구성품", "Other systems/components"],

    "target tow aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "patrol ship/support ship": ["함정", "Ships"],

    "gunboat": ["함정", "Ships"],

    "armoured personnel carrier/armoured supply vehicle": ["기갑차량", "Armoured vehicles"],

    "signals intelligence helicopter": ["항공기·무인기", "Aircraft & UAVs"],

    "naval multiple rocket launcher": ["해군용 무기체계", "Naval weapons"],

    "support/landing ship": ["함정", "Ships"],

    "corvette/minesweeper": ["함정", "Ships"],

    "transport craft": ["함정", "Ships"],

    "salvage ship": ["함정", "Ships"],

    "support craft": ["함정", "Ships"],

    "reconnaissance/signals intelligence aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "light aircraft/reconnaissance drone": ["항공기·무인기", "Aircraft & UAVs"],

    "survey ship": ["함정", "Ships"],

    "training tank": ["기갑차량", "Armoured vehicles"],

    "transport/trainer aircraft": ["항공기·무인기", "Aircraft & UAVs"],

    "infantry fighting vehicle turret": ["기타 체계·구성품", "Other systems/components"],

    "light transport airship": ["항공기·무인기", "Aircraft & UAVs"],

    "coastal defence gun": ["포병체계", "Artillery"],

    "ship nuclear reactor": ["엔진·추진체계", "Engines"],

    "patrol ship/icebreaker": ["함정", "Ships"],

    "submarine-launched ballistic missile": ["미사일·유도무기", "Missiles & guided weapons"],
  
}


# ============================================================
# 4. weapon_type을 기준으로 한국어 / 영어 분류 2개 열 추가
# ============================================================

weapon_type_10group[
    ["weapon_type_group", "weapon_type_group_en"]
] = weapon_type_10group["weapon_type"].map(
    weapon_type_map
).apply(pd.Series)


# ============================================================
# 5. 영어 10개 대분류를 snake_case로 변경
# ============================================================

group_snake_map = {
    "Sensors / ISR / Satellites": "sensors_isr_satellites",
    "Air defence systems": "air_defence_systems",
    "Missiles & guided weapons": "missiles_guided_weapons",
    "Aircraft & UAVs": "aircraft_uavs",
    "Ships": "ships",
    "Naval weapons": "naval_weapons",
    "Engines": "engines",
    "Armoured vehicles": "armoured_vehicles",
    "Other systems/components": "other_systems_components",
    "Artillery": "artillery"
}

weapon_type_10group["weapon_type_group_en"] = (
    weapon_type_10group["weapon_type_group_en"]
    .replace(group_snake_map)
)

# 최종 영어 10개 그룹 목록도 snake_case로 변경
weapon_type_group_en = list(
    group_snake_map.values()
)


# ============================================================
# 6. 206개가 전부 제대로 매핑됐는지 확인
# ============================================================

print(
    weapon_type_10group[
        ["weapon_type_group", "weapon_type_group_en"]
    ].isna().sum()
)


# ============================================================
# 7. 최종 10개 그룹 및 데이터 확인
# ============================================================

print(weapon_type_group)

print(weapon_type_group_en)

print(weapon_type_10group)


# ============================================================
# 8. 최종 CSV 파일 저장
# ============================================================

# 최초 1번 실행
weapon_type_10group.to_csv(
    DATA + "weapon_type_10group.csv",
    index=False,
    encoding="utf-8-sig"
)

# %%