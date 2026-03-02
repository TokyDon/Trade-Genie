"""
Trade Genie - RSS Feed Source
Parses RSS/Atom feeds from major news outlets.
No API key required — always available.
"""

import logging
from datetime import datetime
from typing import List

import feedparser
import requests

from config.settings import settings
from src.models import RawEvent

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; TradeGenie/1.0; +https://github.com/tradegenie)"
    )
}


def _parse_date(entry) -> datetime:
    """Extract published date from a feedparser entry."""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6])
            except Exception:
                pass
    return datetime.utcnow()


def fetch_rss_events(lookback_hours: int = 48) -> List[RawEvent]:
    """Parse all configured RSS feeds and return events."""
    from datetime import timedelta

    events: List[RawEvent] = []
    seen_urls = set()
    cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)

    for feed_config in settings.RSS_FEEDS:
        feed_name = feed_config["name"]
        feed_url = feed_config["url"]

        try:
            # feedparser handles the HTTP request itself but we set a timeout via requests
            resp = requests.get(feed_url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:
            logger.warning(f"RSS fetch failed for {feed_name}: {e}")
            try:
                feed = feedparser.parse(feed_url)
            except Exception as e2:
                logger.error(f"RSS fallback failed for {feed_name}: {e2}")
                continue

        for entry in feed.entries:
            url = getattr(entry, "link", "")
            title = getattr(entry, "title", "")

            if not title or url in seen_urls:
                continue

            published_dt = _parse_date(entry)
            if published_dt < cutoff:
                continue

            seen_urls.add(url)

            summary = getattr(entry, "summary", "") or ""
            # Strip basic HTML tags
            import re
            summary = re.sub(r"<[^>]+>", "", summary)[:1500]

            events.append(
                RawEvent(
                    source="rss",
                    source_name=feed_name,
                    title=title,
                    content=summary.strip(),
                    url=url,
                    published_at=published_dt,
                    raw={"feed": feed_name},
                )
            )

    logger.info(f"RSS: fetched {len(events)} articles from {len(settings.RSS_FEEDS)} feeds")
    return events
