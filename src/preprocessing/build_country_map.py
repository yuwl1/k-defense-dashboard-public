# %%
"""build_country_map.py
무기 수출입 대시보드용 국가 매핑 테이블을 만든다.
  [중간 산출물] temp/sipri_countries.csv    : SIPRI 국가명 -> country_name_en(표시명), iso_official_country_name, iso_a3
  [중간 산출물] temp/country_info_names.csv : 국가정보 폴더 파일 -> country_name_en, iso_official_country_name, iso_a3
  [중간 산출물] temp/ISO_3166_ref.csv       : ISO 3166 참조표 (pycountry가 없는 PC용)
  [최종] country_map_master.csv : 대시보드 대상 국가, iso_a3당 1행 (iso_a3, ISO 공식명, 한글명, SIPRI 군사비·무기거래 국가명, GPI 국가명)
                                  = 국가정보 폴더 국가 + 대한민국(home) + 북한(target)
                                    - SIPRI 데이터가 없는 국가 - EXCLUDE_FROM_MASTER(세이셸, 피지, 쿠바)
  [최종] temp/country_alias_map.csv : SIPRI 국가명(별칭) -> iso_a3, category (이름은 마스터에서 가져옴)
이름 규칙: iso_official_country_name = ISO 3166-1 국가명(pycountry .name), country_name_en = ISO common_name 우선(표시명)
"""
# %%
import os, sys
import pandas as pd

# ===== 경로 (환경에 맞게 수정) =====
SIPRI_DIR   = r"C:\Users\user\Desktop\k-defense-dashboard\data\raw"
GPI_DIR    = r"C:\Users\user\Desktop\k-defense-dashboard\data\raw"      # GPI_Public_Release_2026.xlsx 위치

def find_file(folder, patterns):
    """파일명 패턴으로 파일을 찾는다 (원본/프로젝트 파일명 모두 대응, 대소문자 무시)."""
    import fnmatch
    files = os.listdir(folder)
    for pat in patterns:
        for f in sorted(files):
            if fnmatch.fnmatch(f.lower(), pat.lower()):
                return os.path.join(folder, f)
    raise FileNotFoundError(f"No file matching {patterns} in {folder}\nFiles in folder: {files}")

MILEX = TRADE_FILES = None
COUNTRY_DIR = r"C:\Users\user\Desktop\k-defense-dashboard\data\raw\country_info"
# 국가 매핑 파일 저장 경로
OUT = os.path.join(os.path.dirname(SIPRI_DIR), "mapping")
MASTER_COLS = ["iso_a3", "iso_official_country_name", "country_name_ko", "sipri_milex_country_name", "sipri_trade_country_name", "gpi_country_name"]
if MILEX is None:   # 파일 경로/이름 자동 탐색
    MILEX = find_file(SIPRI_DIR, ["sipri_milex*.xlsx", "SIPRI-Milex-data*.xlsx"])
    TRADE_FILES = [find_file(SIPRI_DIR, ["sipri_trade_1950*.csv", "trade-register-1950*.csv"]),
                   find_file(SIPRI_DIR, ["sipri_trade.csv", "trade-register.csv"])]
    print("Milex :", MILEX); print("Trade :", TRADE_FILES)
try:   # Global Peace Index ("Overall Scores" 시트, country·geocode 열) - 선택 파일: 없으면 gpi_country_name은 빈 값
    GPI_FILE = find_file(GPI_DIR, ["GPI_Public_Release_*.xlsx", "GPI*.xlsx"])
    print("GPI   :", GPI_FILE)
except FileNotFoundError:
    GPI_FILE = None
    print("WARNING: GPI file (GPI_Public_Release_*.xlsx) not found in", GPI_DIR, "- gpi_country_name will be empty")
WORK = f"{OUT}/temp"
os.makedirs(WORK, exist_ok=True)

# ---------------------------------------------------------------
# 영문 표준명 / iso_a3 조회표 (SIPRI 표기 -> (표준 영문명, iso_a3))
# 이름은 ISO 3166-1 기반 일반 약칭이고, 옛 국가는 ISO 3166-3 코드를 쓴다.
# ---------------------------------------------------------------
STD = {}
def add(code, std, *aliases):
    for a in (std,) + aliases:
        STD[a] = (std, code)

for code, std, *al in [
 ("AFG","Afghanistan"),("ALB","Albania"),("DZA","Algeria"),("AGO","Angola"),("ATG","Antigua and Barbuda"),
 ("ARG","Argentina"),("ARM","Armenia"),("ABW","Aruba"),("AUS","Australia"),("AUT","Austria"),
 ("AZE","Azerbaijan"),("BHS","Bahamas"),("BHR","Bahrain"),("BGD","Bangladesh"),("BRB","Barbados"),
 ("BLR","Belarus"),("BEL","Belgium"),("BLZ","Belize"),("BEN","Benin"),("BTN","Bhutan"),
 ("BOL","Bolivia"),("BIH","Bosnia and Herzegovina","Bosnia-Herzegovina"),("BWA","Botswana"),
 ("BRA","Brazil"),("BRN","Brunei"),("BGR","Bulgaria"),("BFA","Burkina Faso"),("BDI","Burundi"),
 ("CPV","Cabo Verde","Cape Verde"),("KHM","Cambodia"),("CMR","Cameroon"),("CAN","Canada"),
 ("CAF","Central African Republic"),("TCD","Chad"),("CHL","Chile"),("CHN","China"),("COL","Colombia"),
 ("COM","Comoros"),("COG","Congo","Congo, Republic"),("COD","DR Congo","Congo, DR"),
 ("CRI","Costa Rica"),("CIV","Cote d'Ivoire"),("HRV","Croatia"),("CUB","Cuba"),("CYP","Cyprus"),
 ("CZE","Czechia"),("DNK","Denmark"),("DJI","Djibouti"),("DOM","Dominican Republic"),
 ("ECU","Ecuador"),("EGY","Egypt"),("SLV","El Salvador"),("GNQ","Equatorial Guinea"),("ERI","Eritrea"),
 ("EST","Estonia"),("SWZ","Eswatini","eSwatini"),("ETH","Ethiopia"),("FJI","Fiji"),("FIN","Finland"),
 ("FRA","France"),("GAB","Gabon"),("GMB","Gambia","Gambia, The"),("GEO","Georgia"),("DEU","Germany"),
 ("GHA","Ghana"),("GRC","Greece"),("GRD","Grenada"),("GTM","Guatemala"),("GIN","Guinea"),
 ("GNB","Guinea-Bissau"),("GUY","Guyana"),("HTI","Haiti"),("HND","Honduras"),("HKG","Hong Kong"),
 ("HUN","Hungary"),("ISL","Iceland"),("IND","India"),("IDN","Indonesia"),("IRN","Iran"),("IRQ","Iraq"),
 ("IRL","Ireland"),("ISR","Israel"),("ITA","Italy"),("JAM","Jamaica"),("JPN","Japan"),("JOR","Jordan"),
 ("KAZ","Kazakhstan"),("KEN","Kenya"),("XKX","Kosovo"),("KWT","Kuwait"),("KGZ","Kyrgyzstan","Kyrgyz Republic"),
 ("LAO","Laos"),("LVA","Latvia"),("LBN","Lebanon"),("LSO","Lesotho"),("LBR","Liberia"),("LBY","Libya"),
 ("LTU","Lithuania"),("LUX","Luxembourg"),("MDG","Madagascar"),("MWI","Malawi"),("MYS","Malaysia"),
 ("MDV","Maldives"),("MLI","Mali"),("MLT","Malta"),("MRT","Mauritania"),("MUS","Mauritius"),
 ("MEX","Mexico"),("MDA","Moldova"),("MNG","Mongolia"),("MNE","Montenegro"),("MAR","Morocco"),
 ("MOZ","Mozambique"),("MMR","Myanmar"),("NAM","Namibia"),("NPL","Nepal"),("NLD","Netherlands"),
 ("NZL","New Zealand"),("NIC","Nicaragua"),("NER","Niger"),("NGA","Nigeria"),
 ("PRK","North Korea","Korea, North"),("MKD","North Macedonia"),("NOR","Norway"),("OMN","Oman"),
 ("PAK","Pakistan"),("PSE","Palestine"),("PAN","Panama"),("PNG","Papua New Guinea"),("PRY","Paraguay"),
 ("PER","Peru"),("PHL","Philippines"),("POL","Poland"),("PRT","Portugal"),("QAT","Qatar"),
 ("ROU","Romania"),("RUS","Russia"),("RWA","Rwanda"),("KNA","Saint Kitts and Nevis"),
 ("VCT","Saint Vincent and the Grenadines","Saint Vincent"),("SAU","Saudi Arabia"),("SEN","Senegal"),
 ("SRB","Serbia"),("SYC","Seychelles"),("SLE","Sierra Leone"),("SGP","Singapore"),("SVK","Slovakia"),
 ("SVN","Slovenia"),("SLB","Solomon Islands"),("SOM","Somalia"),("ZAF","South Africa"),
 ("KOR","South Korea","Korea, South"),("SSD","South Sudan"),("ESP","Spain"),("LKA","Sri Lanka"),
 ("SDN","Sudan"),("SUR","Suriname"),("SWE","Sweden"),("CHE","Switzerland"),("SYR","Syria"),
 ("TWN","Taiwan"),("TJK","Tajikistan"),("TZA","Tanzania"),("THA","Thailand"),
 ("TLS","Timor-Leste","Timor Leste"),("TGO","Togo"),("TON","Tonga"),("TTO","Trinidad and Tobago"),
 ("TUN","Tunisia"),("TUR","Turkiye","Türkiye"),("TKM","Turkmenistan"),("UGA","Uganda"),("UKR","Ukraine"),
 ("ARE","United Arab Emirates"),("GBR","United Kingdom"),("USA","United States","United States of America"),
 ("URY","Uruguay"),("UZB","Uzbekistan"),("VUT","Vanuatu"),("VEN","Venezuela"),("VNM","Viet Nam"),
 ("ESH","Western Sahara"),("YEM","Yemen"),("ZMB","Zambia"),("ZWE","Zimbabwe"),
 # 옛 국가: ISO 3166-3 코드
 ("CSK","Czechoslovakia"),("SUN","USSR","Soviet Union"),("YUG","Yugoslavia"),
 ("DDR","German Democratic Republic","East Germany (GDR)"),("VDR","South Vietnam"),
 ("YMD","South Yemen"),("YAR","North Yemen","Yemen Arab Republic (North Yemen)","Yemen, North"),
]:
    add(code, std, *al)

def code_of(name):
    """SIPRI/국가정보 표기 -> iso_a3 (모르면 '')"""
    return STD.get(str(name).strip(), ("", ""))[1]

# ---------------------------------------------------------------
# ISO 3166 참조 데이터 로드
#   1순위 pycountry, 2순위 Debian iso-codes JSON, 3순위 ISO_3166_ref.csv
# ---------------------------------------------------------------
def load_iso():
    rows = []
    try:
        import pycountry
        for c in pycountry.countries:
            rows.append(dict(iso_a3=c.alpha_3, iso_n3=c.numeric, name=c.name,
                             common=getattr(c, "common_name", ""), official=getattr(c, "official_name", "")))
        hist = {c.alpha_3: c.name for c in pycountry.historic_countries}
    except ImportError:
        import json
        p1 = "/usr/share/iso-codes/json/iso_3166-1.json"
        if os.path.exists(p1):
            for c in json.load(open(p1, encoding="utf-8"))["3166-1"]:
                rows.append(dict(iso_a3=c["alpha_3"], iso_n3=c["numeric"], name=c["name"],
                                 common=c.get("common_name", ""), official=c.get("official_name", "")))
            hist = {c["alpha_3"]: c["name"] for c in json.load(
                open("/usr/share/iso-codes/json/iso_3166-3.json", encoding="utf-8"))["3166-3"]}
        else:
            ref_path = os.path.join(WORK, "ISO_3166_ref.csv") if os.path.exists(os.path.join(WORK, "ISO_3166_ref.csv")) else "ISO_3166_ref.csv"
            ref = pd.read_csv(ref_path, encoding="utf-8-sig", keep_default_na=False, dtype=str)
            rows = [dict(iso_a3=r.iso_a3, iso_n3=r.iso_n3, name=r.iso_official_country_name, common=r.iso_common_country_name, official=r.iso_formal_country_name)
                    for r in ref.itertuples()]
            hist = {}
            for r in ref.itertuples():
                if r.iso_n3 == "":
                    hist[r.iso_a3] = r.iso_official_country_name
    return pd.DataFrame(rows).set_index("iso_a3"), hist

ISO, HIST = load_iso()
# 표시명 = ISO common_name 우선, 없으면 ISO 공식 약칭. 예외는 아래 DISPLAY_OVERRIDE에서만 지정
DISPLAY_OVERRIDE = {"RUS": "Russia", "VNM": "Viet Nam", "COD": "DR Congo", "PSE": "Palestine"}   # SIPRI·KOTRA 표기에 맞춤 (예: Russian Federation -> Russia)

FORMER_NAME = {"CSK": "Czechoslovakia", "SUN": "USSR", "YUG": "Yugoslavia", "DDR": "East Germany",
               "VDR": "South Vietnam", "YMD": "South Yemen", "YAR": "North Yemen", "XKX": "Kosovo"}

def iso_official(code):
    if code in ISO.index:  return ISO.at[code, "name"]
    if code in HIST:       return HIST[code]            # 옛 국가: ISO 3166-3 국가명
    return ""                                           # ISO에 없음 (예: 코소보 XKX)

def display_name(code, fallback=""):
    if code in DISPLAY_OVERRIDE: return DISPLAY_OVERRIDE[code]
    if code in ISO.index:
        return ISO.at[code, "common"] or ISO.at[code, "name"]
    return FORMER_NAME.get(code, fallback)               # 옛 국가/ISO 비등록 국가: 코드당 대표 이름 하나

def iso_n3(code):
    return ISO.at[code, "iso_n3"] if code in ISO.index else ""

FORMER = {"CSK", "SUN", "YUG", "DDR", "VDR", "YMD", "YAR"}   # 옛 국가 코드

def classify(n):
    if n.endswith("**") or n == "European Union": return "international_org"
    if n.endswith("*") or n.startswith("unknown"): return "non_state_or_unknown"
    if code_of(n) in HIST or code_of(n) in FORMER: return "former_state"
    return "country"

# home/target 국가 (대한민국·북한): 국가정보 폴더에 없어 대시보드용으로 추가
HOME = {"KOR": ("대한민국", "home"), "PRK": ("북한", "target")}   # 북한은 target 국가

# 국가정보 폴더에는 없지만 SIPRI·GPI 데이터가 있는 한국 무기 수입국 (대시보드용으로 추가)
EXTRA_COUNTRIES = {"NOR": ("노르웨이", "target"), "EST": ("에스토니아", "target"), "URY": ("우루과이", "target")}

# 마스터에서 제외할 국가: 위험국가 데이터에 없음 {iso_a3: 한글명}
EXCLUDE_FROM_MASTER = {"SYC": "세이셸", "FJI": "피지", "CUB": "쿠바"}

# ---------------------------------------------------------------
# 1단계: SIPRI 국가명 -> temp/sipri_countries.csv
# ---------------------------------------------------------------
REGION_HEADERS = {"Africa","North Africa","sub-Saharan Africa","Americas","Central America and the Caribbean",
    "North America","South America","Asia & Oceania","Oceania","South Asia","East Asia","South East Asia",
    "Central Asia","Europe","Central Europe","Eastern Europe","Western Europe","Middle East"}

def sipri_names():
    names = []
    m = pd.read_excel(MILEX, sheet_name="Constant (2024) US$", header=None)
    for v in m.iloc[6:, 0].dropna():
        v = str(v).strip()
        if v not in REGION_HEADERS:
            names.append(v)
    for p in TRADE_FILES:
        t = pd.read_csv(p, encoding="cp1252", skiprows=11)
        for c in ("Recipient", "Supplier"):
            names += t[c].dropna().astype(str).str.strip().tolist()
    return sorted(set(names), key=lambda x: (x.lower(), x))   # 실행마다 순서가 같도록 정렬 기준을 추가

def step1():
    df = pd.DataFrame({"sipri_country_name": sipri_names()})
    df["iso_a3"] = df["sipri_country_name"].map(code_of)
    df["country_name_en"] = [display_name(c, n) if c else "" for n, c in zip(df["sipri_country_name"], df["iso_a3"])]
    df["iso_official_country_name"] = df["iso_a3"].map(iso_official)
    df = df[["sipri_country_name", "country_name_en", "iso_official_country_name", "iso_a3"]]
    df.to_csv(f"{WORK}/sipri_countries.csv", index=False, encoding="utf-8-sig")
    return pd.read_csv(f"{WORK}/sipri_countries.csv", encoding="utf-8-sig", keep_default_na=False)

# ---------------------------------------------------------------
# 2단계: 국가정보 폴더 -> temp/country_info_names.csv
# ---------------------------------------------------------------
KR = {  # 국가정보 파일명(한글) -> 영문명 (STD 조회 키)
 "가나":"Ghana","과테말라":"Guatemala","그리스":"Greece","나미비아":"Namibia","나이지리아":"Nigeria",
 "남아프리카공화국":"South Africa","네덜란드":"Netherlands","뉴질랜드":"New Zealand","대만":"Taiwan",
 "덴마크":"Denmark","도미니카공화국":"Dominican Republic","독일":"Germany","라오스":"Laos","루마니아":"Romania",
 "르완다":"Rwanda","말라위":"Malawi","말레이시아":"Malaysia","멕시코":"Mexico","모로코":"Morocco",
 "모잠비크":"Mozambique","몬테네그로":"Montenegro","몽골":"Mongolia","미국":"United States","미얀마":"Myanmar",
 "방글라데시":"Bangladesh","베트남":"Viet Nam","벨기에":"Belgium","벨라루스":"Belarus","보츠와나":"Botswana",
 "부룬디":"Burundi","불가리아":"Bulgaria","브라질":"Brazil","사우디아라비아":"Saudi Arabia","세네갈":"Senegal",
 "세르비아":"Serbia","세이셸":"Seychelles","스리랑카":"Sri Lanka","스웨덴":"Sweden","스위스":"Switzerland",
 "스페인":"Spain","슬로바키아":"Slovakia","싱가포르":"Singapore","아랍에미리트":"United Arab Emirates",
 "아르헨티나":"Argentina","아제르바이잔":"Azerbaijan","알제리":"Algeria","에콰도르":"Ecuador",
 "에티오피아":"Ethiopia","영국":"United Kingdom","오만":"Oman","오스트리아":"Austria","요르단":"Jordan",
 "우간다":"Uganda","우즈베키스탄":"Uzbekistan","우크라이나":"Ukraine","이라크":"Iraq","이스라엘":"Israel",
 "이집트":"Egypt","이탈리아":"Italy","인도":"India","인도네시아":"Indonesia","일본":"Japan","잠비아":"Zambia",
 "조지아":"Georgia","중국":"China","지부티":"Djibouti","짐바브웨":"Zimbabwe","체코":"Czechia","칠레":"Chile",
 "카자흐스탄":"Kazakhstan","카타르":"Qatar","캄보디아":"Cambodia","캐나다":"Canada","케냐":"Kenya",
 "코트디부아르":"Cote d'Ivoire","콜롬비아":"Colombia","쿠바":"Cuba","쿠웨이트":"Kuwait","크로아티아":"Croatia",
 "키르기스스탄":"Kyrgyzstan","탄자니아":"Tanzania","태국":"Thailand","튀니지":"Tunisia","튀르키예":"Turkiye",
 "파나마":"Panama","파라과이":"Paraguay","파키스탄":"Pakistan","페루":"Peru","포르투갈":"Portugal",
 "폴란드":"Poland","프랑스":"France","피지":"Fiji","핀란드":"Finland","필리핀":"Philippines","헝가리":"Hungary",
 "호주":"Australia","러시아연방":"Russia","홍콩":"Hong Kong",
}


def step2():
    if os.path.isdir(COUNTRY_DIR):
        files = sorted(os.listdir(COUNTRY_DIR))
    df = pd.DataFrame({"file_name": files})
    df["country_name_ko"] = df["file_name"].map(lambda x: os.path.splitext(x)[0].strip())
    df["iso_a3"] = df["country_name_ko"].map(lambda k: code_of(KR.get(k, "")))
    df["country_name_en"] = df["iso_a3"].map(display_name)
    df["iso_official_country_name"] = df["iso_a3"].map(iso_official)
    df = df[["file_name", "country_name_ko", "country_name_en", "iso_official_country_name", "iso_a3"]]
    df.to_csv(f"{WORK}/country_info_names.csv", index=False, encoding="utf-8-sig")
    return pd.read_csv(f"{WORK}/country_info_names.csv", encoding="utf-8-sig", keep_default_na=False)

# ---------------------------------------------------------------
# SIPRI 프로필: iso_a3당 1행 (대륙, 하위 지역, 파일별 SIPRI 국가명, 데이터 유무 플래그)
#   * 금액·거래량 같은 연도별 숫자는 넣지 않고 별도 표로 관리한다
#   * 플래그는 파일 전체 기간(군사비 1949~2025, 무기거래 1950~2025) 기준이다. has_milex는 숫자 값이 하나라도 있어야 Y ("...", "xxx"는 값이 아님)
# ---------------------------------------------------------------
CONTINENTS = {"Africa", "Americas", "Asia & Oceania", "Europe", "Middle East"}

def gpi_profile():
    """iso_a3별 GPI 국가명 (키: geocode, 'Overall Scores' 시트). 열: gpi_country_name, has_gpi"""
    if GPI_FILE is None:
        return pd.DataFrame(columns=["gpi_country_name", "has_gpi"])
    g = pd.read_excel(GPI_FILE, sheet_name="Overall Scores", header=None)
    hdr = g.index[(g.iloc[:, 0].astype(str).str.strip() == "country") & (g.iloc[:, 1].astype(str).str.strip() == "geocode")]   # 헤더 행 (country | geocode | 2008_Score ...)
    if len(hdr) == 0:
        raise KeyError("GPI sheet 'Overall Scores' needs a header row with 'country' and 'geocode' in the first two columns")
    g = g.iloc[hdr[0] + 1:, :2].copy()
    g.columns = ["country", "geocode"]
    g = g.dropna(subset=["country", "geocode"])
    g["country"] = g["country"].astype(str).str.strip()
    g["geocode"] = g["geocode"].astype(str).str.strip()
    out = g.groupby("geocode")["country"].agg(lambda s: " | ".join(sorted(set(s)))).to_frame("gpi_country_name")
    out["has_gpi"] = "Y"
    return out

def sipri_profile():
    m = pd.read_excel(MILEX, sheet_name="Constant (2024) US$", header=None)
    ncol = m.shape[1]
    rows, continent, sub = [], "", ""
    for i in range(6, len(m)):
        name = m.iat[i, 0]
        if pd.isna(name):
            continue
        name = str(name).strip()
        if not m.iloc[i, 3:ncol].notna().any():          # 데이터 없는 행 = 지역 제목 행
            if name in CONTINENTS: continent, sub = name, ""
            else: sub = name
            continue
        c = code_of(name)
        has_val = bool(m.iloc[i, 3:ncol].apply(pd.to_numeric, errors="coerce").notna().any())   # "...", "xxx"는 값이 아님
        if c:
            rows.append({"iso_a3": c, "sipri_milex_country_name": name, "continent": continent, "subregion": sub, "has": has_val})
    mil = pd.DataFrame(rows).groupby("iso_a3").agg(
        sipri_milex_country_name=("sipri_milex_country_name", lambda s: " | ".join(sorted(set(s)))),
        continent=("continent", "first"), subregion=("subregion", "first"), has=("has", "max"))

    rec, sup, names = set(), set(), {}
    for p in TRADE_FILES:
        t = pd.read_csv(p, encoding="cp1252", skiprows=11)
        for col, bag in (("Recipient", rec), ("Supplier", sup)):
            for n in t[col].dropna().astype(str).str.strip().unique():
                c = code_of(n)
                if c:
                    bag.add(c); names.setdefault(c, set()).add(n)
    tr = pd.DataFrame({"sipri_trade_country_name": {c: " | ".join(sorted(v)) for c, v in names.items()}})
    prof = mil.join(tr, how="outer")
    prof["has_milex"]   = [("Y" if (c in mil.index and bool(mil.at[c, "has"])) else "N") for c in prof.index]   # 숫자 값이 하나라도 있어야 Y
    prof = prof.drop(columns="has")
    prof["has_import"]   = [("Y" if c in rec else "N") for c in prof.index]
    prof["has_export"]   = [("Y" if c in sup else "N") for c in prof.index]
    prof = prof.fillna("")
    prof.loc[(prof["subregion"] == "") & (prof["continent"] != ""), "subregion"] = prof["continent"]   # 중동은 하위 지역이 없음
    return prof

# ---------------------------------------------------------------
# 3단계: 국가 마스터 + SIPRI 별칭표
# ---------------------------------------------------------------
def step3(c1, c2):
    # (a) 국가 마스터: iso_a3당 1행 (국가정보 폴더 + 대한민국·북한)
    m = c2[["iso_a3", "country_name_ko", "country_name_en", "iso_official_country_name", "file_name"]].rename(columns={"file_name": "country_info_file"}).copy()
    m["role"] = "target"
    home = pd.DataFrame([{"iso_a3": c, "country_name_ko": kr, "country_name_en": display_name(c), "iso_official_country_name": iso_official(c),
                          "country_info_file": "", "role": role} for c, (kr, role) in {**HOME, **EXTRA_COUNTRIES}.items()])
    m = pd.concat([home, m], ignore_index=True)
    m["iso_n3"] = m["iso_a3"].map(iso_n3)
    m = m[["iso_a3", "iso_n3", "country_name_en", "iso_official_country_name", "country_name_ko", "role", "country_info_file"]]
    prof = sipri_profile()
    m = m.merge(prof, left_on="iso_a3", right_index=True, how="left")
    m = m.merge(gpi_profile(), left_on="iso_a3", right_index=True, how="left")
    for c in ["has_milex", "has_import", "has_export", "has_gpi"]:
        m[c] = m[c].fillna("N")
    m = m.fillna("")
    m = m[["iso_a3", "iso_n3", "country_name_en", "iso_official_country_name", "country_name_ko", "role", "continent", "subregion",
           "sipri_milex_country_name", "sipri_trade_country_name", "gpi_country_name", "has_milex", "has_import", "has_export", "has_gpi", "country_info_file"]]
    # SIPRI 데이터가 전혀 없는 국가 제외 (has_milex, has_import, has_export 모두 N)
    no_sipri = (m["has_milex"] == "N") & (m["has_import"] == "N") & (m["has_export"] == "N")
    print("Dropped from master (no SIPRI data):", m.loc[no_sipri, "country_name_ko"].tolist())
    m = m[~no_sipri]
    # 위험국가 데이터에 없는 국가 제외
    excl = m["iso_a3"].isin(EXCLUDE_FROM_MASTER)
    print("Dropped from master (not in risk-country data):", m.loc[excl, "country_name_ko"].tolist())
    m = m[~excl]
    m = m.drop(columns=["has_milex", "has_import", "has_export", "has_gpi"])     # 플래그는 위 필터에만 쓰고 저장하지 않음
    m = m.sort_values(["role", "country_name_ko"], ascending=[True, True])      # home 국가가 맨 위
    m = m[MASTER_COLS]                                                           # 최종 마스터 열만 남김 (위 정렬에서 role 사용)
    m.to_csv(f"{OUT}/country_map_master.csv", index=False, encoding="utf-8-sig")

    # (b) 별칭표: SIPRI 표기 -> iso_a3 (+ category). 영문·한글 이름은 마스터에서 가져옴
    out = c1[["sipri_country_name", "iso_a3"]].copy()
    out["category"] = out["sipri_country_name"].map(classify)
    out.to_csv(f"{WORK}/country_alias_map.csv", index=False, encoding="utf-8-sig")

    # (c) ISO 참조표 (pycountry 없이 재현하기 위함)
    ref = ISO.reset_index()[["iso_a3", "iso_n3", "name", "common", "official"]]
    ref.columns = ["iso_a3", "iso_n3", "iso_official_country_name", "iso_common_country_name", "iso_formal_country_name"]
    hist = pd.DataFrame([{"iso_a3": k, "iso_n3": "", "iso_official_country_name": v, "iso_common_country_name": "", "iso_formal_country_name": ""}
                         for k, v in HIST.items()])
    pd.concat([ref, hist]).to_csv(f"{WORK}/ISO_3166_ref.csv", index=False, encoding="utf-8-sig")
    return m, out

def joined_view(master, alias):
    """분석용 조인: sipri_country_name, iso_official_country_name, iso_a3, country_name_ko (마스터 국가만)"""
    return alias.merge(master, on="iso_a3", how="inner")[["sipri_country_name", "iso_official_country_name", "iso_a3", "country_name_ko"]]

if __name__ == "__main__":
    c1 = step1(); c2 = step2(); master, c3 = step3(c1, c2)
    print("sipri_countries:", len(c1), "| with ISO code:", (c1.iso_a3 != "").sum())
    print("country_info_names:", len(c2), "| with ISO code:", (c2.iso_a3 != "").sum())
    print("master:", len(master), "| alias map:", len(c3), "| aliases linked to master:", c3.iso_a3.isin(master.iso_a3).sum())
    print("Master countries with no SIPRI spelling:", master[~master.iso_a3.isin(c3.iso_a3)]["country_name_ko"].tolist())
# %%