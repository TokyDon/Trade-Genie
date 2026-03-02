"""
Trade Genie - Main Entry Point
CLI tool and web server launcher.

Usage:
    # Start web dashboard + scheduler (recommended)
    python run.py

    # Run a one-off analysis now
    python run.py --run

    # Start only the web dashboard (no scheduler)
    python run.py --web-only

    # Start only the scheduler (no web server)
    python run.py --scheduler-only

    # Check configuration
    python run.py --check
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure data directory exists before setting up file logging
_data_dir = Path(__file__).parent / "data"
_data_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_data_dir / "tradegenie.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger("tradegenie")


def check_config():
    """Print configuration status."""
    from config.settings import settings

    print("\n" + "=" * 55)
    print("  ⚡ TRADE GENIE — Configuration Status")
    print("=" * 55)

    warnings = settings.validate()
    llms = settings.available_llms()

    print(f"\n[OK] LLM Providers configured: {', '.join(llms) if llms else 'NONE'}")
    if not llms:
        print("  [!] Add at least one LLM API key to .env to run analysis")

    print(f"\nEmail:         {'[OK] Configured' if settings.GMAIL_ADDRESS and not settings.GMAIL_ADDRESS.startswith('your_') else '[--] Not configured'}")
    print(f"NewsAPI:       {'[OK] Configured' if settings.NEWS_API_KEY and not settings.NEWS_API_KEY.startswith('your_') else '[--] Not configured'}")
    print(f"Reddit:        {'[OK] Configured' if settings.REDDIT_CLIENT_ID and not settings.REDDIT_CLIENT_ID.startswith('your_') else '[--] Not configured'}")
    print(f"Twitter:       {'[OK] Configured' if settings.TWITTER_BEARER_TOKEN and not settings.TWITTER_BEARER_TOKEN.startswith('your_') else '[--] Not configured (optional)'}")
    print(f"Alpha Vantage: {'[OK] Configured' if settings.ALPHA_VANTAGE_API_KEY and not settings.ALPHA_VANTAGE_API_KEY.startswith('your_') else '[--] Not configured'}")
    print(f"GDELT:         [OK] No key required")
    print(f"RSS Feeds:     [OK] {len(settings.RSS_FEEDS)} feeds configured")

    if warnings:
        print(f"\n[!] Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"   • {w}")

    print(f"\nWeb dashboard: http://localhost:{settings.WEB_PORT}")
    print(f"Daily schedule:  {settings.SCHEDULE_DAILY} UTC")
    print(f"Weekly schedule: {settings.SCHEDULE_WEEKLY} UTC")
    print(f"Urgency threshold: {settings.URGENCY_SCORE_THRESHOLD}/10")
    print(f"Top picks per report: {settings.TOP_PICKS_COUNT}")
    print()


def run_analysis_now():
    """Run a one-off analysis immediately."""
    from src.database import init_db
    from src.scheduler import run_full_analysis

    init_db()
    logger.info("Running one-off analysis...")
    run_full_analysis(run_type="adhoc")


def start_web(with_scheduler: bool = True):
    """Start the web dashboard (and optionally the scheduler)."""
    import uvicorn
    from src.database import init_db

    init_db()

    if with_scheduler:
        from src.scheduler import start_scheduler
        start_scheduler()

    logger.info(
        f"Starting Trade Genie web dashboard at "
        f"http://{settings.WEB_HOST}:{settings.WEB_PORT}"
    )
    uvicorn.run(
        "src.delivery.web_app:app",
        host=settings.WEB_HOST,
        port=settings.WEB_PORT,
        reload=False,
        log_level="info",
    )


def start_scheduler_only():
    """Start just the scheduler (headless mode)."""
    import time
    from src.database import init_db
    from src.scheduler import start_scheduler, stop_scheduler

    init_db()
    scheduler = start_scheduler()

    logger.info("Scheduler running in standalone mode. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        stop_scheduler()
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    from config.settings import settings

    # Ensure data dirs exist
    settings.ensure_dirs()

    parser = argparse.ArgumentParser(
        description="Trade Genie — Market Intelligence Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--run", action="store_true", help="Run a one-off analysis now")
    parser.add_argument("--web-only", action="store_true", help="Start web dashboard only (no scheduler)")
    parser.add_argument("--scheduler-only", action="store_true", help="Start scheduler only (no web)")
    parser.add_argument("--check", action="store_true", help="Check configuration status")

    args = parser.parse_args()

    if args.check:
        check_config()
    elif args.run:
        check_config()
        run_analysis_now()
    elif args.web_only:
        start_web(with_scheduler=False)
    elif args.scheduler_only:
        start_scheduler_only()
    else:
        # Default: web dashboard + scheduler
        check_config()
        start_web(with_scheduler=True)
