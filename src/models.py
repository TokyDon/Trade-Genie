"""
Trade Genie - Data Models
Shared dataclasses used across the entire pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class RawEvent:
    """A single piece of raw information from any data source."""
    source: str               # e.g. "newsapi", "reddit", "rss", "gdelt"
    source_name: str          # Human-readable source name, e.g. "BBC News"
    title: str
    content: str
    url: str
    published_at: datetime
    sentiment_hint: Optional[str] = None  # "positive","negative","neutral" if pre-scored
    tags: List[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)  # original payload


@dataclass
class AnalyzedEvent:
    """An event after LLM analysis, per model."""
    model: str                # "openai", "anthropic", "gemini"
    event_summary: str
    geopolitical_context: str
    predicted_impact: str
    affected_sectors: List[str]
    time_horizon: str         # "immediate", "1-2 weeks", "1-3 months"
    confidence_score: float   # 0-10
    urgency_score: float      # 0-10 (triggers immediate alert if above threshold)
    sentiment: str            # "bullish", "bearish", "neutral"
    reasoning: str
    raw_response: str


@dataclass
class StockPick:
    """A single stock/ETF recommendation."""
    ticker: str
    name: str
    exchange: str             # "LSE", "NASDAQ", "NYSE" etc.
    uk_tradeable: bool
    direction: str            # "LONG" or "SHORT"
    rationale: str
    confidence_score: float   # 0-10
    time_horizon: str
    sector: str
    price_target_pct: Optional[float] = None  # expected % move
    suggested_by_models: List[str] = field(default_factory=list)


@dataclass
class EnsembleResult:
    """Cross-model consensus result for a batch of events."""
    run_id: str
    run_type: str             # "daily", "weekly", "adhoc", "urgent"
    generated_at: datetime
    raw_events: List[RawEvent]
    per_model_analyses: List[AnalyzedEvent]
    consensus_summary: str
    consensus_sectors: List[str]
    consensus_sentiment: str
    consensus_confidence: float
    discrepancies: List[str]   # Notable disagreements between models
    top_picks: List[StockPick]
    urgent_alerts: List[str]
    models_used: List[str]
    sources_used: List[str]
    events_processed: int
