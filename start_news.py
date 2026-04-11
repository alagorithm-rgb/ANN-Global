#!/usr/bin/env python3
"""
ANN Feed — AI News Agent (Groq Edition)
────────────────────────────────────────
Scrapes official RSS feeds, generates 2-sentence briefs via Groq's free API
(llama-3.1-8b-instant), and writes news.json for the GitHub Pages site.

Free tier: https://console.groq.com  →  Sign up → API Keys → Create key
Free limit: 14,400 requests/day, 30 req/min — more than enough for this use case.

Requirements:
  pip install feedparser requests schedule

Run manually:
  python agent.py

Run on a schedule (keeps running, re-scrapes every 90 min):
  python agent.py --schedule

Publish to GitHub after each run:
  python agent.py --push
  python agent.py --schedule --push
"""

import feedparser
import requests
import json
import os
import subprocess
import time
import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────

OUTPUT_FILE   = "news.json"   # Written next to this script, served by GitHub Pages
MAX_ARTICLES  = 12            # Articles to keep in news.json
FETCH_EVERY_MINUTES = 90      # How often to re-scrape in --schedule mode

# ── GROQ CONFIG ───────────────────────────────────────────────────────────────
# Get your free key at: https://console.groq.com
# Set it as an environment variable (recommended) OR paste it directly below.
#
# To set as env variable (do this once in your terminal):
#   Windows:  setx GROQ_API_KEY "gsk_your_key_here"
#   Mac/Linux: export GROQ_API_KEY="gsk_your_key_here"
#
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")   # ← or paste key here as fallback
GROQ_MODEL   = "llama-3.1-8b-instant"               # Free, fast, excellent quality
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

# ── GITHUB CONFIG (for --push flag) ───────────────────────────────────────────
# Set this to the absolute path of your local ANN repo folder.
# Example Windows: r"C:\Users\YourName\Desktop\project\ANN-Global"
# Example Mac/Linux: "/home/yourname/projects/ANN-Global"
REPO_PATH = os.path.expanduser("~/Desktop/project/ANN-Global")

# ── RSS SOURCES ───────────────────────────────────────────────────────────────

FEEDS = [
    # Global
    {"url": "https://feeds.reuters.com/reuters/worldNews",           "source": "Reuters",       "region": "Global"},
    {"url": "https://feeds.reuters.com/reuters/technologyNews",      "source": "Reuters",       "region": "Global",  "category": "Technology"},
    {"url": "http://feeds.bbci.co.uk/news/world/rss.xml",            "source": "BBC News",      "region": "Global"},
    {"url": "http://feeds.bbci.co.uk/news/technology/rss.xml",       "source": "BBC Tech",      "region": "Global",  "category": "Technology"},
    {"url": "https://www.aljazeera.com/xml/rss/all.xml",             "source": "Al Jazeera",    "region": "MENA"},
    {"url": "https://apnews.com/rss",                                "source": "AP News",       "region": "Global"},
    # MENA / Tunisia
    {"url": "https://www.tap.info.tn/en/feed",                       "source": "TAP Tunisia",   "region": "Tunisia"},
    {"url": "https://kapitalis.com/feed/",                           "source": "Kapitalis",     "region": "Tunisia"},
    {"url": "https://www.reuters.com/world/middle-east/rss",         "source": "Reuters MENA",  "region": "MENA"},
    # Technology / AI
    {"url": "https://techcrunch.com/feed/",                          "source": "TechCrunch",    "region": "Global",  "category": "Technology"},
    {"url": "https://www.wired.com/feed/rss",                        "source": "WIRED",         "region": "Global",  "category": "Technology"},
    {"url": "https://feeds.arstechnica.com/arstechnica/index",       "source": "Ars Technica",  "region": "Global",  "category": "Technology"},
    # Economy / Finance
    {"url": "https://www.imf.org/en/News/rss",                       "source": "IMF",           "region": "Global",  "category": "Economy"},
]

# ── CATEGORY AUTO-DETECTION ───────────────────────────────────────────────────

CATEGORY_RULES = [
    (["AI", "artificial intelligence", "machine learning", "LLM", "OpenAI", "Anthropic", "Mistral", "GPT", "semiconductor", "chip", "Nvidia"], "Technology"),
    (["cyber", "hack", "ransomware", "malware", "security breach", "vulnerability"],                                                            "Cybersecurity"),
    (["Tunisia", "Tunisian", "Tunis", "BCT", "Sfax", "Bizerte", "Sousse"],                                                                      "Tunisia"),
    (["MENA", "Morocco", "Libya", "Algeria", "Egypt", "Gulf", "Saudi", "UAE", "Qatar"],                                                         "MENA"),
    (["climate", "drought", "temperature", "emissions", "COP", "renewable", "solar"],                                                           "Climate"),
    (["GDP", "inflation", "IMF", "World Bank", "economy", "trade", "recession", "market", "bond", "rate"],                                      "Economy"),
    (["conflict", "war", "strike", "ceasefire", "military", "troops", "attack", "weapons"],                                                     "Geopolitics"),
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
            dt = datetime(*t[:6], tzinfo=timezone.utc)
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

# ── GROQ BRIEF GENERATOR ──────────────────────────────────────────────────────

def generate_brief(title: str, description: str) -> str:
    """
    Calls Groq's free API to generate a 2-sentence news brief.
    Falls back to a cleaned description if the API is unavailable or key is missing.
    """
    # Clean the description
    clean_desc = description
    for tag in ["<p>", "</p>", "<b>", "</b>", "<br>", "<br/>", "\n", "\r"]:
        clean_desc = clean_desc.replace(tag, " ")
    clean_desc = " ".join(clean_desc.split()).strip()[:500]

    # Fallback if no API key set
    if not GROQ_API_KEY:
        if clean_desc:
            return clean_desc[:220] + ("…" if len(clean_desc) > 220 else "")
        return "No summary available."

    prompt = (
        f"Write exactly 2 concise, factual sentences summarising this news story. "
        f"Be direct and informative. Do not add opinions or commentary.\n\n"
        f"Headline: {title}\n"
        f"Context: {clean_desc}"
    )

    try:
        resp = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 120,
                "temperature": 0.2,
            },
            timeout=20,
        )
        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"].strip()
            # Keep first 2 sentences only
            sentences = [s.strip() for s in text.replace("  ", " ").split(". ") if s.strip()]
            brief = ". ".join(sentences[:2])
            if brief and not brief.endswith("."):
                brief += "."
            return brief if len(brief) > 30 else clean_desc[:220]
        else:
            print(f"  ⚠  Groq API error {resp.status_code}: {resp.text[:120]}")
    except Exception as e:
        print(f"  ⚠  Groq request failed ({e}) — using raw description")

    # Fallback
    if clean_desc:
        return clean_desc[:220] + ("…" if len(clean_desc) > 220 else "")
    return "No summary available."

# ── MAIN SCRAPER ──────────────────────────────────────────────────────────────

def scrape_and_generate():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] ANN Feed Agent starting...")

    seen_ids: set = set()
    articles: list = []

    for feed_cfg in FEEDS:
        url         = feed_cfg["url"]
        source      = feed_cfg.get("source", "Unknown")
        region      = feed_cfg.get("region", "Global")
        default_cat = feed_cfg.get("category", None)

        print(f"  → Fetching {source} …", end=" ", flush=True)
        try:
            feed    = feedparser.parse(url)
            entries = feed.entries[:5]  # Top 5 per feed
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

            print(f"    ✍  {title[:65]}…")
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

            # Respect Groq free-tier rate limit (30 req/min → 1 req/2s is safe)
            time.sleep(2)

        if len(articles) >= MAX_ARTICLES * 2:
            break

    # Trim to max
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

    print(f"\n✅ Done! Wrote {len(articles)} articles → {out_path}")
    return out_path

# ── GITHUB PUSH ───────────────────────────────────────────────────────────────

def push_to_github():
    """Commits and pushes news.json (and optionally index.html) to GitHub."""
    print("\n--- Syncing to GitHub ---")
    repo = Path(REPO_PATH)
    if not repo.exists():
        print(f"❌ Repo path not found: {REPO_PATH}")
        print("   Update REPO_PATH at the top of agent.py")
        return

    try:
        os.chdir(repo)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Stage only the data file (never force-push — it rewrites history)
        subprocess.run(["git", "add", "news.json"], check=True)

        # Commit (skip if nothing changed)
        result = subprocess.run(
            ["git", "commit", "-m", f"News update {timestamp}"],
            capture_output=True, text=True
        )
        if "nothing to commit" in result.stdout:
            print("ℹ️  No changes to commit.")
            return

        # Normal push — no --force
        push = subprocess.run(
            ["git", "push", "origin", "main"],
            capture_output=True, text=True
        )
        if push.returncode == 0:
            print("🚀 GitHub updated successfully!")
        else:
            print(f"❌ Push failed:\n{push.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

# ── ENTRY POINT ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ANN Feed AI News Agent")
    parser.add_argument("--schedule", action="store_true",
                        help=f"Run continuously every {FETCH_EVERY_MINUTES} minutes")
    parser.add_argument("--push", action="store_true",
                        help="Commit & push news.json to GitHub after each run")
    args = parser.parse_args()

    # Warn if no API key
    if not GROQ_API_KEY:
        print("⚠  GROQ_API_KEY not set — briefs will use raw RSS descriptions.")
        print("   Get a free key at https://console.groq.com and set it as:")
        print("   export GROQ_API_KEY=gsk_your_key_here\n")
    else:
        print("✅ Groq API key detected")

    def run_once():
        scrape_and_generate()
        if args.push:
            push_to_github()

    if args.schedule:
        print(f"📅 Scheduled mode: running every {FETCH_EVERY_MINUTES} minutes. Ctrl+C to stop.\n")
        try:
            import schedule
            schedule.every(FETCH_EVERY_MINUTES).minutes.do(run_once)
            run_once()  # Run immediately first
            while True:
                schedule.run_pending()
                time.sleep(30)
        except ImportError:
            print("Install schedule: pip install schedule")
        except KeyboardInterrupt:
            print("\nAgent stopped.")
    else:
        run_once()

if __name__ == "__main__":
    main()
