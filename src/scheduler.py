"""
Trade Genie - Job Scheduler
Uses APScheduler to run analysis on a daily/weekly schedule.
Also monitors for urgent events and triggers immediate alerts.
"""

import logging
import os
import subprocess
import sys
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import settings

logger = logging.getLogger(__name__)
_scheduler: Optional[BackgroundScheduler] = None


def run_full_analysis(run_type: str = "scheduled"):
    """Execute the complete intelligence pipeline."""
    logger.info(f"=== Trade Genie Analysis Starting ({run_type}) ===")

    try:
        from src.agents.data_collector import collect_all_events, summarize_events_for_llm
        from src.database import init_db, log_run, mark_email_sent, save_report
        from src.delivery.email_sender import send_report_email
        from src.llm.ensemble import run_ensemble_analysis
        from src.report_generator import save_report_to_file

        init_db()

        # Step 1: Collect events
        logger.info("Step 1/4: Collecting events from all sources...")
        events = collect_all_events(lookback_hours=48)

        if not events:
            logger.warning("No events collected — aborting analysis.")
            log_run("none", run_type, "skipped", "No events collected")
            return

        # Step 2: Format for LLM
        logger.info(f"Step 2/4: Formatting {len(events)} events for LLM analysis...")
        digest = summarize_events_for_llm(events, max_events=60)

        # Step 3: LLM ensemble analysis
        logger.info("Step 3/4: Running LLM ensemble analysis...")
        result = run_ensemble_analysis(events, run_type=run_type, events_digest=digest)

        if not result:
            logger.error("Ensemble analysis returned no result.")
            log_run("none", run_type, "failed", "Ensemble returned None")
            return

        # Step 4: Save and deliver
        logger.info("Step 4/4: Saving report and delivering...")
        report_id = save_report(result)
        report_path = save_report_to_file(result)

        # Decide whether to send email
        should_email = (
            run_type in ("daily", "weekly")
            or result.urgent_alerts
            or result.consensus_confidence >= settings.URGENCY_SCORE_THRESHOLD
        )

        if should_email:
            sent = send_report_email(result)
            if sent:
                mark_email_sent(result.run_id)
                logger.info("Email delivered successfully.")
            else:
                logger.warning("Email delivery failed (check Gmail config in .env)")
        else:
            logger.info("Email skipped (below urgency threshold — view at web dashboard)")

        log_run(result.run_id, run_type, "success", f"{len(result.top_picks)} picks generated")

        logger.info(
            f"=== Analysis Complete ===\n"
            f"  Run ID:    {result.run_id}\n"
            f"  Picks:     {len(result.top_picks)}\n"
            f"  Urgency:   {result.consensus_confidence:.1f}/10\n"
            f"  Sentiment: {result.consensus_sentiment}\n"
            f"  Report:    {report_path}\n"
            f"  Alerts:    {len(result.urgent_alerts)}\n"
            f"  Models:    {', '.join(result.models_used)}"
        )

    except Exception as e:
        logger.exception(f"Analysis failed: {e}")


def run_urgency_check():
    """
    Quick urgency check — runs more frequently to detect breaking events.
    Only triggers a full analysis if critical news is detected.
    """
    try:
        from src.sources.newsapi_source import fetch_newsapi_events
        from src.sources.rss_source import fetch_rss_events

        # Quick 4-hour lookback on headline sources only
        events = fetch_newsapi_events(lookback_hours=4) + fetch_rss_events(lookback_hours=4)

        # Simple keyword-based urgency detection
        CRITICAL_KEYWORDS = [
            "nuclear", "war declared", "military strike", "invasion",
            "stock market crash", "bank collapse", "emergency rate",
            "oil embargo", "sanctions announced", "assassination",
            "pandemic", "outbreak", "attack on",
        ]

        critical_found = []
        for event in events:
            combined = (event.title + " " + (event.content or "")).lower()
            for kw in CRITICAL_KEYWORDS:
                if kw in combined:
                    critical_found.append((kw, event.title[:80]))
                    break

        if critical_found:
            logger.warning(
                f"Urgency check: {len(critical_found)} critical signals detected! "
                f"Triggering immediate full analysis..."
            )
            for kw, title in critical_found[:3]:
                logger.warning(f"  [{kw}] {title}")
            run_full_analysis(run_type="urgent")
        else:
            logger.debug("Urgency check: no critical signals.")

    except Exception as e:
        logger.error(f"Urgency check failed: {e}")


def auto_update():
    """
    Pulls latest code from GitHub. If new commits are found:
      1. Installs any new/updated requirements.
      2. Restarts the process so the new code takes effect.
    When running under launchd (KeepAlive=true), the restart is instant
    and automatic — launchd relaunches the process immediately.
    """
    repo_dir = str(settings.ROOT_DIR)
    logger.info("Auto-update: checking GitHub for new commits...")

    try:
        # Fetch without merging first so we can detect changes
        subprocess.run(
            ["git", "fetch", "origin", "main"],
            cwd=repo_dir, capture_output=True, timeout=30, check=True
        )

        # Compare local HEAD to remote
        local = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_dir
        ).strip()
        remote = subprocess.check_output(
            ["git", "rev-parse", "origin/main"], cwd=repo_dir
        ).strip()

        if local == remote:
            logger.info("Auto-update: already up to date.")
            return

        logger.info(f"Auto-update: new commits found ({local[:7].decode()} → {remote[:7].decode()}). Pulling...")

        # Pull the changes
        pull_result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=repo_dir, capture_output=True, timeout=60
        )
        if pull_result.returncode != 0:
            logger.error(f"Auto-update git pull failed: {pull_result.stderr.decode()}")
            return

        logger.info("Auto-update: pull successful. Installing any new requirements...")

        # Re-install requirements in case new packages were added
        pip_result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r",
             os.path.join(repo_dir, "requirements.txt"), "-q"],
            capture_output=True, timeout=120
        )
        if pip_result.returncode != 0:
            logger.warning(f"Auto-update pip install warning: {pip_result.stderr.decode()}")

        logger.info(
            "Auto-update: complete. Restarting process to load new code...\n"
            "(launchd will restart automatically if running as a service)"
        )

        # Replace current process with fresh copy — launchd sees it exit and restarts it
        os.execv(sys.executable, [sys.executable] + sys.argv)

    except subprocess.TimeoutExpired:
        logger.error("Auto-update timed out — will retry next cycle.")
    except FileNotFoundError:
        logger.error("Auto-update: git not found in PATH. Skipping.")
    except Exception as e:
        logger.error(f"Auto-update failed: {e}")


def start_scheduler():
    """Start the APScheduler background scheduler."""
    global _scheduler

    if _scheduler and _scheduler.running:
        logger.warning("Scheduler is already running.")
        return

    _scheduler = BackgroundScheduler(timezone="UTC")

    # Daily report (default: 7am UTC)
    daily_parts = settings.SCHEDULE_DAILY.split()
    if len(daily_parts) == 5:
        _scheduler.add_job(
            lambda: run_full_analysis("daily"),
            CronTrigger(
                minute=daily_parts[0],
                hour=daily_parts[1],
                day=daily_parts[2],
                month=daily_parts[3],
                day_of_week=daily_parts[4],
            ),
            id="daily_analysis",
            name="Daily Market Intelligence",
            replace_existing=True,
        )
        logger.info(f"Daily analysis scheduled: {settings.SCHEDULE_DAILY} UTC")

    # Weekly report (default: Monday 7am UTC)
    weekly_parts = settings.SCHEDULE_WEEKLY.split()
    if len(weekly_parts) == 5:
        _scheduler.add_job(
            lambda: run_full_analysis("weekly"),
            CronTrigger(
                minute=weekly_parts[0],
                hour=weekly_parts[1],
                day=weekly_parts[2],
                month=weekly_parts[3],
                day_of_week=weekly_parts[4],
            ),
            id="weekly_analysis",
            name="Weekly Market Intelligence",
            replace_existing=True,
        )
        logger.info(f"Weekly analysis scheduled: {settings.SCHEDULE_WEEKLY} UTC")

    # Urgency check: every 3 hours
    _scheduler.add_job(
        run_urgency_check,
        "interval",
        hours=3,
        id="urgency_check",
        name="Breaking News Urgency Check",
        replace_existing=True,
    )
    logger.info("Urgency check scheduled: every 3 hours")

    # Auto-update from GitHub: every hour
    _scheduler.add_job(
        auto_update,
        "interval",
        hours=1,
        id="auto_update",
        name="GitHub Auto-Update",
        replace_existing=True,
    )
    logger.info("Auto-update scheduled: every hour")

    _scheduler.start()
    logger.info("Scheduler started.")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped.")
