"""기업·무기체계 공통 데이터 (기업명, 무기체계 분류 영문↔한글, 기업별 강점 분류)

- final_score_1.py의 GROUPS / company_strength와 같은 기준
- 여러 페이지에서 import 해서 사용: from components.company_weapons import ...
"""

# 기업명(한글 표시명) → 기업 코드 (로고 파일명과 동일) — 화면 표시 순서대로
# LIG넥스원은 2026년 3월 사명이 'LIG D&A'로 변경, 코드(lig_nex1)는 로고 파일명 때문에 유지
COMPANIES = {
    "한화에어로스페이스": "hanwha_aerospace",
    "한화오션": "hanwha_ocean",
    "현대로템": "hyundai_rotem",
    "HD현대중공업": "hd_hyundai",
    "LIG D&A": "lig_nex1",
    "한국항공우주산업(KAI)": "kai",
}

# 무기체계 분류: 영문(snake_case) → 한글 (표시 순서 고정)
WEAPON_GROUP_KO = {
    "sensors_isr_satellites": "센서·감시정찰(ISR)·위성",
    "air_defence_systems": "방공체계",
    "missiles_guided_weapons": "미사일·유도무기",
    "aircraft_uavs": "항공기·무인기",
    "ships": "함정",
    "naval_weapons": "해군용 무기체계",
    "engines": "엔진·추진체",
    "armoured_vehicles": "기갑차량",
    "other_systems_components": "기타 체계·구성품",
    "artillery": "포병체계",
}

# 영문 분류 목록 (final_score_1.py의 GROUPS와 동일한 열 구성)
WEAPON_GROUPS = list(WEAPON_GROUP_KO)

# 기업별 강점 분류: primary = 주요 무기체계(1.0), secondary = 보조 무기체계(0.5)
# 리스트 순서 = 표시 우선순위
# 기업 코드는 대시보드(01_main/02_company)의 로고 파일명 기준
#   (final_score_1.py의 hyundai_heavy_industries → hd_hyundai, lig → lig_nex1)
COMPANY_WEAPON_STRENGTH = {
    "hanwha_aerospace": {
        "primary": ["artillery", "armoured_vehicles"],
        "secondary": ["air_defence_systems", "missiles_guided_weapons", "engines"],
    },
    "hanwha_ocean": {
        "primary": ["ships"],
        "secondary": [],
    },
    "hyundai_rotem": {
        "primary": ["armoured_vehicles"],
        "secondary": [],
    },
    "hd_hyundai": {
        "primary": ["ships"],
        "secondary": [],
    },
    "kai": {
        "primary": ["aircraft_uavs"],
        "secondary": ["sensors_isr_satellites"],
    },
    "lig_nex1": {
        "primary": ["missiles_guided_weapons", "air_defence_systems"],
        "secondary": ["sensors_isr_satellites", "naval_weapons"],
    },
}


def get_company_weapons(company_code, top_n=3):
    """기업의 표시용 무기체계 목록: [(영문, 한글, 'primary' 또는 'secondary'), ...]
    주요 → 보조 순서로 이어 붙여 상위 top_n개만 반환"""
    strength = COMPANY_WEAPON_STRENGTH.get(company_code, {})
    rows = [(g, "primary") for g in strength.get("primary", [])]
    rows += [(g, "secondary") for g in strength.get("secondary", [])]
    return [(g, WEAPON_GROUP_KO[g], level) for g, level in rows[:top_n]]
