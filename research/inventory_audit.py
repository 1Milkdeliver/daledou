"""research/inventory_audit.py — 背包全量盘点（只读文件分析）

解析 one_shot 抓取的完整背包（18 页），输出全部物品+数量+分类。

用法: uv run python research/inventory_audit.py
"""
import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def parse_bag(html: str) -> list[dict]:
    t = re.sub(r"<[^>]+>", "|", html)
    t = re.sub(r"&nbsp;?", " ", t)
    t = re.sub(r"[|\s]+", " ", t)
    items = []
    for m in re.finditer(r"([\u4e00-\u9fa5A-Za-z0-9·（）(\)\-]{2,24}?)\s*数量：(\d+)", t):
        items.append({"name": m.group(1).strip(), "qty": int(m.group(2))})
    return items


def main():
    files = sorted(glob.glob(str(Path("log/one_shot") / "*" / "bag_page*.json")))
    if not files:
        print("没有背包快照，先跑 one_shot_capture.py")
        sys.exit(1)

    total = Counter()
    for f in files:
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        for it in parse_bag(d.get("raw_html", "")):
            total[it["name"]] += it["qty"]

    print(f"=== 背包全量盘点（{len(files)} 页, {len(total)} 种物品）===")
    for name, qty in total.most_common():
        print(f"  {qty:>6} × {name}")

    out = Path("log/inventory_full.json")
    out.write_text(json.dumps(dict(total), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已保存: {out}")


if __name__ == "__main__":
    main()
