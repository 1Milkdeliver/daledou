@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
uv run main.py evening >> log\scheduler_evening.log 2>&1
