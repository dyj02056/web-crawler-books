"""HTTP 요청 공용 유틸리티 — 일시적인 네트워크 오류에 대한 재시도를 담당.

scraper.py와 ai_extractor.py가 공통으로 사용한다.
"""
import time

import requests

MAX_RETRIES = 3
RETRY_DELAY = 2  # 초. 재시도할 때마다 배로 늘어남 (2초 → 4초 → 6초)


def fetch_with_retry(url: str, headers: dict, timeout: int = 10, max_retries: int = MAX_RETRIES):
    """일시적인 네트워크 오류(연결 끊김, 타임아웃 등)에 대비해 재시도하며 요청한다.

    최대 횟수를 다 써도 실패하면 None을 반환한다. 호출하는 쪽에서 None을
    받으면 이 요청은 포기하고 다음 작업으로 넘어가도록 처리해야 한다.
    """
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return requests.get(url, headers=headers, timeout=timeout)
        except requests.RequestException as e:
            last_error = e
            if attempt < max_retries:
                wait = RETRY_DELAY * attempt
                print(f"  요청 실패 ({attempt}/{max_retries}): {e} -> {wait}초 후 재시도")
                time.sleep(wait)

    print(f"  {max_retries}번 재시도했지만 실패해서 건너뜀: {last_error}")
    return None
