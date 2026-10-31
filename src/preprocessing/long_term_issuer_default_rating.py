# %%
import pandas as pd
import numpy as np
# %%
df = pd.read_csv('../../data/raw/20261001_fitch_ratings_sovereign.csv', low_memory=False)

df_country = df[df['rating_type'] == 'Long Term Issuer Default Rating'].copy()
df_country

# %%
# df_country['obligor_name'].value_counts().to_csv('obligor_counts.csv')


# %%
df_country[df_country['obligor_name'] == '"Korea"'][['rating_action_date']]

# %%
df_country['obligor_name'] = df_country['obligor_name'].str.replace('"', '').str.strip()
df_country['obligor_name']


# %%
exclude_keywords = [
    'Bank',
    # 'Corporation',
    # 'Fund',
    # 'Facility',
    # 'Commission',
    # 'Union',
]
df_country = df_country[
    ~df_country['obligor_name'].str.contains('|'.join(exclude_keywords), case=False)
]
# df_country['obligor_name'].value_counts().to_csv('obligor_counts.csv')


# %%
exclude_keywords = [
    
    # 'Corporation',
    # 'Fund',
     'Facility',
    # 'Commission',
    # 'Union',
]
df_country = df_country[
    ~df_country['obligor_name'].str.contains('|'.join(exclude_keywords), case=False)
]
# df_country['obligor_name'].value_counts().to_csv('obligor_counts.csv')
# %%
exclude_keywords = [
    
    'Corporation',
    # 'Fund',
   
    # 'Commission',
    # 'Union',
]
df_country = df_country[
    ~df_country['obligor_name'].str.contains('|'.join(exclude_keywords), case=False)
]
# df_country['obligor_name'].value_counts().to_csv('obligor_counts.csv')
# %%
exclude_keywords = [
    
    'corporacion',
    # 'Fund',
   
    # 'Commission',
    # 'Union',
]
df_country = df_country[
    ~df_country['obligor_name'].str.contains('|'.join(exclude_keywords), case=False)
]
# df_country['obligor_name'].value_counts().to_csv('obligor_counts.csv')
# %%
exclude_keywords = [
    
  'banque',
    # 'Fund',
   
    # 'Commission',
    # 'Union',
]
df_country = df_country[
    ~df_country['obligor_name'].str.contains('|'.join(exclude_keywords), case=False)
]
# df_country['obligor_name'].value_counts().to_csv('obligor_counts.csv')
# %%
exclude_keywords = [
    
  
    'Fund',
   
    # 'Commission',
    # 'Union',
]
df_country = df_country[
    ~df_country['obligor_name'].str.contains('|'.join(exclude_keywords), case=False)
]
# df_country['obligor_name'].value_counts().to_csv('obligor_counts.csv')
# %%
exclude_keywords = [
    
  
     'Mechanism',
   
    # 'Commission',
    # 'Union',
]
df_country = df_country[
    ~df_country['obligor_name'].str.contains('|'.join(exclude_keywords), case=False)
]
# df_country['obligor_name'].value_counts().to_csv('obligor_counts.csv')
# %%
exclude_keywords = [
    
  

   'Community',
    # 'Commission',
    # 'Union',
]
df_country = df_country[
    ~df_country['obligor_name'].str.contains('|'.join(exclude_keywords), case=False)
]
# df_country['obligor_name'].value_counts().to_csv('obligor_counts.csv')
# %%
exclude_keywords = [
    
  

  'Company',
    # 'Commission',
    # 'Union',
]
df_country = df_country[
    ~df_country['obligor_name'].str.contains('|'.join(exclude_keywords), case=False)
]
# df_country['obligor_name'].value_counts().to_csv('obligor_counts.csv')


# %%
exclude_keywords = [
    
  


    # 'Commission',
    'Union',
]
df_country = df_country[
    ~df_country['obligor_name'].str.contains('|'.join(exclude_keywords), case=False)
]
# df_country['obligor_name'].value_counts().to_csv('obligor_counts.csv')
# %%
df_final = df_country[['obligor_name', 'rating', 'rating_action_date']]
df_final
# %%
# df_final[df_final['obligor_name'] == 'United Arab Emirates']
# # %%
# df_final[df_final['obligor_name'] == 'Russia']
# # %%
# df_final[df_final['rating'] == 'C']
# # %%
# df_c = df_final[df_final['rating'].str.contains('C', na=False)]
# df_c.to_csv('df_c.csv')
# # %%
# df_b = df_final[df_final['rating'].str.contains('B', na=False)]
# df_b.to_csv('df_b.csv')
# %%
df_map = pd.read_csv('../../data/mapping/country_map_master.csv', encoding='utf-8')
df_map = df_map[df_map['iso_a3'] != 'KOR'].reset_index(drop=True)
df_map
# %%
df_map_countries_all = (set(df_map['iso_official_country_name'].unique()) | set(df_map['sipri_milex_country_name'].unique()) | set(df_map['sipri_trade_country_name'].unique()) | set(df_map['gpi_country_name'].unique()))

# %%
df_fitching = set(df_final['obligor_name'].unique())
len(df_fitching)
# %%
intersection_countries = df_map_countries_all & df_fitching
len(intersection_countries)

# %%
found_iso = set()
for col in ['iso_official_country_name', 'sipri_milex_country_name', 'sipri_trade_country_name', 'gpi_country_name']:
    found_iso.update(df_map[df_map[col].isin(df_fitching)]['iso_a3'])
len(found_iso)
# %%
unmatched_master = df_map[~df_map['iso_a3'].isin(found_iso)]
print(f"아직 못 찾은 마스터 국가 수: {len(unmatched_master)}개\n")
print(unmatched_master[['iso_a3', 'iso_official_country_name', 'country_name_ko']])
# %%
unmatched_fitch = (list(df_fitching - df_map_countries_all))
print("Fitch 미매칭 목록:", unmatched_fitch)
# %%
# korea는 안씀
# uruguay는 마스터에 없음
# cabo는 마스터에 없음
# latvia는 마스터에 없음
# aruba는 마스터에 없음
# bermuda는 마스터에 없음
# Ras Al Khaimah는 마스터에 없음
# Luxembourg는 마스터에 없음
# Angola는 마스터에 없음
# Norway는 마스터에 없음
# Slovenia는 마스터에 없음
# Malta는 마스터에 없음
# armenia는 마스터에 없음
# Gabon은 마스터에 없음
# Andorra는 마스터에 없음
# Jamaica는 마스터에 없음
# Macao, China는 마스터에 없음
# Turkmenistan는 마스터에 없음
# El Salvador는 마스터에 없음
# Ireland는 마스터에 없음
# cyprus는 마스터에 없음
# North Macedonia, Republic of는 마스터에 없음
# Nicaragua는 마스터에 없음
# San Marino는 마스터에 없음
# Costa Rica는 마스터에 없음
# Benin은 마스터에 없음
# Abu Dhabi는 마스터에 없음
# Cameroon는 마스터에 없음
# The Commonwealth of The Bahamas는 마스터에 없음
# Hong Kong, China은 마스터에 없음
# Lesotho는 마스터에 없음
# Lithuania는 마스터에 없음
# Taiwan, China는 마스터에 없음
# Suriname는 마스터에 없음
# Chad는 마스터에 없음
# Maldives는 마스터에 없음
# Nepal는 마스터에 없음
# Bolivia는 마스터에 없음
# Lebanon은 마스터에 없음
# Bahrain은 마스터에 없음
# Barbados는 마스터에 없음
# Moldova는 마스터에 없음
# Iceland는 마스터에 없음
# Seychelles는 마스터에 없음
# Venezuela는 마스터에 없음
# Congo, Republic of는 마스터에 없음
# Estonia는 마스터에 없음
# Kosovo는 마스터에 없음

# Uzbekistan, Republic of은 있음!
# Taiwan, China는 있음!
# Czech Republic는 있음!
# Hashemite Kingdom of Jordan는 있음

# %%
naming_fix = {
    'Uzbekistan, Republic of' : 'UZB',
    'Taiwan, China' : 'TWN',
    'Czech Republic' : 'CZE',
    'Hashemite Kingdom of Jordan' : 'JOR'
}

naming_to_iso_in_master = {}

for _, row in df_map.iterrows():
    iso_a3 = row['iso_a3']
    for col in ['iso_official_country_name', 'sipri_milex_country_name', 'sipri_trade_country_name', 'gpi_country_name']:
        naming_to_iso_in_master[row[col]] = iso_a3
        
naming_to_iso_in_master.update(naming_fix)
naming_to_iso_in_master
# %%
df_final['iso_a3'] = df_final['obligor_name'].map(naming_to_iso_in_master)
df_final
# %%
df_final['iso_a3'].isna().sum()
# %%
df_final_try = df_final.dropna(subset=['iso_a3'])
df_final_try
# %%
df_final_try['iso_a3'].isna().sum()
# %%
df_final_try = df_final_try[['iso_a3', 'rating', 'rating_action_date']]
df_final_try
# %%
df_final_try.info()
# %%
df_final_try['rating_action_date'] = pd.to_datetime(df_final_try['rating_action_date'])
df_final_try.info()
# %%
# 추가된 국가 확인
codes = ['NOR', 'EST', 'URY']

print(df_final_try[df_final_try['iso_a3'].isin(codes)]
      .groupby('iso_a3').size())

print("최종 국가 수:", df_final_try['iso_a3'].nunique())
print("최종 데이터 행 수:", len(df_final_try))

# %%
# 1. 분석 대상 연도 설정
START_YEAR = 2016
END_YEAR = 2025

# %%
# 2. 원본 등급 이력 정리
df_rating = df_final_try.copy()

df_rating['rating_action_date'] = pd.to_datetime(
    df_rating['rating_action_date'],
    errors='coerce'
)

df_rating = df_rating.dropna(
    subset=['iso_a3', 'rating', 'rating_action_date']
)

# 분석 종료 연도 이후의 데이터는 제외
df_rating = df_rating[
    df_rating['rating_action_date']
    < pd.Timestamp(f'{END_YEAR + 1}-01-01')
].copy()

df_rating['year'] = df_rating['rating_action_date'].dt.year

# %%
# 3. 국가-연도별 마지막 등급만 남기기
df_rating_yearly = (
    df_rating
    .sort_values('rating_action_date')
    .drop_duplicates(
        subset=['iso_a3', 'year'],
        keep='last'
    )
    [['iso_a3', 'year', 'rating']]
)

# %%
# 4. 2016년 이전의 등급 이력도 포함해 연도 조합 생성
# 그래야 과거 등급을 2016년 이후로 이어받을 수 있음

all_countries = sorted(df_rating['iso_a3'].unique())

all_years = pd.DataFrame({
    'year': range(
        int(df_rating['year'].min()),
        END_YEAR + 1
    )
})

df_country_year = pd.MultiIndex.from_product(
    [all_countries, all_years['year']],
    names=['iso_a3', 'year']
).to_frame(index=False)

# %%
# 5. 실제 등급 데이터 결합
df_country_yearly = df_country_year.merge(
    df_rating_yearly,
    on=['iso_a3', 'year'],
    how='left'
)


# %%
# 6. 국가별로 직전 등급 이어받기
df_country_yearly = df_country_yearly.sort_values(
    ['iso_a3', 'year']
).reset_index(drop=True)

df_country_yearly['rating'] = (
    df_country_yearly
    .groupby('iso_a3')['rating']
    .ffill()
)


# %%
# 7. 최종 분석 대상 기간만 추출
df_country_yearly = df_country_yearly[
    df_country_yearly['year'].between(START_YEAR, END_YEAR)
].copy()

df_country_yearly = df_country_yearly[
    ['iso_a3', 'year', 'rating']
].reset_index(drop=True)

# %%
# 8. 결과 검증
print("최종 국가 수:", df_country_yearly['iso_a3'].nunique())
print("최종 데이터 행 수:", len(df_country_yearly))
print("등급 결측치 수:", df_country_yearly['rating'].isna().sum())

# 등급이 없는 국가-연도 확인
print(
    df_country_yearly[
        df_country_yearly['rating'].isna()
    ].to_string(index=False)
)
# %%
# 10. Fitch 등급별 점수 매핑
FITCH_SCORE_MAP = {
    "AAA": 100,
    "AA+": 100, "AA": 100, "AA-": 100,
    "A+": 100, "A": 100, "A-": 100,
    "BBB+": 100, "BBB": 100, "BBB-": 87.5,
    "BB+": 75, "BB": 62.5, "BB-": 50,
    "B+": 37.5, "B": 25, "B-": 12.5,
    "CCC+": 0.0, "CCC": 0.0, "CCC-": 0.0,
    "CC": 0.0, "C": 0.0,
    "RD": 0.0, "D": 0.0, "WD": 0.0,
}

# %%
# 11. 등급을 점수로 변환
df_country_yearly['rating'] = (
    df_country_yearly['rating']
    .map(FITCH_SCORE_MAP)
    .fillna(0.0)
)

# %%
# 12. 최종 CSV 저장
df_country_yearly.to_csv(
    '../../data/processed/fitch_rating_yearly.csv',
    index=False,
    encoding='utf-8-sig'
)
