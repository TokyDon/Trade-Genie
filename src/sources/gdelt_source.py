"""
Trade Genie - GDELT Source
Queries the GDELT 2.0 GKG (Global Knowledge Graph) for geopolitical events.
GDELT is a real-time open dataset of global events — no API key required.
"""

import logging
from datetime import datetime, timedelta
from typing import List

import requests

from src.models import RawEvent

logger = logging.getLogger(__name__)

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"

# Themes that indicate likely market-moving events
GDELT_THEMES = [
    "TAX_FNCACT_OIL",
    "ECON_OILPRICE",
    "MILITARY_CONFLICT",
    "WB_635_CONFLICT_MILITARY",
    "ECON_SANCTIONS",
    "USPEC_POLITICS_GENERAL1",
    "SECURITY_SERVICES",
    "TAX_FNCACT_ENERGY",
    "ENV_CLIMATECHANGE",
    "ECON_TRADE",
    "ECON_INFLATION",
]

GDELT_QUERIES = [
    "war military attack conflict sanctions",
    "oil gas energy supply disruption OPEC",
    "tariff trade war sanctions embargo",
    "election government regime change",
    "central bank rate hike monetary policy",
    "pandemic disease outbreak health emergency",
    "nuclear weapons missile threat",
    "financial crisis bank collapse bailout",
]


def fetch_gdelt_events(lookback_hours: int = 48) -> List[RawEvent]:
    """Fetch geopolitical event signals from GDELT."""
    events: List[RawEvent] = []
    seen_urls = set()

    # GDELT time window
    start_dt = datetime.utcnow() - timedelta(hours=lookback_hours)
    start_str = start_dt.strftime("%Y%m%d%H%M%S")

    for query in GDELT_QUERIES[:5]:  # Limit to avoid rate limiting
        try:
            resp = requests.get(
                GDELT_DOC_API,
                params={
                    "query": query,
                    "mode": "artlist",
                    "maxrecords": 25,
                    "startdatetime": start_str,
                    "format": "json",
                    "sort": "datedesc",
                    "sourcelang": "english",
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for article in data.get("articles", []):
                url = article.get("url", "")
                if url in seen_urls or not article.get("title"):
                    continue
                seen_urls.add(url)

                date_str = article.get("seendate", "")
                try:
                    published_dt = datetime.strptime(date_str, "%Y%m%dT%H%M%SZ")
                except Exception:
                    published_dt = datetime.utcnow()

                # GDELT provides tones: positive/negative sentiment
                tone = article.get("socialimage", "")
                events.append(
                    RawEvent(
                        source="gdelt",
                        source_name=article.get("domain", "GDELT"),
                        title=article.get("title", ""),
                        content=article.get("title", ""),  # GDELT doesn't provide body
                        url=url,
                        published_at=published_dt,
                        raw=article,
                    )
                )
        except requests.RequestException as e:
            logger.error(f"GDELT error for '{query}': {e}")
        except Exception as e:
            logger.error(f"GDELT parse error: {e}")

    logger.info(f"GDELT: fetched {len(events)} events")
    return events
