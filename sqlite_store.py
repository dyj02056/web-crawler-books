"""가격 변동 이력을 추적하기 위한 SQLite 저장소.

CSV/Excel은 실행할 때마다 새로 덮어쓰지만, 이 저장소는 실행 결과를
계속 누적해서 같은 상품의 가격이 시간에 따라 어떻게 바뀌었는지 나중에
조회할 수 있게 한다. 파이썬 기본 모듈(sqlite3)만 사용해 별도 설치가
필요 없다.
"""
import sqlite3
from datetime import datetime, timezone


def save_to_sqlite(rows: list[dict], db_path: str = "price_history.db") -> None:
    """수집 결과를 이력 테이블에 추가한다 (기존 기록은 지우지 않고 누적)."""
    if not rows:
        return

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                price_gbp REAL NOT NULL,
                page INTEGER,
                collected_at TEXT NOT NULL
            )
            """
        )
        collected_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn.executemany(
            "INSERT INTO price_history (title, price_gbp, page, collected_at) VALUES (?, ?, ?, ?)",
            [(row["title"], row["price_gbp"], row.get("page", 0), collected_at) for row in rows],
        )
        conn.commit()
    finally:
        conn.close()


def get_price_history(keyword: str, db_path: str = "price_history.db") -> list[dict]:
    """상품명에 keyword가 포함된 이력을 오래된 순으로 반환한다."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT title, price_gbp, collected_at FROM price_history "
            "WHERE title LIKE ? ORDER BY collected_at ASC",
            (f"%{keyword}%",),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
