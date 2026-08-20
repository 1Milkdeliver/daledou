@echo off
cd /d "D:\Deepseek Harness\daledou"
set PYTHONIOENCODING=utf-8
"C:\Users\Huawei\AppData\Local\hermes\bin\uv.exe" run python research/daily_experiments.py >> log\scheduler_experiments.log 2>&1
