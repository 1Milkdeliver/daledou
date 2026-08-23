"""research/daily_gain_quantify.py — 单日资源获得量化（日志求和）"""
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

    gains = defaultdict(int)
    items = defaultdict(int)
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        line = re.sub(r"^\d{2}:\d{2}:\d{2}\s*\|\s*", "", line).strip()
        # 数值类: 经验值/阅历/积分/斗币/门贡/威望/深渊积分
        for key, pat in [
            ("经验值", r"(\d+)点经验值"),
            ("阅历", r"获得(\d+)点阅历"),
            ("经验", r"获得(\d+)点经验"),
            ("积分", r"积分[^*]*?(\d+)"),
            ("竞技点", r"竞技点数(\d+)"),
            ("门贡", r"门贡\*?(\d+)"),
            ("威望", r"(\d+)点威望"),
            ("许愿点", r"(\d+)许愿点"),
            ("深渊积分", r"(\d+)深渊积分"),
            ("斗币", r"斗币\*(\d+)"),
            ("斗灵石", r"斗灵石[^\d]*(\d+)"),
        ]:
            for m in re.finditer(pat, line):
                gains[key] += int(m.group(1))
        # 物品: 获得/掉落 X（量词前）
        for m in re.finditer(r"获得([\u4e00-\u9fa5A-Za-z·]+?)\*(\d+)", line):
            items[m.group(1)] += int(m.group(2))
        for m in re.finditer(r"获得([\u4e00-\u9fa5A-Za-z·]+?)(?:\*1)?。", line):
            pass  # 单个物品略

    print(f"=== {f.name} 单日数值获得（近似求和）===")
    for k in sorted(gains):
        print(f"  {k}: {gains[k]}")
    print("\n=== 道具获得 TOP15 ===")
    for k, v in sorted(items.items(), key=lambda x: -x[1])[:15]:
        print(f"  {v} × {k}")


if __name__ == "__main__":
    main()
