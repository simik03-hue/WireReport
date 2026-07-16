#!/usr/bin/env python3
"""
fetch_feeds.py

Pulls headlines from the RSS sources listed in config/feeds.json, removes
near-duplicate stories (the same story covered by five outlets), sorts by
recency, and writes two JSON files your website reads:

  data/wire_data.json  -> current homepage content (lead, tier2, columns)
  data/archive.json    -> rolling daily snapshot for the "Previously" section

Run manually:
    python3 scripts/fetch_feeds.py

Run on a schedule (recommended: every 10-15 minutes) via cron - see README.md.

Dependencies:
    pip install feedparser --break-system-packages
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import feedparser
except ImportError:
    sys.exit(
        "Missing dependency 'feedparser'.\n"
        "Install it with:  pip install feedparser --break-system-packages\n"
        "(or just: pip install feedparser, depending on your environment)"
    )

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "feeds.json"
DATA_DIR = BASE_DIR / "data"
WIRE_DATA_PATH = DATA_DIR / "wire_data.json"
ARCHIVE_PATH = DATA_DIR / "archive.json"

MAX_ARCHIVE_DAYS = 14           # how many days of history to keep
ITEMS_PER_COLUMN = 6            # headlines per column
TIER2_COUNT = 3                 # secondary headlines under the lead
DEDUPE_SIMILARITY_THRESHOLD = 0.5   # 0-1, higher = stricter matching


def load_feed_config():
    if not CONFIG_PATH.exists():
        sys.exit(f"Feed config not found at {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_title(title: str) -> set:
    """Lowercase, strip punctuation, return a set of significant words."""
    words = re.findall(r"[a-z0-9]+", title.lower())
    stopwords = {"the", "a", "an", "to", "of", "in", "on", "for", "and", "is",
                 "at", "as", "by", "with", "from", "after", "over", "amid"}
    return {w for w in words if w not in stopwords and len(w) > 2}


def similarity(a: set, b: set) -> float:
    """Jaccard similarity between two word sets."""
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def parse_entry_time(entry):
    """Best-effort parse of an entry's published time, fallback to now."""
    for key in ("published_parsed", "updated_parsed"):
        val = getattr(entry, key, None)
        if val:
            return datetime(*val[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def fetch_all_items(sources):
    """Fetch every configured feed and return a flat list of normalized items."""
    items = []
    for src in sources:
        print(f"Fetching: {src['name']} ({src['url']})")
        try:
            parsed = feedparser.parse(src["url"])
        except Exception as e:
            print(f"  ! failed to fetch {src['name']}: {e}")
            continue

        if parsed.bozo and not parsed.entries:
            print(f"  ! feed for {src['name']} did not parse cleanly, skipping")
            continue

        for entry in parsed.entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if not title or not link:
                continue
            items.append({
                "text": title,
                "url": link,
                "source": src["name"],
                "lean": src.get("lean", "unrated"),
                "topic": src.get("topic", "top"),
                "sourceNote": src.get("note", ""),
                "time": parse_entry_time(entry).isoformat(),
                "_words": normalize_title(title),
            })
    return items


def dedupe_items(items):
    """
    Drop near-duplicate stories. When multiple outlets cover the same story,
    keep the earliest one seen (first in the source list = your preferred
    priority order in feeds.json).
    """
    kept = []
    for item in items:
        is_dupe = False
        for existing in kept:
            if similarity(item["_words"], existing["_words"]) >= DEDUPE_SIMILARITY_THRESHOLD:
                is_dupe = True
                break
        if not is_dupe:
            kept.append(item)
    return kept


def build_site_data(items):
    """Shape the deduped, sorted items into the structure index.html expects."""
    # newest first
    items.sort(key=lambda i: i["time"], reverse=True)

    def clean(i):
        return {k: v for k, v in i.items() if not k.startswith("_")}

    if not items:
        return None

    lead_raw = items[0]
    lead = clean(lead_raw)
    lead["kicker"] = "DEVELOPING"
    lead["deck"] = ""  # fill in manually, or extend with a summary field from the feed

    remaining = items[1:]
    tier2 = [clean(i) for i in remaining[:TIER2_COUNT]]
    remaining = remaining[TIER2_COUNT:]

    # bucket the rest by topic, then round-robin fill three columns
    buckets = {"top": [], "politics": [], "world": [], "business": []}
    for i in remaining:
        buckets.setdefault(i["topic"], buckets["top"]).append(i)

    columns = [[], [], []]
    col_index = 0
    for topic in ("top", "politics", "world", "business"):
        for i in buckets.get(topic, []):
            if all(len(c) >= ITEMS_PER_COLUMN for c in columns):
                break
            # place in the shortest column
            target = min(range(3), key=lambda idx: len(columns[idx]))
            columns[target].append(clean(i))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lead": lead,
        "tier2": tier2,
        "col1": columns[0],
        "col2": columns[1],
        "col3": columns[2],
    }


def update_archive(site_data):
    """Append today's top headlines to the rolling archive, capped at MAX_ARCHIVE_DAYS."""
    archive = []
    if ARCHIVE_PATH.exists():
        with open(ARCHIVE_PATH, "r", encoding="utf-8") as f:
            archive = json.load(f)

    today_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    headlines_today = [site_data["lead"]["text"]] + [t["text"] for t in site_data["tier2"]]

    if archive and archive[0]["date"] == today_str:
        # merge into today's entry instead of duplicating
        existing = set(archive[0]["headlines"])
        for h in headlines_today:
            if h not in existing:
                archive[0]["headlines"].append(h)
    else:
        archive.insert(0, {"date": today_str, "headlines": headlines_today})

    archive = archive[:MAX_ARCHIVE_DAYS]

    with open(ARCHIVE_PATH, "w", encoding="utf-8") as f:
        json.dump(archive, f, indent=2, ensure_ascii=False)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sources = load_feed_config()

    raw_items = fetch_all_items(sources)
    print(f"\nFetched {len(raw_items)} raw items from {len(sources)} sources.")

    deduped = dedupe_items(raw_items)
    print(f"Kept {len(deduped)} items after de-duplication.")

    site_data = build_site_data(deduped)
    if site_data is None:
        print("No items fetched - check your feed URLs in config/feeds.json. "
              "Leaving existing data files untouched.")
        return

    with open(WIRE_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(site_data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {WIRE_DATA_PATH}")

    update_archive(site_data)
    print(f"Updated {ARCHIVE_PATH}")


if __name__ == "__main__":
    main()
