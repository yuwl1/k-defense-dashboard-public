# %%
import pandas as pd

DATA_RAW = "../../data/raw/"
DATA_PROCESSED = "../../data/processed/"

trade_98 = pd.read_csv(
    DATA_RAW + "arms_trade_98_countries_all.csv"
)


# ============================================================
# 1. 한국이 수출한 데이터만 추출
# ============================================================

korea_weapon_data = trade_98[
    trade_98["supplier_iso_a3"] == "KOR"
].copy()


# ============================================================
# 2. 한국 수출 데이터에서 무기 리스트 생성
# ============================================================

korea_weapon_list = korea_weapon_data[
    ["weapon", "status"]
].copy()


# 같은 weapon이 여러 번 있는지 확인
print(
    korea_weapon_list[
        korea_weapon_list.duplicated(
            subset=["weapon"],
            keep=False
        )
    ].sort_values("weapon")
)

korea_weapon_list = (
    korea_weapon_list
    .reset_index(drop=True)
)


# status 종류 확인
status_list = (
    korea_weapon_list["status"]
    .drop_duplicates()
)

print(status_list.to_string(index=False))


# 무기 + 상태 중복 제거
korea_weapon_list = (
    korea_weapon_list
    .drop_duplicates(
        subset=["weapon", "status"]
    )
    .reset_index(drop=True)
)


# ============================================================
# 3. 무기명 → 기업 매핑
# ============================================================

company_map = {
    "K-9 Thunder 155mm": "Hanwha Aerospace",
    "K-10": "Hanwha Aerospace",
    "K-21": "Hanwha Aerospace",
    "KLTV": "Kia",
    "C-STAR": "LIG Nex1",
    "STX-250t": "K Shipbuilding",
    "Po Hang": "Government of the Republic of Korea",
    "Haeuri": "Government of the Republic of Korea",
    "K-11": "SNT Motiv",
    "KF-21 Boramae": "KAI",
    "Type-209/1400": "Hanwha Ocean",
    "Chiron": "LIG Nex1",
    "LPD-122m": "Dae Sun Shipbuilding & Engineering",
    "KT-1 Woongbi": "KAI",
    "T-50 Golden Eagle": "KAI",
    "Promoter": "Daeji P&I",
    "Cheongung": "LIG Nex1",
    "Hughes-500D/MD": "Korean Air",
    "Gagah Samudera": "Hanwha Ocean",
    "FA-50 Block-20": "KAI",
    "Aotearoa": "HD Hyundai Heavy Industries",
    "Sea Dolphin": "Korea Tacoma",
    "HDL-1500": "HD Hyundai Heavy Industries",
    "HDF-3600": "HD Hyundai Heavy Industries",
    "HDP-2200": "HD Hyundai Heavy Industries",
    "K-808 White Tiger": "Hyundai Rotem",
    "HDS-1500": "HD Hyundai Heavy Industries",
    "LCU-1610": "Korea Tacoma",
    "FA-50": "KAI",
    "K-745 Blue Shark": "LIG Nex1",
    "AAV-7A1": "Hanwha Aerospace",
    "HHI-2600": "HD Hyundai Heavy Industries",
    "HDC-3200": "HD Hyundai Heavy Industries",
    "HHI-2400": "HD Hyundai Heavy Industries",
    "K-9": "Hanwha Aerospace",
    "K-2 Black Panther": "Hyundai Rotem",
    "K-239 Chunmoo": "Hanwha Aerospace",
    "CTM-290 KTSSM": "Hanwha Aerospace",
    "CGR-080 239mm": "Hanwha Aerospace",
    "K-2 BL": "Hyundai Rotem",
    "K-2 ARV": "Hyundai Rotem",
    "K-2 AEV": "Hyundai Rotem",
    "KGGB": "LIG Nex1",
    "AT-1K Raybolt": "LIG Nex1",
    "LOGIR": "LIG Nex1",
    "Tigon": "Hyundai Rotem",
    "DW-3000": "Hanwha Ocean",
    "vehicle engine": "HD Hyundai Infracore",
    "Tide": "Hanwha Ocean",
    "Boeing-747-8": "Korean Air",
    "Delos": "HD Hyundai Heavy Industries",
    "Sea Dragon": "HD Hyundai Heavy Industries",
    "DW-2000H": "Hanwha Ocean",
    "KH-178 105mm": "Hyundai WIA",
    "Donghae": "Government of the Republic of Korea",
    "PSMM-5": "Korea Tacoma",
    "Alligator": "Korea Tacoma",
    "Dong Yang-6": "Dae Sun Shipbuilding & Engineering",
    "Barracuda": "Hanwha Aerospace",
    "LVTP-7": "Government of the Republic of Korea",
    "Black Fox": "Hanwha Aerospace",
    "KH-179 155mm": "Hyundai WIA",
    "Sukhanya": "Korea Tacoma",
    "Hanwha-70 70mm": "Hanwha Aerospace",
    "Musytari": "Korea Shipbuilding & Engineering Corporation",
    "K-200 KIFV": "Hanwha Aerospace",
    "Endeavour": "HD Hyundai Heavy Industries",
    "A-37B Dragonfly": "Government of the Republic of Korea",
    "Haksaeng": "Government of the Republic of Korea",
    "F-5A Freedom Fighter": "Government of the Republic of Korea",
    "Cessna-172": "Government of the Republic of Korea",
    "Hawk-50": "Government of the Republic of Korea",
    "CTM-MR": "Hanwha Aerospace",
    "CTM-500": "Hanwha Aerospace",
    "AEGIR-18R": "Hanwha Ocean",
    "M-114 155mm": "Government of the Republic of Korea",
    "M-101A1 105mm": "Government of the Republic of Korea",
    "M-30 107mm": "Government of the Republic of Korea",
}


# company 열 추가
korea_weapon_list["company"] = (
    korea_weapon_list["weapon"]
    .map(company_map)
)

# ============================================================
# 3-1. 기업 미매핑 무기 확인
# ============================================================

unmapped_weapon = (
    korea_weapon_list[
        korea_weapon_list["company"].isna()
    ]
    .reset_index(drop=True)
)

print(
    f"한국 수출 무기·상태 조합: {len(korea_weapon_list)}개"
    f"\n기업 미매핑: {len(unmapped_weapon)}개"
    f"\n\n{unmapped_weapon.to_string(index=False)}"
)

# 미매핑 확인 후에도 아래 코드 계속 실행
if len(unmapped_weapon) > 0:
    raise ValueError(
        f"기업 미매핑 무기가 {len(unmapped_weapon)}개 있습니다. "
        f"company_map을 먼저 보완해주세요."
    )
    
    
# ============================================================
# 4. 최종 사용할 6개 기업 지정
# ============================================================

target_companies = [
    "Hanwha Aerospace",
    "Hanwha Ocean",
    "LIG Nex1",
    "KAI",
    "HD Hyundai Heavy Industries",
    "Hyundai Rotem"
]


# ============================================================
# 5. 무기 + 상태 → 주석 매핑
# ============================================================

note_map = {

    # ============================================================
    # 동일 무기에 신품·중고 거래가 모두 존재
    # ============================================================

    ("K-9 Thunder 155mm", "New"):
        "동일 무기명에 신품·중고 거래가 모두 존재; 해당 행은 신품 거래",

    ("K-9 Thunder 155mm", "Second hand"):
        "동일 무기명에 신품·중고 거래가 모두 존재; 해당 행은 중고 거래",

    ("C-STAR", "New"):
        "동일 무기명에 신품·중고 거래가 모두 존재; 해당 행은 신품 거래",

    ("C-STAR", "Second hand"):
        "동일 무기명에 신품·중고 거래가 모두 존재; 해당 행은 중고 거래",


    # ============================================================
    # 한국 정부의 중고·원조 이전 거래
    # ============================================================

    ("Po Hang", "Second hand"):
        "한국 해군 보유 함정의 중고 이전 거래; "
        "기업의 신품 판매가 아니므로 대한민국 정부 이전으로 매핑",

    ("Haeuri", "Second hand"):
        "한국 해군 보유 함정의 중고 이전 거래; "
        "기업의 신품 판매가 아니므로 대한민국 정부 이전으로 매핑",

    ("Sea Dolphin", "Second hand"):
        "한국 측 보유 함정의 중고 이전 거래; "
        "기업의 신품 판매가 아닌 국가 간 이전 거래",

    ("LCU-1610", "Second hand"):
        "한국 측 보유 함정의 중고 이전 거래; "
        "기업의 신품 판매가 아닌 국가 간 이전 거래",

    ("Donghae", "Second hand"):
        "SIPRI 거래 주석의 'Colombian designation Narino'를 단서로 "
        "콜롬비아 ARC Narino로 이전된 전 한국 해군 함정으로 확인; "
        "중고·원조 거래이므로 대한민국 정부 이전으로 매핑",

    ("LVTP-7", "Second hand"):
        "SIPRI 거래 주석에 'Second-hand; LVTP-7A1 version; aid'로 기록; "
        "한국이 미국에서 도입해 운용하던 장비의 중고 원조 거래이므로 "
        "대한민국 정부 이전으로 매핑",

    ("A-37B Dragonfly", "Second hand"):
        "SIPRI 거래 주석에 'Second-hand; aid'로 기록; "
        "한국 공군이 운용하던 미국산 A-37B의 중고·원조 이전 거래이므로 "
        "대한민국 정부 이전으로 매핑",

    ("Haksaeng", "Second hand"):
        "SIPRI 거래 주석의 'Philippine designation Yap'을 단서로 "
        "필리핀에 이전된 전 한국 해군 Haksaeng급으로 확인; "
        "중고 국가 간 이전 거래이므로 대한민국 정부 이전으로 매핑",

    ("F-5A Freedom Fighter", "Second hand"):
        "SIPRI 거래 주석에 'Second-hand; aid'로 기록; "
        "한국 공군이 운용하던 미국산 F-5A의 중고·원조 이전 거래이므로 "
        "대한민국 정부 이전으로 매핑",

    ("Cessna-172", "Second hand"):
        "SIPRI 거래 주석의 'T-41D version'을 단서로 해당 기체를 확인; "
        "한국이 미국에서 도입해 운용하던 항공기의 중고 이전 거래이므로 "
        "대한민국 정부 이전으로 매핑",

    ("Hawk-50", "Second hand"):
        "SIPRI 한국 도입 거래의 'Hawk Mk-67 version'과 "
        "미국 수출 거래의 'US company for training'을 대조해 "
        "한국 공군 T-59(Hawk Mk.67)의 중고 이전 거래로 확인; "
        "대한민국 정부 이전으로 매핑",
    
    ("M-114 155mm", "Second hand"):
    "미국 제조 장비의 중고 이전 거래; "
    "한국 제조기업의 판매가 아닌 대한민국 정부 거래로 추정하여 매핑",

    ("M-101A1 105mm", "Second hand"):
        "미국 제조 장비의 중고 이전 거래; "
        "한국 제조기업의 판매가 아닌 대한민국 정부 거래로 추정하여 매핑",

    ("M-30 107mm", "Second hand"):
        "미국 제조 장비의 중고 이전 거래; "
        "한국 제조기업의 판매가 아닌 대한민국 정부 거래로 추정하여 매핑",


    # ============================================================
    # 제조사와 실제 거래주체가 다른 경우
    # ============================================================

    ("Hughes-500D/MD", "Second hand"):
        "원제조사와 해당 거래의 한국 측 거래주체가 다름; "
        "한국 측 거래주체 기준 Korean Air로 매핑",

    ("Boeing-747-8", "Second hand"):
        "원제조사와 해당 거래의 한국 측 거래주체가 다름; "
        "한국 측 거래주체 기준 Korean Air로 매핑",
    
    ("AEGIR-18R", "New"):
    "AEGIR-18R 건조계약 관련 거래주체로 Hanwha Ocean을 매핑; "
    "Hanwha Ocean이 해당 장비의 제조사라는 의미는 아님",


    # ============================================================
    # SIPRI 거래 주석을 단서로 실제 모델·명칭 확인
    # ============================================================

    ("vehicle engine", "New"):
        "SIPRI 거래 주석에서 실제 모델이 Hyundai Infracore "
        "DV-27K (1500hp) 디젤엔진으로 확인되어 "
        "HD Hyundai Infracore로 매핑",

    ("Tide", "New"):
        "SIPRI 거래 주석에서 영국 명칭이 Tide-class로 확인되어 "
        "해당 함정을 특정한 뒤 Hanwha Ocean으로 매핑",

    ("Delos", "New"):
        "SIPRI 거래 주석의 'Australian designation Sirius'를 단서로 "
        "HMAS Sirius의 전신 MV Delos로 확인; "
        "당시 Hyundai Mipo Dockyard 건조이며 "
        "현재 기업 기준 HD Hyundai Heavy Industries로 매핑",

    ("Sea Dragon", "New"):
        "SIPRI 거래 주석의 'Bangladeshi designation Madhumati'를 단서로 "
        "BNS Madhumati로 확인; "
        "당시 Hyundai Heavy Industries 건조로 확인되어 "
        "HD Hyundai Heavy Industries로 매핑",

    ("DW-2000H", "New"):
        "SIPRI 거래 주석의 'Bangladeshi designation Bangabandhu'를 단서로 "
        "BNS Bangabandhu로 확인; "
        "당시 Daewoo Shipbuilding & Marine Engineering 건조이며 "
        "현재 기업 기준 Hanwha Ocean으로 매핑",

    ("PSMM-5", "New"):
        "SIPRI 거래 주석의 'Indonesian designation Mandau'를 단서로 "
        "Mandau급 미사일정으로 확인; "
        "Korea Tacoma Marine Industries 건조로 확인되어 매핑",

    ("Alligator", "New"):
        "SIPRI 거래 주석의 'Teluk Semangka' 및 'Capana' 명칭을 단서로 "
        "해당 상륙함 계열을 확인; "
        "Korea Tacoma 건조로 확인되어 매핑",

    ("Dong Yang-6", "Second hand but modernized"):
        "SIPRI 거래 주석의 'Indonesian designation Kambani'를 단서로 "
        "KRI Tanjung Kambani로 확인; "
        "원래 타국 건조 민간선이며 Dae Sun Shipbuilding & Engineering에서 "
        "군용 수송함으로 개조·현대화하여 개조 수행 기업 기준으로 매핑",

    ("Black Fox", "New"):
        "SIPRI 거래 주석의 'Tarantula version'을 단서로 "
        "인도네시아 수출형 Tarantula 6x6로 확인; "
        "당시 Doosan DST 계열 제품이며 "
        "현재 기업 기준 Hanwha Aerospace로 매핑",

    ("K-200 KIFV", "New"):
        "SIPRI 거래 주석의 말레이시아 명칭 'MIFV'와 거래연도를 대조해 "
        "해당 K-200 수출 거래를 확인; "
        "당시 Daewoo 계열 생산품이며 기업 계보상 "
        "현재 Hanwha Aerospace로 매핑",


    # ============================================================
    # 과거 제조기업 → 현재 기업 계보 기준 매핑
    # ============================================================

    ("Barracuda", "New"):
        "당시 Daewoo Heavy Industries 계열에서 개발·생산 후 "
        "Doosan Infracore·Doosan DST로 이어진 장비; "
        "기업 계보상 현재 Hanwha Aerospace로 매핑",

    ("KH-178 105mm", "New"):
        "KH-178 제조기업 계보가 Kia 계열 → WIA → Hyundai WIA로 이어져 "
        "현재 기업 기준 Hyundai WIA로 매핑; "
        "일부 SIPRI 거래는 중고 M-101A1 개조 가능성이 기록되어 있음",

    ("KH-179 155mm", "Second hand"):
        "KH-179 제조기업 계보가 Kia 계열 → WIA → Hyundai WIA로 이어져 "
        "현재 기업 기준 Hyundai WIA로 매핑; "
        "해당 SIPRI 거래 자체는 중고 거래",

    ("Hanwha-70 70mm", "New"):
        "당시 Hanwha Corporation 방산부문 제품으로 확인; "
        "방산부문 기업 계보상 현재 Hanwha Aerospace로 매핑",


    # ============================================================
    # 건조사·제조사 외부 자료 확인
    # ============================================================

    ("Sukhanya", "New"):
        "SIPRI 거래 주석상 일부 인도 현지 면허생산이 포함됨; "
        "한국 건조분의 건조사를 Korea Tacoma로 확인하여 매핑",

    ("Musytari", "New"):
        "말레이시아 해군 자료에서 KD Musytari의 건조사를 "
        "Korea Shipbuilding Engineering Corporation으로 확인하여 매핑",

    ("Endeavour", "New"):
        "뉴질랜드 해군 HMNZS Endeavour로 확인; "
        "당시 Hyundai Heavy Industries가 건조·인도한 함정으로 확인되어 "
        "현재 HD Hyundai Heavy Industries로 매핑"
}


# note 열 추가
korea_weapon_list["note"] = (
    korea_weapon_list.apply(
        lambda row: note_map.get(
            (
                row["weapon"],
                row["status"]
            )
        ),
        axis=1
    )
)


# ============================================================
# 6. 한국 수출 전체 거래 데이터에 기업 매핑
# ============================================================

weapon_idx = korea_weapon_data.columns.get_loc(
    "weapon"
)

korea_weapon_data.insert(
    weapon_idx + 1,
    "company",
    korea_weapon_data["weapon"].map(
        company_map
    )
)


# ============================================================
# 7. 한국 수출 거래에서 최종 6개 기업만 남기기
# ============================================================

korea_weapon_data = korea_weapon_data[
    korea_weapon_data["company"].isin(
        target_companies
    )
].copy()

korea_weapon_data = (
    korea_weapon_data
    .reset_index(drop=True)
)


# ============================================================
# 8. 최종 검수
# ============================================================

print(korea_weapon_list)

# 기업 매핑되지 않은 무기 확인
print(
    korea_weapon_list[
        korea_weapon_list["company"].isna()
    ].to_string(index=False)
)

# 최종 6개 기업 확인
print(
    korea_weapon_data["company"]
    .value_counts()
)

print(
    "최종 한국 수출 거래 행 수:",
    len(korea_weapon_data)
)


# ============================================================
# 9. 최종 CSV 파일 저장
# ============================================================

# 한국 수출 전체 무기 + 기업 매핑 참고용 리스트
# 6개 기업 외의 기업도 그대로 보존
korea_weapon_list.to_csv(
    DATA_PROCESSED + "korea_weapon_company_list.csv",
    index=False,
    encoding="utf-8-sig"
)

# 최종 6개 기업 거래만 저장
korea_weapon_data.to_csv(
    DATA_PROCESSED + "korea_weapon_data.csv",
    index=False,
    encoding="utf-8-sig"
)

# %%