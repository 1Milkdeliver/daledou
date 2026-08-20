"""research/find_links.py — 列出最近快照首页的全部入口链接（cmd 参数 → 文本）

用法: uv run python research/find_links.py [关键词过滤]
"""
import glob
import json
import re
import sys
from pathlib import Path


def main():
    keyword = sys.argv[1] if len(sys.argv) > 1 else None
    files = sorted(glob.glob(str(Path("log/snapshots") / "*.json")))
    if not files:
        print("没有快照，先运行 research/snapshot.py")
        sys.exit(1)

    data = json.loads(Path(files[-1]).read_text(encoding="utf-8"))
    for qq, s in data.items():
        if qq == "_meta":
            continue
        h = s["pages"]["index"]["raw_html"]
        links = re.findall(r'cmd=([a-zA-Z0-9_]+)([^"\'<>]*)"?>([^<]{1,24})', h)
        print(f"=== 首页入口（快照 {Path(files[-1]).name}）共 {len(links)} 个 ===")
        for cmd, args, text in links:
            line = f"{cmd}{args[:40]} -> {text.strip()}"
            if keyword and keyword not in line:
                continue
            print(line)


if __name__ == "__main__":
    main()
