"""
Global Business, Finance & Entrepreneurship Social & Corporate Intelligence Radar
Repository: phdhcornejo/news_diary
Live Web Target: https://globalbusinessradar.netlify.app
Self-contained Python 3.10+ standard library script.
"""

from datetime import datetime
from email.utils import parsedate_to_datetime
import html
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


# ==========================================
# CONFIGURATION & SOURCES
# ==========================================
OUTPUT_DIR = Path("global_business_radar")
NETLIFY_SITE_URL = "https://globalbusinessradar.netlify.app"
PUBLICATION_NAME = "Global Business, Finance & Leadership Brief"

# 1. Direct Corporate Newsrooms, Thought Leaders & Entrepreneurship Feeds
DIRECT_FEEDS = [
    ("Harvard Business Review", "https://hbr.org/resources/pdfs/comm/rss/hbr_ideacast.xml", 3.0),
    ("Y Combinator Blog", "https://www.ycombinator.com/blog/rss/", 3.5),
    ("Andreessen Horowitz (a16z)", "https://a16z.com/feed/", 3.5),
    ("First Round Review", "https://review.firstround.com/feed.xml", 3.0),
    ("NVIDIA Official Blog", "https://blogs.nvidia.com/feed/", 3.0),
    ("Microsoft Official Blog", "https://blogs.microsoft.com/feed/", 2.5),
    ("OpenAI News", "https://openai.com/news/rss.xml", 3.5),
    ("TechCrunch Startups & Venture", "https://techcrunch.com/category/venture/feed/", 2.5),
    ("World Economic Forum", "https://www.weforum.org/agenda/archive/feed/", 3.0),
]

# 2. Public Social Media & Leader Queries via Open Google News RSS (No API Key Required)
SOCIAL_AND_LEADER_QUERIES = [
    (
        "LinkedIn Pulse Leaders",
        'site:linkedin.com/pulse ("CEO" OR "finance" OR "strategy" OR "AI" OR "entrepreneurship")',
        3.0,
    ),
    (
        "X / Twitter Business & Finance",
        '(site:x.com OR site:twitter.com) ("Jensen Huang" OR "Satya Nadella" OR "Jamie Dimon" OR "Larry Fink" OR "Sam Altman" OR "Ray Dalio")',
        3.5,
    ),
    (
        "Reddit Business & Startups",
        '(site:reddit.com/r/business OR site:reddit.com/r/startups OR site:reddit.com/r/finance) ("funding" OR "acquisition" OR "market" OR "strategy")',
        2.0,
    ),
    (
        "Global CEOs & Megacorps",
        '("Jamie Dimon" OR "Larry Fink" OR "Jensen Huang" OR "Satya Nadella" OR "Warren Buffett" OR "Elon Musk") (economy OR markets OR investment OR AI)',
        3.0,
    ),
]

# Weighted entities & themes to surface the highest-signal stories
GLOBAL_LEADERS = {
    "jensen huang": 4.5,
    "satya nadella": 4.5,
    "jamie dimon": 4.5,
    "larry fink": 4.5,
    "sam altman": 4.0,
    "warren buffett": 4.5,
    "ray dalio": 4.0,
    "sundar pichai": 3.5,
    "tim cook": 3.5,
    "elon musk": 3.5,
    "christine lagarde": 4.0,
    "jerome powell": 4.5,
    "marc andreessen": 3.5,
    "paul graham": 3.5,
    "reid hoffman": 3.5,
}

MAJOR_COMPANIES = {
    "nvidia": 3.5,
    "microsoft": 3.0,
    "apple": 3.0,
    "alphabet": 3.0,
    "google": 2.5,
    "amazon": 3.0,
    "meta": 3.0,
    "openai": 3.5,
    "anthropic": 3.5,
    "blackrock": 4.0,
    "jpmorgan": 4.0,
    "goldman sachs": 4.0,
    "morgan stanley": 3.5,
    "berkshire hathaway": 4.0,
    "tsmc": 3.5,
    "y combinator": 3.5,
    "sequoia": 3.5,
    "a16z": 3.5,
}

HIGH_SIGNAL_TOPICS = {
    "series a": 3.0,
    "series b": 3.0,
    "seed round": 2.5,
    "venture capital": 3.0,
    "ipo": 3.5,
    "merger": 3.5,
    "acquisition": 3.5,
    "valuation": 3.0,
    "interest rates": 3.5,
    "inflation": 3.0,
    "capital allocation": 3.5,
    "supply chain": 2.5,
    "sovereign wealth": 3.5,
    "private equity": 3.0,
    "enterprise ai": 3.0,
    "productivity": 2.5,
    "startup": 2.5,
    "founder": 2.5,
}

PAYWALL_DOMAINS = (
    "wsj.com",
    "ft.com",
    "bloomberg.com",
    "nytimes.com",
    "economist.com",
    "barrons.com",
)


def clean_html(raw_text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    if not raw_text:
        return ""
    text = html.unescape(raw_text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_pub_date(date_str: str) -> datetime:
    """Parse RSS publication date safely."""
    if not date_str:
        return datetime.now()
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except Exception:
        return datetime.now()


def build_google_news_rss_url(query: str) -> str:
    """Construct a Google News RSS search URL for social/leader monitoring."""
    encoded = urllib.parse.quote(f"{query} when:2d")
    return f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"


def fetch_rss(source_label: str, url: str, base_bonus: float, channel: str, timeout: int = 12) -> list[dict]:
    """Fetch and parse standard RSS 2.0 XML feeds."""
    items = []
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        xml_data = resp.read()

    root = ET.fromstring(xml_data)
    for item in root.findall(".//item"):
        title = clean_html(item.findtext("title") or "")
        desc = clean_html(item.findtext("description") or "")
        link = (item.findtext("link") or "").strip()
        pub_raw = (item.findtext("pubDate") or "").strip()
        pub_dt = parse_pub_date(pub_raw)

        source_tag = item.find("source")
        publisher = clean_html(source_tag.text) if source_tag is not None and source_tag.text else source_label

        if title:
            items.append(
                {
                    "channel": channel,
                    "feed_group": source_label,
                    "publisher": publisher,
                    "base_bonus": base_bonus,
                    "title": title,
                    "summary": desc,
                    "link": link,
                    "published_at": pub_dt,
                }
            )
    return items


def classify_and_score(article: dict) -> dict:
    """Score relevance based on leaders, major companies, topics, openness, and recency."""
    haystack = f"{article['title']} {article['summary']}".lower()
    score = article.get("base_bonus", 0.0)
    matched_entities = []

    for leader, weight in GLOBAL_LEADERS.items():
        if re.search(r"\b" + re.escape(leader) + r"\b", haystack):
            score += weight
            matched_entities.append(leader.title())

    for comp, weight in MAJOR_COMPANIES.items():
        if re.search(r"\b" + re.escape(comp) + r"\b", haystack):
            score += weight
            matched_entities.append(comp.upper() if len(comp) <= 4 else comp.title())

    for topic, weight in HIGH_SIGNAL_TOPICS.items():
        if re.search(r"\b" + re.escape(topic) + r"\b", haystack):
            score += weight

    if re.search(r"(\$\d+(\.\d+)?\s?(billion|million|b|m)?|\d+(\.\d+)?%)", haystack):
        score += 2.5

    host = urllib.parse.urlparse(article["link"]).netloc.lower()
    if any(host == d or host.endswith("." + d) for d in PAYWALL_DOMAINS):
        score -= 8.0

    age_hours = max(0.0, (datetime.now() - article["published_at"]).total_seconds() / 3600.0)
    if age_hours <= 36:
        score += max(0.0, 3.5 * (1.0 - age_hours / 36.0))

    if any(k in haystack for k in ("startup", "founder", "series a", "series b", "seed round", "venture capital", "y combinator")):
        category = "Entrepreneurship & Venture"
    elif any(k in haystack for k in ("fed", "inflation", "interest rates", "markets", "blackrock", "jpmorgan", "ipo", "valuation")):
        category = "Finance & Capital Markets"
    else:
        category = "Corporate Strategy & Leadership"

    article["score"] = round(score, 2)
    article["category"] = category
    article["matched_entities"] = sorted(set(matched_entities))
    return article


def render_executive_digest(ranked_items: list[dict], top_n: int = 10) -> str:
    """Generate a dark-gold styled HTML executive dashboard with Open Graph tags."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    selected = ranked_items[:top_n]
    lead_title = selected[0]["title"] if selected else PUBLICATION_NAME
    lead_summary = selected[0]["summary"][:180] if selected and selected[0]["summary"] else "Daily business, finance & leadership radar."

    cards_html = []
    for idx, item in enumerate(selected, start=1):
        entities_str = ", ".join(item["matched_entities"]) if item["matched_entities"] else "Global Markets"
        summary_clean = item["summary"] if len(item["summary"]) > 25 else item["title"]
        if len(summary_clean) > 280:
            summary_clean = summary_clean[:277].rsplit(" ", 1)[0] + "..."

        cards_html.append(
            f"""
    <div class="card">
      <div class="card-top">
        <span class="badge">{html.escape(item['category'])}</span>
        <span class="channel">{html.escape(item['channel'])} &middot; {html.escape(item['publisher'])}</span>
      </div>
      <h2>{idx}. <a href="{html.escape(item['link'])}" target="_blank" rel="noopener noreferrer">{html.escape(item['title'])}</a></h2>
      <p class="summary">{html.escape(summary_clean)}</p>
      <div class="meta">
        <span><strong>Key Signals:</strong> {html.escape(entities_str)}</span>
        <span><strong>Impact Score:</strong> {item['score']}</span>
      </div>
    </div>"""
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(PUBLICATION_NAME)} - {now_str}</title>
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{html.escape(lead_title)}" />
  <meta property="og:description" content="{html.escape(lead_summary)}" />
  <meta property="og:url" content="{html.escape(NETLIFY_SITE_URL)}" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0a0a0a;
      --surface: #121212;
      --text: #f5f5f5;
      --muted: #a8a8a8;
      --gold: #c9a962;
      --border: #262218;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Inter', sans-serif;
      padding: 28px 16px;
      line-height: 1.55;
    }}
    .wrapper {{ max-width: 860px; margin: 0 auto; }}
    header {{
      border-bottom: 2px solid var(--gold);
      padding-bottom: 16px;
      margin-bottom: 24px;
    }}
    .kicker {{
      color: var(--gold);
      font-size: 0.78rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      font-weight: 600;
    }}
    h1 {{
      font-family: 'Cormorant Garamond', serif;
      font-size: 2.3rem;
      color: var(--gold);
      margin: 4px 0;
    }}
    .subtitle {{ color: var(--muted); font-size: 0.9rem; }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-left: 3px solid var(--gold);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 16px;
    }}
    .card-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 8px;
    }}
    .badge {{
      background: rgba(201, 169, 98, 0.15);
      color: var(--gold);
      border: 1px solid var(--gold);
      font-size: 0.72rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 4px;
      text-transform: uppercase;
    }}
    .channel {{ color: var(--muted); font-size: 0.8rem; }}
    h2 {{
      font-family: 'Cormorant Garamond', serif;
      font-size: 1.45rem;
      margin-bottom: 8px;
    }}
    h2 a {{ color: var(--text); text-decoration: none; }}
    h2 a:hover {{ color: var(--gold); text-decoration: underline; }}
    .summary {{ color: #d6d6d6; font-size: 0.94rem; margin-bottom: 12px; }}
    .meta {{
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
      font-size: 0.8rem;
      color: var(--gold);
      border-top: 1px solid #1f1f1f;
      padding-top: 8px;
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <header>
      <div class="kicker">Executive Intelligence &amp; Social Radar</div>
      <h1>{html.escape(PUBLICATION_NAME)}</h1>
      <div class="subtitle">Generated: {now_str} &middot; Top {len(selected)} High-Signal Stories</div>
    </header>
    {''.join(cards_html)}
  </div>
</body>
</html>
"""


def run_radar() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_items = []

    for label, url, bonus in DIRECT_FEEDS:
        try:
            raw_items.extend(fetch_rss(label, url, bonus, channel="Corporate / Ecosystem"))
        except Exception as exc:
            print(f"[Warning] Feed skipped ({label}): {exc}")

    for label, query, bonus in SOCIAL_AND_LEADER_QUERIES:
        try:
            rss_url = build_google_news_rss_url(query)
            raw_items.extend(fetch_rss(label, rss_url, bonus, channel="Social / Leaders"))
        except Exception as exc:
            print(f"[Warning] Social query skipped ({label}): {exc}")

    if not raw_items:
        raise RuntimeError("No items retrieved. Check internet connection.")

    deduped = {}
    for item in raw_items:
        scored = classify_and_score(item)
        norm_key = re.sub(r"\W+", "", scored["title"].lower())[:75]
        if norm_key not in deduped or scored["score"] > deduped[norm_key]["score"]:
            deduped[norm_key] = scored

    ranked = sorted(deduped.values(), key=lambda x: x["score"], reverse=True)
    date_tag = datetime.now().strftime("%Y-%m-%d")

    html_content = render_executive_digest(ranked, top_n=10)
    html_path = OUTPUT_DIR / f"business_radar_{date_tag}.html"
    index_path = OUTPUT_DIR / "index.html"
    json_path = OUTPUT_DIR / f"business_radar_{date_tag}.json"
    txt_path = Path("linkedin_post.txt")

    html_path.write_text(html_content, encoding="utf-8")
    index_path.write_text(html_content, encoding="utf-8")

    serializable = [
        {**r, "published_at": r["published_at"].isoformat()} for r in ranked[:25]
    ]
    json_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")

    linkedin_lines = [
        f"GLOBAL BUSINESS, FINANCE & LEADERSHIP RADAR ({date_tag})",
        "Top signals across global executives, corporations, venture ecosystems & social media:",
        "",
    ]
    for i, item in enumerate(ranked[:5], start=1):
        linkedin_lines.append(f"{i}. [{item['category']}] {item['title']} ({item['publisher']})")
    linkedin_lines.append("")
    linkedin_lines.append(f"Full interactive brief with active links: {NETLIFY_SITE_URL}")
    linkedin_lines.append("#BusinessStrategy #Finance #Leadership #Entrepreneurship #GlobalMarkets")
    txt_path.write_text("\n".join(linkedin_lines), encoding="utf-8")

    print(f"Updated {index_path} and {txt_path} for {NETLIFY_SITE_URL}")


if __name__ == "__main__":
    run_radar()
