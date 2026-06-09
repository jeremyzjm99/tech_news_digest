import json
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from config import CLAUDE_MODEL, TOP_ARTICLES_TO_SUMMARIZE

# Load .env first — the SDK reads ANTHROPIC_API_KEY from os.environ automatically
load_dotenv(Path(__file__).parent.parent / ".env")

_client = anthropic.Anthropic()


# ── Stage 1: rank ─────────────────────────────────────────────────────────────

def rank_articles(articles: list[dict]) -> list[dict]:
    """Ask Claude to score every article 1-10. Returns the top N, sorted."""
    if not articles:
        return []

    lines = []
    for i, a in enumerate(articles):
        blurb = _strip_html(a.get("summary", ""))[:200]
        lines.append(f"{i}. [{a['source']}] {a['title']} — {blurb}")
    article_list = "\n".join(lines)

    prompt = f"""You are an editor for a daily AI & Tech digest aimed at data professionals.

Below are {len(articles)} articles collected today. Score each one from 1 (not interesting) to 10 (must-read) based on:
- Relevance to AI, ML, or the tech industry
- Novelty and impact
- Usefulness to a data analyst or engineer

Return ONLY a JSON array, no other text. Each element must have exactly two keys: "index" (integer, the article number) and "score" (integer 1-10).

Example format:
[{{"index": 0, "score": 8}}, {{"index": 1, "score": 3}}]

Articles:
{article_list}"""

    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()

    try:
        scores = _parse_json(raw)
        score_map = {item["index"]: item["score"] for item in scores}
    except Exception:
        print("[summarizer] Could not parse ranking response — using default scores")
        score_map = {}

    for i, article in enumerate(articles):
        article["score"] = score_map.get(i, 0)

    ranked = sorted(articles, key=lambda a: a["score"], reverse=True)
    return ranked[:TOP_ARTICLES_TO_SUMMARIZE]


# ── Stage 2: summarize ────────────────────────────────────────────────────────

def summarize_articles(top_articles: list[dict]) -> list[dict]:
    """For each top article, ask Claude for a 2-3 sentence summary + keywords."""
    for article in top_articles:
        raw_summary = _strip_html(article.get("summary", ""))

        prompt = f"""Summarize the following news article for a data professional audience.

Title: {article['title']}
Source: {article['source']}
Original blurb: {raw_summary}

Return ONLY a JSON object with three keys:
- "summary": a clear, jargon-free 2-3 sentence summary
- "keywords": a list of 3-5 short, broad, reusable terms (single words or common short phrases like "OpenAI", "LLM", "agents", "pricing" — NOT full sentences or hyper-specific technical phrases)
- "category": exactly one label chosen from this fixed list based on the article's content (not its source):
    Research      — papers, model benchmarks, lab findings
    Tools         — libraries, frameworks, open-source releases
    Industry      — funding, acquisitions, company news, product launches
    Policy        — regulation, AI safety, ethics, government
    Infrastructure — cloud, data pipelines, databases, MLOps
    Consumer      — products or apps aimed at general consumers

Example:
{{"summary": "OpenAI released...", "keywords": ["OpenAI", "LLM", "reasoning", "agents"], "category": "Industry"}}"""

        response = _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        try:
            parsed = _parse_json(raw)
            article["ai_summary"] = parsed.get("summary", "")
            article["keywords"]   = ", ".join(parsed.get("keywords", []))
            article["category"]   = parsed.get("category", "")
        except Exception:
            print(f"[summarizer] Could not parse response for: {article['title'][:60]}")
            article["ai_summary"] = ""
            article["keywords"]   = ""

    return top_articles


# ── Stage 3: overview ─────────────────────────────────────────────────────────

def write_overview(top_articles: list[dict]) -> str:
    """Ask Claude to write a short 'Today's Overview' intro paragraph."""
    titles = "\n".join(f"- {a['title']} ({a['source']})" for a in top_articles)

    prompt = f"""You are writing the intro paragraph for a daily AI & Tech digest newsletter.

Today's top stories are:
{titles}

Write a single engaging paragraph (3-5 sentences) that briefly previews today's themes and highlights. Write for a data-professional audience. Do not use bullet points — flowing prose only."""

    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


# ── Public entry point ────────────────────────────────────────────────────────

def run_ai_pipeline(articles: list[dict]) -> tuple[list[dict], str]:
    """
    Full three-stage pipeline.
    Returns (top_articles_with_summaries, overview_paragraph).
    """
    print(f"[summarizer] Stage 1: ranking {len(articles)} articles…")
    top = rank_articles(articles)

    print(f"[summarizer] Stage 2: summarizing {len(top)} top articles…")
    top = summarize_articles(top)

    print("[summarizer] Stage 3: writing today's overview…")
    overview = write_overview(top)

    return top, overview


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_json(text: str):
    """
    Extract and parse JSON from Claude's response.
    Handles markdown code fences like ```json ... ```.
    """
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        text = match.group(1)
    return json.loads(text)
