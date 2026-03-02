"""
Trade Genie - NewsAPI Source
Fetches top headlines and relevant geopolitical/financial news.
"""

import logging
from datetime import datetime, timedelta
from typing import List

import requests

from config.settings import settings
from src.models import RawEvent

logger = logging.getLogger(__name__)

# Queries that capture events likely to move markets
NEWS_QUERIES = [
    "geopolitical conflict war sanctions",
    "oil gas energy supply disruption",
    "central bank interest rate inflation",
    "trade war tariffs supply chain",
    "elections government policy",
    "stock market crash recession",
    "technology AI semiconductor chip",
    "China Taiwan US relations",
    "Middle East Iran Israel conflict",
    "Russia Ukraine war NATO",
    "OPEC oil production",
    "pharmaceutical drug FDA approval",
    "climate policy ESG regulations",
    "bank financial crisis",
    "merger acquisition IPO",
]


def fetch_newsapi_events(lookback_hours: int = 48) -> List[RawEvent]:
    """Fetch recent events from NewsAPI."""
    if not settings.NEWS_API_KEY or settings.NEWS_API_KEY.startswith("your_"):
        logger.warning("NewsAPI key not configured, skipping.")
        return []

    events: List[RawEvent] = []
    seen_urls = set()
    from_date = (datetime.utcnow() - timedelta(hours=lookback_hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    for query in NEWS_QUERIES:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "from": from_date,
                    "sortBy": "relevancy",
                    "language": "en",
                    "pageSize": 10,
                    "apiKey": settings.NEWS_API_KEY,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            for article in data.get("articles", []):
                url = article.get("url", "")
                if url in seen_urls or not article.get("title"):
                    continue
                seen_urls.add(url)

                published_str = article.get("publishedAt", "")
                try:
                    published_dt = datetime.strptime(
                        published_str, "%Y-%m-%dT%H:%M:%SZ"
                    )
                except Exception:
                    published_dt = datetime.utcnow()

                content = (article.get("description") or "") + " " + (
                    article.get("content") or ""
                )

                events.append(
                    RawEvent(
                        source="newsapi",
                        source_name=article.get("source", {}).get("name", "NewsAPI"),
                        title=article.get("title", ""),
                        content=content.strip(),
                        url=url,
                        published_at=published_dt,
                        raw=article,
                    )
                )
        except requests.RequestException as e:
            logger.error(f"NewsAPI error for query '{query}': {e}")

    logger.info(f"NewsAPI: fetched {len(events)} articles")
    return events
