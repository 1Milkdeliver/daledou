@echo off
rem 重建全部定时任务（路径含空格，必须用 \" 转义，否则被劈开）
schtasks /Create /TN "daledou-update" /TR "\"D:\Deepseek Harness\daledou\update_run.bat\"" /SC DAILY /ST 09:00 /F
schtasks /Create /TN "daledou-experiments" /TR "\"D:\Deepseek Harness\daledou\run_experiments.bat\"" /SC DAILY /ST 13:00 /F
schtasks /Create /TN "daledou-noon" /TR "\"D:\Deepseek Harness\daledou\run_noon.bat\"" /SC DAILY /ST 13:05 /F
schtasks /Create /TN "daledou-evening" /TR "\"D:\Deepseek Harness\daledou\run_evening.bat\"" /SC DAILY /ST 20:05 /F
schtasks /Create /TN "daledou-snapshot" /TR "\"D:\Deepseek Harness\daledou\run_snapshot.bat\"" /SC DAILY /ST 22:00 /F
schtasks /Create /TN "daledou-snapshot6" /TR "\"D:\Deepseek Harness\daledou\run_snapshot6.bat\"" /SC DAILY /ST 06:05 /F
schtasks /Create /TN "daledou-battlereports" /TR "\"D:\Deepseek Harness\daledou\run_battlereports.bat\"" /SC DAILY /ST 14:30 /F
schtasks /Create /TN "daledou-monitor" /TR "\"D:\Deepseek Harness\daledou\run_monitor.bat\"" /SC MINUTE /MO 30 /F
