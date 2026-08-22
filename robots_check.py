"""사이트의 robots.txt 규칙을 확인해 크롤링이 허용되는지 판단하는 유틸리티.

크몽 등 마켓플레이스의 "크롤링·자동화 서비스는 합법적으로 수집 가능한
범위 내에서만 등록"이라는 정책을 코드 차원에서도 실제로 지키기 위해,
scraper.py와 ai_extractor.py 양쪽에서 이 함수를 거치도록 한다.
"""
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


def is_crawling_allowed(url: str, user_agent: str = "*") -> bool:
    """robots.txt 기준으로 해당 URL을 크롤링해도 되는지 확인한다.

    robots.txt 자체가 없거나 가져오지 못하는 사이트는 규칙을 안 둔 것으로
    보고 허용으로 간주한다 (많은 소규모 사이트가 robots.txt가 없음).
    반면 robots.txt가 있는데 명시적으로 금지한 경로는 차단한다.
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
    except Exception:
        return True

    return parser.can_fetch(user_agent, url)
