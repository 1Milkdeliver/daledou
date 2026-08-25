@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
uv run python research/daily_experiments.py >> log\scheduler_experiments.log 2>&1
