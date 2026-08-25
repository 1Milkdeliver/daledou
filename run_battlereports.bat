@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
uv run python research/battle_reports.py >> log\scheduler_battlereports.log 2>&1
