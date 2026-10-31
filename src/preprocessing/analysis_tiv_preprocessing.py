# %%
import io
import pandas as pd

path = "../../data/raw/tiv_supplier_for_analysis.csv"
lines = open(path, encoding="utf-8-sig").read().splitlines()
# %%
blocks = []      # 잘라낸 표들을 담을 상자
cur = None       # 지금 담고 있는 표

for line in lines:
    if line.startswith("Supplier,"):      # 헤더 줄 = 새 표의 시작
        cur = [line]
    elif cur is not None:
        if line.strip() == "":            # 빈 줄 = 표의 끝
            blocks.append(cur)
            cur = None
        else:
            cur.append(line)
            
print(len(blocks))   # 20이 나오면 성공 (20개국)
# %%
parts = []
for b in blocks:
    df = pd.read_csv(io.StringIO("\n".join(b)))
    df = df.rename(columns={"Supplier": "supplier"})
    is_total = df["supplier"].str.startswith("Total exports to")
    recipient = df.loc[is_total, "supplier"].iloc[0].replace("Total exports to ", "")
    df = df[~is_total].copy()
    df.insert(0, "recipient", recipient)
    parts.append(df)

wide = pd.concat(parts, ignore_index=True)
# %%
years = [str(y) for y in range(2016, 2026)]

for y in years:
    wide[y] = pd.to_numeric(wide[y].astype(str).str.strip(), errors="coerce")
wide[years] = wide[years].fillna(0)

long = wide.melt(
    id_vars=["recipient", "supplier"],
    value_vars=years,
    var_name="year",
    value_name="tiv",
)
long["year"] = long["year"].astype(int)
# %%
master = pd.read_csv("../../data/mapping/country_map_master.csv")
m = master[["sipri_trade_country_name", "iso_a3"]]

long = long.merge(
    m.rename(columns={"sipri_trade_country_name": "recipient", "iso_a3": "recipient_iso"}),
    on="recipient", how="left",
)
long = long.merge(
    m.rename(columns={"sipri_trade_country_name": "supplier", "iso_a3": "supplier_iso"}),
    on="supplier", how="left",
)

# 매핑 안 된 국가 확인
print(long.loc[long["recipient_iso"].isna(), "recipient"].unique())
print(long.loc[long["supplier_iso"].isna(), "supplier"].unique())
# %%
# 마스터에 없는 공급국 8개 (ISO 3166-1 alpha-3 표준 코드)
extra_iso = {
    "Bosnia-Herzegovina": "BIH",
    "Brunei": "BRN",
    "Iran": "IRN",
    "Ireland": "IRL",
    "Latvia": "LVA",
    "Lithuania": "LTU",
    "North Macedonia": "MKD",
    "Slovenia": "SVN",
}

# 1) 마스터에서 못 찾은 칸만 딕셔너리로 채우기
long["supplier_iso"] = long["supplier_iso"].fillna(long["supplier"].map(extra_iso))

# 2) 국가가 아닌 항목은 별도 라벨 (국가 코드로 착각하지 않게 구분)
long.loc[long["supplier"] == "unknown supplier(s)", "supplier_iso"] = "UNK"

# 3) 남은 빈칸이 없는지 확인
print(long["supplier_iso"].isna().sum())
# %%
# 열 이름 정리 + 필요한 열만 + 정렬
clean = long.rename(columns={
    "recipient_iso": "recipient_iso_a3",
    "supplier_iso": "supplier_iso_a3",
    "tiv": "tiv_official",
})[["recipient_iso_a3", "year", "supplier_iso_a3", "tiv_official"]]

clean = clean.sort_values(["recipient_iso_a3", "year", "supplier_iso_a3"]).reset_index(drop=True)

# 저장 전 점검
key = ["recipient_iso_a3", "year", "supplier_iso_a3"]
print(len(clean))                         # 3040
print(clean.isna().sum().sum())           # 0
print(clean.duplicated(subset=key).sum()) # 0

# 저장
clean.to_csv(
    "../../data/analysis/tiv_supplier_official_clean.csv",
    index=False,
    encoding="utf-8-sig",
)