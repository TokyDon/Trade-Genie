"""
Trade Genie - Alpha Vantage Source
Fetches market news sentiment and price data for context.
Alpha Vantage free tier: 25 requests/day, 5 requests/minute.
"""

import logging
import time
from datetime import datetime
from typing import List, Optional

import requests

from config.settings import settings
from src.models import RawEvent

logger = logging.getLogger(__name__)
AV_BASE = "https://www.alphavantage.co/query"


def _av_request(params: dict, delay: float = 13.0) -> Optional[dict]:
    """Make a rate-limited Alpha Vantage request."""
    if not settings.ALPHA_VANTAGE_API_KEY or settings.ALPHA_VANTAGE_API_KEY.startswith("your_"):
        return None
    params["apikey"] = settings.ALPHA_VANTAGE_API_KEY
    try:
        resp = requests.get(AV_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # Rate limit: free tier allows 5 req/min
        time.sleep(delay)
        return data
    except Exception as e:
        logger.error(f"Alpha Vantage request failed: {e}")
        return None


def fetch_market_news_events() -> List[RawEvent]:
    """Fetch global market news sentiment from Alpha Vantage."""
    if not settings.ALPHA_VANTAGE_API_KEY or settings.ALPHA_VANTAGE_API_KEY.startswith("your_"):
        logger.warning("Alpha Vantage key not configured, skipping news sentiment.")
        return []

    events: List[RawEvent] = []

    # Topics of interest for market-moving news
    topics = [
        "geopolitics",
        "energy_transportation",
        "mergers_and_acquisitions",
        "financial_markets",
        "technology",
        "manufacturing",
    ]

    for topic in topics[:3]:  # Conserve API calls on free tier
        data = _av_request({
            "function": "NEWS_SENTIMENT",
            "topics": topic,
            "limit": 20,
            "sort": "RELEVANCE",
        })
        if not data:
            break

        for item in data.get("feed", []):
            title = item.get("title", "")
            url = item.get("url", "")
            if not title:
                continue

            # Parse date: "20240102T150000"
            time_str = item.get("time_published", "")
            try:
                published_dt = datetime.strptime(time_str, "%Y%m%dT%H%M%S")
            except Exception:
                published_dt = datetime.utcnow()

            # Alpha Vantage provides sentiment scores
            overall_sentiment = item.get("overall_sentiment_label", "")
            overall_score = float(item.get("overall_sentiment_score", 0))

            content = item.get("summary", "")

            # Add ticker-level sentiment if present
            ticker_sentiments = item.get("ticker_sentiment", [])
            if ticker_sentiments:
                ticker_lines = [
                    f"{t['ticker']}: {t.get('ticker_sentiment_label','?')} "
                    f"(score: {t.get('ticker_sentiment_score','?')})"
                    for t in ticker_sentiments[:5]
                ]
                content += "\n\nTicker sentiment:\n" + "\n".join(ticker_lines)

            events.append(
                RawEvent(
                    source="alphavantage",
                    source_name=item.get("source", "Alpha Vantage"),
                    title=title,
                    content=content,
                    url=url,
                    published_at=published_dt,
                    sentiment_hint=overall_sentiment.lower() if overall_sentiment else None,
                    tags=[topic] + [t["ticker"] for t in ticker_sentiments[:3]],
                    raw=item,
                )
            )

    logger.info(f"Alpha Vantage: fetched {len(events)} news items")
    return events


def get_stock_quote(ticker: str) -> Optional[dict]:
    """Fetch current price quote for a ticker."""
    data = _av_request({"function": "GLOBAL_QUOTE", "symbol": ticker}, delay=13.0)
    if not data:
        return None
    quote = data.get("Global Quote", {})
    if not quote:
        return None
    return {
        "ticker": ticker,
        "price": float(quote.get("05. price", 0)),
        "change_pct": quote.get("10. change percent", "0%"),
        "volume": quote.get("06. volume", ""),
        "previous_close": float(quote.get("08. previous close", 0)),
    }
