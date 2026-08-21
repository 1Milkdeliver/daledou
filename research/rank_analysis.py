"""research/rank_analysis.py — 排行榜数据挖掘（第一档·1）

步骤:
  1. 列出 rank_main 的全部链接（找真正的 Top-N 榜单接口）
  2. 若找到榜单接口则抓取并解析玩家条目
  3. 输出全服数值分布/天花板

用法: uv run python research/rank_analysis.py
"""
import asyncio
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import src.tasks.register  # noqa: F401
from src.utils.config import Config
from src.utils.client import Client


def load_one_shot(name: str) -> str:
    files = glob.glob(str(Path("log/one_shot") / "*" / f"{name}.json"))
    return json.loads(Path(files[-1]).read_text(encoding="utf-8"))["raw_html"] if files else ""


def dump_links(html: str) -> list[tuple[str, str]]:
    out = []
    for m in re.finditer(r'phonepk\?([^"\'<>]+)">([^<]{1,20})', html):
        q = m.group(1).replace("&amp;", "&")
        out.append((q, m.group(2).strip()))
    return out


def parse_players(html: str) -> list[dict]:
    """解析榜单玩家条目（兼容两种格式）"""
    t = re.sub(r"<[^>]+>", "|", html)
    t = re.sub(r"[|\s]+", " ", t)
    players = []
    # 格式1（等级/战力类）: "1 名字 255级 经验113518147"
    for m in re.finditer(
        r"(\d+)\s*([\u4e00-\u9fa5A-Za-z0-9·_\*]{1,16}?)\s*(\d+)级\s*([^\s]{1,6})([\d,]+)", t):
        players.append({"rank": int(m.group(1)), "name": m.group(2),
                        "level": int(m.group(3)), "metric": m.group(4),
                        "value": int(m.group(5).replace(",", ""))})
    if players:
        return players
    # 格式2（数值类）: "1 名字 12345"
    for m in re.finditer(
        r"(\d+)\s*([\u4e00-\u9fa5A-Za-z0-9·_\*]{2,16}?)\s*([\d,]+)", t):
        players.append({"rank": int(m.group(1)), "name": m.group(2),
                        "value": int(m.group(3).replace(",", ""))})
    return players


RANK_ENDPOINTS = [
    ("等级榜", "cmd=viewrank&sev=0&page=1"),
    ("财富榜", "cmd=viewdoudourank&page=1&sev=0"),
    ("荣誉榜", "cmd=honorrank&sev=0"),
    ("义气度榜", "cmd=brotherrank&sev=0"),
    ("斗神塔榜", "cmd=towerrank&sev=0"),
    ("帮派榜", "cmd=viewfacrank&type=0&page=1&sev=0"),
]


async def main():
    html = load_one_shot("rank_main")
    links = dump_links(html)
    print(f"=== rank_main 共 {len(links)} 个链接 ===")

    out_dir = Path("log/one_shot") / "rank_lists"
    summary = {}

    # 直接重解析已抓取的榜单页面
    for f in sorted((out_dir).glob("*.json")):
        if f.name == "_summary.json":
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        players = parse_players(d["raw_html"])
        if players:
            vals = [p.get("value", p.get("level", 0)) for p in players]
            summary[d["name"]] = {
                "top": players[0], "count": len(players),
                "max": max(vals), "min": min(vals), "top5": players[:5],
            }
            print(f"\n[{d['name']}] {len(players)} 名 | 值域 {min(vals)}~{max(vals)}")
            for p in players[:5]:
                extra = f" Lv{p.get('level','-')}" if "level" in p else ""
                print(f"  #{p['rank']} {p['name']}{extra} {p.get('metric','')}{p.get('value','')}")

    (out_dir / "_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n汇总 → {out_dir / '_summary.json'}")


if __name__ == "__main__":
    asyncio.run(main())
