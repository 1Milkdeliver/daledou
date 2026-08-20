@echo off
cd /d "D:\Deepseek Harness\daledou"
set PYTHONIOENCODING=utf-8
"C:\Users\Huawei\AppData\Local\hermes\bin\uv.exe" run main.py evening >> log\scheduler_evening.log 2>&1
