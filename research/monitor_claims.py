"""research/monitor_claims.py — 活动监控 + 随时领取

每 30 分钟由定时任务执行：
  1. 抓首页 → 提取全部活动入口（今日可做地图）
  2. 与上次对比 → 记录活动 上新/下架（写 log/activity_monitor.log + 状态）
  3. 08:00~23:00 内：对免费可领任务逐个执行（已领取守卫自动跳过，安全）
     —— 覆盖"活动到点解锁/每日刷新后随时可领"的场景

用法: uv run python research/monitor_claims.py
"""
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import src.tasks.register  # noqa: F401
from src.utils.config import Config
from src.utils.client import Client

REPO = Path(__file__).resolve().parent.parent
STATE = REPO / "log" / "activity_state.json"
LOG = REPO / "log" / "activity_monitor.log"

# 免费可领任务（含守卫，重复执行安全）
CLAIM_TASKS = [
    "noon.幸运鹅",
    "noon.九宫宝库",
    "noon.今日活跃度",
    "evening.登录有礼",
    "evening.周周礼包",
    "evening.乐斗驿站",
    "evening.幸运转盘",
    "evening.大笨钟",
    "evening.幸运金蛋",
]


def log(msg: str):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} | {msg}"
    print(line)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def entry_map(html: str) -> list[str]:
    """首页活动入口（仅 phonepk 链接的文本，避免数值/属性噪声）"""
    return sorted({m.group(1).strip() for m in
                   re.finditer(r'phonepk\?[^"\'<>]+">([^<]{1,20})', html)
                   if m.group(1).strip()})


def main():
    cookies = Config.load_cookies()
    if not cookies:
        log("无 cookie")
        return
    qq, cookie = next(iter(cookies.items()))
    hour = datetime.now().hour

    # 1) 抓首页
    try:
        import asyncio
        from src.utils.daledou import DaLeDou  # noqa

        async def fetch():
            async with Client(qq, cookie) as client:
                return await client.get("cmd=index&style=1")
        html = asyncio.run(fetch())
    except Exception as e:
        log(f"首页抓取失败: {e}")
        return

    current = entry_map(html)
    previous = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else []
    if current != previous:
        new = [e for e in current if e not in previous]
        gone = [e for e in previous if e not in current]
        if new:
            log(f"活动上新: {new}")
        if gone:
            log(f"活动下架: {gone}")
        STATE.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        log(f"入口无变化（{len(current)} 个）")

    # 2) 08:00~23:00 内执行免费领取
    if not (8 <= hour < 23):
        log(f"当前 {hour} 点，跳过领取（仅监控）")
        return

    for task in CLAIM_TASKS:
        module, name = task.split(".", 1)
        if f">{name}<" not in html:
            continue  # 入口不在首页，跳过
        try:
            r = subprocess.run(
                ["uv", "run", "main.py", task], cwd=str(REPO),
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=180)
            tail = (r.stdout + r.stderr).strip().splitlines()
            last = [l for l in tail if "|" in l][-1:] or ["(无输出)"]
            log(f"领取[{task}]: {last[0][:100]}")
        except Exception as e:
            log(f"领取[{task}]异常: {e}")


if __name__ == "__main__":
    main()
