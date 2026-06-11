import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config import OUTPUT_DIR

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_OUTPUT_DIR = Path(OUTPUT_DIR)


def render_digest(top_articles: list[dict], overview: str, analytics: dict):
    """Render all HTML pages and write them to the output/ directory."""
    _OUTPUT_DIR.mkdir(exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))
    env.filters["tojson"] = json.dumps
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")

    _render("digest.html", env, "digest.html", {
        "articles": top_articles,
        "overview": overview,
        "date": today,
    })

    _render("analytics.html", env, "analytics.html", {
        "analytics": analytics,
        "date": today,
    })

    print(f"[renderer] Pages written to {_OUTPUT_DIR}/")


def _render(template_name: str, env: Environment, output_name: str, context: dict):
    template = env.get_template(template_name)
    html = template.render(**context)
    ((_OUTPUT_DIR) / output_name).write_text(html, encoding="utf-8")
