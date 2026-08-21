"""research/shop_analysis.py — 商店定价全表分析（第一档·2）

解析 one_shot 抓到的 shop_main + shop_tab_* 页面:
  物品名 / 价格 / 货币（鹅币/斗豆） / 页签分类
输出: log/shop_prices.json + 控制台统计

用法: uv run python research/shop_analysis.py
"""
import glob
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


def parse_items(html: str, tab: str) -> list[dict]:
    """物品条目: 名称 + 价格/单价 + 货币"""
    t = re.sub(r"<[^>]+>", "|", html)
    t = re.sub(r"&nbsp;?", " ", t)
    t = re.sub(r"[|\s]+", " ", t)
    items = []
    for m in re.finditer(
        r"([\u4e00-\u9fa5A-Za-z0-9·\-]{2,20}?)\s*([\d.]+)/([\d.]+)\s*鹅币", t):
        items.append({"name": m.group(1).strip(), "price": float(m.group(2)),
                      "unit": float(m.group(3)), "currency": "鹅币", "tab": tab})
    for m in re.finditer(
        r"([\u4e00-\u9fa5A-Za-z0-9·\-]{2,20}?)\s*([\d.]+)/([\d.]+)\s*斗豆", t):
        items.append({"name": m.group(1).strip(), "price": float(m.group(2)),
                      "unit": float(m.group(3)), "currency": "斗豆", "tab": tab})
    return items


def main():
    all_items = []
    for f in sorted(glob.glob(str(Path("log/one_shot") / "*" / "shop*.json"))):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        tab = d["name"].replace("shop_tab_", "").replace("shop_main", "主页")
        all_items += parse_items(d["raw_html"], tab)

    # 去重（同物品同价）
    seen = set()
    unique = []
    for it in all_items:
        key = (it["name"], it["price"], it["currency"])
        if key not in seen:
            seen.add(key)
            unique.append(it)

    out = Path("log/shop_prices.json")
    out.write_text(json.dumps(unique, ensure_ascii=False, indent=2), encoding="utf-8")

    prices = [i["price"] for i in unique if i["currency"] == "鹅币"]
    print(f"解析到 {len(unique)} 种商品（鹅币 {len(prices)} 件）")
    print(f"鹅币价格区间: {min(prices) if prices else '-'} ~ {max(prices) if prices else '-'}")
    print("\n按页签分布:")
    by_tab = Counter(i["tab"] for i in unique)
    for tab, c in by_tab.most_common():
        print(f"  {tab}: {c} 件")

    print("\n价格分层（鹅币）:")
    buckets = defaultdict(int)
    for p in prices:
        if p < 1:
            buckets["<1"] += 1
        elif p < 10:
            buckets["1-10"] += 1
        elif p < 50:
            buckets["10-50"] += 1
        elif p < 100:
            buckets["50-100"] += 1
        else:
            buckets[">100"] += 1
    for k in sorted(buckets):
        print(f"  {k}: {buckets[k]} 件")

    print("\n最贵 10 件:")
    for i in sorted(unique, key=lambda x: -x["price"])[:10]:
        print(f"  {i['name']} {i['price']}{i['currency']} [{i['tab']}]")

    print(f"\n已保存: {out}")


if __name__ == "__main__":
    main()
