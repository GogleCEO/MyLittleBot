import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "bot.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                user_id INTEGER PRIMARY KEY,
                rating INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()

def get_rating(user_id: int) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT rating FROM ratings WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row[0] if row else 0


def update_rating(user_id: int, delta: int) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO ratings (user_id, rating) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET rating = rating + ?
        """, (user_id, delta, delta))
        conn.commit()
        row = conn.execute(
            "SELECT rating FROM ratings WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row[0]

def get_top_ratings(limit: int = 10) -> list[tuple[int, int]]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT user_id, rating FROM ratings ORDER BY rating DESC LIMIT ?", (limit,)).fetchall()
        return rows
