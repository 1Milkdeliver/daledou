"""research/claim_free_rewards.py — 执行已确认的免费领取（用户已授权）

1. 九宫宝库：转动轮盘（剩余 6 卡，免费）→ 拿钥匙
2. 重出江湖：查"领取礼包"是否免邀请可领（不发送好友邀请）
3. 幸运鹅：查看今日领取状态

用法: uv run python research/claim_free_rewards.py
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


def text_of(html: str) -> str:
    t = re.sub(r"<[^>]+>", "|", html)
    t = re.sub(r"&nbsp;?", " ", t)
    return re.sub(r"[|\s]+", " ", t).strip()


def find_links(html: str, keyword: str) -> list[str]:
    """找包含关键字的操作链接完整查询串"""
    out = []
    for m in re.finditer(r'phonepk\?([^"\'<>]+)">([^<]{1,16})', html):
        q, t = m.group(1).replace("&amp;", "&"), m.group(2).strip()
        if keyword in t:
            out.append(q)
    return out


async def main():
    cookies = Config.load_cookies()
    qq, cookie = next(iter(cookies.items()))
    probe_dir = Path("log/entrance_probe")
    out_dir = Path("log/claim_results")
    out_dir.mkdir(parents=True, exist_ok=True)

    def load_probe(name: str) -> str:
        f = probe_dir / f"{name}.json"
        return json.loads(f.read_text(encoding="utf-8"))["raw_html"] if f.exists() else ""

    async with Client(qq, cookie) as client:
        # ---- 1) 九宫宝库：转轮盘 ----
        print("=== 九宫宝库 ===")
        html = load_probe("九宫宝库")
        spin_links = find_links(html, "转动轮盘")
        print(f"转动轮盘链接: {spin_links[:2]}")
        for i, q in enumerate(spin_links[:6]):
            r = await client.get(q)
            t = text_of(r)
            print(f"  第{i+1}次转动: {t[:100]}")
            await asyncio.sleep(0.3)
            # 若转动后拿到钥匙，可能进宝库页有领取
            keys = re.findall(r'phonepk\?([^"\'<>]+)">([^<]{1,10})', r)
            for kq, kt in keys:
                if "宝库" in kt or "钥匙" in kt or "领取" in kt:
                    r2 = await client.get(kq.replace("&amp;", "&"))
                    print(f"    -> [{kt}]: {text_of(r2)[:100]}")
                    break

        # ---- 2) 重出江湖：查领取礼包 ----
        print("\n=== 重出江湖（领取礼包，不发送邀请）===")
        html = load_probe("重出江湖")
        claim_links = find_links(html, "领取礼包")
        print(f"领取礼包链接: {claim_links[:2]}")
        if claim_links:
            r = await client.get(claim_links[0])
            print(f"  领取结果: {text_of(r)[:120]}")
        else:
            print("  无领取礼包链接")

        # ---- 3) 幸运鹅状态 ----
        print("\n=== 幸运鹅（今日状态）===")
        html = load_probe("幸运鹅")
        claimed = "已领取" in text_of(html)
        print(f"  今日是否已领取: {claimed}")

    print("\n执行完成，结果见上（原始页面存 log/entrance_probe 与 log/claim_results）")


if __name__ == "__main__":
    asyncio.run(main())
