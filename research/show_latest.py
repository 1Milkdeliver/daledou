"""research/show_latest.py — 查看最近一次快照的摘要（角色属性 + 今日可做清单）

用法: uv run python research/show_latest.py
"""
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    files = sorted(glob.glob(str(Path("log/snapshots") / "*.json")))
    if not files:
        print("没有快照，先运行 research/snapshot.py")
        sys.exit(1)

    data = json.loads(Path(files[-1]).read_text(encoding="utf-8"))
    print(f"最新快照: {files[-1]}")
    for qq, s in data.items():
        if qq == "_meta":
            continue
        print(f"=== 账号 {qq} ===")
        print(f"角色: {s['character']}")
        for module, tasks in s["available_tasks"].items():
            print(f"[{module}] 今日可做 {len(tasks)} 个:")
            for t in tasks:
                print(f"    - {t}")


if __name__ == "__main__":
    main()
