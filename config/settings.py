"""
Trade Genie - Central Configuration
Loads from .env file and provides typed settings to all modules.
"""

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load .env from project root
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings:
    # --- Paths ---
    ROOT_DIR: Path = ROOT_DIR
    DATA_DIR: Path = ROOT_DIR / "data"
    REPORTS_DIR: Path = ROOT_DIR / "data" / "reports"
    CACHE_DIR: Path = ROOT_DIR / "data" / "cache"
    DB_PATH: Path = ROOT_DIR / "data" / "tradegenie.db"
    TEMPLATES_DIR: Path = ROOT_DIR / "templates"

    # --- LLM ---
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_GEMINI_API_KEY: Optional[str] = os.getenv("GOOGLE_GEMINI_API_KEY")

    # --- Data Sources ---
    NEWS_API_KEY: Optional[str] = os.getenv("NEWS_API_KEY")
    REDDIT_CLIENT_ID: Optional[str] = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: Optional[str] = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT: str = os.getenv("REDDIT_USER_AGENT", "TradeGenie/1.0")
    TWITTER_BEARER_TOKEN: Optional[str] = os.getenv("TWITTER_BEARER_TOKEN")
    ALPHA_VANTAGE_API_KEY: Optional[str] = os.getenv("ALPHA_VANTAGE_API_KEY")

    # --- Email ---
    GMAIL_ADDRESS: Optional[str] = os.getenv("GMAIL_ADDRESS")
    GMAIL_APP_PASSWORD: Optional[str] = os.getenv("GMAIL_APP_PASSWORD")
    EMAIL_RECIPIENTS: List[str] = [
        e.strip()
        for e in os.getenv("EMAIL_RECIPIENTS", "").split(",")
        if e.strip()
    ]

    # --- Scheduling ---
    SCHEDULE_DAILY: str = os.getenv("SCHEDULE_DAILY", "0 7 * * *")
    SCHEDULE_WEEKLY: str = os.getenv("SCHEDULE_WEEKLY", "0 7 * * 1")
    URGENCY_SCORE_THRESHOLD: float = float(
        os.getenv("URGENCY_SCORE_THRESHOLD", "8.5")
    )

    # --- Report ---
    TOP_PICKS_COUNT: int = int(os.getenv("TOP_PICKS_COUNT", "10"))

    # --- Web Dashboard ---
    WEB_SECRET_KEY: str = os.getenv(
        "WEB_SECRET_KEY", "change-me-to-random-secret"
    )
    WEB_DASHBOARD_PASSWORD: Optional[str] = os.getenv("WEB_DASHBOARD_PASSWORD")
    WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8080"))

    # --- RSS Feed Sources ---
    RSS_FEEDS: List[dict] = [
        {"name": "Reuters", "url": "https://feeds.reuters.com/reuters/topNews"},
        {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/rss.xml"},
        {"name": "BBC Business", "url": "https://feeds.bbci.co.uk/news/business/rss.xml"},
        {"name": "Financial Times", "url": "https://www.ft.com/rss/home"},
        {"name": "The Guardian Business", "url": "https://www.theguardian.com/uk/business/rss"},
        {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
        {"name": "Associated Press", "url": "https://rsshub.app/ap/topics/apf-topnews"},
        {"name": "CNBC Top News", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
        {"name": "MarketWatch", "url": "https://feeds.marketwatch.com/marketwatch/topstories/"},
        {"name": "Seeking Alpha", "url": "https://seekingalpha.com/feed.xml"},
    ]

    # --- Reddit Subreddits to Monitor ---
    REDDIT_SUBREDDITS: List[str] = [
        "worldnews",
        "geopolitics",
        "wallstreetbets",
        "investing",
        "stocks",
        "UKInvesting",
        "SecurityAnalysis",
        "Economics",
        "politics",
        "europe",
        "MiddleEast",
    ]

    # --- UK-Focused ETF Universe ---
    # ETFs available on major UK platforms (HL, IG, AJ Bell etc.)
    UK_ETF_UNIVERSE: List[dict] = [
        # Energy
        {"ticker": "IEOG.L",  "name": "iShares Oil & Gas Exploration ETF",      "sector": "Energy"},
        {"ticker": "XOIL.L",  "name": "Xtrackers MSCI World Energy ETF",         "sector": "Energy"},
        {"ticker": "OGIG.L",  "name": "iShares Global Oil & Gas ETF",            "sector": "Energy"},
        # Defence
        {"ticker": "DFEN.L",  "name": "iShares Global Aerospace & Defence ETF",  "sector": "Defence"},
        {"ticker": "NATO.L",  "name": "HANetf Future of Defence ETF",            "sector": "Defence"},
        # Tech / AI
        {"ticker": "IITU.L",  "name": "iShares S&P 500 IT Sector ETF",           "sector": "Technology"},
        {"ticker": "QDVE.L",  "name": "iShares S&P 500 Digital Security ETF",    "sector": "Technology"},
        {"ticker": "ROBO.L",  "name": "ROBO Global Robotics & Automation ETF",   "sector": "AI/Robotics"},
        # Gold / Commodities
        {"ticker": "SGLN.L",  "name": "iShares Physical Gold ETC",               "sector": "Gold"},
        {"ticker": "CMOD.L",  "name": "iShares Diversified Commodity Swap ETF",  "sector": "Commodities"},
        {"ticker": "SUCO.L",  "name": "iShares S&P Commodity Producers ETF",     "sector": "Commodities"},
        # Emerging Markets / Geopolitical
        {"ticker": "IEEM.L",  "name": "iShares Core MSCI EM IMI ETF",            "sector": "Emerging Markets"},
        {"ticker": "CEMS.L",  "name": "iShares MSCI EM ESG Screened ETF",        "sector": "Emerging Markets"},
        # Healthcare / Bio
        {"ticker": "IUHC.L",  "name": "iShares S&P 500 Health Care ETF",         "sector": "Healthcare"},
        {"ticker": "BIOT.L",  "name": "iShares Nasdaq Biotechnology ETF",        "sector": "Biotech"},
        # Financials
        {"ticker": "IUFS.L",  "name": "iShares S&P 500 Financials ETF",          "sector": "Financials"},
        # Broad
        {"ticker": "ISF.L",   "name": "iShares Core FTSE 100 ETF",              "sector": "UK Broad"},
        {"ticker": "VWRL.L",  "name": "Vanguard FTSE All-World ETF",             "sector": "Global Broad"},
        # Safe Haven
        {"ticker": "IGLT.L",  "name": "iShares Core UK Gilts ETF",              "sector": "Bonds/Safe Haven"},
        {"ticker": "IBTM.L",  "name": "iShares $ Treasury Bond 7-10yr ETF",     "sector": "Bonds/Safe Haven"},
    ]

    def available_llms(self) -> List[str]:
        """Returns list of which LLM providers have keys configured."""
        providers = []
        if self.OPENAI_API_KEY and not self.OPENAI_API_KEY.startswith("your_"):
            providers.append("openai")
        if self.ANTHROPIC_API_KEY and not self.ANTHROPIC_API_KEY.startswith("your_"):
            providers.append("anthropic")
        if self.GOOGLE_GEMINI_API_KEY and not self.GOOGLE_GEMINI_API_KEY.startswith("your_"):
            providers.append("gemini")
        return providers

    def validate(self) -> List[str]:
        """Returns list of warnings about missing config."""
        warnings = []
        if not self.available_llms():
            warnings.append("No LLM API keys configured — analysis will not work")
        if not self.NEWS_API_KEY or self.NEWS_API_KEY.startswith("your_"):
            warnings.append("NEWS_API_KEY not set — NewsAPI source disabled")
        if not self.REDDIT_CLIENT_ID or self.REDDIT_CLIENT_ID.startswith("your_"):
            warnings.append("Reddit credentials not set — Reddit source disabled")
        if not self.ALPHA_VANTAGE_API_KEY or self.ALPHA_VANTAGE_API_KEY.startswith("your_"):
            warnings.append("ALPHA_VANTAGE_API_KEY not set — market data limited")
        if not self.GMAIL_ADDRESS or self.GMAIL_ADDRESS.startswith("your_"):
            warnings.append("Gmail not configured — email delivery disabled")
        return warnings

    def ensure_dirs(self):
        """Create data directories if they don't exist."""
        for d in [self.DATA_DIR, self.REPORTS_DIR, self.CACHE_DIR]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
