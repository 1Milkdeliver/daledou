@echo off
cd /d "D:\Deepseek Harness\daledou"
set PYTHONIOENCODING=utf-8
"C:\Users\Huawei\AppData\Local\hermes\bin\uv.exe" run python research/snapshot.py >> log\scheduler_snapshot6.log 2>&1
