"""
Trade Genie - LLM Ensemble Engine
Runs all configured LLMs in parallel, then cross-checks results
to identify consensus picks and flag discrepancies.
This reduces hallucination risk and improves confidence calibration.
"""

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional

from config.settings import settings
from src.llm.anthropic_client import analyze_with_anthropic
from src.llm.gemini_client import analyze_with_gemini
from src.llm.openai_client import analyze_with_openai
from src.models import EnsembleResult, RawEvent, StockPick

logger = logging.getLogger(__name__)


def _run_all_llms(events_digest: str) -> Dict[str, Optional[dict]]:
    """Run all available LLMs concurrently."""
    llm_runners = {
        "openai": lambda: analyze_with_openai(events_digest, settings.TOP_PICKS_COUNT),
        "anthropic": lambda: analyze_with_anthropic(events_digest, settings.TOP_PICKS_COUNT),
        "gemini": lambda: analyze_with_gemini(events_digest, settings.TOP_PICKS_COUNT),
    }

    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_name = {
            executor.submit(fn): name for name, fn in llm_runners.items()
        }
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                result = future.result()
                if result:
                    results[name] = result
                    logger.info(f"LLM {name}: analysis received.")
                else:
                    logger.info(f"LLM {name}: no result (not configured or failed).")
            except Exception as e:
                logger.error(f"LLM {name} raised exception: {e}")

    return results


def _extract_picks(model_result: dict, model_name: str) -> List[StockPick]:
    """Parse stock picks from a single model's JSON result."""
    picks = []
    for item in model_result.get("top_picks", []):
        try:
            picks.append(
                StockPick(
                    ticker=item.get("ticker", ""),
                    name=item.get("name", ""),
                    exchange=item.get("exchange", ""),
                    uk_tradeable=bool(item.get("uk_tradeable", True)),
                    direction=item.get("direction", "LONG"),
                    rationale=item.get("rationale", ""),
                    confidence_score=float(item.get("confidence", 5.0)),
                    time_horizon=item.get("time_horizon", ""),
                    sector=item.get("sector", ""),
                    price_target_pct=item.get("price_target_pct"),
                    suggested_by_models=[model_name],
                )
            )
        except Exception as e:
            logger.warning(f"Could not parse pick from {model_name}: {item} — {e}")
    return picks


def _merge_picks(all_picks: List[StockPick]) -> List[StockPick]:
    """
    Merge picks across models. Items mentioned by multiple models get
    boosted confidence and are ranked higher (consensus premium).
    """
    merged: Dict[str, StockPick] = {}

    for pick in all_picks:
        key = pick.ticker.upper()
        if key in merged:
            existing = merged[key]
            # Average confidence, note additional model
            existing.confidence_score = round(
                (existing.confidence_score + pick.confidence_score) / 2, 2
            )
            # Consensus bonus: +1 point per additional model agreement
            n_models = len(existing.suggested_by_models)
            existing.confidence_score = min(10.0, existing.confidence_score + 0.5)
            existing.suggested_by_models.extend(pick.suggested_by_models)
            # Merge rationale
            if pick.rationale not in existing.rationale:
                existing.rationale += f"\n[{pick.suggested_by_models[0]}] {pick.rationale}"
        else:
            merged[key] = pick

    # Sort: consensus picks first, then by confidence
    result = sorted(
        merged.values(),
        key=lambda p: (len(p.suggested_by_models), p.confidence_score),
        reverse=True,
    )
    return result


def _find_discrepancies(model_results: Dict[str, dict]) -> List[str]:
    """Identify notable disagreements between models."""
    discrepancies = []
    models = list(model_results.keys())

    if len(models) < 2:
        return discrepancies

    # Sentiment disagreements
    sentiments = {
        name: res.get("consensus_sentiment", "UNKNOWN")
        for name, res in model_results.items()
    }
    unique_sentiments = set(sentiments.values())
    if len(unique_sentiments) > 1:
        sentiment_str = ", ".join(f"{k}: {v}" for k, v in sentiments.items())
        discrepancies.append(f"SENTIMENT DISAGREEMENT: {sentiment_str}")

    # Urgency score disagreements (>2 point difference)
    urgencies = {
        name: float(res.get("urgency_score", 5))
        for name, res in model_results.items()
    }
    urgency_vals = list(urgencies.values())
    if max(urgency_vals) - min(urgency_vals) > 2:
        urgency_str = ", ".join(f"{k}: {v:.1f}" for k, v in urgencies.items())
        discrepancies.append(f"URGENCY DISAGREEMENT: {urgency_str}")

    # Picks unique to only one model (no consensus)
    all_tickers: Dict[str, List[str]] = {}
    for name, res in model_results.items():
        for pick in res.get("top_picks", []):
            ticker = pick.get("ticker", "").upper()
            if ticker:
                all_tickers.setdefault(ticker, []).append(name)

    solo_picks = [t for t, models in all_tickers.items() if len(models) == 1]
    if solo_picks:
        discrepancies.append(
            f"SOLO PICKS (only one model agrees): {', '.join(solo_picks[:5])}"
        )

    consensus_picks = [t for t, models in all_tickers.items() if len(models) >= 2]
    if consensus_picks:
        discrepancies.append(
            f"CONSENSUS PICKS (multiple models agree): {', '.join(consensus_picks[:8])}"
        )

    return discrepancies


def run_ensemble_analysis(
    events: List[RawEvent],
    run_type: str = "adhoc",
    events_digest: Optional[str] = None,
) -> Optional[EnsembleResult]:
    """
    Main entry point: runs all LLMs, merges results, returns EnsembleResult.
    """
    if not events and not events_digest:
        logger.error("No events provided for analysis.")
        return None

    if not events_digest:
        from src.agents.data_collector import summarize_events_for_llm
        events_digest = summarize_events_for_llm(events)

    if not settings.available_llms():
        logger.error("No LLM providers configured. Please add API keys to .env")
        return None

    logger.info(f"Running ensemble analysis with: {settings.available_llms()}")

    # Run all LLMs
    model_results = _run_all_llms(events_digest)

    if not model_results:
        logger.error("All LLM analyses failed.")
        return None

    # Extract and merge picks
    all_picks: List[StockPick] = []
    for model_name, result in model_results.items():
        picks = _extract_picks(result, model_name)
        all_picks.extend(picks)

    merged_picks = _merge_picks(all_picks)
    top_picks = merged_picks[: settings.TOP_PICKS_COUNT]

    # Find discrepancies
    discrepancies = _find_discrepancies(model_results)

    # Consensus metrics (average across models)
    urgency_scores = [
        float(r.get("urgency_score", 5)) for r in model_results.values()
    ]
    avg_urgency = sum(urgency_scores) / len(urgency_scores)

    # Determine consensus sentiment (majority vote)
    sentiments = [r.get("consensus_sentiment", "NEUTRAL") for r in model_results.values()]
    from collections import Counter
    sentiment_vote = Counter(sentiments).most_common(1)[0][0]

    # Collect all sectors
    all_sectors = []
    for r in model_results.values():
        for si in r.get("sector_impacts", []):
            if si.get("direction") == "BULLISH":
                all_sectors.append(si.get("sector", ""))
    from collections import Counter as C
    top_sectors = [s for s, _ in C(all_sectors).most_common(5) if s]

    # Build consensus summary
    summaries = [r.get("event_summary", "") for r in model_results.values() if r.get("event_summary")]
    if len(summaries) > 1:
        consensus_summary = (
            f"Cross-model consensus summary ({len(model_results)} models):\n\n"
            + "\n\n---\n\n".join(
                f"**{name}**: {r.get('event_summary', '')}"
                for name, r in model_results.items()
            )
        )
    elif summaries:
        consensus_summary = summaries[0]
    else:
        consensus_summary = "No summary generated."

    # Urgent alerts
    urgent_alerts = []
    if avg_urgency >= settings.URGENCY_SCORE_THRESHOLD:
        urgent_alerts.append(
            f"HIGH URGENCY ALERT: Average urgency score {avg_urgency:.1f}/10 — "
            f"immediate attention recommended!"
        )
    for r in model_results.values():
        for key_theme in r.get("key_themes", []):
            if any(
                kw in key_theme.lower()
                for kw in ["war", "attack", "crisis", "crash", "nuclear", "collapse"]
            ):
                urgent_alerts.append(f"Critical theme detected: {key_theme}")

    # Deduplicate urgent alerts
    urgent_alerts = list(dict.fromkeys(urgent_alerts))

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + run_type

    result = EnsembleResult(
        run_id=run_id,
        run_type=run_type,
        generated_at=datetime.utcnow(),
        raw_events=events,
        per_model_analyses=[],  # Could store AnalyzedEvent objects here
        consensus_summary=consensus_summary,
        consensus_sectors=top_sectors,
        consensus_sentiment=sentiment_vote,
        consensus_confidence=avg_urgency,
        discrepancies=discrepancies,
        top_picks=top_picks,
        urgent_alerts=urgent_alerts,
        models_used=list(model_results.keys()),
        sources_used=list({e.source for e in events}),
        events_processed=len(events),
    )

    # Store full model results for reporting
    result._model_results = model_results  # type: ignore

    logger.info(
        f"Ensemble complete: {len(top_picks)} picks, "
        f"urgency={avg_urgency:.1f}, sentiment={sentiment_vote}, "
        f"discrepancies={len(discrepancies)}"
    )
    return result
