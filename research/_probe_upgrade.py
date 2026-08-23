"""探测：铁匠铺/星石合成/武器升级 的动作链接（只读）"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import src.tasks.register  # noqa: F401
from src.utils.config import Config
from src.utils.client import Client


def dump(client, label, cmd):
    html = asyncio.run(Client, None)  # placeholder
    return


async def main():
    cookies = Config.load_cookies()
    qq, cookie = next(iter(cookies.items()))
    async with Client(qq, cookie) as client:
        pages = [
            ("铁匠铺", "cmd=black_smith&op=0&type_id=0"),
            ("星盘", "cmd=astrolabe"),
            ("强化", "cmd=viewupdate"),
        ]
        for label, cmd in pages:
            html = await client.get(cmd)
            t = re.sub(r"<[^>]+>", "|", html)
            t = re.sub(r"[|\s]+", " ", t)
            print(f"\n===== {label} =====")
            print(f"文本: {t[:220]}")
            # 操作链接（排除导航）
            skip = ("返回", "商店", "兑换", "背包", "强化", "镶嵌", "经脉", "佣兵",
                    "武林", "规则", "帮助", "关闭", "攻略", "首页", "乐斗")
            print("动作链接:")
            for m in re.finditer(r'phonepk\?([^"\'<>]+)">([^<]{1,12})', html):
                q, n = m.group(1).replace("&amp;", "&"), m.group(2).strip()
                if n and not any(s in n for s in skip):
                    print(f"  {q[:95]} -> {n}")


asyncio.run(main())
