"""research/battle_reports.py — 战报样本归档（每天一条完整战报，只读）

流程：
  1. 抓 乐斗记录（cmd=info）
  2. 选一条：优先含"历练 BOSS"关键词（默认 宋姜，来自配置 历练 6114）的同类型战报，
     否则取第一条带"查看乐斗过程"的记录
  3. 抓完整战报（cmd=viewfight...）
  4. 解析回合，存档 log/battle_reports/YYYY-MM-DD.json

用途：为 Codex 的"同类战斗不同构筑 ×3 份完整战报"积累样本（每天 1 条）。

用法: uv run python research/battle_reports.py
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

# 优先匹配的"同类型"战斗关键词（历练 BOSS 名，来自 config default.yaml 的 历练 配置）
PREFER_KEYWORDS = ["宋姜", "大鹏"]


def text_of(html: str) -> str:
    t = re.sub(r"<[^>]+>", "|", html)
    t = re.sub(r"&nbsp;?", " ", t)
    return re.sub(r"[|\s]+", " ", t).strip()


def parse_records(html: str) -> list[dict]:
    """解析乐斗记录：序号 + 结果文本 + 完整 viewfight 查询串（含 zapp_uin/sid 前缀）"""
    records = []
    for m in re.finditer(
        r'(\d+):(.*?)(?:phonepk\?([^"\'<>]+)">查看乐斗过程|\s*<br\s*/?>|$)',
        html, re.DOTALL,
    ):
        text = re.sub(r"<[^>]+>", "", m.group(2))
        text = re.sub(r"\s+", " ", text).strip()
        vf = (m.group(3) or "").replace("&amp;", "&")
        records.append({"seq": m.group(1), "text": text, "viewfight": vf})
    return [r for r in records if r["viewfight"]]


def parse_rounds(detail_html: str) -> list[dict]:
    """从完整战报解析回合"""
    t = text_of(detail_html)
    rounds = []
    for m in re.finditer(r"回合(\d+)[：:](.*?)(?=回合\d+[：:]|$)", t):
        rounds.append({"round": int(m.group(1)), "desc": m.group(2).strip()[:160]})
    return rounds


async def main():
    cookies = Config.load_cookies()
    qq, cookie = next(iter(cookies.items()))
    out_dir = Path("log/battle_reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    async with Client(qq, cookie) as client:
        info_html = await client.get("cmd=info")
        records = parse_records(info_html)
        if not records:
            print("乐斗记录里没有可查看的战报（今天还没打过架？）")
            return

        # 优先同类型（历练 BOSS），否则第一条
        picked = None
        for kw in PREFER_KEYWORDS:
            for r in records:
                if kw in r["text"]:
                    picked = r
                    break
            if picked:
                break
        if not picked:
            picked = records[0]

        detail_html = await client.get(picked["viewfight"])
        rounds = parse_rounds(detail_html)
        scene = re.search(r"战斗场景：([^ <]+)", text_of(detail_html))
        participants = re.search(r"参战角色：([^ <]+)", text_of(detail_html))

        record = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "record_text": picked["text"],
            "battle_id": picked["viewfight"],
            "scene": scene.group(1) if scene else "",
            "participants": participants.group(1) if participants else "",
            "rounds": rounds,
            "raw_detail_html": detail_html,
        }
        out = out_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"战报已归档: {out}")
        print(f"  场景: {record['scene']} | 参战: {record['participants']}")
        print(f"  回合数: {len(rounds)}")
        print(f"  记录: {record['record_text'][:60]}")
        if rounds:
            print(f"  首回合: {rounds[0]['desc'][:70]}")


if __name__ == "__main__":
    asyncio.run(main())
