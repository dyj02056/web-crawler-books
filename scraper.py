"""
웹 크롤러 포트폴리오 샘플: webscraper.io의 가상 전자제품 쇼핑몰에서
카테고리별 상품 정보를 수집해 CSV / Excel 파일로 저장한다.

webscraper.io/test-sites 는 크롤링 연습을 위해 공개된 샌드박스 쇼핑몰이므로
실제 서비스에 사용할 때는 클라이언트가 지정하는 사이트의 이용약관을
반드시 먼저 확인해야 한다.
"""
import argparse
import csv

import requests
import xlsxwriter
from bs4 import BeautifulSoup

BASE_URL = "https://webscraper.io/test-sites/e-commerce/allinone/{}"
CATEGORIES = {
    "노트북": "computers/laptops",
    "태블릿": "computers/tablets",
    "스마트폰": "phones/touch",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio-scraper-demo)"}


def scrape_products(categories: list[str] | None = None) -> list[dict]:
    """지정한 카테고리(기본: 전체)의 상품 정보를 수집한다.

    이 쇼핑몰은 카테고리 페이지 하나에 상품이 전부 나와 있어 페이지를
    넘기지 않아도 된다(카테고리당 요청 1회).
    """
    targets = categories or list(CATEGORIES.keys())
    results = []
    for name in targets:
        path = CATEGORIES.get(name)
        if not path:
            print(f"알 수 없는 카테고리라 건너뜀: {name}")
            continue

        url = BASE_URL.format(path)
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            print(f"{name} 카테고리 요청 실패 (status {res.status_code})")
            continue
        res.encoding = res.apparent_encoding

        soup = BeautifulSoup(res.text, "html.parser")
        for card in soup.select(".thumbnail"):
            title = card.select_one("a.title")["title"]
            price_text = card.select_one(".price [itemprop='price']").text.strip()
            price = float(price_text.lstrip("$"))
            rating_el = card.select_one("[data-rating]")
            rating = int(rating_el["data-rating"]) if rating_el else 0
            review_el = card.select_one("[itemprop='reviewCount']")
            review_count = int(review_el.text.strip()) if review_el else 0
            results.append(
                {
                    "category": name,
                    "title": title,
                    "price_usd": price,
                    "rating": rating,
                    "review_count": review_count,
                }
            )
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
    money_fmt = workbook.add_format({"num_format": "$0.00"})
    cell_fmt = workbook.add_format({"border": 1})

    header_labels = ["카테고리", "상품명", "가격(USD)", "평점", "리뷰 수"]
    for col, label in enumerate(header_labels):
        sheet.write(0, col, label, header_fmt)

    for row_idx, row in enumerate(rows, start=1):
        sheet.write(row_idx, 0, row["category"], cell_fmt)
        sheet.write(row_idx, 1, row["title"], cell_fmt)
        sheet.write_number(row_idx, 2, row["price_usd"], money_fmt)
        sheet.write_number(row_idx, 3, row["rating"], cell_fmt)
        sheet.write_number(row_idx, 4, row["review_count"], cell_fmt)

    sheet.set_column("A:A", 12)
    sheet.set_column("B:B", 45)
    sheet.set_column("C:C", 12)
    sheet.set_column("D:D", 8)
    sheet.set_column("E:E", 10)
    sheet.freeze_panes(1, 0)
    workbook.close()


def main():
    parser = argparse.ArgumentParser(description="가상 쇼핑몰(전자제품) 상품 정보 크롤러")
    parser.add_argument(
        "--categories",
        default=",".join(CATEGORIES.keys()),
        help=f"수집할 카테고리, 쉼표로 구분 (기본: 전체 — {', '.join(CATEGORIES.keys())})",
    )
    parser.add_argument("--csv", default="output_products.csv", help="CSV 출력 경로")
    parser.add_argument("--excel", default="output_products.xlsx", help="Excel 출력 경로")
    args = parser.parse_args()
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]

    print(f"{len(categories)}개 카테고리 수집 시작: {', '.join(categories)}")
    rows = scrape_products(categories)
    print(f"{len(rows)}건 수집 완료")

    save_to_csv(rows, args.csv)
    save_to_excel(rows, args.excel)
    print(f"저장 완료: {args.csv}, {args.excel}")


if __name__ == "__main__":
    main()
