@echo off
cd /d "D:\Deepseek Harness\daledou"
set PYTHONIOENCODING=utf-8
"C:\Users\Huawei\AppData\Local\hermes\bin\uv.exe" run python research/monitor_daemon.py >> log\scheduler_monitor.log 2>&1
