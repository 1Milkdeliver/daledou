"""research/claim_nine_palace.py — 九宫宝库完整领取（剩余抽奖卡 + 寻宝）

流程：
  1. 重复转动轮盘直到抽奖卡用完（页面显示"剩余抽奖卡：N"）
  2. 转动后进宝库页 → 找"开始寻宝"并执行（消耗钥匙换宝物）

用法: uv run python research/claim_nine_palace.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import src.tasks.register  # noqa: F401
from src.utils.config import Config
from src.utils.client import Client


def text_of(html: str) -> str:
    t = re.sub(r"<[^>]+>", "|", html)
    t = re.sub(r"&nbsp;?", " ", t)
    return re.sub(r"[|\s]+", " ", t).strip()


def remaining_cards(html: str) -> int:
    m = re.search(r"剩余抽奖卡：(\d+)", html)
    return int(m.group(1)) if m else 0


def find_action(html: str, keyword: str) -> list[str]:
    out = []
    for m in re.finditer(r'phonepk\?([^"\'<>]+)">([^<]{1,16})', html):
        q, t = m.group(1).replace("&amp;", "&"), m.group(2).strip()
        if keyword in t:
            out.append(q)
    return out


async def main():
    cookies = Config.load_cookies()
    qq, cookie = next(iter(cookies.items()))

    async with Client(qq, cookie) as client:
        # 1) 转动轮盘直到卡用完
        for i in range(8):
            page = await client.get("cmd=lottery&op=drawwheel")
            t = text_of(page)
            cards = remaining_cards(page)
            if "获得了" in t:
                got = re.search(r"获得了：([^，。]{1,20})", t)
                print(f"  转动{i+1}: 获得 {got.group(1) if got else '?'} | 剩余卡:{cards}")
            elif "抽奖卡" in t and cards == 0:
                print(f"  转动{i+1}: 抽奖卡已用完")
                break
            else:
                print(f"  转动{i+1}: {t[:80]}")
            if cards == 0:
                break
            await asyncio.sleep(0.3)

        # 2) 寻宝（进宝库后用钥匙开宝物）
        page = await client.get("cmd=lottery")
        t = text_of(page)
        print(f"\n当前宝库页: {t[:150]}")
        hunt_links = find_action(page, "寻宝")
        print(f"寻宝链接: {hunt_links[:3]}")
        for q in hunt_links[:5]:
            r = await client.get(q)
            print(f"  寻宝: {text_of(r)[:100]}")
            await asyncio.sleep(0.3)


if __name__ == "__main__":
    asyncio.run(main())
