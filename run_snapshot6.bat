@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
uv run python research/snapshot.py >> log\scheduler_snapshot6.log 2>&1
