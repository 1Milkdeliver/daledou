"""research/daily_output_summary.py — 单日运行产出统计（只读日志分析）

从最近一天账号日志统计：参加了哪些任务（活动）+ 每个的产出行。

用法: uv run python research/daily_output_summary.py [日期]
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else ""
    logs = sorted((REPO / "log/1206423023").glob("*.log"))
    if date:
        logs = [f for f in logs if date in f.name]
    if not logs:
        print("没有日志")
        sys.exit(1)
    f = logs[-1]

    tasks = defaultdict(list)
    order = []
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        line = re.sub(r"^\d{2}:\d{2}:\d{2}\s*\|\s*", "", line).strip()
        if not line or "运行耗时" in line or "Traceback" in line:
            continue
        # 行格式: 任务名：内容
        m = re.match(r"^([^：]{1,10})：(.{1,120})$", line)
        if m:
            task, content = m.group(1), m.group(2)
            if task not in tasks:
                order.append(task)
            tasks[task].append(content)

    print(f"=== {f.name} 每日活动与产出统计 ===")
    print(f"参与任务数: {len(order)}")
    for t in order:
        lines = tasks[t]
        # 产出行 = 含 恭喜/获得/领取/成功/战胜
        rewards = [l for l in lines if re.search(r"恭喜|获得|领取|成功|战胜|兑换", l)]
        print(f"\n[{t}] 共{len(lines)}行, 产出{len(rewards)}行")
        for r in rewards[:4]:
            print(f"    {r[:80]}")
        if len(rewards) > 4:
            print(f"    ... 等 {len(rewards)} 条")


if __name__ == "__main__":
    main()
