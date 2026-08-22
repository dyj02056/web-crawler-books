"""
셀렉터를 미리 만들어두지 않은 낯선 사이트에서도, AI(Gemini)에게 페이지
내용을 보여주고 상품 정보를 대신 뽑아달라고 요청하는 보조 모듈.

동작하려면 GOOGLE_API_KEY가 필요하다. aistudio.google.com에서 구글
계정으로 로그인해 무료로 발급받은 뒤, .env.example을 참고해 .env
파일에 넣어두면 자동으로 읽어온다.
"""
import json
import os

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from google.genai import types

from http_utils import fetch_with_retry
from robots_check import is_crawling_allowed

load_dotenv()

MODEL = "gemini-3.6-flash"
MAX_TEXT_CHARS = 12000
HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio-scraper-demo)"}

PROMPT_TEMPLATE = """다음은 어떤 쇼핑몰 웹페이지에서 뽑아낸 텍스트입니다.
이 안에서 상품 목록을 찾아 JSON 배열로만 응답하세요. 다른 설명은 넣지 마세요.

각 상품은 아래 형식을 따릅니다.
{{"title": "상품명", "price": 숫자 또는 null}}

상품 정보를 하나도 찾을 수 없으면 빈 배열 []만 응답하세요.

페이지 내용:
---
{page_text}
---
"""


def fetch_page_text(url: str) -> str:
    """페이지에서 스크립트/스타일 등을 제거한 순수 텍스트만 추출한다."""
    if not is_crawling_allowed(url, HEADERS["User-Agent"]):
        raise RuntimeError(
            f"robots.txt에서 이 경로의 크롤링을 금지하고 있어 요청을 중단했습니다: {url}"
        )

    res = fetch_with_retry(url, HEADERS)
    if res is None:
        raise RuntimeError(f"재시도했지만 페이지를 가져오지 못했습니다: {url}")
    res.raise_for_status()
    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text[:MAX_TEXT_CHARS]


def extract_with_ai(url: str) -> list[dict]:
    """AI에게 페이지 내용을 보여주고 상품 목록을 JSON으로 뽑아 받는다.

    셀렉터가 정해진 사이트를 크롤링하는 scrape_products()보다 느리고
    비용(API 호출)이 들지만, 미리 설정을 만들어두지 않은 사이트에도
    바로 시도해볼 수 있다는 장점이 있다.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY가 설정되지 않았습니다. .env.example을 참고해서 "
            ".env 파일을 만들고 발급받은 키를 넣어주세요."
        )

    page_text = fetch_page_text(url)
    if not page_text:
        return []

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT_TEMPLATE.format(page_text=page_text),
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    try:
        items = json.loads(response.text)
    except (json.JSONDecodeError, TypeError):
        print("AI 응답을 JSON으로 해석하지 못했습니다.")
        return []

    rows = []
    for item in items:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        rows.append(
            {
                "title": item["title"],
                "price_gbp": float(item["price"]) if item.get("price") is not None else 0.0,
                "page": 0,  # AI 추출은 페이지 개념이 없어 0으로 표시
            }
        )
    return rows
