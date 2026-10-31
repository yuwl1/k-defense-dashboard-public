"""2016~2025년 GPI 종합점수(Overall Score)를 전처리하는 코드.

입력 파일:
    data/raw/GPI_Public_Release_2026.xlsx
    data/mapping/country_map_master.csv

출력 파일:
    data/processed/gpi_overall.csv
        iso_a3, year, score
        (96개국 × 10개년 = 960행, 국가 코드 및 연도순 정렬)

기존에 생성된 별도의 요약 CSV 파일이 있으면 삭제한다.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "raw" / "GPI_Public_Release_2026.xlsx"
MASTER = ROOT / "data" / "mapping" / "country_map_master.csv"
OUTPUT = ROOT / "data" / "processed"
YEARS = list(range(2016, 2026))
EXPECTED_COUNTRIES = 99


def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(f"GPI 원본 엑셀 파일이 없습니다: {SOURCE}")
    if not MASTER.is_file():
        raise FileNotFoundError(f"국가 마스터 CSV가 없습니다: {MASTER}")

    # 1. 국가 마스터 csv 불러오기
    master = pd.read_csv(MASTER, encoding="utf-8-sig", keep_default_na=False)
    master_columns = ["iso_a3", "gpi_country_name"]
    missing = [column for column in master_columns if column not in master.columns]
    if missing:
        raise ValueError(f"국가 마스터에 필요한 열이 없습니다: {missing}")

    master = master[master_columns].copy()
    master["iso_a3"] = master["iso_a3"].astype(str).str.strip().str.upper()
    master["gpi_country_name"] = master["gpi_country_name"].astype(str).str.strip()
    if (master[master_columns] == "").any().any():
        raise ValueError("국가 마스터의 iso_a3 또는 GPI 국가명이 비어 있습니다.")
    if master["iso_a3"].duplicated().any():
        raise ValueError("국가 마스터에 중복된 iso_a3 코드가 있습니다.")
    if len(master) != EXPECTED_COUNTRIES:
        raise ValueError(
            f"국가 마스터의 국가 수가 {EXPECTED_COUNTRIES}개가 아닙니다: {len(master)}개"
        )

    # 2. GPI 원본 불러오기
    source_columns = [f"{year}_Score" for year in YEARS]
    raw = pd.read_excel(SOURCE, sheet_name="Overall Scores", header=7)
    required = ["country", "geocode", *source_columns]
    missing = [column for column in required if column not in raw.columns]
    if missing:
        raise ValueError(f"GPI 원본에 필요한 열이 없습니다: {missing}")

    source = raw[required].dropna(subset=["country", "geocode"]).copy()
    source["geocode"] = source["geocode"].astype(str).str.strip().str.upper()
    source["country"] = source["country"].astype(str).str.strip()
    if source["geocode"].duplicated().any():
        raise ValueError("GPI 원본에 중복된 geocode가 있습니다.")

    # 3. 마스터 csv의 iso_a3로 geocode 대체
    matched = master.merge(
        source, left_on="iso_a3", right_on="geocode", how="left",
        validate="one_to_one", indicator=True,
    )
    unmatched = matched.loc[matched["_merge"] != "both", "iso_a3"].tolist()
    if unmatched:
        raise ValueError(f"GPI 원본에서 찾을 수 없는 마스터 국가 코드: {unmatched}")

    wrong_names = matched[matched["gpi_country_name"] != matched["country"]]
    if not wrong_names.empty:
        examples = [
            f"{row.iso_a3}: master={row.gpi_country_name!r}, GPI={row.country!r}"
            for row in wrong_names.itertuples(index=False)
        ]
        raise ValueError("국가 코드와 GPI 국가명 불일치: " + "; ".join(examples))

    # 4. 국가별로 정렬
    annual = matched.melt(
        id_vars=["iso_a3"],
        value_vars=source_columns,
        var_name="year",
        value_name="score",
    )
    annual["year"] = annual["year"].str[:4].astype(int)
    annual["score"] = pd.to_numeric(annual["score"], errors="coerce")
    if annual["score"].isna().any():
        raise ValueError("96개국 GPI Overall Score에 결측값이 있습니다.")
    if not annual["score"].between(1, 5).all():
        raise ValueError("GPI Overall Score가 1~5 범위를 벗어났습니다.")
    if len(annual) != EXPECTED_COUNTRIES * len(YEARS):
        raise ValueError(f"연도별 데이터 행 수가 예상과 다릅니다: {len(annual)}행")
    if annual.duplicated(["iso_a3", "year"]).any():
        raise ValueError("국가-연도 조합이 중복되어 있습니다.")

    annual = (
        annual[["iso_a3", "year", "score"]]
        .sort_values(["iso_a3", "year"])
        .reset_index(drop=True)
    )
    
    # 최종 결과에서 한국 제외
    annual = annual[annual["iso_a3"] != "KOR"].reset_index(drop=True)

    # 5. CSV로 저장
    OUTPUT.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT / "gpi_overall.csv"
    old_summary_file = OUTPUT / "gpi_overall_summary_2016_2025.csv"
    old_combined_file = OUTPUT / "gpi_overall_2016_2025.csv"

    annual.to_csv(output_file, index=False, encoding="utf-8-sig")

    # 기존 CSV 파일 삭제
    for old_file in [old_summary_file, old_combined_file]:
        if old_file.is_file():
            old_file.unlink()
            print(f"기존 CSV 삭제 완료: {old_file}")

    print(f"마스터 국가 수: {len(master)}개")
    print(f"전처리 데이터: {len(annual):,}행, 열: {list(annual.columns)}")
    print(f"저장 완료: {output_file}")



if __name__ == "__main__":
    main()
