"""research/probe_entrances.py — 探测疑似免费活动入口（含执行领取）

目标入口：九宫宝库/幸运鹅/全民神器/全服限兑/福缘树仙/至尊传功/重出江湖/生日/神将领奖/帮战
流程：
  1. 从最新快照首页提取这些入口的完整 cmd 查询串
  2. 逐个抓取页面（只读第一步，先看内容）
  3. 页面若含"免费/点击领取"类链接则跟进执行（用户已授权）
  4. 记录每个入口: 页面内容 / 是否免费 / 领取结果

用法: uv run python research/probe_entrances.py
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

TARGETS = ["九宫宝库", "幸运鹅", "全民神器", "全服限兑", "福缘树仙",
           "至尊传功", "重出江湖", "生日", "神将领奖", "帮战"]


def text_of(html: str) -> str:
    t = re.sub(r"<[^>]+>", "|", html)
    t = re.sub(r"&nbsp;?", " ", t)
    return re.sub(r"[|\s]+", " ", t).strip()


def extract_target_links(index_html: str) -> dict[str, str]:
    """从首页提取目标入口的完整查询串"""
    links = {}
    for m in re.finditer(r'phonepk\?([^"\'<>]+)">([^<]{1,20})', index_html):
        q, t = m.group(1), m.group(2).strip()
        if t in TARGETS:
            links[t] = q.replace("&amp;", "&")
    return links


async def main():
    files = sorted(glob.glob(str(Path("log/snapshots") / "*.json")),
                   key=lambda p: Path(p).stat().st_mtime)
    data = json.loads(Path(files[-1]).read_text(encoding="utf-8"))
    qq = next(k for k in data if k != "_meta")
    index_html = data[qq]["pages"]["index"]["raw_html"]
    links = extract_target_links(index_html)
    print(f"从首页找到 {len(links)}/{len(TARGETS)} 个目标入口\n")

    cookies = Config.load_cookies()
    cookie = cookies[qq]
    out_dir = Path("log/entrance_probe")
    out_dir.mkdir(parents=True, exist_ok=True)

    async with Client(qq, cookie) as client:
        for name, q in links.items():
            html = await client.get(q)
            (out_dir / f"{name}.json").write_text(
                json.dumps({"name": name, "cmd": q, "raw_html": html,
                            "preview": text_of(html)}, ensure_ascii=False, indent=2),
                encoding="utf-8")
            t = text_of(html)
            # 检测页面里的操作链接
            actions = re.findall(r'phonepk\?([^"\'<>]+)">([^<]{1,16})', html)
            actions = [(a.replace("&amp;", "&"), b.strip()) for a, b in actions
                       if b.strip() not in ("返回", "返回上一页", "返回大乐斗首页")]
            print(f"=== {name} ({len(html)}B) ===")
            print(f"  页面: {t[:120]}")
            print(f"  操作链接: {[b for _, b in actions[:6]]}")
            print()
            await asyncio.sleep(0.1)

    print(f"页面已保存到 {out_dir}")


if __name__ == "__main__":
    asyncio.run(main())
