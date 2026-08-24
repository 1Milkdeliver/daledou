@echo off
rem 每小时活动监控任务（08:00-23:00，每日触发，一次性检查）
for %%H in (08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23) do (
  schtasks /Create /TN "daledou-monitor-%%H" /TR "\"D:\Deepseek Harness\daledou\run_monitor_once.bat\"" /SC DAILY /ST %%H:00 /F
)
