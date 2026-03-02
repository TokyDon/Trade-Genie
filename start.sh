#!/bin/bash
# Trade Genie - Auto-start script for macOS launchd
# This file is called by the LaunchAgent plist on login/boot.

# Resolve the project directory (this script lives in the repo root)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Start Trade Genie (web dashboard + built-in daily/weekly scheduler)
exec python3 run.py >> "$SCRIPT_DIR/data/launch.log" 2>&1
