"""
Trade Genie - Report Generator
Builds HTML and plain-text reports from EnsembleResult objects.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from config.settings import settings
from src.models import EnsembleResult, StockPick

DIRECTION_COLOR = {"LONG": "#16a34a", "SHORT": "#dc2626"}
SENTIMENT_COLOR = {
    "BULLISH": "#16a34a",
    "BEARISH": "#dc2626",
    "NEUTRAL": "#6b7280",
    "MIXED": "#d97706",
}
URGENCY_COLOR = {
    range(0, 4): "#6b7280",
    range(4, 7): "#d97706",
    range(7, 9): "#ea580c",
    range(9, 11): "#dc2626",
}


def _urgency_color(score: float) -> str:
    if score < 4:
        return "#6b7280"
    if score < 7:
        return "#d97706"
    if score < 9:
        return "#ea580c"
    return "#dc2626"


def _confidence_bar(score: float) -> str:
    pct = min(100, score * 10)
    color = "#16a34a" if score >= 7 else "#d97706" if score >= 5 else "#dc2626"
    return (
        f'<div style="background:#e5e7eb;border-radius:4px;height:8px;width:100%;">'
        f'<div style="background:{color};width:{pct}%;height:8px;border-radius:4px;"></div>'
        f"</div><small>{score:.1f}/10</small>"
    )


def _pick_card(pick: StockPick, rank: int) -> str:
    dir_color = DIRECTION_COLOR.get(pick.direction, "#6b7280")
    models_str = " + ".join(pick.suggested_by_models) if pick.suggested_by_models else "1 model"
    consensus_badge = (
        '<span style="background:#1d4ed8;color:white;padding:2px 6px;'
        'border-radius:3px;font-size:11px;margin-left:6px;">CONSENSUS</span>'
        if len(pick.suggested_by_models) >= 2
        else ""
    )
    price_target = (
        f'<span style="color:{dir_color};font-weight:bold;">+{pick.price_target_pct:.0f}% target</span>'
        if pick.price_target_pct
        else ""
    )

    return f"""
    <div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin-bottom:12px;background:white;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
        <div>
          <span style="font-size:18px;font-weight:700;color:#111827;">{rank}. {pick.ticker}</span>
          <span style="color:#6b7280;margin-left:8px;">{pick.name}</span>
          {consensus_badge}
        </div>
        <div style="text-align:right;">
          <span style="background:{dir_color};color:white;padding:3px 10px;border-radius:4px;font-weight:bold;">
            {pick.direction}
          </span>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px;">
        <div><small style="color:#6b7280;">Sector</small><br><strong>{pick.sector}</strong></div>
        <div><small style="color:#6b7280;">Exchange</small><br><strong>{pick.exchange or "LSE"}</strong></div>
        <div><small style="color:#6b7280;">Time Horizon</small><br><strong>{pick.time_horizon}</strong></div>
      </div>
      <div style="margin-bottom:8px;">
        <small style="color:#6b7280;">Confidence</small><br>{_confidence_bar(pick.confidence_score)}
      </div>
      {f'<div style="margin-bottom:8px;">{price_target}</div>' if price_target else ""}
      <div style="background:#f9fafb;padding:10px;border-radius:6px;font-size:13px;color:#374151;line-height:1.5;">
        {pick.rationale}
      </div>
      <div style="margin-top:6px;"><small style="color:#9ca3af;">Suggested by: {models_str}</small></div>
    </div>
    """


def build_html_report(result: EnsembleResult) -> str:
    """Generate a full HTML report from an EnsembleResult."""
    model_results = getattr(result, "_model_results", {})

    # Header stats
    urgency_color = _urgency_color(result.consensus_confidence)
    sentiment_color = SENTIMENT_COLOR.get(result.consensus_sentiment, "#6b7280")

    picks_html = "".join(
        _pick_card(pick, i + 1) for i, pick in enumerate(result.top_picks)
    )

    # Per-model themes
    themes_html = ""
    for model_name, model_data in model_results.items():
        themes = model_data.get("key_themes", [])
        preds = model_data.get("predictive_signals", [])
        sector_impacts = model_data.get("sector_impacts", [])
        themes_html += f"""
        <div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin-bottom:16px;">
          <h3 style="margin:0 0 12px 0;color:#1f2937;font-size:16px;">
            🤖 {model_name.title()} Analysis
            <span style="font-size:12px;color:#6b7280;font-weight:normal;margin-left:8px;">
              Urgency: {model_data.get('urgency_score','?')}/10 | 
              Sentiment: {model_data.get('consensus_sentiment','?')}
            </span>
          </h3>
          <div style="margin-bottom:10px;">
            <strong>Key Themes:</strong>
            <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;">
              {''.join(f'<span style="background:#dbeafe;color:#1d4ed8;padding:3px 8px;border-radius:4px;font-size:13px;">{t}</span>' for t in themes)}
            </div>
          </div>
          {''.join(f"""
          <div style="background:#f9fafb;padding:10px;border-radius:6px;margin-bottom:8px;font-size:13px;">
            <strong>&gt; {p.get('theme','')}</strong> ({p.get('time_horizon','')}, confidence: {p.get('confidence',0)}/10)<br>
            <em>{p.get('prediction','')}</em><br>
            <small style="color:#6b7280;">Why not priced in: {p.get('why_not_priced_in','')}</small>
          </div>
          """ for p in preds[:3])}
        </div>
        """

    # Discrepancies
    disc_html = ""
    if result.discrepancies:
        items = "".join(
            f'<li style="margin-bottom:6px;">{d}</li>' for d in result.discrepancies
        )
        disc_html = f"""
        <div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:8px;padding:16px;margin-bottom:20px;">
          <h3 style="margin:0 0 10px 0;color:#92400e;">[!] Model Discrepancies</h3>
          <ul style="margin:0;padding-left:20px;font-size:13px;color:#78350f;">{items}</ul>
        </div>
        """

    # Urgent alerts
    alert_html = ""
    if result.urgent_alerts:
        items = "".join(
            f'<div style="padding:8px;margin-bottom:6px;background:#fee2e2;border-radius:4px;'
            f'font-size:13px;color:#991b1b;">[!!] {a}</div>'
            for a in result.urgent_alerts
        )
        alert_html = f"""
        <div style="background:#fef2f2;border:2px solid #f87171;border-radius:8px;
                    padding:16px;margin-bottom:20px;">
          <h3 style="margin:0 0 10px 0;color:#dc2626;">[!!] Urgent Alerts</h3>
          {items}
        </div>
        """

    date_str = result.generated_at.strftime("%A, %d %B %Y at %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trade Genie Report — {date_str}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background:#f3f4f6; color:#111827; margin:0; padding:20px; }}
  .container {{ max-width:900px; margin:0 auto; }}
  h1, h2, h3 {{ margin-top:0; }}
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1e3a5f,#0f172a);color:white;
              border-radius:12px;padding:24px;margin-bottom:20px;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <div>
        <h1 style="margin:0;font-size:28px;">⚡ Trade Genie</h1>
        <p style="margin:4px 0 0;opacity:0.8;font-size:14px;">
          Market Intelligence Report &mdash; {date_str}
        </p>
        <p style="margin:4px 0 0;opacity:0.6;font-size:12px;">
          Run type: {result.run_type.upper()} | 
          {result.events_processed} events analysed | 
          Models: {', '.join(result.models_used)}
        </p>
      </div>
      <div style="text-align:right;">
        <div style="font-size:36px;font-weight:700;color:{urgency_color};">
          {result.consensus_confidence:.1f}
        </div>
        <div style="font-size:12px;opacity:0.8;">Urgency Score</div>
        <div style="margin-top:6px;">
          <span style="background:{sentiment_color};padding:4px 12px;border-radius:4px;
                       font-weight:700;font-size:14px;">
            {result.consensus_sentiment}
          </span>
        </div>
      </div>
    </div>
  </div>

  {alert_html}

  <!-- Summary -->
  <div style="background:white;border-radius:8px;padding:20px;margin-bottom:20px;
              border:1px solid #e5e7eb;">
    <h2 style="font-size:18px;color:#1f2937;margin-bottom:12px;">📋 Executive Summary</h2>
    <div style="font-size:14px;line-height:1.7;color:#374151;">
      {result.consensus_summary.replace(chr(10), '<br>')}
    </div>
    {'<div style="margin-top:12px;"><strong>Key sectors:</strong> ' + 
     ', '.join(f'<span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;border-radius:4px;margin:0 3px;font-size:13px;">{s}</span>' for s in result.consensus_sectors) +
     '</div>' if result.consensus_sectors else ''}
  </div>

  {disc_html}

  <!-- Top Picks -->
  <div style="margin-bottom:20px;">
    <h2 style="font-size:20px;color:#1f2937;margin-bottom:16px;">
      Top {len(result.top_picks)} UK-Tradeable Picks
    </h2>
    {picks_html}
  </div>

  <!-- Per-model analysis -->
  <div style="margin-bottom:20px;">
    <h2 style="font-size:20px;color:#1f2937;margin-bottom:16px;">
      Per-Model Analysis
    </h2>
    {themes_html}
  </div>

  <!-- Footer -->
  <div style="text-align:center;font-size:12px;color:#9ca3af;padding:16px;
              border-top:1px solid #e5e7eb;margin-top:20px;">
    Trade Genie — Automated Market Intelligence | 
    For informational purposes only. Not financial advice. 
    Always do your own research before investing.
  </div>

</div>
</body>
</html>"""


def build_plain_text_report(result: EnsembleResult) -> str:
    """Generate plain-text version of the report (for email fallback)."""
    lines = [
        "=" * 60,
        f"  TRADE GENIE — Market Intelligence Report",
        f"  {result.generated_at.strftime('%A %d %B %Y %H:%M UTC')}",
        "=" * 60,
        f"  Run type: {result.run_type.upper()}",
        f"  Events analysed: {result.events_processed}",
        f"  Models: {', '.join(result.models_used)}",
        f"  Urgency Score: {result.consensus_confidence:.1f}/10",
        f"  Consensus Sentiment: {result.consensus_sentiment}",
        "=" * 60,
        "",
    ]

    if result.urgent_alerts:
        lines.append("!! URGENT ALERTS")
        for alert in result.urgent_alerts:
            lines.append(f"  !! {alert}")
        lines.append("")

    lines += ["EXECUTIVE SUMMARY", "-" * 40, result.consensus_summary, ""]

    if result.discrepancies:
        lines += ["[!] MODEL DISCREPANCIES", "-" * 40]
        for d in result.discrepancies:
            lines.append(f"  • {d}")
        lines.append("")

    lines += [f"TOP {len(result.top_picks)} PICKS", "-" * 40]
    for i, pick in enumerate(result.top_picks, 1):
        consensus = " [CONSENSUS]" if len(pick.suggested_by_models) >= 2 else ""
        lines.append(
            f"{i:2}. {pick.ticker:<12} {pick.direction:<5} "
            f"Conf:{pick.confidence_score:.1f}/10  {pick.sector}{consensus}"
        )
        lines.append(f"     {pick.name}")
        lines.append(f"     Horizon: {pick.time_horizon}")
        lines.append(f"     {pick.rationale[:200]}")
        lines.append("")

    lines += [
        "-" * 60,
        "DISCLAIMER: For informational purposes only. Not financial advice.",
        "Trade Genie — Automated Market Intelligence",
    ]

    return "\n".join(lines)


def save_report_to_file(result: EnsembleResult) -> Path:
    """Save HTML report to disk and return path."""
    filename = f"report_{result.run_id}.html"
    path = settings.REPORTS_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_html_report(result))
    logger.info(f"Report saved: {path}")
    return path
