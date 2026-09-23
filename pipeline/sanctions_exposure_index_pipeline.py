# -*- coding: utf-8 -*-
"""Published methodology: deduplicated topical Google News RSS sample.

This pipeline does not claim to measure risk, exposure, entity relations, or
forecast outcomes. Article volume is a property of the news feed and query.
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

import yaml

sys.path.insert(0, os.path.dirname(__file__))
from data_fetcher import fetch_google_news_rss, safe_fetch

SNAPSHOT_SIZE = 50
EVENT_LIMIT = 15
MAX_RETAIN_HOURS = 24

def load_config():
    with open(os.path.join(os.path.dirname(__file__), "config.yaml"), encoding="utf-8") as handle:
        return yaml.safe_load(handle)

def load_previous():
    try:
        with open("data/output.json", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}

def main():
    config = load_config()
    previous = load_previous()
    query = config["news_query"]
    fresh = safe_fetch(fetch_google_news_rss, query, SNAPSHOT_SIZE) or []
    articles = [dict(article) for article in fresh[:SNAPSHOT_SIZE]]
    mode = "live" if articles else "unavailable"
    notes = []
    if not articles:
        try:
            previous_at = datetime.fromisoformat(previous["meta"]["generated"].replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - previous_at
            retained = previous.get("live_data", {}).get("news_articles", [])
            if timedelta(0) <= age <= timedelta(hours=MAX_RETAIN_HOURS) and retained:
                articles = [dict(article) for article in retained[:SNAPSHOT_SIZE]]
                mode = "partial"
                notes.append("News fetch failed; showing a retained sample less than 24 hours old.")
        except (KeyError, TypeError, ValueError):
            pass
    for article in articles:
        article.pop("tone", None)
    domains = {article.get("domain") for article in articles if article.get("domain")}
    output = {
        "meta": {
            "project": config["project"]["id"],
            "generated": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "sources": ["news_articles"] if articles else [],
            "source_notes": notes,
            "version": "2.0.0",
            "methodology": {
                "scope": "topical news sample",
                "source": "Google News RSS",
                "query": query,
                "sample_limit": SNAPSHOT_SIZE,
                "limit": "News coverage is not an official sanctions-list check, entity match, ownership graph, or exposure score.",
            },
        },
        "stats": [
            {"label": "Articles sampled", "value": str(len(articles))},
            {"label": "Distinct news domains", "value": str(len(domains))},
        ],
        "live_data": {"news_articles": articles} if articles else {},
        "events": articles[:EVENT_LIMIT],
        "llm_summary": "",
    }
    os.makedirs("data", exist_ok=True)
    temporary = "data/output.json.tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, "data/output.json")
    print(f"Published {len(articles)} sampled headlines; mode={mode}; domains={len(domains)}")

if __name__ == "__main__":
    main()
