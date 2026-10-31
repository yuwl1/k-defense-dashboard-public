# %%
import pandas as pd
import numpy as np
# %%
df_score = pd.read_csv('../../data/processed/final_score_1.csv')
df_score
# %%

# %%

excelfile_path = '../../data/raw/sipri_milex.xlsx'
xls = pd.ExcelFile(excelfile_path)
print(xls.sheet_names)
# %%

df_gdp = pd.read_excel(excelfile_path, sheet_name="Share of GDP", header=5)


qatar_data = df_gdp[df_gdp["Country"].astype(str).str.strip().str.lower() == "qatar"]

print(qatar_data)
# %%
qatar_data[[2021, 2022]]
# %%
df_currentus = pd.read_excel(excelfile_path, sheet_name="Current US$", header=5)
qatar_data2 = df_currentus[df_currentus["Country"].astype(str).str.strip().str.lower() == "qatar"]

qatar_data_milex = qatar_data2[[2021, 2022]] * 10**6
qatar_data_milex
# %%
qatar_data_milex.sum(axis=1)
# %%
qatar2021_gdp = qatar_data2[2021] * 10**6 / qatar_data[2021]
# %%
qatar2022_gdp = qatar_data2[2022] * 10**6 / qatar_data[2022]

# %%
average_ratio = (qatar_data_milex.sum(axis=1) / (qatar2021_gdp + qatar2022_gdp)).values[0]
average_ratio
# %%
import pandas as pd
import requests

# 1. 세계은행 API 파라미터 설정
country = "QAT"  # 카타르 ISO-3 코드
indicator = "NY.GDP.MKTP.CD"  # 명목 GDP 지표 코드
start_year = 2016
end_year = 2025

# 세계은행 API 엔드포인트 (format=json 필수)
url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
params = {"date": f"{start_year}:{end_year}", "format": "json", "per_page": 100}

# 2. 데이터 요청
response = requests.get(url, params=params)
data = response.json()

# 세계은행 응답 구조: data[0]은 메타데이터 페이지 정보, data[1]에 실제 레코드 리스트가 들어있음
records = data[1]

# 3. 데이터 파싱 및 2021, 2022 제외
parsed_data = []
exclude_years = {2021, 2022}

for row in records:
    year = int(row["date"])
    if year in exclude_years:
        continue  # 2021, 2022 건너뛰기

    parsed_data.append(
        {
            "iso_a3": row["countryiso3code"],
            "year": year,
            "nominal_gdp_usd": row[
                "value"
            ],  # 명목 GDP (단위: 달러, 미집계 연도는 None)
        }
    )

# 4. 데이터프레임 변환 및 연도순 정렬
df_qatar_gdp = (
    pd.DataFrame(parsed_data).sort_values("year").reset_index(drop=True)
)

print(df_qatar_gdp)
# %%
average_ratio.info()
# %%
df_qatar_gdp['mil_ex_cur'] = df_qatar_gdp['nominal_gdp_usd'] * average_ratio
df_qatar_gdp
# %%
import numpy as np
import pandas as pd
import requests

# 1. 세계은행 API에서 카타르 GDP 디플레이터(NY.GDP.DEFL.ZS) 수집
country = "QAT"
indicator = "NY.GDP.DEFL.ZS"
url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
params = {"date": "2016:2025", "format": "json", "per_page": 100}

res = requests.get(url, params=params).json()

# 2. 연도별 디플레이터 딕셔너리 구성 {연도: 디플레이터값}
defl_dict = {}
for row in res[1]:
    year = int(row["date"])
    defl_dict[year] = row["value"]

# 3. 기준 연도(2024년) 디플레이터 값 확보 (미발표 결측 대비 fallback 포함)
deflator_2024 = defl_dict.get(2024)

# if deflator_2024 is None or pd.isna(deflator_2024):
#     # 세계은행 집계 지연으로 2024년이 비어있을 경우 가장 최근 유효 연도(2023)에 연 2.5% 상승률 반영
#     valid_years = [y for y, v in defl_dict.items() if v is not None]
#     latest_year = max(valid_years)
#     deflator_2024 = defl_dict[latest_year] * (1.025 ** (2024 - latest_year))
#     print(
#         f"※ 안내: 2024년 디플레이터 미발표로 {latest_year}년 기준 추정치({deflator_2024:.2f})를 사용합니다."
#     )
# else:
    # print(f"2024년 기준 디플레이터: {deflator_2024:.2f}")

print(f"2024년 기준 디플레이터: {deflator_2024:.2f}")
# 4. df_qatar_gdp에 연도별 디플레이터 매핑
df_qatar_gdp["deflator"] = df_qatar_gdp["year"].map(defl_dict)

# 디플레이터 결측 연도(예: 2025년 등)는 직전 연도 디플레이터 기준으로 보간
# df_qatar_gdp["deflator"] = (
#     df_qatar_gdp["deflator"]
#     .ffill()
#     .bfill()
#     .fillna(deflator_2024)
# )

# 5. Constant (2024) US$ 변환 공식 적용
# 공식: 실질 국방비 = 명목 국방비 * (2024년 물가지수 / 당해연도 물가지수)
df_qatar_gdp["constant_2024_milex_usd"] = df_qatar_gdp["mil_ex_cur"] * (
    deflator_2024 / df_qatar_gdp["deflator"]
)

df_qatar_gdp
# %%
df_qatar_gdp['military_expenditure_gdp_pct'] = average_ratio * 100
df_qatar_gdp= df_qatar_gdp.rename(columns={'constant_2024_milex_usd' : 'military_expenditure_usd'})
df_qatar_gdp
# %%
df_qatar_gdp = df_qatar_gdp[['iso_a3', 'year', 'military_expenditure_usd', 'military_expenditure_gdp_pct']]
df_qatar_gdp
# %%
df_qatar_gdp
# %%
import pandas as pd
import requests

# 1. API 요청 설정 (UAE 국가 코드: ARE, 명목 GDP 지표: NY.GDP.MKTP.CD)
country = "ARE"
indicator = "NY.GDP.MKTP.CD"
url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
params = {"date": "2016:2025", "format": "json", "per_page": 100}

# 2. 데이터 호출 및 파싱
response = requests.get(url, params=params)
data = response.json()

records = []
if len(data) > 1 and data[1]:
    for row in data[1]:
        records.append(
            {
                "iso_a3": row["countryiso3code"],
                "year": int(row["date"]),
                "nominal_gdp_usd": row[
                    "value"
                ],  # 당해연도 명목 GDP (달러 단위)
            }
        )

# 3. 데이터프레임 변환 및 연도순(오름차순) 정렬
df_uae_gdp = (
    pd.DataFrame(records).sort_values("year").reset_index(drop=True)
)

df_uae_gdp.iloc[9, 2] = df_uae_gdp.iloc[8, 2]
df_uae_gdp
# %%
df_uae_gdp.iloc[4:9, 2].mean()
# %%
average_ratio_uae_pct = 23900000000 / df_uae_gdp.iloc[4:9, 2].mean() * 100
average_ratio_uae_pct
# %%
df_uae_gdp['cur_mil_ex'] = df_uae_gdp['nominal_gdp_usd'] * average_ratio_uae_pct / 100
df_uae_gdp
# %%
df_uae_gdp['military_expenditure_gdp_pct'] = average_ratio_uae_pct
df_uae_gdp
# %%
import pandas as pd
import requests

# 1. 세계은행 API에서 UAE GDP 디플레이터(NY.GDP.DEFL.ZS) 수집
country = "ARE"
indicator = "NY.GDP.DEFL.ZS"
url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
params = {"date": "2016:2025", "format": "json", "per_page": 100}

res = requests.get(url, params=params).json()

# 2. 연도별 디플레이터 딕셔너리 구성 {연도: 값}
defl_dict = {}
if len(res) > 1 and res[1]:
    for row in res[1]:
        defl_dict[int(row["date"])] = row["value"]

# 3. df_uae_gdp에 디플레이터 매핑 및 2024년 기준값 추출
df_uae_gdp["deflator"] = df_uae_gdp["year"].map(defl_dict)

# 2024년 디플레이터 값을 꺼내서 2025년 행에 대입
df_uae_gdp.loc[df_uae_gdp['year'] == 2025, 'deflator'] = (
    df_uae_gdp.loc[df_uae_gdp['year'] == 2024, 'deflator'].values[0]
)

deflator_2024 = defl_dict[2024]

# 4. Constant 2024 US$ 기준 국방비 계산
# 공식: 당해연도 명목 국방비 * (2024년 디플레이터 / 당해연도 디플레이터)
df_uae_gdp["military_expenditure_usd"] = df_uae_gdp["cur_mil_ex"] * (
    deflator_2024 / df_uae_gdp["deflator"]
)

df_uae_gdp
# %%
df_uae_gdp = df_uae_gdp[['iso_a3', 'year', 'military_expenditure_usd', 'military_expenditure_gdp_pct']]
df_uae_gdp
# %%
import pandas as pd
import requests

# # 1. API 요청 설정 (UAE 국가 코드: ARE, 명목 GDP 지표: NY.GDP.MKTP.CD)
# country = "UZB"
# indicator = "NY.GDP.MKTP.CD"
# url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
# params = {"date": "2016:2025", "format": "json", "per_page": 100}

# # 2. 데이터 호출 및 파싱
# response = requests.get(url, params=params)
# data = response.json()

# records = []
# if len(data) > 1 and data[1]:
#     for row in data[1]:
#         records.append(
#             {
#                 "iso_a3": row["countryiso3code"],
#                 "year": int(row["date"]),
#                 "nominal_gdp_usd": row[
#                     "value"
#                 ],  # 당해연도 명목 GDP (달러 단위)
#             }
#         )

# # 3. 데이터프레임 변환 및 연도순(오름차순) 정렬
# df_uzb_gdp = (
#     pd.DataFrame(records).sort_values("year").reset_index(drop=True)
# )

# # df_uzb_gdp.iloc[9, 2] = df_uae_gdp.iloc[8, 2]
# df_uzb_gdp
# # %%
# df_uzb_gdp = df_uzb_gdp[df_uzb_gdp['year'] != 2018].reset_index(drop=True)
# df_uzb_gdp
# # %%
# df_uzb_gdp.iloc[3:8, 2].mean()
# # %%
# average_ratio_uzb_pct = 2800000000 / df_uzb_gdp.iloc[3:8, 2].mean() * 100
# average_ratio_uzb_pct 
# # %%
# df_uzb_gdp['military_expenditure_gdp_pct'] = average_ratio_uzb_pct
# df_uzb_gdp
# # %%
# df_uzb_gdp['cur_mil_ex'] = df_uzb_gdp['nominal_gdp_usd'] * average_ratio_uzb_pct / 100
# df_uzb_gdp
# # %%
# import pandas as pd
# import requests

# # 1. 세계은행 API에서 우즈베키스탄 GDP 디플레이터(NY.GDP.DEFL.ZS) 요청
# country = "UZB"
# indicator = "NY.GDP.DEFL.ZS"
# url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
# params = {"date": "2016:2025", "format": "json", "per_page": 100}

# res = requests.get(url, params=params).json()

# # 2. 연도별 디플레이터 딕셔너리 구성 {연도: 값}
# defl_dict = {}
# if len(res) > 1 and res[1]:
#     for row in res[1]:
#         defl_dict[int(row["date"])] = row["value"]

# # 3. df_uzb_gdp에 디플레이터 매핑 및 2024년 기준값 확보
# df_uzb_gdp["deflator"] = df_uzb_gdp["year"].map(defl_dict)
# deflator_2024 = defl_dict.get(2024)

# # 2025년 디플레이터가 아직 미발표(NaN)라면 직전 연도(2024년) 값으로 보충
# # df_uzb_gdp["deflator"] = df_uzb_gdp["deflator"].ffill()

# # 4. Constant 2024 US$ 기준 국방비 계산
# # 공식: 당해연도 명목 국방비 * (2024년 디플레이터 / 당해연도 디플레이터)
# df_uzb_gdp["military_expenditure_usd"] = df_uzb_gdp["cur_mil_ex"] * (
#     deflator_2024 / df_uzb_gdp["deflator"]
# )

# df_uzb_gdp
# # %%
# df_uzb_gdp = df_uzb_gdp[['iso_a3', 'year', 'military_expenditure_usd', 'military_expenditure_gdp_pct']]
# df_uzb_gdp
# %%
df_qatar_gdp
# %%
df_uae_gdp
# %%
df_final_score1 = pd.read_csv('../../data/processed/final_score_1.csv')
df_final_score1
# %%
# 1. 기준 키를 인덱스로 지정
df_base = df_final_score1.set_index(["iso_a3", "year"])
df_patch = df_qatar_gdp.set_index(["iso_a3", "year"])

# 2. NaN 자리만 df_patch 값으로 채우기 (기존 실측치는 안전하게 보존)
df_base = df_base.combine_first(df_patch)
# %%
# 3. 인덱스 원복
df_final_score2 = df_base.reset_index()
df_final_score2[df_final_score2['iso_a3'] == 'QAT']
# %%
df_base2 = df_final_score2.set_index(["iso_a3", "year"])
df_patch_uae = df_uae_gdp.set_index(["iso_a3", "year"])
# %%
df_base2 = df_base2.combine_first(df_patch_uae)

df_final_score2 = df_base2.reset_index()
df_final_score2[df_final_score2['iso_a3'] == 'ARE']
# %%
df_base3 = df_final_score2.set_index(["iso_a3", "year"])
# df_patch_uzb = df_uzb_gdp.set_index(["iso_a3", "year"])
# %%
# df_base3 = df_base3.combine_first(df_patch_uzb)

df_final_score2 = df_base3.reset_index()
df_final_score2[df_final_score2['iso_a3'] == 'UZB']

# %%

# %%
# 대상 컬럼
target_cols = ['military_expenditure_usd', 'military_expenditure_gdp_pct']

# MMR의 2024년 값을 2025년 행에 복사
df_final_score2.loc[(df_final_score2['iso_a3'] == 'MMR') & (df_final_score2['year'] == 2025), target_cols] = df_final_score2.loc[
    (df_final_score2['iso_a3'] == 'MMR') & (df_final_score2['year'] == 2024), target_cols
].values

df_final_score2[df_final_score2['iso_a3'] == 'MMR']
# %%
df_final_score2.to_csv('../../data/processed/final_score_2.csv', index=False)
# %%
