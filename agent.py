#!/usr/bin/env python3
"""
ANN Feed — AI News Agent  (Groq Edition)
─────────────────────────────────────────
Scrapes 30+ RSS feeds (Tunisia + Global), generates crisp 2-sentence
briefs via Groq's FREE API, writes news.json, and optionally pushes
to GitHub in one command.

FREE SETUP (do once):
  1. pip install feedparser requests schedule
  2. Sign up at https://console.groq.com → API Keys → Create Key
  3. Set env variable:
       Windows:   setx GROQ_API_KEY "gsk_your_key_here"
       Mac/Linux: export GROQ_API_KEY="gsk_your_key_here"
  4. Set REPO_PATH below to your local repo folder.

USAGE:
  python agent.py                   # run once, no push
  python agent.py --push            # run once + git push
  python agent.py --schedule        # run every 90 min, no push
  python agent.py --schedule --push # run every 90 min + auto push
"""

import feedparser
import requests
import json
import os
import subprocess
import time
import argparse
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

# ══════════════════════════════════════════════════════════════════
#  ★  EDIT THESE TWO LINES ONLY  ★
# ══════════════════════════════════════════════════════════════════

# Absolute path to your local repo folder (contains index.html)
# Windows example:  r"C:\Users\YourName\Desktop\ANN-Global"
# Mac/Linux example: "/home/yourname/projects/ANN-Global"
REPO_PATH = os.path.expanduser("REPO_PATH = r"C:\Users\Alaeddine Nijaoui\Desktop\project\ANN-Global")

# Groq free API key — set via env variable (recommended) or paste here
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ══════════════════════════════════════════════════════════════════
#  INTERNALS
# ══════════════════════════════════════════════════════════════════

OUTPUT_FILE         = "news.json"
MAX_ARTICLES        = 30           # total articles in news.json
ENTRIES_PER_FEED    = 5            # headlines pulled per source
FETCH_EVERY_MINUTES = 90           # schedule interval

GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"

# ══════════════════════════════════════════════════════════════════
#  RSS FEEDS
# ══════════════════════════════════════════════════════════════════

FEEDS = [

    # ── TUNISIA ──────────────────────────────────────────────────
    {"url": "https://www.tap.info.tn/en/feed",
     "source": "TAP",            "region": "Tunisia"},
    {"url": "https://www.tap.info.tn/fr/feed",
     "source": "TAP (FR)",       "region": "Tunisia"},
    {"url": "https://www.watania1.tn/feed/",
     "source": "Watania 1",      "region": "Tunisia"},
    {"url": "https://www.babnet.net/rss2.php",
     "source": "Babnet",         "region": "Tunisia"},
    {"url": "https://www.lapresse.tn/feed/",
     "source": "La Presse TN",   "region": "Tunisia"},
    {"url": "https://www.mosaiquefm.net/rss",
     "source": "Mosaique FM",    "region": "Tunisia"},
    {"url": "https://www.ifmnews.com/feed/",
     "source": "IFM",            "region": "Tunisia"},
    {"url": "https://www.radionationale.tn/feed/",
     "source": "Radio Nationale","region": "Tunisia"},
    {"url": "https://diwanem.com/feed/",
     "source": "Diwan FM",       "region": "Tunisia"},
    {"url": "https://kapitalis.com/feed/",
     "source": "Kapitalis",      "region": "Tunisia"},

    # ── MENA / AFRICA ─────────────────────────────────────────────
    {"url": "https://www.aljazeera.com/xml/rss/all.xml",
     "source": "Al Jazeera",     "region": "MENA"},
    {"url": "https://www.reuters.com/world/middle-east/rss",
     "source": "Reuters MENA",   "region": "MENA"},
    {"url": "https://www.financialafrik.com/feed/",
     "source": "Financial Afrik","region": "Africa",  "category": "Economy"},
    {"url": "https://www.leconomiste.com.tn/feed/",
     "source": "L'Economiste",   "region": "Tunisia", "category": "Economy"},

    # ── GLOBAL ────────────────────────────────────────────────────
    {"url": "https://feeds.reuters.com/reuters/worldNews",
     "source": "Reuters",        "region": "Global"},
    {"url": "http://feeds.bbci.co.uk/news/world/rss.xml",
     "source": "BBC News",       "region": "Global"},
    {"url": "https://apnews.com/rss",
     "source": "AP News",        "region": "Global"},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
     "source": "New York Times", "region": "Global"},
    {"url": "https://nypost.com/feed/",
     "source": "New York Post",  "region": "Global"},
    {"url": "https://www.independent.co.uk/news/rss",
     "source": "The Independent","region": "Global"},
    {"url": "https://feeds.washingtonpost.com/rss/world",
     "source": "Washington Post","region": "Global"},
    {"url": "http://rss.cnn.com/rss/edition_world.rss",
     "source": "CNN",            "region": "Global"},
    {"url": "https://www.economist.com/the-world-this-week/rss.xml",
     "source": "The Economist",  "region": "Global"},

    # ── TECHNOLOGY / AI ───────────────────────────────────────────
    {"url": "https://feeds.reuters.com/reuters/technologyNews",
     "source": "Reuters Tech",   "region": "Global", "category": "Technology"},
    {"url": "http://feeds.bbci.co.uk/news/technology/rss.xml",
     "source": "BBC Tech",       "region": "Global", "category": "Technology"},
    {"url": "https://techcrunch.com/feed/",
     "source": "TechCrunch",     "region": "Global", "category": "Technology"},
    {"url": "https://www.wired.com/feed/rss",
     "source": "WIRED",          "region": "Global", "category": "Technology"},
    {"url": "https://feeds.arstechnica.com/arstechnica/index",
     "source": "Ars Technica",   "region": "Global", "category": "Technology"},

    # ── ECONOMY / FINANCE ─────────────────────────────────────────
    {"url": "https://www.ft.com/?format=rss",
     "source": "Financial Times","region": "Global", "category": "Economy"},
    {"url": "https://www.imf.org/en/News/rss",
     "source": "IMF",            "region": "Global", "category": "Economy"},
]

# ══════════════════════════════════════════════════════════════════
#  CATEGORY DETECTION
# ══════════════════════════════════════════════════════════════════

CATEGORY_RULES = [
    (["AI", "artificial intelligence", "machine learning", "LLM",
      "OpenAI", "Anthropic", "Mistral", "GPT", "chatbot",
      "semiconductor", "chip", "TSMC", "Nvidia", "Intel"],       "Technology"),
    (["cyber", "hack", "ransomware", "malware",
      "security breach", "vulnerability", "phishing"],           "Cybersecurity"),
    (["Tunisia", "Tunisian", "Tunis", "BCT", "Sfax",
      "Bizerte", "Sousse", "Monastir", "Kairouan"],              "Tunisia"),
    (["MENA", "Morocco", "Libya", "Algeria", "Egypt",
      "Gulf", "Saudi", "UAE", "Qatar", "Jordan", "Lebanon"],     "MENA"),
    (["Africa", "African", "AfDB", "AfCFTA", "Sahel"],           "Africa"),
    (["climate", "drought", "emissions", "COP",
      "renewable", "solar", "carbon", "temperature"],            "Climate"),
    (["GDP", "inflation", "IMF", "World Bank", "economy",
      "trade", "recession", "market", "bond", "interest rate",
      "fiscal", "monetary", "fintech", "finance"],               "Economy"),
    (["conflict", "war", "strike", "ceasefire",
      "military", "troops", "attack", "weapons"],                "Geopolitics"),
]

def guess_category(text: str, default: str = "World") -> str:
    t = text.lower()
    for keywords, cat in CATEGORY_RULES:
        if any(k.lower() in t for k in keywords):
            return cat
    return default

def article_id(title: str) -> str:
    return hashlib.md5(title.encode()).hexdigest()[:10]

def format_time(entry) -> str:
    try:
        t = entry.get("published_parsed") or entry.get("updated_parsed")
        if t:
            dt  = datetime(*t[:6], tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            diff = now - dt
            if diff.days == 0:
                if diff.seconds < 3600:
                    return f"{diff.seconds // 60}m ago"
                return f"{diff.seconds // 3600}h ago"
            if diff.days == 1:
                return "Yesterday"
            return dt.strftime("%b %d")
    except Exception:
        pass
    return ""

def clean_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", text).strip()

# ══════════════════════════════════════════════════════════════════
#  GROQ BRIEF GENERATOR
# ══════════════════════════════════════════════════════════════════

def generate_brief(title: str, description: str, retry: bool = True) -> str:
    clean_desc = clean_html(description)[:500]

    if not GROQ_API_KEY:
        return (clean_desc[:220] + "…") if len(clean_desc) > 220 else clean_desc or "No summary available."

    prompt = (
        "Write exactly 2 concise, factual sentences summarising this news story. "
        "Be direct and informative. No opinions, no preamble, no commentary.\n\n"
        f"Headline: {title}\nContext: {clean_desc}"
    )

    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 120, "temperature": 0.2},
            timeout=20,
        )
        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"].strip()
            sentences = [s.strip() for s in text.split(". ") if s.strip()]
            brief = ". ".join(sentences[:2])
            if brief and not brief.endswith("."):
                brief += "."
            return brief if len(brief) > 30 else clean_desc[:220]
        elif resp.status_code == 429 and retry:
            print("  ⏳ Rate limit — waiting 12 s…")
            time.sleep(12)
            return generate_brief(title, description, retry=False)
        else:
            print(f"  ⚠  Groq {resp.status_code}")
    except Exception as e:
        print(f"  ⚠  Groq error ({e})")

    return (clean_desc[:220] + "…") if len(clean_desc) > 220 else clean_desc or "No summary available."

# ══════════════════════════════════════════════════════════════════
#  SCRAPER
# ══════════════════════════════════════════════════════════════════

def scrape_and_generate():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] ANN Feed Agent starting…")
    print(f"  {len(FEEDS)} feeds  |  target {MAX_ARTICLES} articles\n")

    seen_ids: set  = set()
    articles: list = []

    for feed_cfg in FEEDS:
        url         = feed_cfg["url"]
        source      = feed_cfg.get("source", "Unknown")
        region      = feed_cfg.get("region", "Global")
        default_cat = feed_cfg.get("category", None)

        print(f"  → {source:<22}", end=" ", flush=True)
        try:
            feed    = feedparser.parse(url)
            entries = feed.entries[:ENTRIES_PER_FEED]
            if not entries:
                print("0 entries")
                continue
            print(f"{len(entries)} entries")
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        for entry in entries:
            title = entry.get("title", "").strip()
            if not title:
                continue
            uid = article_id(title)
            if uid in seen_ids:
                continue
            seen_ids.add(uid)

            desc     = entry.get("summary", "") or entry.get("description", "")
            link     = entry.get("link", "#")
            time_str = format_time(entry)
            category = default_cat or guess_category(title + " " + desc)

            print(f"    ✍  {title[:72]}…")
            brief = generate_brief(title, desc)

            articles.append({
                "id":       uid,
                "title":    title,
                "brief":    brief,
                "source":   source,
                "url":      link,
                "category": category,
                "region":   region,
                "time":     time_str,
                "date":     datetime.now().strftime("%b %d"),
            })

            time.sleep(2)   # Groq free tier: ≤30 req/min

        if len(articles) >= MAX_ARTICLES:
            print(f"\n  ✅ Reached {MAX_ARTICLES} article limit.")
            break

    articles = articles[:MAX_ARTICLES]

    now = datetime.now()
    output = {
        "updated":  now.strftime("%H:%M"),
        "date":     now.strftime("%b %d, %Y"),
        "count":    len(articles),
        "articles": articles,
    }

    out_path = Path(__file__).parent / OUTPUT_FILE
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅  Wrote {len(articles)} articles → {out_path}\n")

# ══════════════════════════════════════════════════════════════════
#  GIT PUSH
# ══════════════════════════════════════════════════════════════════

def push_to_github():
    print("── Pushing to GitHub ───────────────────────────")
    repo = Path(REPO_PATH)
    if not repo.exists():
        print(f"❌  Repo path not found: {REPO_PATH}")
        print("    Open agent.py and set REPO_PATH at the top.")
        return
    try:
        os.chdir(repo)
        subprocess.run(["git", "add", "news.json"], check=True)
        result = subprocess.run(
            ["git", "commit", "-m", f"[ANN] News update {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
            capture_output=True, text=True
        )
        if "nothing to commit" in result.stdout + result.stderr:
            print("ℹ️   news.json unchanged — nothing to push.")
            return
        push = subprocess.run(["git", "push", "origin", "main"],
                               capture_output=True, text=True)
        if push.returncode == 0:
            print("🚀  Pushed! Site updates in ~60 s.")
        else:
            print(f"❌  Push failed:\n{push.stderr}")
            print("    Try: git pull origin main  then run agent again.")
    except Exception as e:
        print(f"❌  {e}")

# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="ANN Feed AI News Agent")
    parser.add_argument("--schedule", action="store_true",
                        help=f"Run every {FETCH_EVERY_MINUTES} min continuously")
    parser.add_argument("--push", action="store_true",
                        help="Push news.json to GitHub after each run")
    args = parser.parse_args()

    print("═" * 50)
    print("  ANN Feed — AI News Agent")
    print("═" * 50)
    if not GROQ_API_KEY:
        print("⚠  GROQ_API_KEY not set — using raw RSS text as fallback.")
        print("   Free key: https://console.groq.com\n")
    else:
        print(f"✅  Groq key detected  |  {len(FEEDS)} feeds  |  max {MAX_ARTICLES} articles\n")

    def run_once():
        scrape_and_generate()
        if args.push:
            push_to_github()

    if args.schedule:
        print(f"📅  Scheduled mode — every {FETCH_EVERY_MINUTES} min. Ctrl+C to stop.\n")
        try:
            import schedule as sched
            sched.every(FETCH_EVERY_MINUTES).minutes.do(run_once)
            run_once()
            while True:
                sched.run_pending()
                time.sleep(30)
        except ImportError:
            print("Run:  pip install schedule")
        except KeyboardInterrupt:
            print("\n⏹  Agent stopped.")
    else:
        run_once()

if __name__ == "__main__":
    main()
