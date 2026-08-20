"""research/preview_pages.py — 查看最近快照各页面的纯文本预览

用法: uv run python research/preview_pages.py [页面名过滤]
"""
import glob
import json
import re
import sys
from pathlib import Path


def latest_snapshot() -> Path:
    """最新的正式快照（YYYY-MM-DD_HHMMSS.json，按修改时间）"""
    candidates = [
        Path(f) for f in glob.glob(str(Path("log/snapshots") / "*.json"))
    ]
    if not candidates:
        print("没有快照，先运行 research/snapshot.py")
        sys.exit(1)
    return max(candidates, key=lambda p: p.stat().st_mtime)


def main():
    keyword = sys.argv[1] if len(sys.argv) > 1 else None
    f = latest_snapshot()
    data = json.loads(f.read_text(encoding="utf-8"))
    print(f"最新快照: {f.name}")
    for qq, s in data.items():
        if qq == "_meta":
            continue
        for name, page in s["pages"].items():
            if keyword and keyword not in name:
                continue
            preview = page.get("preview", "")
            preview = re.sub(r"\s+", " ", preview).strip()
            print(f"\n[{name}] ({len(page['raw_html'])} 字节)")
            print(preview[:200])


if __name__ == "__main__":
    main()
