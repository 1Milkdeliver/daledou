"""research/diff.py — 快照差分对比

用法:
    uv run python research/diff.py <快照A.json> <快照B.json>

对比两个快照: 角色属性变化、今日可做任务入口变化、各页面 HTML 变化摘要。
用于“行动前后差分实验”和“每日状态变化”研究。
"""
import json
import re
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def html_changes(before: str, after: str) -> list[str]:
    """提取两个 HTML 之间变化的文本行（去掉标签后对比）"""
    def lines(html: str) -> list[str]:
        text = re.sub(r"<[^>]+>", "|", html)
        return [l.strip() for l in text.split("|") if l.strip()]

    b, a = lines(before), lines(after)
    removed, added = [], []
    for l in b:
        if l not in a:
            removed.append(l)
    for l in a:
        if l not in b:
            added.append(l)
    # 去重并截断
    return removed[:20], added[:20]


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    b, a = load(sys.argv[1]), load(sys.argv[2])

    for qq in [k for k in b if k != "_meta"]:
        if qq not in a:
            print(f"账号 {qq} 只存在于快照A")
            continue
        print(f"=== 账号 {qq} ===")
        cb, ca = b[qq]["character"], a[qq]["character"]
        if cb != ca:
            print(f"角色属性变化: {cb} -> {ca}")
        else:
            print("角色属性: 无变化")

        for module in b[qq]["available_tasks"]:
            tb = set(b[qq]["available_tasks"][module])
            ta = set(a[qq]["available_tasks"][module])
            if tb != ta:
                print(f"[{module}] 入口变化: +{sorted(ta - tb)} -{sorted(tb - ta)}")
        if all(
            set(b[qq]["available_tasks"][m]) == set(a[qq]["available_tasks"][m])
            for m in b[qq]["available_tasks"]
        ):
            print("任务入口: 无变化")

        for name in b[qq]["pages"]:
            if name == "index":
                continue
            before_html = b[qq]["pages"][name]["raw_html"]
            after_html = a[qq]["pages"][name]["raw_html"]
            if before_html == after_html:
                continue
            removed, added = html_changes(before_html, after_html)
            print(f"[{name}] 页面变化: 移除 {len(removed)} 条 / 新增 {len(added)} 条")
            for l in removed[:8]:
                print(f"    - {l[:80]}")
            for l in added[:8]:
                print(f"    + {l[:80]}")


if __name__ == "__main__":
    main()
