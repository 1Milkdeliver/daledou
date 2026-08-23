"""research/nine_palace_vault.py — 九宫宝库完整流程（开石棺 + 转盘）

1. 进宝库 → 打开 9 个石棺（找开棺链接）
2. 结束九宫抽奖 → 回轮盘 → 转动剩余抽奖卡
3. 循环直到抽奖卡用完

用法: uv run python research/nine_palace_vault.py
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


def all_links(html: str) -> list[tuple[str, str]]:
    out = []
    for m in re.finditer(r'phonepk\?([^"\'<>]+)">([^<]{1,16})', html):
        out.append((m.group(1).replace("&amp;", "&"), m.group(2).strip()))
    return out


async def main():
    cookies = Config.load_cookies()
    qq, cookie = next(iter(cookies.items()))

    async with Client(qq, cookie) as client:
        page = await client.get("cmd=lottery")
        print("=== 宝库页全部链接 ===")
        for q, t in all_links(page):
            print(f"  {q[:70]} -> {t}")

        # 尝试开石棺：找含"石棺"或 op 的链接
        open_links = [q for q, t in all_links(page) if "石棺" in t or "open" in q or "sarc" in q]
        print(f"\n疑似开棺链接: {open_links[:4]}")


if __name__ == "__main__":
    asyncio.run(main())
