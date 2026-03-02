"""
Trade Genie - Twitter/X Source
Searches for market-relevant tweets via Twitter API v2.
Requires Basic tier or higher (~$100/month).
If no key is provided, this source is silently skipped.
"""

import logging
from datetime import datetime, timedelta
from typing import List

import requests

from config.settings import settings
from src.models import RawEvent

logger = logging.getLogger(__name__)

TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"

# High-signal accounts to specifically monitor (politicians, analysts, central banks)
POWER_ACCOUNTS = [
    "FedReserve", "ecb", "bankofengland",
    "realDonaldTrump", "POTUS", "StateDept",
    "ZeroHedge", "RaoulGMI", "LynAldenContact",
    "PeterSchiff", "GeorgeGammon",
]

SEARCH_QUERIES = [
    "geopolitical conflict war -is:retweet lang:en",
    "oil sanctions OPEC -is:retweet lang:en",
    "Federal Reserve interest rate -is:retweet lang:en",
    "market crash recession -is:retweet lang:en",
    "China Taiwan military -is:retweet lang:en",
    "nuclear threat missile -is:retweet lang:en",
    "BREAKING news markets -is:retweet lang:en",
    "inflation stagflation deflation -is:retweet lang:en",
]


def fetch_twitter_events(lookback_hours: int = 24) -> List[RawEvent]:
    """Fetch relevant tweets via Twitter API v2."""
    if (
        not settings.TWITTER_BEARER_TOKEN
        or settings.TWITTER_BEARER_TOKEN.startswith("your_")
    ):
        logger.info("Twitter bearer token not configured, skipping.")
        return []

    headers = {"Authorization": f"Bearer {settings.TWITTER_BEARER_TOKEN}"}
    start_time = (datetime.utcnow() - timedelta(hours=lookback_hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    events: List[RawEvent] = []
    seen_ids = set()

    for query in SEARCH_QUERIES:
        try:
            resp = requests.get(
                TWITTER_SEARCH_URL,
                headers=headers,
                params={
                    "query": query,
                    "start_time": start_time,
                    "max_results": 20,
                    "tweet.fields": "created_at,public_metrics,author_id",
                    "expansions": "author_id",
                    "user.fields": "username,name,verified",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            # Build user lookup
            users = {
                u["id"]: u
                for u in data.get("includes", {}).get("users", [])
            }

            for tweet in data.get("data", []):
                tweet_id = tweet.get("id", "")
                if tweet_id in seen_ids:
                    continue
                seen_ids.add(tweet_id)

                # Filter low-engagement tweets
                metrics = tweet.get("public_metrics", {})
                if (
                    metrics.get("retweet_count", 0) < 5
                    and metrics.get("like_count", 0) < 20
                ):
                    continue

                author = users.get(tweet.get("author_id", ""), {})
                author_name = author.get("name", "Twitter User")
                username = author.get("username", "unknown")

                created_str = tweet.get("created_at", "")
                try:
                    published_dt = datetime.strptime(
                        created_str, "%Y-%m-%dT%H:%M:%S.%fZ"
                    )
                except Exception:
                    try:
                        published_dt = datetime.strptime(
                            created_str, "%Y-%m-%dT%H:%M:%SZ"
                        )
                    except Exception:
                        published_dt = datetime.utcnow()

                events.append(
                    RawEvent(
                        source="twitter",
                        source_name=f"@{username}",
                        title=f"@{username}: {tweet['text'][:100]}...",
                        content=tweet.get("text", ""),
                        url=f"https://twitter.com/{username}/status/{tweet_id}",
                        published_at=published_dt,
                        raw={**tweet, "author": author},
                    )
                )
        except requests.RequestException as e:
            logger.error(f"Twitter error for '{query}': {e}")
        except Exception as e:
            logger.error(f"Twitter parse error: {e}")

    logger.info(f"Twitter: fetched {len(events)} tweets")
    return events
