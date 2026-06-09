import os

# ── Claude API ────────────────────────────────────────────────────────────────
# Reads the API key from your environment variables, never hardcoded here
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"

# ── Pipeline settings ─────────────────────────────────────────────────────────
MAX_ARTICLES_PER_FEED = 5        # how many articles to pull from each source
TOP_ARTICLES_TO_SUMMARIZE = 10   # how many articles Claude summarizes per day

# ── News sources ──────────────────────────────────────────────────────────────
# Each source has a URL (the RSS feed) and a category (AI/ML or Tech)
FEEDS = [
    # AI / ML sources
    {"url": "https://huggingface.co/blog/feed.xml",              "category": "AI/ML", "name": "HuggingFace"},
    {"url": "https://deepmind.google/blog/rss/",                 "category": "AI/ML", "name": "Google DeepMind"},
    {"url": "https://www.anthropic.com/rss.xml",                 "category": "AI/ML", "name": "Anthropic"},
    {"url": "https://venturebeat.com/category/ai/feed/",         "category": "AI/ML", "name": "VentureBeat AI"},
    # Tech industry sources
    {"url": "https://techcrunch.com/feed/",                      "category": "Tech",  "name": "TechCrunch"},
    {"url": "https://www.theverge.com/rss/index.xml",            "category": "Tech",  "name": "The Verge"},
    {"url": "https://www.wired.com/feed/rss",                    "category": "Tech",  "name": "Wired"},
    {"url": "https://news.ycombinator.com/rss",                  "category": "Tech",  "name": "Hacker News"},
]

# ── File paths ────────────────────────────────────────────────────────────────
DATABASE_PATH = "data/digest.db"
OUTPUT_DIR = "output"
