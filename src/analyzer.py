import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from config import DATABASE_PATH


def run_analytics() -> dict:
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return {
            "source_hit_rate":  _source_hit_rate(conn),
            "weekly_keywords":  _top_keywords(conn),
            "top_articles":     _weekly_top_articles(conn),
            "topic_velocity":   _topic_velocity(conn),
            "topic_trend":      _topic_trend(conn),
        }


def _source_hit_rate(conn) -> list[dict]:
    """Per source over the last 7 days: total fetched, top-10 hits, hit rate %."""
    rows = conn.execute("""
        SELECT source,
               COUNT(*)                                                    AS total,
               SUM(CASE WHEN score > 0 THEN 1 ELSE 0 END)                 AS top10_count,
               ROUND(100.0 * SUM(CASE WHEN score > 0 THEN 1 ELSE 0 END)
                     / COUNT(*), 1)                                        AS hit_rate_pct
          FROM articles
         WHERE created_at >= DATE('now', '-7 days')
         GROUP BY source
         ORDER BY hit_rate_pct DESC
    """).fetchall()
    return [dict(r) for r in rows]


def _top_keywords(conn, top_n: int = 20) -> list[dict]:
    """Most frequent keywords across top-10 articles in the last 7 days."""
    rows = conn.execute("""
        SELECT keywords
          FROM articles
         WHERE keywords IS NOT NULL
           AND keywords != ''
           AND created_at >= DATE('now', '-7 days')
    """).fetchall()

    counter = Counter()
    for row in rows:
        for kw in row["keywords"].split(","):
            word = kw.strip().lower()
            if word:
                counter[word] += 1

    return [{"keyword": kw, "count": cnt} for kw, cnt in counter.most_common(top_n)]


def _weekly_top_articles(conn, top_n: int = 5) -> list[dict]:
    """Highest-scored articles from the past 7 days — the week's best content."""
    rows = conn.execute("""
        SELECT title, url, source, score, ai_summary
          FROM articles
         WHERE score >= 5
           AND created_at >= DATE('now', '-7 days')
         ORDER BY score DESC
         LIMIT ?
    """, (top_n,)).fetchall()
    return [dict(r) for r in rows]


def _topic_velocity(conn, top_n: int = 10) -> list[dict]:
    """
    Compare keyword frequency this week vs last week.
    Returns the fastest-growing keywords with their growth rate.
    Keywords that are brand-new this week are marked as 'new'.
    """
    def _count_keywords(rows) -> Counter:
        counter = Counter()
        for row in rows:
            for kw in row["keywords"].split(","):
                word = kw.strip().lower()
                if word:
                    counter[word] += 1
        return counter

    this_week_rows = conn.execute("""
        SELECT keywords FROM articles
         WHERE keywords IS NOT NULL AND keywords != ''
           AND created_at >= DATE('now', '-7 days')
    """).fetchall()

    last_week_rows = conn.execute("""
        SELECT keywords FROM articles
         WHERE keywords IS NOT NULL AND keywords != ''
           AND created_at >= DATE('now', '-14 days')
           AND created_at <  DATE('now', '-7 days')
    """).fetchall()

    this_week = _count_keywords(this_week_rows)
    last_week = _count_keywords(last_week_rows)

    results = []
    for kw, this_count in this_week.items():
        prev_count = last_week.get(kw, 0)
        if prev_count == 0:
            growth = None       # brand new this week
        else:
            growth = round((this_count - prev_count) / prev_count * 100)
        results.append({
            "keyword":    kw,
            "this_week":  this_count,
            "last_week":  prev_count,
            "growth":     growth,   # None means new, positive means rising, negative means falling
        })

    # Sort: new keywords first, then by growth rate descending
    results.sort(key=lambda x: (x["growth"] is not None, -(x["growth"] or 0), -x["this_week"]))
    return results[:top_n]


def _topic_trend(conn, n_weeks: int = 6, top_n: int = 6) -> dict:
    """
    Keyword frequency per week for the past n_weeks.
    Returns the top_n most frequent keywords overall, with per-week counts.
    Used for the multi-week line chart — data fills in over time.
    """
    days = n_weeks * 7
    rows = conn.execute(f"""
        SELECT keywords, DATE(created_at) AS date
          FROM articles
         WHERE keywords IS NOT NULL AND keywords != ''
           AND created_at >= DATE('now', '-{days} days')
    """).fetchall()

    week_counts = defaultdict(Counter)
    week_labels = {}

    for row in rows:
        date = datetime.strptime(row["date"], "%Y-%m-%d")
        week_start = date - timedelta(days=date.weekday())   # Monday
        week_key   = week_start.strftime("%Y-%m-%d")         # for sorting
        week_labels[week_key] = week_start.strftime("%b %d") # for display
        for kw in row["keywords"].split(","):
            word = kw.strip().lower()
            if word:
                week_counts[week_key][word] += 1

    if not week_counts:
        return {"labels": [], "series": []}

    total = Counter()
    for c in week_counts.values():
        total.update(c)
    top_keywords = [kw for kw, _ in total.most_common(top_n)]

    sorted_weeks = sorted(week_counts.keys())
    return {
        "labels": [week_labels[w] for w in sorted_weeks],
        "series": [
            {"keyword": kw, "counts": [week_counts[w].get(kw, 0) for w in sorted_weeks]}
            for kw in top_keywords
        ],
    }
