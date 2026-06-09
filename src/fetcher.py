import feedparser
from datetime import datetime, timezone
from dateutil import parser as dateparser

from config import FEEDS, MAX_ARTICLES_PER_FEED


def fetch_all_articles() -> list[dict]:
    """Go through every feed, collect articles, return them as a list."""
    all_articles = []

    for feed_config in FEEDS:
        try:
            feed = feedparser.parse(feed_config["url"])
            entries = feed.entries[:MAX_ARTICLES_PER_FEED]

            for entry in entries:
                article = {
                    "title":     entry.get("title", "No title"),
                    "url":       entry.get("link", ""),
                    "summary":   entry.get("summary", entry.get("description", "")),
                    "published": _parse_date(entry),
                    "source":    feed_config["name"],
                    "category":  feed_config["category"],
                }
                all_articles.append(article)

        except Exception as e:
            print(f"[fetcher] Could not fetch {feed_config['name']}: {e}")

    # sort by newest first
    all_articles.sort(key=lambda a: a["published"], reverse=True)
    return all_articles


def _parse_date(entry) -> datetime:
    """Extract and parse the publication date from an RSS entry."""
    for field in ("published", "updated"):
        raw = entry.get(f"{field}_parsed") or entry.get(field)
        if raw:
            try:
                if hasattr(raw, "tm_year"):
                    return datetime(*raw[:6], tzinfo=timezone.utc)
                return dateparser.parse(str(raw)).replace(tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)  # fallback: use current time if no date found
