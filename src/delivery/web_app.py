"""
Trade Genie - Web Dashboard (FastAPI)
A clean, responsive web interface to browse intelligence reports.
Access at: http://localhost:8080
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config.settings import settings
from src import database
from src.models import EnsembleResult
from src.report_generator import build_html_report

logger = logging.getLogger(__name__)

app = FastAPI(title="Trade Genie", description="Market Intelligence Dashboard")

# Templates
TEMPLATES_DIR = settings.TEMPLATES_DIR
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Simple in-memory running state
_running_analysis = {"status": "idle", "started_at": None, "run_id": None}


def _check_auth(request: Request) -> bool:
    """Check if dashboard password is required and validated."""
    if not settings.WEB_DASHBOARD_PASSWORD:
        return True
    session = request.cookies.get("tg_auth")
    return session == settings.WEB_DASHBOARD_PASSWORD


@app.on_event("startup")
async def startup():
    database.init_db()
    logger.info("Trade Genie web dashboard started.")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page showing recent reports."""
    if not _check_auth(request):
        return RedirectResponse("/login")

    reports = database.get_reports(limit=20)
    # Parse JSON fields
    for r in reports:
        if r.get("top_picks_json"):
            r["top_picks"] = json.loads(r["top_picks_json"])[:5]
        if r.get("urgent_alerts_json"):
            r["urgent_alerts"] = json.loads(r["urgent_alerts_json"])
        if r.get("models_used"):
            r["models_list"] = json.loads(r["models_used"])
        r["generated_at_fmt"] = r.get("generated_at", "")[:16].replace("T", " ")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "reports": reports,
            "running": _running_analysis,
            "page_title": "Trade Genie Dashboard",
        },
    )


@app.get("/report/{run_id}", response_class=HTMLResponse)
async def view_report(request: Request, run_id: str):
    """View a specific report as full HTML."""
    if not _check_auth(request):
        return RedirectResponse("/login")

    report = database.get_report_by_id(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # If we have the full HTML report on disk, serve it
    report_path = settings.REPORTS_DIR / f"report_{run_id}.html"
    if report_path.exists():
        return HTMLResponse(content=report_path.read_text(encoding="utf-8"))

    # Otherwise reconstruct from DB data
    if report.get("full"):
        full = report["full"]
        return HTMLResponse(
            content=f"<pre style='font-family:monospace;padding:20px'>"
            f"{json.dumps(full, indent=2)}</pre>"
        )

    raise HTTPException(status_code=404, detail="Report data not found")


@app.post("/run", response_class=JSONResponse)
async def trigger_analysis(
    request: Request,
    background_tasks: BackgroundTasks,
    run_type: str = "adhoc",
):
    """Trigger an ad-hoc analysis run."""
    if not _check_auth(request):
        raise HTTPException(status_code=401)

    if _running_analysis["status"] == "running":
        return JSONResponse({"status": "already_running", "message": "Analysis is already in progress."})

    background_tasks.add_task(_run_analysis_task, run_type)
    return JSONResponse({"status": "started", "message": f"Analysis started ({run_type})."})


@app.get("/status", response_class=JSONResponse)
async def get_status(request: Request):
    """Get current run status."""
    return JSONResponse(_running_analysis)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return HTMLResponse("""
    <!DOCTYPE html><html><head><title>Trade Genie Login</title>
    <style>body{font-family:sans-serif;display:flex;justify-content:center;
    align-items:center;height:100vh;background:#f3f4f6;margin:0;}
    .box{background:white;padding:40px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.1);
    min-width:320px;}h1{margin:0 0 24px;font-size:24px;color:#111;}
    input{width:100%;padding:10px;border:1px solid #d1d5db;border-radius:6px;font-size:15px;
    margin-bottom:16px;box-sizing:border-box;}
    button{width:100%;padding:12px;background:#1e3a5f;color:white;border:none;border-radius:6px;
    font-size:16px;cursor:pointer;}</style></head>
    <body><div class="box"><h1>⚡ Trade Genie</h1>
    <form method="POST" action="/login">
    <input type="password" name="password" placeholder="Dashboard password">
    <button>Sign In</button></form></div></body></html>
    """)


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == settings.WEB_DASHBOARD_PASSWORD:
        response = RedirectResponse("/", status_code=302)
        response.set_cookie("tg_auth", password, httponly=True, max_age=86400 * 30)
        return response
    return HTMLResponse("<p>Wrong password. <a href='/login'>Try again</a></p>")


async def _run_analysis_task(run_type: str):
    """Background task that runs the full analysis pipeline."""
    global _running_analysis
    _running_analysis = {
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "run_id": None,
    }
    try:
        from src.agents.data_collector import collect_all_events, summarize_events_for_llm
        from src.llm.ensemble import run_ensemble_analysis
        from src.report_generator import save_report_to_file
        from src.delivery.email_sender import send_report_email
        import asyncio

        # Run blocking code in thread pool
        import concurrent.futures

        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            # Collect data
            events = await loop.run_in_executor(pool, collect_all_events, 48)
            digest = await loop.run_in_executor(
                pool, summarize_events_for_llm, events
            )
            # LLM analysis
            result = await loop.run_in_executor(
                pool, run_ensemble_analysis, events, run_type, digest
            )

        if result:
            database.save_report(result)
            save_report_to_file(result)
            _running_analysis["run_id"] = result.run_id

            # Send email if urgency is high or it's scheduled
            if result.urgent_alerts or run_type in ("daily", "weekly"):
                send_report_email(result)
                database.mark_email_sent(result.run_id)

        _running_analysis["status"] = "complete"

    except Exception as e:
        logger.error(f"Analysis task failed: {e}")
        _running_analysis["status"] = "error"
        _running_analysis["error"] = str(e)
