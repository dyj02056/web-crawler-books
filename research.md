# research.md — web-crawler-books

## 관련 파일/폴더
```
web-crawler-books/
├── scraper.py       # 페이지 기반 크롤링 + CSV/Excel 저장 로직, CLI 진입점
├── ai_extractor.py  # 셀렉터 없는 사이트를 Gemini로 대신 추출하는 보조 모듈
├── robots_check.py  # 크롤링 전 robots.txt 허용 여부를 확인하는 공용 유틸
├── .env.example     # GOOGLE_API_KEY 설정 예시 (실제 .env는 gitignore 처리)
├── README.md        # 프로젝트 요약 (포트폴리오용)
├── 설명서.md         # 처음 보는 사람을 위한 상세 설명
├── .gitignore       # 출력 파일(csv/xlsx), __pycache__, .venv, .env 제외
└── .git/            # origin: github.com/dyj02056/web-crawler-books (main)
```
`output_products.csv`, `output_products.xlsx`는 실행 시 생성되는
산출물이며 `.gitignore`에 의해 저장소에는 포함되지 않음. `.env`도 실제
API 키가 들어있어 저장소에 포함되지 않음(`.env.example`만 커밋됨).

## 크몽 카테고리 정책 준수 검토 (2026-08-22)
크몽 IT·프로그래밍 카테고리의 비승인 사유 중 "크롤링·자동화 범위
불명확"(비공개 API 접근, 무단 크롤링, 타 플랫폼 정책 위반 소지가 있는
서비스 제한, 합법적 수집 범위 내에서만 등록) 항목을 이 프로젝트에
대조 검토함.

**실제로 발견된 문제와 조치**: 이전 버전이 크롤링 대상으로 쓰던
`webscraper.io/test-sites/e-commerce/`는, 그 사이트 자신의
`robots.txt`에 `Disallow: /test-sites/e-commerce/`가 명시되어 있었음
(직접 `curl`로 확인). 즉 "크롤링 연습용으로 공개된 사이트"라는 설명과
별개로, 검색엔진 등 일반 크롤러에 대해서는 그 경로의 접근을 명시적으로
금지하고 있었던 것 — 이 상태로 크몽에 서비스를 등록했다면 정책 위반
소지가 있었음.

**해결**: 대상 사이트를 `scrapeme.live`(robots.txt로 상품 목록 페이지를
막지 않는 것을 확인함 — `/wp-admin/` 등 통상적인 워드프레스 관리 경로만
제외)로 교체하고, 요청 전 robots.txt를 실제로 확인하는
`robots_check.is_crawling_allowed()`를 `scraper.py`와 `ai_extractor.py`
양쪽에 통합함 (기존에는 사람이 읽는 문서에만 "확인하라"고 적혀 있었고
코드가 실제로 확인하지는 않았음 — 이제는 코드 차원에서 강제됨).

## 현재 구조 설명
파일 3개로 역할이 분리됨:
- `scraper.py` — CLI 진입점. `scrape_products(pages)`(셀렉터 기반 크롤링),
  `save_to_csv/save_to_excel`(저장), `main()`(인자 처리 및 분기)
- `ai_extractor.py` — `extract_with_ai(url)`. 셀렉터가 없는 사이트를
  Gemini로 대신 추출
- `robots_check.py` — `is_crawling_allowed(url, user_agent)`. 위 둘이
  공통으로 호출하는 안전장치

대상 사이트는 `scrapeme.live/shop/page/{N}/`(스크래핑 연습용 공개
가상 포켓몬 쇼핑몰, WooCommerce 기반)이며, 실제 페이지네이션이 있어
`--pages` 옵션으로 수집 범위를 조절함(페이지당 16개 상품, 마지막 페이지
초과 시 404 응답으로 자동 종료).

## 기능 동작 흐름 정리
1. CLI 실행 시 argparse가 `--pages`(기본 3), `--csv`, `--excel`,
   `--ai-url` 인자를 파싱
2. `--ai-url`이 없으면 `scrape_products()`가 1페이지부터 순회하며
   `requests.get()` 호출
3. **각 요청 직전 `is_crawling_allowed()`로 robots.txt를 확인** —
   금지된 경로면 그 자리에서 루프를 멈추고 이유를 출력
4. 응답이 200이 아니면(마지막 페이지 초과 등) 루프 종료
5. `BeautifulSoup(html.parser)`로 `li.product` 카드를 찾아 상품명
   (`.woocommerce-loop-product__title`), 가격(`.price .amount`의
   마지막 값 — 할인 상품은 원가/할인가가 같이 나와서 마지막 값이
   실제 판매가)을 딕셔너리로 수집
6. 전체 페이지 수집이 끝난 뒤 한 번에 `save_to_csv()` → `save_to_excel()` 호출
7. 콘솔에 진행 상황(`print`)만 출력, 별도 로깅 없음

`--ai-url` 사용 시: `ai_extractor.extract_with_ai()`가 동일하게
robots.txt를 먼저 확인 → 페이지 텍스트 추출(스크립트/스타일/nav/footer
제거, 최대 12,000자) → Gemini(`gemini-3.6-flash`)에 JSON 강제 응답으로
요청 → `{title, price_gbp, page:0}` 스키마로 정규화해 반환.

## 관련 파일 목록
| 파일 | 역할 |
|---|---|
| `scraper.py` | 크롤링 실행 시작점, 셀렉터 기반 수집 |
| `ai_extractor.py` | AI 기반 수집 (셀렉터 없는 사이트용) |
| `robots_check.py` | robots.txt 허용 여부 확인 (양쪽이 공유) |
| `README.md`, `설명서.md` | 사람이 읽는 설명 문서 |
| `.gitignore` | 산출물/캐시/비밀키 제외 규칙 |

### 수정 가능 파일 + 이유
- **`scraper.py`** — 실제 클라이언트 사이트로 대상을 바꿀 때 `BASE_URL`,
  CSS 셀렉터(`li.product` 등)를 전면 교체해야 함. 저장 포맷을
  늘리거나(JSON, Google Sheets 등) 에러 처리를 보강할 때도 이 파일을
  중심으로 수정
- **`ai_extractor.py`** — 프롬프트나 추출 스키마를 조정할 때, 또는
  모델명이 만료되어 교체가 필요할 때 (실제로 `gemini-2.5-flash` →
  `gemini-3.6-flash` 교체 이력 있음)
- **`robots_check.py`** — robots.txt 판단 정책 자체를 바꿀 때(예: 확인
  실패 시 기본값을 "허용"이 아닌 "차단"으로 더 보수적으로 바꾸고 싶을 때)
- **`.gitignore`** — 출력 파일명이나 경로가 바뀌면 패턴 추가 필요

## 기존 규칙
- **네이밍**: 함수/변수는 snake_case, 상수는 UPPER_SNAKE_CASE
  (`BASE_URL`, `HEADERS`, `MODEL`)
- **상태관리**: 없음 — 전역 상태 없이 순수 함수가 리스트를 반환/전달하는 구조
- **API 호출**: `requests.get(url, headers=HEADERS, timeout=10)` 동기
  호출. `User-Agent` 헤더는 지정하지만 재시도(retry)·백오프 로직은 없음.
  응답 인코딩은 `res.apparent_encoding`으로 명시적으로 감지해서 사용.
  **크롤링 요청 전에는 반드시 `is_crawling_allowed()`를 먼저 거치는 것이
  이 프로젝트의 규칙**(scraper.py, ai_extractor.py 둘 다 동일 패턴)
- **에러 처리**: 상태 코드/robots.txt 체크로 조기 종료는 하지만, 네트워크
  예외(`ConnectionError`, `Timeout` 등)에 대한 `try/except`는 여전히
  없어 예외 발생 시 프로그램이 그대로 죽음

## 위험요소
| 구분 | 내용 |
|---|---|
| 중복 구현 | 클라이언트 사이트마다 파싱 셀렉터를 새로 짜야 함 — 재사용 가능한 부분은 저장 함수(CSV/Excel)와 robots.txt 체크 정도 |
| 정합성 | 마지막 페이지 판별을 `status_code != 200`에 의존 — scrapeme.live는 범위를 벗어나면 404를 반환하는 것을 확인해 안전하지만, 다른 사이트로 대상을 바꾸면 재검증 필요 |
| 권한 | 현재는 로그인 불필요한 공개 페이지만 대상. 실제 클라이언트 사이트가 로그인/세션이 필요하면 인증 로직을 새로 추가해야 함 |
| 성능 | 완전 동기 처리. 페이지 수가 많아지면 선형적으로 느려짐 — 대량 크롤링이 필요해지면 비동기 처리 또는 Scrapy 전환 검토 필요 |
| 예외 미처리로 인한 데이터 손실 | 모든 결과를 리스트에 모은 뒤 마지막에 한 번에 저장하는 구조라, 크롤링 도중 예외가 나면 그때까지 수집한 데이터도 파일로 전혀 저장되지 않고 사라짐 |
| robots.txt 판단의 보수성 | `robots_check.py`는 robots.txt를 못 가져오면(네트워크 오류 등) "허용"으로 간주함 — 이는 "규칙이 아예 없는 사이트"와 "일시적으로 확인에 실패한 상황"을 구분하지 못한다는 한계 |

## AI 기반 추출 기능 (ai_extractor.py)
셀렉터가 준비되지 않은 사이트에도 대응할 수 있도록 `--ai-url` 옵션을
추가함. `google-genai` SDK로 Gemini(`gemini-3.6-flash`)를 호출하며,
`GOOGLE_API_KEY`는 `.env` 파일에서 `python-dotenv`로 로드함(무료 등급
키, aistudio.google.com에서 구글 계정으로 발급). 요청 전 robots.txt
확인은 `scrape_products()`와 동일하게 적용됨.

실제 테스트 결과(scrapeme.live 5페이지, 16건): 상품명·가격 모두 정확히
추출됨. 이전 버전(webscraper.io 대상, 태블릿 카테고리 21건) 테스트에서는
평점(rating)도 추출하려 했으나 전부 0으로 나왔음 — 그 사이트의 별점이
텍스트가 아니라 아이콘으로만 표시되어 있어 텍스트 추출 단계에서 정보
자체가 사라졌기 때문. 이후 스키마를 title/price로 단순화하며 이 필드
자체를 제거함(AI로 못 읽는 필드를 요청하는 건 무의미하다고 판단).

## 위험요소 (AI 기능)
| 구분 | 내용 |
|---|---|
| 비용/속도 | API 호출 1회당 비용·지연이 발생하고 무료 등급은 분당 요청 수 제한이 있어, 대량 상품에는 부적합 (소량/1회성 낯선 사이트 탐색용으로 한정) |
| 데이터 정확도 | 아이콘/이미지 기반 정보는 못 읽음. LLM 특성상 동일 입력에도 결과가 완전히 결정적이지 않을 수 있음 |
| 비밀키 관리 | `.env` 파일이 실수로 커밋되면 API 키가 유출됨 — `.gitignore`에 `.env` 추가로 1차 방어 |
| 모델명 변경 | 실제 테스트 중 `gemini-2.5-flash`가 신규 사용자에게 더 이상 제공되지 않아 `gemini-3.6-flash`로 교체한 이력 있음 — Google이 모델을 자주 세대교체하므로 향후에도 만료 가능성 있음 |

## 구현 전 질문 (진행 상황)
1. ~~**대상 사이트**~~ → ✅ 완료: 연습용 서점 사이트 → 전자제품 쇼핑몰
   → (robots.txt 위반 발견 후) 포켓몬 쇼핑몰(scrapeme.live)로 재교체
2. **에러 처리 수준** — 포트폴리오 데모 수준(현재 상태 유지)으로 둘지,
   실제 납품 가능한 수준(재시도, 로깅, 부분 실패 시에도 중간 저장)까지
   보강할지 아직 미정
3. **대량 크롤링 대응** — AI 기반 추출(`--ai-url`)을 추가함(셀렉터 없는
   사이트 대응이라는 다른 각도의 확장). 대량 처리 성능 자체에 대한
   Scrapy 전환 여부는 여전히 미정
4. **출력 포맷 확장** — CSV/Excel 외에 클라이언트가 자주 요구하는
   형태(Google Sheets 자동 업로드, DB 저장 등)까지 미리 확장 가능하게
   설계할지, 지금처럼 파일 저장 두 가지로 한정할지 아직 미정
