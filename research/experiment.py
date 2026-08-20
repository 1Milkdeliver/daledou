"""research/experiment.py — 差分实验记录器

用法:
    uv run python research/experiment.py <模块.任务> [--out 目录]

流程（对应 Codex 研究方案第 4 步“前后快照差分”）:
    1. 快照 before（只读）
    2. 执行指定任务（会真实操作游戏，注意选择免费/无消耗的任务）
    3. 快照 after（只读）
    4. 自动 diff，输出 输入->输出 记录到 JSON 和 console

示例:
    uv run python research/experiment.py noon.邪神秘宝
"""
import asyncio
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from research.snapshot import fetch_all, main as snapshot_main  # noqa: F401
from research.diff import main as diff_main

REPO = Path(__file__).resolve().parent.parent


def take_snapshot(tag: str) -> Path:
    """返回本次快照文件路径"""
    out = REPO / "log" / "snapshots" / f"{tag}_{datetime.now().strftime('%H%M%S')}.json"
    sys.argv = ["snapshot.py", "--out", str(out)]
    snapshot_main()
    return out


def run_task(arg: str) -> str:
    """执行 uv run main.py <arg>，返回输出"""
    result = subprocess.run(
        ["uv", "run", "main.py", arg],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    return result.stdout + result.stderr


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    task_arg = sys.argv[1]

    print(f"[1/3] 快照 before ...")
    before = take_snapshot("before")

    print(f"[2/3] 执行任务: uv run main.py {task_arg}")
    output = run_task(task_arg)
    print(output[-2000:])

    print(f"[3/3] 快照 after + diff ...")
    after = take_snapshot("after")

    # 保存实验记录
    record = {
        "task": task_arg,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "before": str(before),
        "after": str(after),
        "task_output": output,
    }
    record_path = REPO / "log" / "experiments" / datetime.now().strftime("%Y%m%d_%H%M%S.json")
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"实验记录: {record_path}")

    print("\n========== 差分结果 ==========")
    sys.argv = ["diff.py", str(before), str(after)]
    diff_main()


if __name__ == "__main__":
    main()
