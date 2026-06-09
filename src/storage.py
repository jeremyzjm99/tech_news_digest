import sqlite3
import hashlib
from datetime import datetime, timezone

from config import DATABASE_PATH


def init_db():
    """Create the articles table if it doesn't exist yet."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url_hash    TEXT UNIQUE NOT NULL,
                title       TEXT NOT NULL,
                url         TEXT NOT NULL,
                summary     TEXT,
                source      TEXT,
                category    TEXT,
                published   TEXT,
                keywords    TEXT,
                ai_summary  TEXT,
                score       INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)


def is_new(url: str) -> bool:
    """Return True if this article URL has never been saved before."""
    url_hash = _hash(url)
    with sqlite3.connect(DATABASE_PATH) as conn:
        row = conn.execute(
            "SELECT 1 FROM articles WHERE url_hash = ?", (url_hash,)
        ).fetchone()
    return row is None


def save_article(article: dict):
    """Save one article to the database. Skips silently if it already exists."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO articles
                (url_hash, title, url, summary, source, category, published)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _hash(article["url"]),
                article["title"],
                article["url"],
                article["summary"],
                article["source"],
                article["category"],
                str(article["published"]),
            ),
        )


def get_recent_top_articles() -> list[dict]:
    """Load the best scored articles from the past 2 days for the digest page."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT title, url, summary, source, category, published,
                   ai_summary, keywords, score
              FROM articles
             WHERE score >= 5
               AND created_at >= DATE('now', '-2 days')
             ORDER BY score DESC
             LIMIT 10
        """).fetchall()
    return [dict(r) for r in rows]


def update_ai_fields(article: dict):
    """Save the AI-generated score, summary, keywords, and category back to the database."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute(
            """
            UPDATE articles
               SET score      = ?,
                   ai_summary = ?,
                   keywords   = ?,
                   category   = ?
             WHERE url_hash   = ?
            """,
            (
                article.get("score", 0),
                article.get("ai_summary", ""),
                article.get("keywords", ""),
                article.get("category", ""),
                _hash(article["url"]),
            ),
        )


def _hash(url: str) -> str:
    """Generate a short unique fingerprint from a URL."""
    return hashlib.md5(url.encode()).hexdigest()
