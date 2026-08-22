# research.md — web-crawler-books

## 관련 파일/폴더
```
web-crawler-books/
├── scraper.py    # 크롤링 + CSV/Excel 저장 로직 전체
├── README.md     # 프로젝트 요약 (포트폴리오용)
├── 설명서.md      # 처음 보는 사람을 위한 상세 설명
├── .gitignore    # 출력 파일(csv/xlsx), __pycache__, .venv 제외
└── .git/         # origin: github.com/dyj02056/web-crawler-books (main)
```
`output_products.csv`, `output_products.xlsx`는 실행 시 생성되는
산출물이며 `.gitignore`에 의해 저장소에는 포함되지 않음.

## 현재 구조 설명
단일 스크립트(`scraper.py`)에 함수 4개로 구성:
- `scrape_products(categories)` — 크롤링 본체
- `save_to_csv(rows, path)` — CSV 저장
- `save_to_excel(rows, path)` — 서식 있는 Excel 저장 (xlsxwriter)
- `main()` — argparse로 CLI 인자 처리 후 위 함수들을 순서대로 호출

대상 사이트는 `webscraper.io/test-sites/e-commerce/allinone`(크롤링
연습용 공개 가상 전자제품 쇼핑몰)으로, 노트북/태블릿/스마트폰 3개
카테고리가 `CATEGORIES` 딕셔너리에 하드코딩되어 있음. 이 사이트는
카테고리 페이지 하나에 상품이 전부 나와 있어 페이지네이션이 없음
(카테고리당 요청 1회로 끝).

## 기능 동작 흐름 정리
1. CLI 실행 시 argparse가 `--categories`(기본: 전체 3개), `--csv`,
   `--excel` 인자를 파싱
2. `scrape_products()`가 지정된 카테고리를 순회하며 `requests.get()` 호출
3. 알 수 없는 카테고리명이 들어오면 건너뛰고 경고 출력, 응답이 200이
   아니면 그 카테고리만 건너뜀 (페이지네이션이 없어 "마지막 페이지 판별"
   문제 자체가 사라짐 — books.toscrape.com 버전에 있던 정합성 위험 해소)
4. `BeautifulSoup(html.parser)`로 `.thumbnail` 카드를 찾아 상품명(`a.title`의
   `title` 속성 — 화면에는 "..."로 잘려 보이지만 속성에는 전체 이름이
   들어있음), 가격(`$` 접두사 제거), 평점(`data-rating` 속성, 별 개수를
   세는 방식보다 안정적), 리뷰 수를 딕셔너리로 수집
5. 전체 카테고리 수집이 끝난 뒤 한 번에 `save_to_csv()` → `save_to_excel()` 호출
6. 콘솔에 진행 상황(`print`)만 출력, 별도 로깅 없음

## 관련 파일 목록
| 파일 | 역할 |
|---|---|
| `scraper.py` | 유일한 구현 파일 |
| `README.md`, `설명서.md` | 사람이 읽는 설명 문서 |
| `.gitignore` | 산출물/캐시 제외 규칙 |

### 수정 가능 파일 + 이유
- **`scraper.py`** — 실제 클라이언트 사이트로 대상을 바꿀 때 `BASE_URL`,
  `CATEGORIES`, CSS 셀렉터(`.thumbnail` 등)를 전면 교체해야 함. 저장
  포맷을 늘리거나(JSON, Google Sheets 등) 에러 처리를 보강할 때도 이
  파일만 수정
- **`.gitignore`** — 출력 파일명이나 경로가 바뀌면 패턴 추가 필요

## 기존 규칙
- **네이밍**: 함수/변수는 snake_case, 상수는 UPPER_SNAKE_CASE
  (`BASE_URL`, `CATEGORIES`, `HEADERS`)
- **상태관리**: 없음 — 전역 상태 없이 순수 함수가 리스트를 반환/전달하는 구조
- **API 호출**: `requests.get(url, headers=HEADERS, timeout=10)` 동기
  호출. `User-Agent` 헤더는 지정하지만 재시도(retry)·백오프 로직은 없음.
  응답 인코딩은 `res.apparent_encoding`으로 명시적으로 감지해서 사용
  (특수문자가 깨져 파싱이 실패하던 실제 버그를 이전 버전에서 수정하며
  추가된 패턴, 이번 재작성에서도 유지)
- **에러 처리**: 카테고리 단위로는 상태 코드 체크로 스킵 처리하지만,
  네트워크 예외(`ConnectionError`, `Timeout` 등)에 대한 `try/except`는
  여전히 없어 예외 발생 시 프로그램이 그대로 죽음

## 위험요소
| 구분 | 내용 |
|---|---|
| 중복 구현 | 클라이언트 사이트마다 파싱 셀렉터를 새로 짜야 함 — 재사용 가능한 부분은 저장 함수(CSV/Excel) 정도뿐 |
| 정합성 | ~~마지막 페이지 판별 문제~~ → 이번 재작성으로 페이지네이션 자체가 없어져 해소됨. 다만 카테고리 이름이 오타나 개편으로 바뀌면 조용히 0건 수집될 수 있음 |
| 권한 | 현재는 로그인 불필요한 공개 페이지만 대상. 실제 클라이언트 사이트가 로그인/세션이 필요하면 인증 로직을 새로 추가해야 함 |
| 성능 | 완전 동기 처리. 카테고리 수가 적어(3개) 지금은 문제 없지만, 카테고리/페이지가 많은 대형 쇼핑몰을 대상으로 하면 비동기 처리 또는 Scrapy 전환 검토 필요 |
| 예외 미처리로 인한 데이터 손실 | 모든 결과를 리스트에 모은 뒤 마지막에 한 번에 저장하는 구조라, 크롤링 도중 예외가 나면 그때까지 수집한 데이터도 파일로 전혀 저장되지 않고 사라짐 |

## 구현 전 질문 (진행 상황)
1. ~~**대상 사이트**~~ → ✅ 완료: 연습용 서점 사이트에서 실제 쇼핑몰과
   유사한 전자제품 쇼핑몰(webscraper.io, 카테고리별 크롤링)로 교체함
2. **에러 처리 수준** — 포트폴리오 데모 수준(현재 상태 유지)으로 둘지,
   실제 납품 가능한 수준(재시도, 로깅, 부분 실패 시에도 중간 저장)까지
   보강할지 아직 미정
3. **대량 크롤링 대응** — 지금의 동기 방식(requests+bs4)을 유지할지,
   아니면 이미 설치해둔 Scrapy로 재작성해서 "대량 크롤링도 가능"함을
   별도 예시로 보여줄지 아직 미정
4. **출력 포맷 확장** — CSV/Excel 외에 클라이언트가 자주 요구하는
   형태(Google Sheets 자동 업로드, DB 저장 등)까지 미리 확장 가능하게
   설계할지, 지금처럼 파일 저장 두 가지로 한정할지 아직 미정
