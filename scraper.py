"""
웹 크롤러 포트폴리오 샘플: books.toscrape.com에서 도서 정보를 수집해
CSV / Excel 파일로 저장한다.

books.toscrape.com은 스크래핑 연습을 위해 공개된 샌드박스 사이트이므로
실제 서비스에 사용할 때는 클라이언트가 지정하는 사이트의 이용약관을
반드시 먼저 확인해야 한다.
"""
import argparse
import csv
import time

import requests
import xlsxwriter
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/catalogue/page-{}.html"
RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio-scraper-demo)"}


def scrape_books(pages: int = 3, delay: float = 0.5) -> list[dict]:
    """books.toscrape.com에서 지정한 페이지 수만큼 도서 정보를 수집한다."""
    results = []
    for page in range(1, pages + 1):
        url = BASE_URL.format(page)
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            break
        res.encoding = res.apparent_encoding  # 서버가 인코딩을 명시하지 않아 £ 등 기호가 깨지는 것 방지
        soup = BeautifulSoup(res.text, "html.parser")
        for article in soup.select("article.product_pod"):
            title = article.h3.a["title"]
            price = article.select_one(".price_color").text.strip().lstrip("£")
            availability = article.select_one(".availability").text.strip()
            rating_class = article.select_one("p.star-rating")["class"][1]
            rating = RATING_MAP.get(rating_class, 0)
            results.append(
                {
                    "title": title,
                    "price_gbp": float(price),
                    "rating": rating,
                    "availability": availability,
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
    sheet = workbook.add_worksheet("도서 목록")

    header_fmt = workbook.add_format(
        {"bold": True, "bg_color": "#2b2420", "font_color": "#ffffff", "border": 1}
    )
    money_fmt = workbook.add_format({"num_format": "£0.00"})
    cell_fmt = workbook.add_format({"border": 1})

    headers = ["title", "price_gbp", "rating", "availability", "page"]
    header_labels = ["도서명", "가격(GBP)", "평점", "재고 상태", "페이지"]
    for col, label in enumerate(header_labels):
        sheet.write(0, col, label, header_fmt)

    for row_idx, row in enumerate(rows, start=1):
        sheet.write(row_idx, 0, row["title"], cell_fmt)
        sheet.write_number(row_idx, 1, row["price_gbp"], money_fmt)
        sheet.write_number(row_idx, 2, row["rating"], cell_fmt)
        sheet.write(row_idx, 3, row["availability"], cell_fmt)
        sheet.write_number(row_idx, 4, row["page"], cell_fmt)

    sheet.set_column("A:A", 45)
    sheet.set_column("B:B", 12)
    sheet.set_column("C:C", 8)
    sheet.set_column("D:D", 18)
    sheet.set_column("E:E", 8)
    sheet.freeze_panes(1, 0)
    workbook.close()


def main():
    parser = argparse.ArgumentParser(description="books.toscrape.com 도서 정보 크롤러")
    parser.add_argument("--pages", type=int, default=3, help="수집할 페이지 수 (기본 3)")
    parser.add_argument("--csv", default="output_books.csv", help="CSV 출력 경로")
    parser.add_argument("--excel", default="output_books.xlsx", help="Excel 출력 경로")
    args = parser.parse_args()

    print(f"{args.pages}페이지 수집 시작...")
    rows = scrape_books(pages=args.pages)
    print(f"{len(rows)}건 수집 완료")

    save_to_csv(rows, args.csv)
    save_to_excel(rows, args.excel)
    print(f"저장 완료: {args.csv}, {args.excel}")


if __name__ == "__main__":
    main()
