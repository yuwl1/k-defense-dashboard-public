# %%
import os
import numpy as np
import pandas as pd
from pathlib import Path

# ============================================================
# 1. 경로
# ============================================================
# 실행 위치와 상관없이 프로젝트 폴더를 찾음:
# 이 파일(또는 노트북 실행 폴더)에서 위로 올라가며 data/raw 폴더가 있는 곳
def find_project_root():
    try:
        start = Path(__file__).resolve().parent   # .py로 실행할 때
    except NameError:
        start = Path.cwd()                        # 노트북(.ipynb)·대화형 실행일 때

    for folder in [start, *start.parents]:
        if (folder / "data" / "raw").is_dir():
            return folder

    raise FileNotFoundError(f"data/raw 폴더를 찾지 못했습니다. 시작 위치: {start}")


BASE_DIR = find_project_root()
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = DATA_DIR / "processed"

SIPRI_FILE = RAW_DIR / "sipri_milex.xlsx"
MASTER_FILE = DATA_DIR / "mapping" / "country_map_master.csv"
if not MASTER_FILE.is_file():
    MASTER_FILE = OUTPUT_DIR / "country_map_master.csv"

# 경로 확인
print("=" * 60)
print("Path check")
print("=" * 60)

print(f"Project folder : {BASE_DIR}")
print(f"Data folder    : {DATA_DIR}")
print(f"SIPRI file     : {SIPRI_FILE}")
print(f"Country master : {MASTER_FILE}")

print("\nFile exists?")
print(
    "SIPRI :",
    os.path.exists(SIPRI_FILE)
)
print(
    "MASTER:",
    os.path.exists(MASTER_FILE)
)

print("=" * 60)
# %%
YEARS1 = list(range(2015, 2026))

# 국가가 아닌 집계 행은 국가별 분석에서 제외 (SIPRI Milex 시트에 값이 있는 European Union 행이 있음)
EXCLUDE_AGGREGATES = {"European Union"}


# %%
def load_sheet(sheet):
    d = pd.read_excel(SIPRI_FILE, sheet_name=sheet, header=5).rename(columns={"Country": "sipri_country_name"})
    d.columns = [int(c) if str(c).isdigit() else c for c in d.columns]
    # 추가: 전체 연도가 결측이어서 제외되는 행 수 (지역 구분 행 포함)
    print(f"[{sheet}] 전체 연도 결측으로 제외된 행:", d[YEARS1].isna().all(axis=1).sum())
    return d[["sipri_country_name"] + YEARS1].dropna(subset=YEARS1, how="all")    # 지역 제목 행 제거
    

def to_long(d, name):
    l = d.melt("sipri_country_name", YEARS1, "year", name)
    # 추가: Wide → Long 변환 전후 행 수 확인
    print(f"[{name}] Wide → Long: {len(d)}행 × {len(YEARS1)}개년 = {len(l)}건")
    l[name] = pd.to_numeric(l[name], errors="coerce")               # "...", "xxx" -> NaN
    # 추가: 연도별 결측 및 숫자 변환 실패로 제외되는 건수
    print(f"[{name}] 결측으로 제외된 건수:", l[name].isna().sum())
    return l.dropna(subset=[name])

# 1) 군사비 (2024년 불변가격 US$, 단위: 달러)
mil_all = to_long(load_sheet("Constant (2024) US$"), "military_expenditure_usd")
mil_all["military_expenditure_usd"] = (mil_all["military_expenditure_usd"] * 1e6).round(0).astype("int64")
mil = mil_all[~mil_all["sipri_country_name"].isin(EXCLUDE_AGGREGATES)]
mil = mil.sort_values(["sipri_country_name", "year"])

# 2) GDP 대비 군사비 비중 (%)
sh_all = to_long(load_sheet("Share of GDP"), "military_expenditure_gdp_pct")
sh_all["military_expenditure_gdp_pct"] = (sh_all["military_expenditure_gdp_pct"] * 100).round(6)      # 부동소수점 오차 제거 (3.2900000000000005 -> 3.29)
sh = sh_all[~sh_all["sipri_country_name"].isin(EXCLUDE_AGGREGATES)]
sh = sh.sort_values(["sipri_country_name", "year"])

# 단위 변환 대상 데이터 건수 확인
# 숫자가 없는 값은 제거되었으며, 마스터 국가 필터링 전 기준

print("국방비 단위 변환 건수:", len(mil_all))
print("GDP 비중 단위 변환 건수:", len(sh_all))

# European Union 집계 행 제외 후 건수
print("국방비 집계 행 제외 후:", len(mil))
print("GDP 비중 집계 행 제외 후:", len(sh))

# 3) 국가 마스터에서 국가 정보를 붙임
#    - iso_a3(와 스크립트 내부용 iso_official_country_name)는 country_map_master.csv에서 sipri_milex_country_name으로 매칭
#    - 마스터 밖 국가(대시보드 대상 아님)는 iso_a3가 빈 값
EXTRA_COLS = ["iso_official_country_name", "iso_a3"]
SAVE_MIL = ["iso_a3", "year", "military_expenditure_usd"]       # 군사비 표의 열
SAVE_SH  = ["iso_a3", "year", "military_expenditure_gdp_pct"]  # GDP 비중 표의 열

def build_country_lookup():
    """sipri_country_name (SIPRI spelling) -> iso_official_country_name, iso_a3 (master countries only)"""
    rows = {}
    if os.path.exists(MASTER_FILE):
        m = pd.read_csv(MASTER_FILE, encoding="utf-8-sig", keep_default_na=False)
        for r in m.itertuples():
            for n in str(r.sipri_milex_country_name).split(" | "):
                if n.strip():
                    rows[n.strip()] = {"iso_official_country_name": r.iso_official_country_name, "iso_a3": r.iso_a3}
    else:
        print("WARNING: country_map_master.csv not found - iso_official_country_name / iso_a3 stay empty (run build_country_map.py first)")
    return pd.DataFrame.from_dict(rows, orient="index", columns=EXTRA_COLS).rename_axis("sipri_country_name").reset_index()

COUNTRY_LOOKUP = build_country_lookup()

def with_country_info(d):
    out = d.merge(COUNTRY_LOOKUP, on="sipri_country_name", how="left")
    out[EXTRA_COLS] = out[EXTRA_COLS].fillna("")
    return out

mil_out, sh_out = with_country_info(mil), with_country_info(sh)
# 국가 마스터와 일치하는 국가(대시보드 대상)만 남김
# 마스터가 없으면 매칭할 수 없어 모든 국가를 그대로 둠
HAS_MASTER = os.path.exists(MASTER_FILE)
if HAS_MASTER:
    mil_out, sh_out = mil_out[mil_out["iso_a3"] != ""], sh_out[sh_out["iso_a3"] != ""]
    

# 국방비와 GDP 대비 국방비 비중 통합
merged_out = pd.merge(
    mil_out[SAVE_MIL],
    sh_out[SAVE_SH],
    on=["iso_a3", "year"],
    how="outer",
    validate="one_to_one"
)

# 컬럼 순서 정리
SAVE_COLS = [
    "iso_a3",
    "year",
    "military_expenditure_usd",
    "military_expenditure_gdp_pct"
]

# 전체 분석 대상 국가 × 연도 조합 생성
master = pd.read_csv(MASTER_FILE, encoding="utf-8-sig")

all_countries = master["iso_a3"].dropna().unique()

full_data = pd.MultiIndex.from_product(
    [all_countries, YEARS1],
    names=["iso_a3", "year"]
).to_frame(index=False)

# 결측 국가·연도 행 추가 건수 확인
print("국가 매핑 및 통합 후:", len(merged_out), "행")
print("전체 국가·연도 조합:", len(full_data), "행")
print("추가된 결측 행:", len(full_data) - len(merged_out), "건")

# 전체 국가·연도를 유지하고 기존 전처리 데이터 연결
merged_out = full_data.merge(
    merged_out,
    on=["iso_a3", "year"],
    how="left",
    validate="one_to_one"
)

# 컬럼 및 정렬
merged_out = merged_out[SAVE_COLS]
merged_out = merged_out.sort_values(["iso_a3", "year"]).reset_index(drop=True)

# ============================================================
# 결측치 처리
# ============================================================
# 대상 국가와 방식
#   MMR : 2025년 값이 없어 2024년 값을 그대로 사용
#   QAT : 2021·2022년 값만 있음 → SIPRI 현재가격 국방비 합 / (국방비 ÷ GDP 비중으로 구한 GDP 합)을 빈 연도에 적용
#   UZB : 2018년 값만 있음
#         2016~2017년 : 2018년 실측치를 세계은행 실질 GDP 성장률로 거꾸로 계산, GDP 비중은 2018년 값
#         2020~2025년 : 이슈페이퍼 표 3-5(PDF 71쪽)의 2020~2024 평균 국방비 2,800백만 달러 / 같은 기간 평균 명목 GDP를 GDP 비중으로 적용
#                       (명목 GDP × 비중 → 미국 GDP 디플레이터로 2024년 불변가격 달러 환산)
#         2019년 : 2018년과 2020년 국방비의 평균, GDP 비중은 2018년 값
#         2015년은 추정 대상이 아니므로 결측으로 유지
#   ARE : 값이 전혀 없음 → 같은 표의 2020~2024 평균 국방비 23,900백만 달러 기준
#   DJI, LAO, PRK : 근거 자료가 없어 결측으로 유지
# 빈 연도의 국방비 = 비율 × 명목 GDP × (2024년 디플레이터 / 해당 연도 디플레이터)
#   → 세계은행 명목 GDP(현재 달러)를 2024년 불변가격 달러로 환산
#   → 세계은행에 없는 연도(UAE 2025)는 가장 가까운 이전 연도의 GDP·디플레이터를 사용
# ARE의 비율 = 이슈페이퍼 평균 국방비 / 세계은행 명목 GDP의 평균 (평균 기간은 GDP_WINDOW)
import json
import urllib.request

IMPUTE_LAST_YEAR = ["MMR"]
PAPER_AVG_MIL = {"ARE": 23900e6}                   # 이슈페이퍼 평균 국방비 (달러)
IMPUTE_GDP_BASED = ["QAT", "ARE"]
# 평균 GDP를 구하는 연도 (시작, 끝)
GDP_WINDOW = {"ARE": (2020, 2024)}

# UZB: 실질 GDP 성장률 방식
UZB_CODE = "UZB"
UZB_AVG_MIL = 2800e6                                # 이슈페이퍼 2020~2024 평균 국방비 (달러)
UZB_BASE_YEAR = 2018                                # SIPRI 실측치가 있는 유일한 연도
UZB_FILL_YEARS = list(range(2016, 2026))            # 추정할 연도 (2015년은 결측 유지)
UZB_GDP_WINDOW = (2020, 2024)                       # 평균 명목 GDP를 구하는 연도
USD_DEFLATOR_CODE = "USA"                           # 달러 금액을 2024년 불변가격으로 바꿀 때 쓰는 미국 GDP 디플레이터
WB_CODES = IMPUTE_GDP_BASED + [UZB_CODE, USD_DEFLATOR_CODE]     # 세계은행에서 받을 국가 (명목 GDP·디플레이터)
GROWTH_FILE = os.path.join(DATA_DIR, "raw/world_bank_uzb_growth.csv")    # 성장률 저장본 (gdp_growth_pct: %)
IMPUTE_YEARS = YEARS1                               # 결측을 채울 연도 (2016~2025만 채우려면 list(range(2016, 2026)))
BASE_YEAR = 2024                                    # 불변가격 기준 연도
WB_FILE = os.path.join(DATA_DIR, "raw/world_bank_gdp_deflator.csv")    # 세계은행 자료 저장본
WB_INDICATORS = {"gdp_nominal_usd": "NY.GDP.MKTP.CD", "gdp_deflator": "NY.GDP.DEFL.ZS"}


def load_world_bank(codes):
    """세계은행 명목 GDP·GDP 디플레이터. API를 먼저 시도해 저장본을 갱신하고, 실패하면 저장본을 사용한다."""
    try:
        parts = []
        for col, ind in WB_INDICATORS.items():
            url = (f"https://api.worldbank.org/v2/country/{';'.join(codes)}/indicator/{ind}"
                   f"?format=json&per_page=1000&date={YEARS1[0]}:{YEARS1[-1]}")
            with urllib.request.urlopen(url, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            parts.append(pd.DataFrame([{"iso_a3": x["countryiso3code"], "year": int(x["date"]), col: x["value"]} for x in data[1]]))
        wb = parts[0].merge(parts[1], on=["iso_a3", "year"], how="outer").sort_values(["iso_a3", "year"])
        wb.to_csv(WB_FILE, index=False, encoding="utf-8-sig")
        print(f"  세계은행 API에서 받아 저장: {WB_FILE}")
        return wb
    except Exception as e:
        if os.path.exists(WB_FILE):
            wb = pd.read_csv(WB_FILE, encoding="utf-8-sig")
            if set(codes) <= set(wb["iso_a3"]):
                print(f"  ※ 세계은행 API 호출 실패({e}) → 저장본 사용: {WB_FILE}")
                return wb
            raise RuntimeError(f"세계은행 API 호출 실패({e}), 저장본에 필요한 국가가 없습니다: {sorted(set(codes) - set(wb['iso_a3']))}. 인터넷에 연결해 다시 실행하세요.")
        raise RuntimeError(f"세계은행 자료를 받지 못했고 저장본도 없습니다 ({e}). 인터넷 연결을 확인하거나 {WB_FILE} 파일을 준비하세요.")


def qatar_style_ratio(code):
    """자국 값이 있는 연도의 비율: SIPRI 현재가격 국방비 합 / (현재가격 국방비 ÷ GDP 비중으로 구한 GDP 합) × 100"""
    name = COUNTRY_LOOKUP.loc[COUNTRY_LOOKUP["iso_a3"] == code, "sipri_country_name"].iloc[0]
    def row(sheet):
        d = pd.read_excel(SIPRI_FILE, sheet_name=sheet, header=5)
        d.columns = [int(c) if str(c).isdigit() else c for c in d.columns]
        d = d[d["Country"].astype(str).str.strip() == name]
        return d[YEARS1].apply(pd.to_numeric, errors="coerce").iloc[0]
    cur, share = row("Current US$") * 1e6, row("Share of GDP")
    ok = cur.notna() & share.notna()
    return cur[ok].sum() / (cur[ok] / share[ok]).sum() * 100


def load_growth(code):
    """세계은행 실질 GDP 성장률(NY.GDP.MKTP.KD.ZG, %). API를 먼저 시도해 저장본을 갱신하고, 실패하면 저장본을 사용한다."""
    try:
        url = (f"https://api.worldbank.org/v2/country/{code}/indicator/NY.GDP.MKTP.KD.ZG"
               f"?format=json&per_page=1000&date={YEARS1[0]}:{YEARS1[-1]}")
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        g = pd.DataFrame([{"iso_a3": code, "year": int(x["date"]), "gdp_growth_pct": x["value"]} for x in data[1]]).sort_values("year")
        g.to_csv(GROWTH_FILE, index=False, encoding="utf-8-sig")
        print(f"  세계은행 API에서 받아 저장: {GROWTH_FILE}")
    except Exception as e:
        if not os.path.exists(GROWTH_FILE):
            raise RuntimeError(f"성장률 자료를 받지 못했고 저장본도 없습니다 ({e}). 인터넷 연결을 확인하거나 {GROWTH_FILE} 파일을 준비하세요.")
        print(f"  ※ 세계은행 API 호출 실패({e}) → 저장본 사용: {GROWTH_FILE}")
        g = pd.read_csv(GROWTH_FILE, encoding="utf-8-sig")
        g = g[g["iso_a3"] == code]
    return {int(y): v / 100 for y, v in zip(g["year"], g["gdp_growth_pct"]) if pd.notna(v)}


def fill_uzb(df, growth, wb):
    """UZB 결측 채우기. 반환: (2016~2019년 GDP 비중 %, 2020~2025년 GDP 비중 %, 채운 연도 목록)
    2016~2017: 2018년 실측치 / (1 + 실질 GDP 성장률)로 거꾸로 계산
    2020~2025: 비중 = 2,800백만 달러 / 평균 명목 GDP(2020~2024), 국방비 = 명목 GDP × 비중 × (미국 디플레이터 2024 / 해당 연도)
    2019    : 2018년과 2020년 국방비의 평균"""
    rows = df["iso_a3"] == UZB_CODE
    base = df[rows & (df["year"] == UZB_BASE_YEAR)].iloc[0]
    m18, pct18 = base["military_expenditure_usd"], base["military_expenditure_gdp_pct"]
    if pd.isna(m18) or pd.isna(pct18):
        raise ValueError(f"UZB {UZB_BASE_YEAR}년 SIPRI 실측치가 없어 추정을 할 수 없습니다.")
    lack = [y for y in (2017, 2018) if y not in growth]
    if lack:
        raise ValueError(f"UZB 실질 GDP 성장률이 없는 연도: {lack}")

    gdp = wb[wb["iso_a3"] == UZB_CODE].set_index("year")["gdp_nominal_usd"].reindex(YEARS1)
    dfl = wb[wb["iso_a3"] == USD_DEFLATOR_CODE].set_index("year")["gdp_deflator"].reindex(YEARS1)
    yrs_hi = list(range(UZB_GDP_WINDOW[0], YEARS1[-1] + 1))                   # 2020~2025
    for name, ser, need in (("UZB 명목 GDP", gdp, yrs_hi), ("미국 GDP 디플레이터", dfl, yrs_hi + [BASE_YEAR])):
        lack = [y for y in need if pd.isna(ser.get(y))]
        if lack:
            raise ValueError(f"{name} 자료가 없는 연도: {lack}")

    est, pct = {}, {}
    for y in (2016, 2017, 2018, 2019):
        pct[y] = pct18
    est[2018] = m18
    est[2017] = est[2018] / (1 + growth[2018])
    est[2016] = est[2017] / (1 + growth[2017])
    ratio = UZB_AVG_MIL / gdp.loc[UZB_GDP_WINDOW[0]:UZB_GDP_WINDOW[1]].mean()
    for y in yrs_hi:
        pct[y] = ratio * 100
        est[y] = gdp[y] * ratio * dfl[BASE_YEAR] / dfl[y]
    est[2019] = (est[2018] + est[2020]) / 2

    miss = rows & df["military_expenditure_usd"].isna() & df["year"].isin(UZB_FILL_YEARS)
    yrs = df.loc[miss, "year"]
    df.loc[miss, "military_expenditure_usd"] = yrs.map(est).values
    df.loc[miss, "military_expenditure_gdp_pct"] = yrs.map(pct).values
    return pct18, ratio * 100, yrs.tolist()


def fill_by_gdp(df, code, wb, paper_mil=None):
    """GDP 비율 방식으로 빈 연도를 채운다. 반환: (적용 비율 %, 채운 연도 목록)"""
    g = wb[wb["iso_a3"] == code].set_index("year").reindex(YEARS1)
    g = g.ffill()                                                            # 없는 연도는 이전 연도 값 사용
    rows = df["iso_a3"] == code
    if paper_mil is None:
        pct = qatar_style_ratio(code)                                          # 자국 값이 있는 연도로 계산
    else:
        w0, w1 = GDP_WINDOW[code]
        pct = paper_mil / g.loc[w0:w1, "gdp_nominal_usd"].mean() * 100         # 이슈페이퍼 평균 국방비 / 평균 GDP
    miss = rows & df["military_expenditure_usd"].isna() & df["year"].isin(IMPUTE_YEARS)
    yrs = df.loc[miss, "year"]
    const_gdp = g.loc[yrs, "gdp_nominal_usd"].values * g.loc[BASE_YEAR, "gdp_deflator"] / g.loc[yrs, "gdp_deflator"].values
    df.loc[miss, "military_expenditure_usd"] = pct / 100 * const_gdp
    df.loc[miss, "military_expenditure_gdp_pct"] = pct
    return pct, yrs.tolist()


print("\n[결측치 처리]")
MISSING_BEFORE = int(merged_out["military_expenditure_usd"].isna().sum())
print("처리 전 결측 건수:", merged_out[["military_expenditure_usd", "military_expenditure_gdp_pct"]].isna().sum().to_dict())
wb_data = load_world_bank(WB_CODES)

for code in IMPUTE_LAST_YEAR:       # 마지막 값 유지
    rows = merged_out["iso_a3"] == code
    last = merged_out[rows & merged_out["military_expenditure_usd"].notna()].sort_values("year").iloc[-1]
    miss = rows & merged_out["military_expenditure_usd"].isna()
    yrs = merged_out.loc[miss, "year"].tolist()
    merged_out.loc[miss, ["military_expenditure_usd", "military_expenditure_gdp_pct"]] = [last["military_expenditure_usd"], last["military_expenditure_gdp_pct"]]
    print(f"  {code}: {yrs} → {int(last['year'])}년 값 그대로 적용")

for code in IMPUTE_GDP_BASED:       # GDP 비율 방식
    pct, yrs = fill_by_gdp(merged_out, code, wb_data, PAPER_AVG_MIL.get(code))
    print(f"  {code}: {yrs} → GDP 대비 {pct:.6f}%를 적용해 국방비 역산 (2024년 불변가격 달러)")

uzb_pct_lo, uzb_pct_hi, uzb_yrs = fill_uzb(merged_out, load_growth(UZB_CODE), wb_data)      # UZB
print(f"  {UZB_CODE}: {uzb_yrs} → 2016~2019년 GDP 비중 {uzb_pct_lo:.6f}%, 2020~2025년 GDP 비중 {uzb_pct_hi:.6f}% 적용 (2015년은 결측 유지)")

left = merged_out.loc[merged_out["military_expenditure_usd"].isna(), "iso_a3"].value_counts().sort_index()
N_IMPUTED = int(MISSING_BEFORE - merged_out["military_expenditure_usd"].isna().sum())     # 결측 처리로 채워진 행 수
print("처리 후 결측 건수:", merged_out[["military_expenditure_usd", "military_expenditure_gdp_pct"]].isna().sum().to_dict())
print("결측으로 남은 국가(근거 자료 없음):", left.to_dict())

# 최종 데이터의 컬럼별 결측 건수 확인
print(merged_out[
    ["military_expenditure_usd", "military_expenditure_gdp_pct"]
].isna().sum())
# %%
# 최종 결과에서 한국 제외
merged_out = merged_out[merged_out["iso_a3"] != "KOR"].reset_index(drop=True)

# ============================================================
# 전처리 전후 분포 비교
# ============================================================

# 전처리 전: 마스터 국가 필터링 전 데이터 (단위 변환 완료, 집계 행 제외)
# 전처리 후: 최종 통합 데이터

comparison = pd.DataFrame({
    "변수": [
        "military_expenditure_usd",
        "military_expenditure_usd",
        "military_expenditure_gdp_pct",
        "military_expenditure_gdp_pct"
    ],
    "구분": ["전처리 전", "전처리 후", "전처리 전", "전처리 후"],
    "유효값 수": [
        mil["military_expenditure_usd"].count(),
        merged_out["military_expenditure_usd"].count(),
        sh["military_expenditure_gdp_pct"].count(),
        merged_out["military_expenditure_gdp_pct"].count()
    ],
    "평균": [
        mil["military_expenditure_usd"].mean(),
        merged_out["military_expenditure_usd"].mean(),
        sh["military_expenditure_gdp_pct"].mean(),
        merged_out["military_expenditure_gdp_pct"].mean()
    ],
    "중앙값": [
        mil["military_expenditure_usd"].median(),
        merged_out["military_expenditure_usd"].median(),
        sh["military_expenditure_gdp_pct"].median(),
        merged_out["military_expenditure_gdp_pct"].median()
    ],
    "최솟값": [
        mil["military_expenditure_usd"].min(),
        merged_out["military_expenditure_usd"].min(),
        sh["military_expenditure_gdp_pct"].min(),
        merged_out["military_expenditure_gdp_pct"].min()
    ],
    "최댓값": [
        mil["military_expenditure_usd"].max(),
        merged_out["military_expenditure_usd"].max(),
        sh["military_expenditure_gdp_pct"].max(),
        merged_out["military_expenditure_gdp_pct"].max()
    ],
    "표준편차": [
        mil["military_expenditure_usd"].std(),
        merged_out["military_expenditure_usd"].std(),
        sh["military_expenditure_gdp_pct"].std(),
        merged_out["military_expenditure_gdp_pct"].std()
    ]
})

print(comparison.to_string(index=False))

# 통합 CSV 저장, 결측치는 NaN처리
merged_out.to_csv(
    os.path.join(OUTPUT_DIR, "military_expenditure.csv"),
    index=False,
    encoding="utf-8-sig",
    na_rep="NaN"
)
# # 3) 증가 추세 (국가별 1행)
# w = mil.pivot(index="sipri_country_name", columns="year", values="military_expenditure_usd")
# trend = pd.DataFrame({
#     "CAGR_2015_2025(%)": ((w[2025] / w[2015]) ** (1 / 10) - 1) * 100,
#     "CAGR_2022_2025(%)": ((w[2025] / w[2022]) ** (1 / 3) - 1) * 100,
#     "YoY_2025(%)": (w[2025] / w[2024] - 1) * 100,
# }).round(4)
# trend.reset_index().to_csv(os.path.join(OUTPUT_DIR, "15_25_growth_trend.csv"), index=False, encoding="utf-8-sig")
# print(len(mil), len(sh), len(trend))

# %%
# ============================================================
# 3. 검증 (원본 엑셀을 독립적으로 다시 읽어 결과와 비교)
# ============================================================
MIL_COL = "military_expenditure_usd"
SH_COL = "military_expenditure_gdp_pct"
SHEET_MIL, SHEET_SH = "Constant (2024) US$", "Share of GDP"

RESULTS = []

def check(name, ok, detail=""):
    RESULTS.append({"item": name, "result": "PASS" if ok else "FAIL", "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ->  {detail}" if detail else ""))

def info(msg):
    print(f"   · {msg}")

def read_raw(sheet):
    d = pd.read_excel(SIPRI_FILE, sheet_name=sheet, header=5).rename(columns={"Country": "sipri_country_name"})
    d.columns = [int(c) if str(c).isdigit() else c for c in d.columns]
    d["sipri_country_name"] = d["sipri_country_name"].astype("string").str.strip()
    return d[d["sipri_country_name"].notna()]

print("=" * 60)
print("Validation start")
print("=" * 60)

raw_mil, raw_sh = read_raw(SHEET_MIL), read_raw(SHEET_SH)

# --- (1) 입력 구조 -------------------------------------------
print("\n[1] Input structure")
check("Target year columns exist (2015~2025)",
      all(y in raw_mil.columns for y in YEARS1) and all(y in raw_sh.columns for y in YEARS1),
      f"{YEARS1[0]}~{YEARS1[-1]} ({len(YEARS1)} years)")

# 지역 제목 행 = 군사비 시트에서 모든 연도가 빈 행 (Africa, Europe 등). 두 시트에 같은 규칙 적용
year_cols_all = [c for c in raw_mil.columns if isinstance(c, int)]
REGIONS = set(raw_mil.loc[raw_mil[year_cols_all].isna().all(axis=1), "sipri_country_name"])
country_mil = raw_mil[~raw_mil["sipri_country_name"].isin(REGIONS)]
country_sh = raw_sh[~raw_sh["sipri_country_name"].isin(REGIONS)]
info(f"Raw rows: expenditure sheet {len(raw_mil)} / GDP-share sheet {len(raw_sh)}  (excluding {len(REGIONS)} region heading rows)")
info(f"Raw country/aggregate rows: expenditure {len(country_mil)} / GDP share {len(country_sh)}")
check("Both sheets list the same entities", set(country_mil["sipri_country_name"]) == set(country_sh["sipri_country_name"]),
      "" if set(country_mil["sipri_country_name"]) == set(country_sh["sipri_country_name"])
      else f"difference: {sorted(set(country_mil['sipri_country_name']) ^ set(country_sh['sipri_country_name']))}")
check("No duplicate entity names in raw data", not country_mil["sipri_country_name"].duplicated().any() and not country_sh["sipri_country_name"].duplicated().any())

# --- (2) 원본 대비 건수 -----------------------------------
print("\n[2] Value counts vs. raw data (numeric cells = result rows)")
def numeric_cells(d):
    return int(d[YEARS1].apply(pd.to_numeric, errors="coerce").notna().sum().sum())

n_raw_mil, n_raw_sh = numeric_cells(country_mil), numeric_cells(country_sh)
check("Expenditure row count matches", n_raw_mil == len(mil_all), f"raw numeric cells {n_raw_mil:,} = converted {len(mil_all):,} (after removing aggregates {len(mil):,})")
check("GDP-share row count matches", n_raw_sh == len(sh_all), f"raw numeric cells {n_raw_sh:,} = converted {len(sh_all):,} (after removing aggregates {len(sh):,})")

# 값 검증: 표본이 아니라 전체 값을 비교 (원본 값 × 배수 = 결과 값)
def compare_values(raw_country, out_df, col, mult, tol):
    r = raw_country.melt("sipri_country_name", YEARS1, "year", "raw")
    r["raw"] = pd.to_numeric(r["raw"], errors="coerce")
    r = r.dropna(subset=["raw"])
    j = r.merge(out_df, on=["sipri_country_name", "year"], how="inner")
    diff = (j["raw"] * mult - j[col]).abs()
    return len(j), int((diff > tol).sum())

n1, bad1 = compare_values(country_mil, mil, MIL_COL, 1e6, 0.5)      # 달러 반올림 오차 허용
n2, bad2 = compare_values(country_sh, sh, SH_COL, 100, 1e-6)
check("Expenditure values: all rows match (raw US$ m x 1e6)", bad1 == 0, f"{n1:,} compared, {bad1} mismatches")
check("GDP-share values: all rows match (raw ratio x 100)", bad2 == 0, f"{n2:,} compared, {bad2} mismatches")

# --- (3) 국가 수 ---------------------------------------
print("\n[3] Number of countries")
agg_found = sorted(set(mil_all["sipri_country_name"]) & EXCLUDE_AGGREGATES)
info(f"Aggregate rows removed: {agg_found if agg_found else 'none'}")
n_mil_c, n_sh_c = mil["sipri_country_name"].nunique(), sh["sipri_country_name"].nunique()
no_data_mil = sorted(set(country_mil["sipri_country_name"]) - set(mil_all["sipri_country_name"]) - EXCLUDE_AGGREGATES)
no_data_sh = sorted(set(country_sh["sipri_country_name"]) - set(sh_all["sipri_country_name"]) - EXCLUDE_AGGREGATES)
info(f"Of {len(country_mil) - len(agg_found)} raw country rows, countries with 2015~2025 values: expenditure {n_mil_c} / GDP share {n_sh_c}")
info(f"Countries dropped because they have no 2015~2025 value: expenditure {len(no_data_mil)}, GDP share {len(no_data_sh)}")
if no_data_mil:
    info(f"  dropped (expenditure): {no_data_mil}")
check("Countries in result + dropped countries = raw country rows (expenditure)",
      n_mil_c + len(no_data_mil) == len(country_mil) - len(agg_found),
      f"{n_mil_c} + {len(no_data_mil)} = {len(country_mil) - len(agg_found)}")
only_mil = sorted(set(mil["sipri_country_name"]) - set(sh["sipri_country_name"]))
only_sh = sorted(set(sh["sipri_country_name"]) - set(mil["sipri_country_name"]))
info(f"Only in expenditure: {len(only_mil)} {only_mil} / only in GDP share: {len(only_sh)} {only_sh}")

print("\n   Countries with values, by year")
yc = pd.DataFrame({"expenditure": mil.groupby("year")["sipri_country_name"].nunique(),
                   "gdp_share": sh.groupby("year")["sipri_country_name"].nunique()})
print(yc.T.to_string())
check("Every year has data", len(yc) == len(YEARS1) and (yc > 0).all().all(), f"{len(yc)} years")
mx, mn = int(yc["expenditure"].max()), int(yc["expenditure"].min())
check("Country count per year is stable (max - min <= 10)", mx - mn <= 10, f"max {mx} / min {mn}")

# --- (4) 데이터 품질 ----------------------------------------------
print("\n[4] Data quality")
check("No duplicate (sipri_country_name, year)", not mil.duplicated(["sipri_country_name", "year"]).any() and not sh.duplicated(["sipri_country_name", "year"]).any())
check("No missing values", mil[[MIL_COL]].notna().all().all() and sh[[SH_COL]].notna().all().all())
check("No negative values", (mil[MIL_COL] >= 0).all() and (sh[SH_COL] >= 0).all())
check("No leading/trailing spaces in names", (mil["sipri_country_name"] == mil["sipri_country_name"].str.strip()).all() and (sh["sipri_country_name"] == sh["sipri_country_name"].str.strip()).all())
check("Years within 2015~2025", mil["year"].between(2015, 2025).all() and sh["year"].between(2015, 2025).all())
zero_m, zero_s = int((mil[MIL_COL] == 0).sum()), int((sh[SH_COL] == 0).sum())
info(f"Rows with value 0: expenditure {zero_m} / GDP share {zero_s} (SIPRI reports 0; either truly 0 or rounded)")

# --- (5) 단위와 크기 -------------------------------------------
print("\n[5] Units and scale (US$ m x 1e6, ratio x 100)")
def val(df, ent, year, col):
    s = df[(df["sipri_country_name"] == ent) & (df["year"] == year)][col]
    return s.iloc[0] if len(s) else None

us_m, us_s = val(mil, "United States of America", 2024, MIL_COL), val(sh, "United States of America", 2024, SH_COL)
kr_m = val(mil, "Korea, South", 2024, MIL_COL)
check("US 2024 expenditure is in US$ (0.5 ~ 2 trillion)", us_m is not None and 5e11 <= us_m <= 2e12, f"{us_m:,.0f}" if us_m else "no US data")
check("South Korea 2024 expenditure is in US$ (30 ~ 80 billion)", kr_m is not None and 3e10 <= kr_m <= 8e10, f"{kr_m:,.0f}" if kr_m else "no Korea data")
check("US 2024 GDP share is in % (1 ~ 10)", us_s is not None and 1 <= us_s <= 10, f"{us_s:.2f}%" if us_s else "no US data")
check("GDP share within 0~100%", sh[SH_COL].between(0, 100).all(), f"min {sh[SH_COL].min():.4f} / median {sh[SH_COL].median():.2f} / max {sh[SH_COL].max():.2f}")
check("No floating-point noise in GDP share (6 decimals)", (sh[SH_COL].round(6) == sh[SH_COL]).all())
high = sh[sh[SH_COL] > 20][["sipri_country_name", "year", SH_COL]]
if len(high):
    info(f"GDP share above 20%: {len(high)} rows (war / conflict countries; check the raw values): {sorted(set(high['sipri_country_name']))}")
# 전년 대비 급변 (3배 이상 증가 또는 1/3 이하 감소)
w = mil.pivot(index="sipri_country_name", columns="year", values=MIL_COL)
ratio = (w / w.shift(1, axis=1)).stack()
jump = ratio[(ratio >= 3) | (ratio <= 1 / 3)]
info(f"Year-on-year jumps (>=3x or <=1/3): {len(jump)}" + (f": {sorted(set(i[0] for i in jump.index))}" if len(jump) else ""))

# --- (6) 국가 마스터 대조 --------------------------------
print("\n[6] Against the country master (country_map_master.csv)")
if os.path.exists(MASTER_FILE):
    master = pd.read_csv(MASTER_FILE, encoding="utf-8-sig", keep_default_na=False)
    names = master["sipri_milex_country_name"].str.split(" \\| ")
    master_ents = {n.strip() for lst in names for n in lst if n.strip()}
    raw_names = set(country_mil["sipri_country_name"])
    check("SIPRI expenditure names in the master match the raw data",
          master_ents <= raw_names, "" if master_ents <= raw_names else f"mismatch: {sorted(master_ents - raw_names)}")
    have = master[master["sipri_milex_country_name"].apply(lambda x: any(n.strip() in set(mil['sipri_country_name']) for n in x.split(' | ')) if x else False)]
    miss = master[~master["iso_a3"].isin(have["iso_a3"])]
    info(f"Of {len(master)} master countries, {len(have)} have expenditure data (2015~2025)")
    if len(miss):
        info(f"{len(miss)} master countries without data: {miss['iso_official_country_name'].tolist()}")
    out_of_scope = sorted(set(mil["sipri_country_name"]) - master_ents)
    info(f"{len(out_of_scope)} countries are in the data but not in the master (dashboard scope) -> removed when joining with the master")
else:
    info("country_map_master.csv not found - skipping master checks (run build_country_map.py first)")

# --- (7) 최종 통합 데이터 검증 (저장 파일은 만들지 않고 결과만 출력) ---------------------
print("\n[7] 최종 통합 데이터 (military_expenditure.csv)")
if os.path.exists(MASTER_FILE):
    m7 = pd.read_csv(MASTER_FILE, encoding="utf-8-sig", keep_default_na=False)
    iso7 = set(m7["iso_a3"]) - {"KOR"}                  # 최종 결과에서 한국은 제외했으므로 검증 기준에서도 뺌
    n_exp = len(iso7) * len(YEARS1)
    check("열 구성이 설계와 같음", list(merged_out.columns) == SAVE_COLS, str(list(merged_out.columns)))
    check("행 수 = 마스터 국가 수 × 연도 수", len(merged_out) == n_exp, f"{len(merged_out):,}행 = {len(iso7)}개국 × {len(YEARS1)}년")
    check("(iso_a3, year) 중복 없음", not merged_out.duplicated(["iso_a3", "year"]).any())
    check("마스터 국가가 모두 포함되고 마스터 밖 국가는 없음", set(merged_out["iso_a3"]) == iso7,
          f"차이: {sorted(set(merged_out['iso_a3']) ^ iso7)}" if set(merged_out["iso_a3"]) != iso7 else f"{len(iso7)}개국")
    check("연도가 2015~2025 전체를 국가마다 한 번씩 가짐", (merged_out.groupby("iso_a3")["year"].apply(lambda s: sorted(s) == YEARS1)).all())
    # 앞서 검증한 SIPRI 값은 그대로 두고, 결측 처리로 채운 행만 늘어났는지
    n_mil, n_sh = int(merged_out[MIL_COL].notna().sum()), int(merged_out[SH_COL].notna().sum())
    check("군사비 유효값 수 = SIPRI 검증값 + 결측 처리로 채운 값", n_mil == int((mil_out["iso_a3"] != "KOR").sum()) + N_IMPUTED,
          f"최종 {n_mil:,}건 = SIPRI(한국 제외) {int((mil_out['iso_a3'] != 'KOR').sum()):,}건 + 채움 {N_IMPUTED}건")
    check("GDP 비중 유효값 수 = SIPRI 검증값 + 결측 처리로 채운 값", n_sh == int((sh_out["iso_a3"] != "KOR").sum()) + N_IMPUTED,
          f"최종 {n_sh:,}건 = SIPRI(한국 제외) {int((sh_out['iso_a3'] != 'KOR').sum()):,}건 + 채움 {N_IMPUTED}건")
    j1 = merged_out.merge(mil_out[SAVE_MIL], on=["iso_a3", "year"], suffixes=("", "_chk")).dropna(subset=[MIL_COL])
    j2 = merged_out.merge(sh_out[SAVE_SH], on=["iso_a3", "year"], suffixes=("", "_chk")).dropna(subset=[SH_COL])
    check("SIPRI 군사비 값이 최종 표에 그대로 들어감 (결측 처리가 덮어쓰지 않음)", (j1[MIL_COL] == j1[MIL_COL + "_chk"]).all(), f"{len(j1):,}건 비교")
    check("SIPRI GDP 비중 값이 최종 표에 그대로 들어감 (결측 처리가 덮어쓰지 않음)", (j2[SH_COL] == j2[SH_COL + "_chk"]).all(), f"{len(j2):,}건 비교")
    check("값 범위가 정상 (군사비 0 이상, GDP 비중 0~100%)",
          (merged_out[MIL_COL].dropna() >= 0).all() and merged_out[SH_COL].dropna().between(0, 100).all())
    # 저장된 CSV를 다시 읽어 최종 표와 같은지 확인 (읽기만 함)
    f_out = os.path.join(OUTPUT_DIR, "military_expenditure.csv")
    back = pd.read_csv(f_out, encoding="utf-8-sig", keep_default_na=True, na_values=["NaN"])
    same = (list(back.columns) == list(merged_out.columns) and len(back) == len(merged_out)
            and back["iso_a3"].astype(str).tolist() == merged_out["iso_a3"].astype(str).tolist()
            and back["year"].tolist() == merged_out["year"].tolist()
            and np.allclose(back[MIL_COL].astype(float), merged_out[MIL_COL].astype(float), equal_nan=True, rtol=0, atol=0.5)
            and np.allclose(back[SH_COL].astype(float), merged_out[SH_COL].astype(float), equal_nan=True, rtol=0, atol=1e-6))
    check("저장된 CSV를 다시 읽어도 최종 표와 같음 (NaN 포함)", same, f_out)
    check("군사비와 GDP 비중의 결측 위치가 같음", (merged_out[MIL_COL].isna() == merged_out[SH_COL].isna()).all(),
          "" if (merged_out[MIL_COL].isna() == merged_out[SH_COL].isna()).all() else "두 열의 결측 위치가 다른 국가가 있음")
    # 결측 처리 결과: 처리 대상 국가에 결측이 남지 않았고, 남은 결측은 근거 자료가 없는 국가뿐인지
    cnt = merged_out.groupby("iso_a3")[[MIL_COL, SH_COL]].count()
    ko = m7.set_index("iso_a3")["country_name_ko"]
    left_c = sorted(c for c in cnt.index if cnt.loc[c, MIL_COL] < len(YEARS1))
    done_ok = all(cnt.loc[c, MIL_COL] == len(YEARS1) for c in IMPUTE_LAST_YEAR + IMPUTE_GDP_BASED if c in cnt.index)
    check("결측 처리 대상 국가(MMR, QAT, ARE)에 결측이 남지 않음", done_ok,
          "" if done_ok else str({c: int(cnt.loc[c, MIL_COL]) for c in IMPUTE_LAST_YEAR + IMPUTE_GDP_BASED}))
    uzb_left = merged_out.loc[(merged_out["iso_a3"] == UZB_CODE) & merged_out[MIL_COL].isna(), "year"].tolist()
    check("UZB는 2015년만 결측으로 남음 (성장률 추정은 2016~2025년)", uzb_left == [2015], f"결측 연도: {uzb_left}")
    check("남은 결측은 근거 자료가 없는 국가(DJI, LAO, PRK)와 UZB 2015년뿐", left_c == ["DJI", "LAO", "PRK", "UZB"], f"{[f'{ko[c]}({c})' for c in left_c]}")
    info(f"전체 연도 데이터 있는 국가: {int((cnt[MIL_COL] == len(YEARS1)).sum())}개국 / {len(cnt)}개국")
    info(f"최종 결측 건수: 군사비 {int(merged_out[MIL_COL].isna().sum())}건 / GDP 비중 {int(merged_out[SH_COL].isna().sum())}건 (전체 {len(merged_out):,}행)")
else:
    info("country_map_master.csv가 없어 최종 데이터 검증을 건너뜀 (build_country_map.py를 먼저 실행하세요)")

# --- 요약 ----------------------------------------------------------
rep = pd.DataFrame(RESULTS)
n_fail = int((rep["result"] == "FAIL").sum())
print("\n" + "=" * 60)
print(f"검증 결과: 전체 {len(rep)}개 중 PASS {len(rep) - n_fail} / FAIL {n_fail}")
print("=" * 60)
if n_fail:
    print(rep[rep["result"] == "FAIL"].to_string(index=False))
# %%
