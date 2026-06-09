from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from src.fetcher import fetch_all_articles
from src.storage import init_db, is_new, save_article, update_ai_fields, get_recent_top_articles
from src.summarizer import run_ai_pipeline
from src.analyzer import run_analytics
from src.renderer import render_digest


def main():
    print("=== AI & Tech Digest Pipeline ===")

    # 1. Set up database
    init_db()

    # 2. Fetch articles from all RSS feeds
    articles = fetch_all_articles()
    print(f"[main] Fetched {len(articles)} articles total")

    # 3. Keep only articles we haven't seen before
    new_articles = [a for a in articles if is_new(a["url"])]
    print(f"[main] {len(new_articles)} new articles to process")

    overview = ""

    if new_articles:
        # 4. Save new articles to database
        for article in new_articles:
            save_article(article)
        print(f"[main] Saved {len(new_articles)} articles to database")

        # 5. Run AI pipeline (rank → summarize → overview)
        top_articles, overview = run_ai_pipeline(new_articles)

        # 6. Write AI results back to database
        for article in top_articles:
            update_ai_fields(article)
        print(f"[main] Updated {len(top_articles)} articles with AI fields")
    else:
        print("[main] No new articles today")

    # 7. Always pull the digest from the database (past 2 days, score >= 5)
    top_articles = get_recent_top_articles()
    if not overview:
        overview = "No new articles were found today. Showing the most recent top stories."
    print(f"[main] Rendering digest with {len(top_articles)} articles")

    # 8. Run SQL analytics (always runs — uses 7-day window)
    analytics = run_analytics()

    # 9. Render HTML pages
    render_digest(top_articles, overview, analytics)

    print("=== Done ===")


if __name__ == "__main__":
    main()
