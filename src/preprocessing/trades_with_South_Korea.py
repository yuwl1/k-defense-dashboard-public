# %%
import pandas as pd
# %%
import os
print(os.getcwd())
# %%
data_path = "../../data/raw/arms_trade_98_countries_all.csv"
df = pd.read_csv(data_path)
df
# %%
공급국이_한국 = df[df['supplier_iso_a3'] == 'KOR']
공급국이_한국
# %%
공급국이_한국 = 공급국이_한국.sort_values('order_year').drop_duplicates(subset=['recipient_iso_a3'], keep='first').reset_index(drop=True)
공급국이_한국 = 공급국이_한국[['recipient_iso_a3', 'order_year']]
공급국이_한국
# %%

# %%
df1 = 공급국이_한국.rename(columns={'recipient_iso_a3': 'iso_a3', 'order_year': 'the_initial_year_of_south_korea\'s_defense_exports'}).copy()

df1
# %%

# %%
map_master_path = '../../data/mapping/country_map_master.csv'
map_master = pd.read_csv(map_master_path)
ref_cols = map_master[['iso_a3']]

ref_cols = ref_cols[ref_cols['iso_a3'] != 'KOR'].reset_index(drop=True)
ref_cols
# %%
df_first_step = pd.merge(
    df1,
    ref_cols,
    on='iso_a3',
    how='right'
    
)
df_first_step
# %%

# %%
df_company_base = pd.read_csv('../../data/processed/korea_weapon_data.csv', encoding='utf-8')
df_company_base
# %%
df_HA = df_company_base[df_company_base['company'] == 'Hanwha Aerospace'].sort_values('order_year').drop_duplicates(subset='recipient_iso_a3', keep='first').reset_index(drop=True)
df_HA = df_HA[['recipient_iso_a3', 'order_year']].rename(columns={'recipient_iso_a3': 'iso_a3', 'order_year': 'the_initial_year_of_hanwha_aerospace\'s_defense_exports'})
df_HA
# %%

# %%
df_Hyundai_Rotem = df_company_base[df_company_base['company'] == 'Hyundai Rotem'].sort_values('order_year').drop_duplicates(subset='recipient_iso_a3', keep='first').reset_index(drop=True)
df_Hyundai_Rotem = df_Hyundai_Rotem[['recipient_iso_a3', 'order_year']].rename(columns={'recipient_iso_a3': 'iso_a3', 'order_year': 'the_initial_year_of_hyundai_rotem\'s_defense_exports'})
df_Hyundai_Rotem
# %%

# %%
df_LIG_Nex1 = df_company_base[df_company_base['company'] == 'LIG Nex1'].sort_values('order_year').drop_duplicates(subset='recipient_iso_a3', keep='first').reset_index(drop=True)
df_LIG_Nex1 = df_LIG_Nex1[['recipient_iso_a3', 'order_year']].rename(columns={'recipient_iso_a3': 'iso_a3', 'order_year': 'the_initial_year_of_lig\'s_defense_exports'})
df_LIG_Nex1
# %%

# %%
df_KAI = df_company_base[df_company_base['company'] == 'KAI'].sort_values('order_year').drop_duplicates(subset='recipient_iso_a3', keep='first').reset_index(drop=True)
df_KAI = df_KAI[['recipient_iso_a3', 'order_year']].rename(columns={'recipient_iso_a3': 'iso_a3', 'order_year': 'the_initial_year_of_kai\'s_defense_exports'})
df_KAI
# %%

# %%
df_hanwha_ocean = df_company_base[df_company_base['company'] == 'Hanwha Ocean'].sort_values('order_year').drop_duplicates(subset='recipient_iso_a3', keep='first').reset_index(drop=True)
df_hanwha_ocean = df_hanwha_ocean[['recipient_iso_a3', 'order_year']].rename(columns={'recipient_iso_a3': 'iso_a3', 'order_year': 'the_initial_year_of_hanwha_ocean\'s_defense_exports'})
df_hanwha_ocean
# %%

# %%
df_hyundai_heavy_industries = df_company_base[df_company_base['company'] == 'HD Hyundai Heavy Industries'].sort_values('order_year').drop_duplicates(subset='recipient_iso_a3', keep='first').reset_index(drop=True)
df_hyundai_heavy_industries = df_hyundai_heavy_industries[['recipient_iso_a3', 'order_year']].rename(columns={'recipient_iso_a3': 'iso_a3', 'order_year': 'the_initial_year_of_hyundai_heavy_industries\'s_defense_exports'})
df_hyundai_heavy_industries
# %%

# %%
df_first_step
# %%
df_final = df_first_step.merge(
    df_HA,
    on=['iso_a3'],
    how='left'
)
df_final
# %%
df_final = df_final.merge(
    df_hanwha_ocean,
    on=['iso_a3'],
    how='left'
)
df_final
# %%
df_final = df_final.merge(
    df_Hyundai_Rotem,
    on=['iso_a3'],
    how='left'
)
df_final
# %%
df_final = df_final.merge(
    df_hyundai_heavy_industries,
    on=['iso_a3'],
    how='left'
)
df_final
# %%
df_final = df_final.merge(
    df_KAI,
    on=['iso_a3'],
    how='left'
)
df_final
# %%
df_final = df_final.merge(
    df_LIG_Nex1,
    on=['iso_a3'],
    how='left'
)
df_final
# %%
df_final = df_final.fillna(0)
df_final
# %%
# df_final.iloc[:, 1:] = df_final.iloc[:, 1:].astype(int)
# df_final
# %%
df_final[df_final.columns[1:]] = df_final[df_final.columns[1:]].astype('int64')
# %%
df_final.info()
# %%
df_final.to_csv('../../data/processed/transaction_history.csv', index=False)
# %%
