@echo off
cd /d "D:\Deepseek Harness\daledou"
set PYTHONIOENCODING=utf-8
"C:\Users\Huawei\AppData\Local\hermes\bin\uv.exe" run python research/battle_reports.py >> log\scheduler_battlereports.log 2>&1
