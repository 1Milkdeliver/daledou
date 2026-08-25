@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
uv run main.py noon >> log\scheduler_noon.log 2>&1
