"""research/battle_reports.py — 战报样本归档（每日最多 3 条，只读归档）

原则：只归档【已经发生】的战报，绝不为采样触发任何战斗。

流程：
  1. 抓 乐斗记录（cmd=info，只读）
  2. 把已有记录分类：历练 / 斗神塔 / 好友BOSS / 其他
  3. 每类最多取 1 条，抓其完整战报（cmd=viewfight...，只读）
  4. 存档 log/battle_reports/YYYY-MM-DD_类型.json（每天最多 3 条）

类型关键词（来自实测日志与配置）：
  历练:  宋姜/大鹏/马大王/凶尸/虾兵头目/夜叉元帅/霹雳头领/嗜血鬼王/象仙
  斗神塔: 山贼/强盗/荷官/海盗/镖师/蛤蟆/狐狸精/树精/花妖/黑熊
  好友:  金毛鹅王/乐斗程管/俊猴王/月敏妹妹/斗神幻像/乐斗剑君/乐斗菜菜/
         新手小王子/羊魔王/乐斗教主/乐斗帅帅/乐斗姜公/乐斗月璇/乐斗源大侠/马大师

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

TYPE_KEYWORDS = {
    "历练": ["宋姜", "大鹏", "马大王", "凶尸", "虾兵头目", "夜叉元帅",
            "霹雳头领", "嗜血鬼王", "象仙", "历练"],
    "斗神塔": ["山贼", "强盗", "荷官", "海盗", "镖师", "蛤蟆", "狐狸精",
              "树精", "花妖", "黑熊", "斗神塔"],
    "好友": ["金毛鹅王", "乐斗程管", "俊猴王", "月敏妹妹", "斗神幻像",
            "乐斗剑君", "乐斗菜菜", "新手小王子", "羊魔王", "乐斗教主",
            "乐斗帅帅", "乐斗姜公", "乐斗月璇", "乐斗源大侠", "马大师",
            "好友", "侠侣"],
    "仙武修真": ["寻仙", "问道", "连儿", "帝释天", "张三丰"],
    "副本": ["江湖长梦", "深渊", "异兽", "迷阵", "遗迹", "画卷"],
}


def extract_opponent(text: str) -> str:
    """从战报文本提取对手名（用于"其他"类标签）"""
    for pat in (r"(?:挑战|干掉|与|对战)([\u4e00-\u9fa5A-Za-z0-9·★]{1,10})",
                r"BOSS([\u4e00-\u9fa5A-Za-z0-9·★]{1,10})"):
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return "未知名"


def text_of(html: str) -> str:
    t = re.sub(r"<[^>]+>", "|", html)
    t = re.sub(r"&nbsp;?", " ", t)
    return re.sub(r"[|\s]+", " ", t).strip()


def parse_records(html: str) -> list[dict]:
    """解析乐斗记录：序号 + 结果文本 + 完整 viewfight 查询串"""
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


def classify(text: str) -> str:
    """按关键词给战报分类（返回 历练/斗神塔/好友/其他）"""
    for t, kws in TYPE_KEYWORDS.items():
        if any(k in text for k in kws):
            return t
    return "其他"


def parse_rounds(detail_html: str) -> list[dict]:
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
            print("乐斗记录里没有可查看的战报（今天还没有战斗发生，不触发）")
            return

        # 每类最多取 1 条（只归档已发生的）
        picked = {}
        for r in records:
            t = classify(r["text"])
            if t not in picked:
                picked[t] = r
            if len(picked) >= 3:
                break

        # 不足 3 条时用"其他"类去重补齐（每天尽量归档满 3 条不同类型战报）
        if len(picked) < 3:
            for r in records:
                if all(r is not p for p in picked.values()):
                    picked[f"其他_{extract_opponent(r['text'])}"] = r
                if len(picked) >= 3:
                    break

        date = datetime.now().strftime("%Y-%m-%d")
        for t, r in picked.items():
            detail_html = await client.get(r["viewfight"])
            rounds = parse_rounds(detail_html)
            scene = re.search(r"战斗场景：([^ <]+)", text_of(detail_html))
            parts = re.search(r"参战角色：([^ <]+)", text_of(detail_html))
            record = {
                "date": date,
                "type": t,
                "record_text": r["text"],
                "battle_id": r["viewfight"],
                "scene": scene.group(1) if scene else "",
                "participants": parts.group(1) if parts else "",
                "rounds": rounds,
                "raw_detail_html": detail_html,
            }
            out = out_dir / f"{date}_{t}.json"
            out.write_text(json.dumps(record, ensure_ascii=False, indent=2),
                           encoding="utf-8")
            print(f"[{t}] 已归档: {out.name} | 场景: {record['scene']} | "
                  f"回合: {len(rounds)} | {record['record_text'][:40]}")
            await asyncio.sleep(0.1)

        if not picked:
            print("今天还没有可归档的战斗记录")


if __name__ == "__main__":
    asyncio.run(main())
