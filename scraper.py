"""
웹 크롤러 포트폴리오 샘플: scrapeme.live(스크래핑 연습용으로 공개된
가상 포켓몬 쇼핑몰)에서 상품명과 가격을 수집해 CSV / Excel 파일로 저장한다.

scrapeme.live는 스크래핑 연습을 위해 공개된 샌드박스 쇼핑몰이며, robots.txt로
크롤링을 제한하지 않는 걸 직접 확인하고 사용했다. 실제 서비스에 사용할 때는
클라이언트가 지정하는 사이트의 robots.txt와 이용약관을 반드시 먼저 확인해야
하며, 이 코드는 요청 전 robots.txt를 자동으로 확인하도록 되어 있다.
"""
import argparse
import csv
import time

import requests
import xlsxwriter
from bs4 import BeautifulSoup

from ai_extractor import extract_with_ai
from robots_check import is_crawling_allowed

BASE_URL = "https://scrapeme.live/shop/page/{}/"
HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio-scraper-demo)"}


def scrape_products(pages: int = 3, delay: float = 0.5) -> list[dict]:
    """지정한 페이지 수만큼 상품명과 가격을 수집한다."""
    results = []
    for page in range(1, pages + 1):
        url = BASE_URL.format(page)

        if not is_crawling_allowed(url, HEADERS["User-Agent"]):
            print(f"robots.txt에서 크롤링을 금지한 경로라 중단함: {url}")
            break

        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            break
        res.encoding = res.apparent_encoding

        soup = BeautifulSoup(res.text, "html.parser")
        for card in soup.select("li.product"):
            title_el = card.select_one(".woocommerce-loop-product__title")
            price_els = card.select(".price .amount")
            if not title_el or not price_els:
                continue
            # 할인 중인 상품은 원가/할인가가 같이 나오므로 마지막 값(실제 판매가)을 사용
            price = float(price_els[-1].text.strip().lstrip("£"))
            results.append(
                {
                    "title": title_el.text.strip(),
                    "price_gbp": price,
                    "page": page,
                }
            )
        time.sleep(delay)  # 서버 부하를 주지 않기 위한 매너 딜레이
    return results


def save_to_csv(rows: list[dict], path: str) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


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

    headers = ["title", "price_gbp", "page"]
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
    parser.add_argument(
        "--ai-url",
        default=None,
        help="셀렉터가 준비되지 않은 사이트 URL. 지정하면 페이지 크롤링 대신 "
        "AI(Gemini)가 해당 페이지에서 상품 정보를 대신 추출한다 (GOOGLE_API_KEY 필요)",
    )
    args = parser.parse_args()

    if args.ai_url:
        print(f"AI로 상품 정보 추출 시도: {args.ai_url}")
        rows = extract_with_ai(args.ai_url)
    else:
        print(f"{args.pages}페이지 수집 시작...")
        rows = scrape_products(pages=args.pages)

    print(f"{len(rows)}건 수집 완료")

    save_to_csv(rows, args.csv)
    save_to_excel(rows, args.excel)
    print(f"저장 완료: {args.csv}, {args.excel}")


if __name__ == "__main__":
    main()
