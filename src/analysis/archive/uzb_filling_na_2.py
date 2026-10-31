#%%
import numpy as np
import pandas as pd
import requests

df_final_score1 = pd.read_csv('../../data/processed/final_score_1.csv')

# 1. 세계은행 API 데이터 수집 함수 (국가 코드 및 지표 지정)
def get_wb_data(country, indicator):
    url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?date=2016:2025&format=json"
    res = requests.get(url).json()
    data = {}
    if len(res) > 1 and res[1]:
        for row in res[1]:
            if row["value"] is not None:
                data[int(row["date"])] = float(row["value"])
    return data

# 우즈베키스탄: (1) 실질 GDP 성장률(%), (2) 명목 GDP(Current USD)
growth_raw = get_wb_data("UZB", "NY.GDP.MKTP.KD.ZG")
gdp_nominal_raw = get_wb_data("UZB", "NY.GDP.MKTP.CD")

growth_raw
gdp_nominal_raw
#%%
# 미국: 달러 가치 환산을 위한 미국 GDP 디플레이터 (CPI를 원할 경우 "FP.CPI.TOTL" 사용)
us_deflator_raw = get_wb_data("USA", "NY.GDP.DEFL.ZS")

us_deflator_raw
#%%
growth_dict = {
    yr: (growth_raw[yr] / 100.0) if yr in growth_raw else None
    for yr in range(2016, 2026)
}

# 2. 2018년 실측치 추출 (df_final_score1 기준)
m_2018 = df_final_score1.loc[
    (df_final_score1["iso_a3"] == "UZB") & (df_final_score1["year"] == 2018),
    "military_expenditure_usd",
].values[0]

pct_2018 = df_final_score1.loc[
    (df_final_score1["iso_a3"] == "UZB") & (df_final_score1["year"] == 2018),
    "military_expenditure_gdp_pct",
].values[0]

uzb_milex = {}
uzb_pct = {}

# 3. 2016~2018년: 실질 성장률 역산 및 2018년 GDP 대비 국방비 비율 유지
uzb_milex[2018] = m_2018
uzb_milex[2017] = uzb_milex[2018] / (1.0 + growth_dict[2018])
uzb_milex[2016] = uzb_milex[2017] / (1.0 + growth_dict[2017])

uzb_pct[2016] = pct_2018
uzb_pct[2017] = pct_2018
uzb_pct[2018] = pct_2018

# 4. 2020~2025년: 2020-2024 명목 GDP 산술평균 대비 2,800백만 달러 비율 적용 및 2024 달러 가치 변환
idx_2020_2024 = [2020, 2021, 2022, 2023, 2024]

# 2020-2024 명목 GDP 산술평균 계산
gdp_nom_2020_2024_mean = np.mean([gdp_nominal_raw[yr] for yr in idx_2020_2024])

# KIET 이슈페이퍼 2020-2024 평균 국방비 (2,800백만 달러)
target_avg_milex = 2800 * (10 ** 6)

# 2020-2024 평균 GDP 대비 국방비 비율 산출 (소수 비율 및 퍼센트 비중)
avg_milex_ratio_2020_2024 = target_avg_milex / gdp_nom_2020_2024_mean
pct_2020_2024 = avg_milex_ratio_2020_2024 * 100.0

# 2024년 기준 미국 물가지수 (기준점)
deflator_2024 = us_deflator_raw[2024]

for yr in range(2020, 2026):
    # (a) 2020~2025년 GDP 대비 국방비 비율(%)은 2020-2024 평균 비율 그대로 사용
    uzb_pct[yr] = pct_2020_2024
    
    # (b) 해당 연도 명목 GDP에 비율을 곱해 당해연도 명목 달러(Current USD) 기준 국방비 산출

    nom_gdp_yr = gdp_nominal_raw.get(yr)

        
    milex_current_usd = nom_gdp_yr * avg_milex_ratio_2020_2024
    
    # (c) 미국 달러 가치 비율(D_2024 / D_yr)을 곱해 2024년 기준 달러(current2024)로 단위 변환
    deflator_yr = us_deflator_raw.get(yr)
    usd_to_2024_factor = deflator_2024 / deflator_yr
    
    uzb_milex[yr] = milex_current_usd * usd_to_2024_factor

# 5. 2019년: GDP 대비 비율은 2018년치 유지, 국방비 지출은 2018년치와 2020년치(2024 달러 기준)의 산술평균
uzb_pct[2019] = pct_2018
uzb_milex[2019] = (uzb_milex[2018] + uzb_milex[2020]) / 2.0

# 6. 최종 데이터프레임 생성
uzb_patch_list = []
for yr in range(2016, 2026):
    uzb_patch_list.append({
        "iso_a3": "UZB",
        "year": yr,
        "military_expenditure_usd": uzb_milex[yr],
        "military_expenditure_gdp_pct": uzb_pct[yr],
    })

df_patch_uzb = pd.DataFrame(uzb_patch_list)
print(df_patch_uzb)