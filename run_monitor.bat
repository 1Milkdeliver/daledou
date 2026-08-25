@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
uv run python research/monitor_claims.py >> log\scheduler_monitor.log 2>&1
