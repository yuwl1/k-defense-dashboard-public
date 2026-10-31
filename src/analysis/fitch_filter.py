"""Fitch 신용등급 기준 제외 대상 국가 추출"""

from pathlib import Path
import pandas as pd

# 프로젝트 루트 경로
BASE_DIR = Path(__file__).resolve().parents[2]

# Fitch CSV 경로
FITCH_CSV_PATH = BASE_DIR / "data" / "processed" / "fitchrating.csv"


def get_fitch_excluded_countries(
    prediction_year: int,
    return_ratings: bool = False,
) -> set[str]:
    """
    예측 연도 직전까지의 최신 Fitch 등급을 기준으로
    C 계열, RD, D, WD 국가의 ISO 코드 집합을 반환한다.

    예시:
        2025년 예측 → 2024-12-31까지의 최신 등급 사용
        2026년 예측 → 2025-12-31까지의 최신 등급 사용
    """

    # ==========================================
    # 1. Fitch CSV 불러오기
    # ==========================================
    df = pd.read_csv(FITCH_CSV_PATH, dtype=str)

    required = {"iso_a3", "rating", "rating_action_date"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Fitch CSV에 필요한 컬럼이 없습니다: {sorted(missing)}"
        )

    # ==========================================
    # 2. 데이터 형식 정리
    # ==========================================
    df["iso_a3"] = df["iso_a3"].str.strip().str.upper()
    df["rating"] = df["rating"].str.strip().str.upper()

    df["rating_action_date"] = pd.to_datetime(
        df["rating_action_date"],
        errors="raise"
    )

    # ==========================================
    # 3. 예측 연도 이전 데이터만 사용
    # ==========================================
    cutoff = pd.Timestamp(
        year=prediction_year,
        month=1,
        day=1
    )

    df = df.loc[
        df["rating_action_date"] < cutoff
    ].copy()

    # ==========================================
    # 4. 국가별 가장 최근 신용등급 선택
    # ==========================================
    latest = (
        df.sort_values(
            "rating_action_date",
            kind="stable"
        )
        .drop_duplicates(
            subset="iso_a3",
            keep="last"
        )
    )

    # ==========================================
    # 5. C 계열, RD, D, WD 국가만 추출
    # ==========================================
    excluded_mask = (
        latest["rating"].str.startswith("C", na=False)
        | latest["rating"].isin({"RD", "D", "WD"})
    )

    # 제외 대상 국가와 신용등급 추출
    excluded = latest.loc[
        excluded_mask,
        ["iso_a3", "rating"]
    ]

    # 등급 정보까지 요청하면 {국가: 등급} 반환
    if return_ratings:
        return dict(zip(excluded["iso_a3"], excluded["rating"]))

    # 기존처럼 국가 코드만 반환
    return set(excluded["iso_a3"])
