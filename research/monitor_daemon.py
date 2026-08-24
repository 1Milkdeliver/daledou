"""research/monitor_daemon.py — 活动监控常驻守护

每日 08:00 由定时任务启动，内部每 30 分钟执行一次 monitor_claims 检查：
活动上新/下架记录 + 免费活动领取。运行至次日 08:00 被新实例接管
（MultipleInstances IgnoreNew 保证不重复）。

用法: uv run python research/monitor_daemon.py
"""
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 小时窗口：8~23 点领取，其余时段仅监控
CHECK_INTERVAL = 30 * 60  # 30 分钟


def main():
    from research.monitor_claims import main as check

    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} | 监控守护启动（每 {CHECK_INTERVAL//60} 分钟检查）")
    while True:
        try:
            check()
        except Exception as e:
            print(f"{datetime.now():%Y-%m-%d %H:%M:%S} | 检查异常: {e}")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
