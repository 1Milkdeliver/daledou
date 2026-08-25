"""research/daily_experiments.py — 每日免费差分实验（自动积累社交/领取类前后差分）

每天 06:06 由定时任务触发（早于 06:10 的日常任务，紧贴服务器 06:00 每日刷新），
抢在每日重置后的第一次领取之前做"快照 → 领取 → 快照 → 差分"，
积累 Codex 要的"异步社交/每日领取前后差分"样本。

只包含免费、无消耗、每日一次的任务；日常任务稍后重跑时会命中
"已领取"守卫自动跳过，不影响每日产出。

用法: uv run python research/daily_experiments.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from research.experiment import take_snapshot, run_task
from research.diff import main as diff_main

REPO = Path(__file__).resolve().parent.parent

# 每日可做、免费、无消耗的领取/抽取类实验
DAILY_TASKS = [
    "noon.领取徒弟经验",  # 师徒贡献（异步社交归因）每日领取
    "noon.每日奖励",      # 每日登录奖励（固定产出）
    "noon.邪神秘宝",      # 免费抽取（概率分布样本）
]


def main():
    for task in DAILY_TASKS:
        print(f"\n========== 实验: {task} ==========")
        before = take_snapshot("daily_before")
        print(f"[执行] uv run main.py {task}")
        output = run_task(task)
        print(output[-600:])
        after = take_snapshot("daily_after")

        record = {
            "task": task,
            "kind": "daily-free",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "before": str(before),
            "after": str(after),
            "task_output": output,
        }
        out = REPO / "log" / "experiments" / datetime.now().strftime("%Y%m%d_%H%M%S.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"实验记录: {out}")

        print("\n--- 差分 ---")
        sys.argv = ["diff.py", str(before), str(after)]
        diff_main()


if __name__ == "__main__":
    main()
