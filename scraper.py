"""
웹 크롤러 포트폴리오 샘플: scrapeme.live(스크래핑 연습용으로 공개된
가상 포켓몬 쇼핑몰)에서 상품명과 가격을 수집해 CSV / Excel 파일로 저장한다.

scrapeme.live는 스크래핑 연습을 위해 공개된 샌드박스 쇼핑몰이며, robots.txt로
크롤링을 제한하지 않는 걸 직접 확인하고 사용했다. 실제 서비스에 사용할 때는
클라이언트가 지정하는 사이트의 robots.txt와 이용약관을 반드시 먼저 확인해야
하며, 이 코드는 요청 전 robots.txt를 자동으로 확인하도록 되어 있다.

크롤링 도중 인터넷이 끊기거나 사이트가 잠깐 응답하지 않아도 데이터가
통째로 사라지지 않도록, 페이지 단위로 CSV에 바로바로 이어서 저장한다.
"""
import argparse
import csv
import json
import time

import xlsxwriter
from bs4 import BeautifulSoup

from ai_extractor import extract_with_ai
from http_utils import fetch_with_retry
from robots_check import is_crawling_allowed
from sqlite_store import get_price_history, save_to_sqlite

BASE_URL = "https://scrapeme.live/shop/page/{}/"
HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio-scraper-demo)"}
FIELDNAMES = ["title", "price_gbp", "page"]


def scrape_products(pages: int = 3, delay: float = 0.5, csv_path: str = "output_products.csv") -> list[dict]:
    """지정한 페이지 수만큼 상품명과 가격을 수집한다.

    페이지 하나를 처리할 때마다 결과를 csv_path에 바로 이어서 저장한다.
    중간에 프로그램이 중단되어도 그때까지 모은 데이터는 파일에 안전하게
    남는다. 실행을 새로 시작할 때는 이전 실행의 결과를 덮어쓰고 시작하므로
    이전 데이터와 겹쳐 쌓이지 않는다.
    """
    # 새 실행 시작 — 이전 파일을 지우고 헤더만 먼저 기록해둔다
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()

    all_rows: list[dict] = []
    for page in range(1, pages + 1):
        url = BASE_URL.format(page)

        if not is_crawling_allowed(url, HEADERS["User-Agent"]):
            print(f"robots.txt에서 크롤링을 금지한 경로라 중단함: {url}")
            break

        res = fetch_with_retry(url, HEADERS)
        if res is None:
            continue  # 이 페이지는 포기하고 다음 페이지로 넘어감
        if res.status_code != 200:
            break
        res.encoding = res.apparent_encoding

        soup = BeautifulSoup(res.text, "html.parser")
        page_rows = []
        for card in soup.select("li.product"):
            title_el = card.select_one(".woocommerce-loop-product__title")
            price_els = card.select(".price .amount")
            if not title_el or not price_els:
                continue
            # 할인 중인 상품은 원가/할인가가 같이 나오므로 마지막 값(실제 판매가)을 사용
            price = float(price_els[-1].text.strip().lstrip("£"))
            page_rows.append({"title": title_el.text.strip(), "price_gbp": price, "page": page})

        if page_rows:
            # 이 페이지 결과를 CSV에 즉시 이어쓰기 (중간 저장) — 페이지당 한 번만 기록되므로 중복 없음
            with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
                csv.DictWriter(f, fieldnames=FIELDNAMES).writerows(page_rows)

        all_rows.extend(page_rows)
        time.sleep(delay)  # 서버 부하를 주지 않기 위한 매너 딜레이

    return all_rows


def read_from_csv(path: str) -> list[dict]:
    """CSV에 저장된 결과를 다시 읽어온다 (Excel을 CSV 기준으로 재생성할 때 사용)."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        return []
    for row in rows:
        row["price_gbp"] = float(row["price_gbp"])
        row["page"] = int(row["page"])
    return rows


def save_to_csv(rows: list[dict], path: str) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def save_to_json(rows: list[dict], path: str) -> None:
    """다른 프로그램에서 바로 가져다 쓰기 편하도록 JSON으로도 저장한다."""
    if not rows:
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def save_to_excel(rows: list[dict], path: str) -> None:
    if not rows:
        return
    workbook = xlsxwriter.Workbook(path)
    sheet = workbook.add_worksheet("상품 목록")

    header_fmt = workbook.add_format(
        {"bold": True, "bg_color": "#2b2420", "font_color": "#ffffff", "border": 1}
    )
    money_fmt = workbook.add_format({"num_format": "£0.00"})
    cell_fmt = workbook.add_format({"border": 1})

    header_labels = ["상품명", "가격(GBP)", "페이지"]
    for col, label in enumerate(header_labels):
        sheet.write(0, col, label, header_fmt)

    for row_idx, row in enumerate(rows, start=1):
        sheet.write(row_idx, 0, row["title"], cell_fmt)
        sheet.write_number(row_idx, 1, row["price_gbp"], money_fmt)
        sheet.write_number(row_idx, 2, row["page"], cell_fmt)

    sheet.set_column("A:A", 30)
    sheet.set_column("B:B", 12)
    sheet.set_column("C:C", 8)
    sheet.freeze_panes(1, 0)
    workbook.close()


def main():
    parser = argparse.ArgumentParser(description="scrapeme.live 상품 정보 크롤러")
    parser.add_argument("--pages", type=int, default=3, help="수집할 페이지 수 (기본 3)")
    parser.add_argument("--csv", default="output_products.csv", help="CSV 출력 경로")
    parser.add_argument("--excel", default="output_products.xlsx", help="Excel 출력 경로")
    parser.add_argument("--json", default="output_products.json", help="JSON 출력 경로")
    parser.add_argument(
        "--db", default="price_history.db", help="가격 이력을 누적 저장할 SQLite 파일 경로"
    )
    parser.add_argument(
        "--ai-url",
        default=None,
        help="셀렉터가 준비되지 않은 사이트 URL. 지정하면 페이지 크롤링 대신 "
        "AI(Gemini)가 해당 페이지에서 상품 정보를 대신 추출한다 (GOOGLE_API_KEY 필요)",
    )
    parser.add_argument(
        "--history",
        default=None,
        help="크롤링 대신, 상품명에 이 키워드가 포함된 과거 가격 이력을 조회해서 보여준다",
    )
    args = parser.parse_args()

    if args.history:
        history = get_price_history(args.history, db_path=args.db)
        if not history:
            print(f"'{args.history}' 관련 가격 이력이 아직 없습니다.")
        else:
            for row in history:
                print(f"{row['collected_at']} | {row['title']} | GBP {row['price_gbp']}")
        return

    if args.ai_url:
        print(f"AI로 상품 정보 추출 시도: {args.ai_url}")
        rows = extract_with_ai(args.ai_url)
        save_to_csv(rows, args.csv)
        save_to_excel(rows, args.excel)
        save_to_json(rows, args.json)
        save_to_sqlite(rows, args.db)
        print(f"{len(rows)}건 수집 완료")
        print(f"저장 완료: {args.csv}, {args.excel}, {args.json}, {args.db}")
        return

    print(f"{args.pages}페이지 수집 시작...")
    try:
        scrape_products(pages=args.pages, csv_path=args.csv)
    finally:
        # 정상 종료든 중간에 중단되었든, CSV에 안전하게 저장된 내용을
        # 기준으로 나머지 출력 포맷을 (다시) 생성한다.
        saved_rows = read_from_csv(args.csv)
        save_to_excel(saved_rows, args.excel)
        save_to_json(saved_rows, args.json)
        save_to_sqlite(saved_rows, args.db)

    print(f"{len(saved_rows)}건 수집 완료")
    print(f"저장 완료: {args.csv}, {args.excel}, {args.json}, {args.db}")


if __name__ == "__main__":
    main()
