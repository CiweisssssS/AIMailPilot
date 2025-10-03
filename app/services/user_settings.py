import sqlite3
from typing import List, Dict
from contextlib import contextmanager


DB_PATH = "user_settings.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_keywords (
                user_id TEXT,
                term TEXT,
                weight REAL,
                scope TEXT,
                PRIMARY KEY (user_id, term)
            )
        """)
        conn.commit()


def get_user_keywords(user_id: str) -> List[Dict]:
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT term, weight, scope FROM user_keywords WHERE user_id = ?",
            (user_id,)
        )
        rows = cursor.fetchall()
        return [
            {
                'term': row['term'],
                'weight': row['weight'],
                'scope': row['scope']
            }
            for row in rows
        ]


def add_keyword(user_id: str, term: str, weight: float, scope: str):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO user_keywords (user_id, term, weight, scope) VALUES (?, ?, ?, ?)",
            (user_id, term, weight, scope)
        )
        conn.commit()


def remove_keyword(user_id: str, term: str):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM user_keywords WHERE user_id = ? AND term = ?",
            (user_id, term)
        )
        conn.commit()


def update_user_settings(user_id: str, add_keywords: List[Dict], remove_keywords: List[str]) -> bool:
    try:
        for keyword in add_keywords:
            add_keyword(user_id, keyword['term'], keyword['weight'], keyword['scope'])
        
        for term in remove_keywords:
            remove_keyword(user_id, term)
        
        return True
    except Exception:
        return False


init_db()
