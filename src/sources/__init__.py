"""
Trade Genie - Data Sources Package
"""
from src.sources.newsapi_source import fetch_newsapi_events
from src.sources.reddit_source import fetch_reddit_events
from src.sources.gdelt_source import fetch_gdelt_events
from src.sources.rss_source import fetch_rss_events
from src.sources.twitter_source import fetch_twitter_events
from src.sources.alphavantage_source import fetch_market_news_events

__all__ = [
    "fetch_newsapi_events",
    "fetch_reddit_events",
    "fetch_gdelt_events",
    "fetch_rss_events",
    "fetch_twitter_events",
    "fetch_market_news_events",
]
