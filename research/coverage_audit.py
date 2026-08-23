"""research/coverage_audit.py — 自动化覆盖缺口审计（只读文件分析）

对比: 首页全部入口链接 vs 已注册任务名
输出: 已覆盖 / 未覆盖入口清单 + 缺口分类

用法: uv run python research/coverage_audit.py
"""
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import src.tasks.register  # noqa: F401
from src.tasks.register import get_all_modules, get_module_tasks


def main():
    # 1) 已注册任务名
    registered = set()
    for m in get_all_modules():
        registered.update(get_module_tasks(m).keys())

    # 2) 首页全部入口（最新快照 index）
    files = sorted(glob.glob(str(Path("log/snapshots") / "*.json")),
                   key=lambda p: Path(p).stat().st_mtime)
    data = json.loads(Path(files[-1]).read_text(encoding="utf-8"))
    qq = next(k for k in data if k != "_meta")
    html = data[qq]["pages"]["index"]["raw_html"]
    links = {}
    for m in re.finditer(r'phonepk\?[^"\'<>]*cmd=([a-zA-Z0-9_]+)[^"\'<>]*">([^<]{1,20})', html):
        cmd, text = m.group(1), m.group(2).strip()
        if cmd not in ("index", "store", "viewshop"):
            links.setdefault(text, set()).add(cmd)

    # 3) 覆盖对比
    covered = {t for t in links if t in registered}
    uncovered = {t for t in links if t not in registered}

    print(f"已注册任务: {len(registered)} 个 | 首页入口: {len(links)} 个")
    print(f"覆盖: {len(covered)} 个 | 未覆盖: {len(uncovered)} 个\n")
    print("=== 未覆盖入口（可能遗漏的免费/活动入口）===")
    for t in sorted(uncovered):
        print(f"  {t}  ({','.join(sorted(links[t]))[:40]})")


if __name__ == "__main__":
    main()
