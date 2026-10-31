# Third-Party Notices (제3자 자료 고지)

이 저장소의 **소스코드**는 [LICENSE](LICENSE)(MIT)를 따릅니다.
아래의 **데이터·이미지·아이콘·소프트웨어**는 각 원 저작권자의 소유이며, 해당 라이선스·이용약관에 따라 사용합니다.
MIT 라이선스는 이 자료들에 적용되지 않습니다.

본 프로젝트는 **비상업적 교육 목적**(AI 교육 팀프로젝트)으로 제작되었습니다.
본 대시보드는 언급된 기업·기관과 제휴·후원 관계가 없습니다.

항목별 상세 출처(저작자·라이선스·원본 링크·변경 내용)는 대시보드의 **"데이터 출처"** 화면과 아래 파일에서 확인할 수 있습니다.

- 데이터: `data/sources/data_sources.csv`
- 이미지·아이콘: `images/**/credits.csv` (이미지가 있는 폴더마다 하나씩)

---

## 1. 데이터

| 데이터 | 제공기관 | 라이선스·이용조건 | 저장소 포함 여부 |
|---|---|---|---|
| Arms Transfers Database | SIPRI | 비상업적 분석·인용 시 출처 표기. 데이터셋 10% 초과 재배포는 SIPRI 허가 필요 ([Terms](https://www.sipri.org/databases/terms)) | 가공·집계 결과만 포함, 원자료 미포함 |
| Military Expenditure Database | SIPRI | 위와 같음 | 가공·집계 결과만 포함, 원자료 미포함 |
| Global Peace Index 2026 | Institute for Economics & Peace | [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) (비상업) — 가공 데이터도 같은 라이선스로 공개 | 가공 결과 포함, 원본 미포함 |
| GDP·GDP 디플레이터 | World Bank | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | 국방비 보완 결과만 포함, 원본(`data/raw/`) 미포함 |
| UN 안보리 무기 금수조치 | UN Security Council | 공개 결의(UNSCR) 정보, 출처 표기 | 미포함 (해석 시 제외 대상 안내에만 참고) |
| Sovereign Rating History | Fitch Ratings (SEC Rule 17g-7 공시) | Fitch 사전 서면 동의 없는 재배포 금지 ([Terms](https://fitch.group/terms-of-use/)) | **원본 미포함** (점수로 변환한 결과만 사용) |
| 국가정보 | KOTRA | 저작권 KOTRA | **원문(PDF) 미포함** (98개국 기준 목록만 사용) |

### SIPRI 파생 자료 안내
- `data/processed/tiv_*.csv`(`tiv_delivery_yearly.csv`, `tiv_recipient.csv`, `tiv_weapon_group.csv` 등)는 SIPRI Arms Transfers Database에서 국가·연도·분류별로 집계한 파생 자료이며, 개별 거래 정보(무기명·수량·계약연도·설명문 등)는 포함하지 않습니다.
- `data/processed/arms_trade_98_countries_order_2021_2025.csv`는 SIPRI Arms Transfers Database의 2021~2025년 주문 자료를 무기분류별로 집계한 요약표로, 분류별 주문 TIV 상위 3개 무기체계(무기명·순위·주문 TIV 합계, 30행)만 담고 있으며 개별 계약 정보(수입국·공급국·수량·연도·설명문 등)는 포함하지 않습니다.
- `data/processed/korea_weapon_data.csv`(115건)는 SIPRI Arms Transfers Database 중 한국이 공급한 거래를 6개 분석 기업 기준으로 추출한 자료로, 개별 거래 정보(무기명·수량·연도·SIPRI 설명문)를 포함합니다. 전체 데이터셋의 10% 미만이며 비상업적 교육 목적으로만 사용합니다.
- `data/processed/military_expenditure.csv`는 SIPRI Military Expenditure Database에서 분석 대상국·기간만 추출한 파생 자료입니다.
- SIPRI 원자료(`data/raw/`)는 저장소에 포함하지 않습니다.
- 이 자료들은 비상업적 교육 목적으로만 사용하며, 원 데이터의 저작권과 이용조건은 SIPRI에 있습니다.

데이터 출처 표기 예:
- Source: SIPRI Arms Transfers Database / SIPRI Military Expenditure Database, Stockholm International Peace Research Institute.
- Source: Global Peace Index 2026, Institute for Economics & Peace, licensed under CC BY-NC-SA 4.0.
- Source: World Bank, World Development Indicators, licensed under CC BY 4.0.

---

## 2. 아이콘·국기

### Google Material Symbols — Apache License 2.0
- 위치: `images/01_main_images/`, `images/04_country_images/icons/`, `images/icon/material-*.png`(앱 로고·사이드바 메뉴), `images/common/etc/material-*.png`·`rank-*.png`(달력·순위·카드 아이콘), `images/03_weapon_images/material-*.png`
- 출처: https://fonts.google.com/icons
- 변경: 검은색 PNG로 변환해 화면에서 테마 색으로 표시. 1~3위 트로피는 금·은·동 색으로 변환, 10위는 원 테두리에 숫자 10을 넣어 제작
- 라이선스 전문: https://www.apache.org/licenses/LICENSE-2.0

> Copyright Google LLC. Licensed under the Apache License, Version 2.0 (the "License");
> you may not use these files except in compliance with the License.
> Unless required by applicable law or agreed to in writing, software distributed under
> the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.

### flag-icons — MIT License
- 위치: `images/common/country/` (국기 109개)
- 출처: https://github.com/lipis/flag-icons
- 변경: 1x1 SVG를 원형으로 잘라 256px PNG로 변환, 연한 테두리 추가
- 국기별 원본 링크: `images/common/country/credits.csv`

```text
The MIT License (MIT)

Copyright (c) 2013 Panayiotis Lipiridis

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 3. 이미지

### 무기체계 사진 (`images/common/weapon/`)
사진별 저작자·라이선스·원본 링크는 `images/common/weapon/credits.csv`에 있습니다. 모든 사진은 크기만 조정했습니다.

| 라이선스 | 출처 | 비고 |
|---|---|---|
| Public Domain | 미 국방부(DVIDS)·미 해군·미 육군·미 공군, NASA, 필리핀·인도네시아 해군 등 (Wikimedia Commons) | 미 국방부 이미지 사용은 미 국방부의 보증·후원을 의미하지 않음 |
| CC0 | Wikimedia Commons | |
| CC BY 2.0 / 3.0 / 4.0 | Wikimedia Commons 각 저작자 | 저작자·라이선스 표기 |
| CC BY-SA 2.0 / 2.0 KR / 3.0 / 4.0 | Wikimedia Commons 각 저작자 | 저작자·라이선스 표기, 변경 시 같은 라이선스 |
| 공공누리 제1유형 (KOGL Type 1) | 대한민국 국방부·방위사업청 (Wikimedia Commons) | 출처 표시 |
| AI 생성 이미지 | OpenAI ChatGPT | 실제 장비와 차이가 있을 수 있음 |

### 기타 이미지
| 파일 | 저작자 | 라이선스 |
|---|---|---|
| `images/common/etc/world_map.png` | Aloha CL ([Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Blank-map-world-iceless-Greenland.png)) | CC0 |
| `images/icon/sidebar-background.png` | OpenAI ChatGPT (AI 생성) | AI 생성 이미지 |

---

## 4. 상표

대시보드에 언급된 기업명(한화에어로스페이스, 한화오션, 현대로템, HD현대중공업, LIG D&A, 한국항공우주산업 등)과 무기체계명은 각 기업의 상표일 수 있습니다.
본 대시보드는 기업 로고 이미지를 사용하지 않으며, 기업명은 식별 목적으로만 텍스트로 표시합니다.

---

## 5. 오픈소스 소프트웨어

이 프로젝트는 아래 오픈소스 라이브러리를 사용합니다(`requirements.txt`). 라이브러리 자체는 이 저장소에 포함하지 않습니다.

| 라이브러리 | 라이선스 |
|---|---|
| Streamlit | Apache License 2.0 |
| pandas | BSD 3-Clause |
| NumPy | BSD 3-Clause |
| Plotly | MIT |
| Pillow | MIT-CMU (HPND) |
| streamlit-plotly-events | MIT |
| 기타 의존성 | 각 패키지의 라이선스 (`pip show <패키지명>`으로 확인) |

지도 경계 데이터는 Plotly에 내장된 Natural Earth 데이터(Public Domain)를 사용합니다.

---

*본 고지는 법률 자문이 아니며, 각 자료의 최신 이용조건은 원 제공처에서 확인하시기 바랍니다.*
