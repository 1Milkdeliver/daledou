"""research/nine_palace_full.py — 九宫宝库完整领取（开棺循环 + 转盘循环）

流程循环：
  A. 宝库页：开 9 个石棺（drawbox index 0..8，记录每个结果）
  B. 退出宝库（quitbox）→ 轮盘页
  C. 转动轮盘（drawwheel）直到抽奖卡=0 或进宝库
  重复 A-C 直到剩余抽奖卡=0 且宝库已清

用法: uv run python research/nine_palace_full.py
"""
import asyncio
import json
import re
import sys
from datetime import datetime
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
    return int(m.group(1)) if m else -1


def in_vault(html: str) -> bool:
    return "drawbox" in html or "石棺" in html


async def main():
    cookies = Config.load_cookies()
    qq, cookie = next(iter(cookies.items()))
    results = []
    out = Path("log/nine_palace_results.json")

    async with Client(qq, cookie) as client:
        page = await client.get("cmd=lottery")
        for round_no in range(6):
            cards = remaining_cards(page)
            print(f"\n===== 第 {round_no+1} 轮 | 剩余卡: {cards} =====")

            # A) 开棺（若在宝库）
            if in_vault(page):
                for idx in range(9):
                    r = await client.get(f"cmd=lottery&op=drawbox&index={idx}")
                    t = text_of(r)
                    got = re.search(r"(?:获得|打开了|恭喜)([^<]{2,40})", t)
                    results.append({"round": round_no + 1, "box": idx,
                                    "result": got.group(1) if got else t[:50]})
                    print(f"  石棺{idx}: {got.group(1) if got else t[:60]}")
                    await asyncio.sleep(0.2)
                    # 开完后可能回轮盘页
                    page = r
                    if not in_vault(page):
                        break
                # 还在宝库就退出
                if in_vault(page):
                    page = await client.get("cmd=lottery&op=quitbox")
                    print(f"  退出宝库: {text_of(page)[:60]}")
            else:
                print("  当前不在宝库（轮盘页）")

            # B/C) 转动轮盘（若在轮盘页且有卡）
            cards = remaining_cards(page)
            if cards > 0 and not in_vault(page):
                page = await client.get("cmd=lottery&op=drawwheel")
                t = text_of(page)
                got = re.search(r"获得了：([^，。]{1,20})", t)
                results.append({"round": round_no + 1, "box": "wheel",
                                "result": got.group(1) if got else t[:60]})
                print(f"  转盘: {got.group(1) if got else t[:70]} | 剩余卡: {remaining_cards(page)}")
                await asyncio.sleep(0.3)
            else:
                print(f"  无卡可转或需先处理宝库（卡:{cards}）")
                if cards <= 0:
                    break

    out.write_text(json.dumps(
        {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
         "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n全部结果已保存: {out}")
    for r in results:
        print(f"  轮{r['round']} 箱{r['box']}: {r['result'][:50]}")


if __name__ == "__main__":
    asyncio.run(main())
