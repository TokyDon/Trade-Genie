"""
Trade Genie - Database Layer
SQLite storage for reports and run history.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from config.settings import settings

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT UNIQUE NOT NULL,
            run_type TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            consensus_sentiment TEXT,
            consensus_confidence REAL,
            urgency_score REAL,
            models_used TEXT,
            sources_used TEXT,
            events_processed INTEGER,
            top_picks_json TEXT,
            discrepancies_json TEXT,
            urgent_alerts_json TEXT,
            consensus_summary TEXT,
            full_json TEXT,
            email_sent INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS run_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            run_type TEXT,
            status TEXT,
            message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
    logger.info("Database initialised.")


def save_report(result) -> int:
    """Save an EnsembleResult to the database. Returns row ID."""
    import dataclasses

    top_picks_data = []
    for pick in result.top_picks:
        top_picks_data.append({
            "ticker": pick.ticker,
            "name": pick.name,
            "exchange": pick.exchange,
            "uk_tradeable": pick.uk_tradeable,
            "direction": pick.direction,
            "rationale": pick.rationale,
            "confidence_score": pick.confidence_score,
            "time_horizon": pick.time_horizon,
            "sector": pick.sector,
            "price_target_pct": pick.price_target_pct,
            "suggested_by_models": pick.suggested_by_models,
        })

    # Build full JSON (includes raw model results if available)
    full_data = {
        "run_id": result.run_id,
        "run_type": result.run_type,
        "generated_at": result.generated_at.isoformat(),
        "consensus_summary": result.consensus_summary,
        "consensus_sectors": result.consensus_sectors,
        "consensus_sentiment": result.consensus_sentiment,
        "consensus_confidence": result.consensus_confidence,
        "discrepancies": result.discrepancies,
        "top_picks": top_picks_data,
        "urgent_alerts": result.urgent_alerts,
        "models_used": result.models_used,
        "sources_used": result.sources_used,
        "events_processed": result.events_processed,
    }

    # Include per-model results if available
    if hasattr(result, "_model_results"):
        full_data["model_results"] = {
            name: {k: v for k, v in data.items() if not k.startswith("_")}
            for name, data in result._model_results.items()
        }

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT OR REPLACE INTO reports
            (run_id, run_type, generated_at, consensus_sentiment, consensus_confidence,
             urgency_score, models_used, sources_used, events_processed,
             top_picks_json, discrepancies_json, urgent_alerts_json,
             consensus_summary, full_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.run_id,
                result.run_type,
                result.generated_at.isoformat(),
                result.consensus_sentiment,
                result.consensus_confidence,
                result.consensus_confidence,  # urgency = confidence in this context
                json.dumps(result.models_used),
                json.dumps(result.sources_used),
                result.events_processed,
                json.dumps(top_picks_data),
                json.dumps(result.discrepancies),
                json.dumps(result.urgent_alerts),
                result.consensus_summary,
                json.dumps(full_data, default=str),
            ),
        )
        return cursor.lastrowid


def get_reports(limit: int = 20) -> List[dict]:
    """Retrieve recent reports."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM reports ORDER BY generated_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def get_report_by_id(run_id: str) -> Optional[dict]:
    """Retrieve a single report by run_id."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM reports WHERE run_id = ?", (run_id,)
        ).fetchone()
    if row:
        data = dict(row)
        # Parse full JSON
        if data.get("full_json"):
            data["full"] = json.loads(data["full_json"])
        return data
    return None


def mark_email_sent(run_id: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE reports SET email_sent = 1 WHERE run_id = ?", (run_id,)
        )


def log_run(run_id: str, run_type: str, status: str, message: str = ""):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO run_log (run_id, run_type, status, message) VALUES (?, ?, ?, ?)",
            (run_id, run_type, status, message),
        )
