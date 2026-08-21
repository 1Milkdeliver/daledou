"""research/one_shot_capture.py — 一次性只读抓取（A组研究）

目标：把常规快照没覆盖的完整数据抓齐（全部只读，无游戏操作）：
  1. 完整背包（18 页，直到内容重复为止）
  2. 商店全部页签（自动发现页签链接并抓取）
  3. 排行榜全部子榜（自动发现分榜链接并抓取）
  4. 徽章加成页、成就封赏页（从徽章/成就页发现的链接）

输出: log/one_shot/<时间戳>/ 下每个页面一个 JSON（raw_html + preview）

用法: uv run python research/one_shot_capture.py
"""
import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import src.tasks.register  # noqa: F401
from src.utils.config import Config
from src.utils.client import Client


def text_of(html: str) -> str:
    t = re.sub(r"<[^>]+>", "|", html)
    t = re.sub(r"&nbsp;?", " ", t)
    return re.sub(r"[|\s]+", " ", t).strip()[:150]


def extract_links(html: str) -> list[tuple[str, str]]:
    """提取页面内 (cmd查询串, 链接文本)，已反转义"""
    links = []
    for m in re.finditer(r'phonepk\?([^"\'<>]+)">([^<]{1,20})', html):
        q = m.group(1).replace("&amp;", "&")
        if "cmd=" in q:
            links.append((q, m.group(2).strip()))
    return links


async def main():
    cookies = Config.load_cookies()
    qq, cookie = next(iter(cookies.items()))
    out_dir = Path("log/one_shot") / datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    def save(name: str, cmd: str, html: str):
        (out_dir / f"{name}.json").write_text(
            json.dumps({"name": name, "cmd": cmd, "raw_html": html,
                        "preview": text_of(html)}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        saved.append(name)

    async with Client(qq, cookie) as client:
        # 1) 完整背包：逐页抓，内容重复即停
        print("[1/4] 完整背包 ...")
        prev = ""
        for page in range(1, 25):
            html = await client.get(f"cmd=store&page={page}")
            if html == prev or "很抱歉" in html:
                break
            save(f"bag_page{page:02d}", f"cmd=store&page={page}", html)
            prev = html
            await asyncio.sleep(0.1)
        print(f"    抓取 {len([s for s in saved if s.startswith('bag_page')])} 页")

        # 2) 商店页签
        print("[2/4] 商店页签 ...")
        shop_main = await client.get("cmd=viewshop&type=3&shop=1&page=1")
        save("shop_main", "cmd=viewshop&type=3&shop=1&page=1", shop_main)
        tabs = [(q, t) for q, t in extract_links(shop_main) if "viewshop" in q]
        seen = set()
        for q, t in tabs:
            if q in seen:
                continue
            seen.add(q)
            html = await client.get(q)
            save(f"shop_tab_{t[:8]}", q, html)
            await asyncio.sleep(0.1)
        print(f"    抓取 {len(seen)} 个页签")

        # 3) 排行榜子榜
        print("[3/4] 排行榜子榜 ...")
        rank_main = await client.get("cmd=perrank&sev=-1")
        save("rank_main", "cmd=perrank&sev=-1", rank_main)
        rank_links = [(q, t) for q, t in extract_links(rank_main) if "perrank" in q]
        seen = set()
        for q, t in rank_links:
            if q in seen:
                continue
            seen.add(q)
            html = await client.get(q)
            save(f"rank_{t[:8]}", q, html)
            await asyncio.sleep(0.1)
        print(f"    抓取 {len(seen)} 个子榜")

        # 4) 徽章加成 / 成就封赏
        print("[4/4] 徽章加成 + 成就封赏 ...")
        badge_html = await client.get("cmd=achievement")
        glory_html = await client.get("cmd=glory")
        for q, t in extract_links(badge_html) + extract_links(glory_html):
            if "加成" in t or "封赏" in t or "规则" in t:
                html = await client.get(q)
                save(f"extra_{t[:10]}", q, html)
                await asyncio.sleep(0.1)

    print(f"\n完成！共抓取 {len(saved)} 个页面 → {out_dir}")
    print("页面清单:", ", ".join(saved))


if __name__ == "__main__":
    asyncio.run(main())
