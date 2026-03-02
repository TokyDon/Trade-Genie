# ⚡ Trade Genie

**Automated Market Intelligence Agent** — monitors world events in real-time, predicts market-moving developments *before* they're priced in, and delivers ranked UK-tradeable stock/ETF picks with confidence scores.

---

## What it does

1. **Monitors** 6 data sources simultaneously (news, Reddit, GDELT geopolitical events, RSS feeds, Twitter/X, Alpha Vantage)
2. **Analyses** using 3 LLMs in parallel (OpenAI GPT-4o, Anthropic Claude, Google Gemini)
3. **Cross-checks** model outputs to flag discrepancies and boost confidence on consensus picks
4. **Ranks** UK-tradeable ETFs and stocks most likely to move, with confidence scores 0–10
5. **Delivers** via email (Gmail) and/or a web dashboard at `http://localhost:8080`
6. **Schedules** daily/weekly reports + continuous urgency monitoring (every 3 hours)

> **Example**: When US-Iran tensions were building over recent weeks, the agent would have flagged rising geopolitical risk → predicted oil service sector upside → recommended IEOG.L with high confidence *before* the news was fully priced in.

---

## Quick Start (5 minutes)

### 1. Prerequisites
- Python 3.11+ ([download](https://www.python.org/downloads/))
- Works on Windows, macOS, Linux

### 2. Install dependencies

```bash
cd "Trade Genie"
pip install -r requirements.txt
```

### 3. Configure API keys

```bash
cp .env.example .env
```

Open `.env` and fill in your keys (see [API Keys](#api-keys) below).

### 4. Check your configuration

```bash
python run.py --check
```

### 5. Run your first analysis

```bash
python run.py --run
```

### 6. Start the full system (web dashboard + scheduler)

```bash
python run.py
```

Then open **http://localhost:8080** in your browser.

---

## API Keys

| Service | Required | Cost | Get it |
|---------|----------|------|--------|
| **OpenAI** | At least one LLM | ~$0.01-0.05/run | [platform.openai.com](https://platform.openai.com) |
| **Anthropic** | At least one LLM | ~$0.02-0.08/run | [console.anthropic.com](https://console.anthropic.com) |
| **Google Gemini** | At least one LLM | Free tier available | [aistudio.google.com](https://aistudio.google.com) |
| **NewsAPI** | Recommended | Free (100 req/day) | [newsapi.org/register](https://newsapi.org/register) |
| **Reddit** | Recommended | Free | [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) |
| **Alpha Vantage** | Recommended | Free (25 req/day) | [alphavantage.co](https://www.alphavantage.co/support/#api-key) |
| **Twitter/X** | Optional | ~$100/month | [developer.twitter.com](https://developer.twitter.com) |
| **GDELT** | Auto | Free | No key needed |
| **RSS Feeds** | Auto | Free | No key needed |

> **Minimum viable setup**: One LLM key + GDELT + RSS feeds will work with zero cost.  
> **Recommended**: OpenAI or Anthropic key + NewsAPI + Reddit = strong signal quality.

### Gmail Setup (for email delivery)

1. Enable 2-factor authentication on your Gmail account
2. Go to Google Account → Security → [App Passwords](https://myaccount.google.com/apppasswords)
3. Create an app password for "Mail"
4. Use that 16-character password as `GMAIL_APP_PASSWORD` in `.env`

### Reddit Setup

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click "Create App" → select **script**
3. Fill in any name and redirect URI (e.g. `http://localhost`)
4. Copy the client ID (under the app name) and secret

---

## Usage

```bash
# Start everything (web + scheduler) — recommended
python run.py

# One-off analysis (prints report + optionally emails)
python run.py --run

# Web dashboard only (no auto-scheduling)
python run.py --web-only

# Scheduler only (headless, no web UI)
python run.py --scheduler-only

# Check what's configured
python run.py --check
```

---

## Web Dashboard

Visit **http://localhost:8080** to:

- Browse all intelligence reports
- See top picks at a glance (with consensus badges)
- View full HTML reports with per-model analysis
- Trigger on-demand analysis with one click
- See urgency alerts in real-time

If you set `WEB_DASHBOARD_PASSWORD` in `.env`, you'll be prompted to log in.

---

## Report Structure

Each report contains:

| Section | Description |
|---------|-------------|
| **Executive Summary** | Cross-model consensus narrative of key world events |
| **Urgency Score** | 0–10 (≥8.5 triggers immediate email alert) |
| **Consensus Sentiment** | BULLISH / BEARISH / NEUTRAL / MIXED |
| **Top Picks** | Ranked ETFs/stocks with ticker, direction, confidence, rationale |
| **CONSENSUS badge** | Picks recommended by 2+ models get a confidence bonus |
| **Model Discrepancies** | Where models disagree — signals uncertainty |
| **Per-model Analysis** | Full breakdown from each LLM independently |
| **Predictive Signals** | What's likely to happen next — *before* it's in the news |

### Confidence Scoring

- **7–10**: Strong signal, multiple models agree
- **5–7**: Moderate confidence, worth monitoring
- **0–5**: Weak signal, speculative

---

## Scheduling

Configure in `.env`:

```
# Cron format: minute hour day month day_of_week
SCHEDULE_DAILY=0 7 * * *        # Every day at 7am UTC
SCHEDULE_WEEKLY=0 7 * * 1       # Every Monday at 7am UTC
URGENCY_SCORE_THRESHOLD=8.5     # Auto-email if urgency ≥ this
```

The system also runs an **urgency check every 3 hours** that scans for breaking news keywords. If critical signals are detected, it immediately triggers a full analysis and sends an alert email.

---

## UK Tradeable ETFs

The system prioritises LSE-listed ETFs available on UK platforms (Hargreaves Lansdown, IG, AJ Bell, Interactive Brokers UK):

| Sector | Example ETFs |
|--------|-------------|
| Energy/Oil | `IEOG.L`, `XOIL.L`, `OGIG.L` |
| Defence | `DFEN.L`, `NATO.L` |
| Technology | `IITU.L`, `QDVE.L`, `ROBO.L` |
| Gold/Commodities | `SGLN.L`, `CMOD.L` |
| Emerging Markets | `IEEM.L` |
| Healthcare | `IUHC.L`, `BIOT.L` |
| Safe Haven | `IGLT.L`, `IBTM.L` |
| UK/Global Broad | `ISF.L`, `VWRL.L` |

You can add more ETFs or individual stocks to `UK_ETF_UNIVERSE` in `config/settings.py`.

---

## Project Structure

```
Trade Genie/
├── run.py                  # Main entry point (CLI)
├── requirements.txt
├── .env.example            # Copy to .env and fill in keys
├── config/
│   └── settings.py         # All configuration
├── src/
│   ├── models.py           # Shared data models
│   ├── database.py         # SQLite storage
│   ├── report_generator.py # HTML/text report builder
│   ├── scheduler.py        # APScheduler jobs
│   ├── agents/
│   │   └── data_collector.py    # Aggregates all sources
│   ├── sources/
│   │   ├── newsapi_source.py
│   │   ├── reddit_source.py
│   │   ├── gdelt_source.py
│   │   ├── rss_source.py
│   │   ├── twitter_source.py
│   │   └── alphavantage_source.py
│   ├── llm/
│   │   ├── prompts.py           # Shared analysis prompt
│   │   ├── openai_client.py
│   │   ├── anthropic_client.py
│   │   ├── gemini_client.py
│   │   └── ensemble.py          # Cross-model consensus engine
│   └── delivery/
│       ├── email_sender.py      # Gmail SMTP
│       └── web_app.py           # FastAPI dashboard
├── templates/
│   └── dashboard.html           # Web UI template
└── data/
    ├── reports/                 # HTML report files
    ├── cache/
    ├── tradegenie.db            # SQLite database
    └── tradegenie.log           # Log file
```

---

## Running on iMac (macOS)

Exactly the same steps — Python runs identically on macOS:

```bash
# If you don't have Python 3.11+:
brew install python@3.11

# Then exactly the same as above:
pip3 install -r requirements.txt
cp .env.example .env
python3 run.py --check
python3 run.py
```

To run it automatically on login (macOS):
1. Open **Automator** → New Document → **Application**
2. Add "Run Shell Script": `cd "/path/to/Trade Genie" && python3 run.py`
3. Save and add to **System Settings → Login Items**

---

## Disclaimer

Trade Genie is for **informational and research purposes only**. It does not constitute financial advice. Always conduct your own research and consider consulting a qualified financial advisor before making investment decisions. Past performance and predictive accuracy do not guarantee future results.
