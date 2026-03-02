"""
Trade Genie - Data Collector
Runs all data sources concurrently and returns a deduplicated,
ranked list of RawEvents.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List

from src.models import RawEvent
from src.sources import (
    fetch_gdelt_events,
    fetch_market_news_events,
    fetch_newsapi_events,
    fetch_reddit_events,
    fetch_rss_events,
    fetch_twitter_events,
)

logger = logging.getLogger(__name__)


def collect_all_events(lookback_hours: int = 48) -> List[RawEvent]:
    """
    Runs all data sources concurrently and returns a merged,
    deduplicated list of events sorted by recency.
    """
    logger.info(f"Starting data collection (lookback={lookback_hours}h)...")

    tasks = {
        "newsapi": lambda: fetch_newsapi_events(lookback_hours),
        "reddit": lambda: fetch_reddit_events(lookback_hours),
        "gdelt": lambda: fetch_gdelt_events(lookback_hours),
        "rss": lambda: fetch_rss_events(lookback_hours),
        "twitter": lambda: fetch_twitter_events(min(lookback_hours, 24)),
        "alphavantage": lambda: fetch_market_news_events(),
    }

    all_events: List[RawEvent] = []
    sources_used = []

    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_name = {
            executor.submit(fn): name for name, fn in tasks.items()
        }
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                events = future.result()
                if events:
                    all_events.extend(events)
                    sources_used.append(name)
                    logger.info(f"  {name}: {len(events)} events")
                else:
                    logger.info(f"  {name}: 0 events (skipped or no data)")
            except Exception as e:
                logger.error(f"  {name} failed: {e}")

    # Deduplicate by URL
    seen_urls = set()
    unique_events = []
    for event in all_events:
        if event.url not in seen_urls:
            seen_urls.add(event.url)
            unique_events.append(event)

    # Sort by recency
    unique_events.sort(key=lambda e: e.published_at, reverse=True)

    logger.info(
        f"Collection complete: {len(unique_events)} unique events "
        f"from {len(sources_used)} sources: {', '.join(sources_used)}"
    )
    return unique_events


def summarize_events_for_llm(events: List[RawEvent], max_events: int = 60) -> str:
    """
    Format events into a compact text block suitable for LLM context.
    Keeps the most recent events and limits total token size.
    """
    # Take a cross-section: most recent events, but diversity across sources
    sources_seen = {}
    selected = []
    for event in events:
        count = sources_seen.get(event.source, 0)
        if count < 15:  # Max 15 per source
            selected.append(event)
            sources_seen[event.source] = count + 1
        if len(selected) >= max_events:
            break

    lines = [
        f"=== WORLD EVENTS DIGEST ({len(selected)} items, "
        f"as of {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}) ===\n"
    ]

    for i, event in enumerate(selected, 1):
        date_str = event.published_at.strftime("%Y-%m-%d %H:%M")
        lines.append(
            f"[{i}] [{event.source_name}] {date_str}\n"
            f"TITLE: {event.title}\n"
            f"CONTENT: {(event.content or '')[:500]}\n"
            f"URL: {event.url}\n"
        )

    return "\n".join(lines)
