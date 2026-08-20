"""research/entity_model.py — 用户端数据结构：从快照解析账号实体模型

把最新快照的各页面 HTML 解析成结构化实体模型（角色/背包/武器/佣兵/星石/
徽章/成就/师徒/好友/排行），输出 JSON。解析为尽力而为，字段缺失不影响整体。

用法: uv run python research/entity_model.py
输出: log/account_model.json
"""
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def text_of(html: str) -> str:
    """HTML → 紧凑纯文本"""
    t = re.sub(r"<[^>]+>", "|", html)
    t = re.sub(r"&nbsp;?", " ", t)
    t = re.sub(r"[|\s]+", " ", t).strip()
    return t


def extract(html: str, patterns: list[tuple[str, str]]) -> dict:
    """按 (key, 正则) 列表尽力提取"""
    out = {}
    for key, pat in patterns:
        m = re.search(pat, html)
        if m:
            out[key] = m.group(1).strip()
    return out


def parse_bag(html: str) -> list[dict]:
    """背包：物品名 + 数量（按 名称 数量：N 模式）"""
    items = []
    for m in re.finditer(r"([\u4e00-\u9fa5A-Za-z0-9·（）(\)\-]{2,24}?)\s*数量：(\d+)", text_of(html)):
        items.append({"name": m.group(1).strip(), "qty": int(m.group(2))})
    return items


def parse_weapons(html: str) -> list[dict]:
    """强化页：武器/技能 + 等级 + 成功率（文本模式，容忍标签）"""
    t = text_of(html)
    out = []
    for m in re.finditer(
        r"([\u4e00-\u9fa5A-Za-z0-9·\-]{2,16}?)\s*(\d+)级.*?成功率:([^（ )]+)", t
    ):
        out.append({"name": m.group(1), "level": m.group(2), "rate": m.group(3)})
    return out[:20]


def parse_mercenaries(html: str) -> list[dict]:
    """佣兵：名字 + 碎片进度（文本模式）"""
    t = text_of(html)
    out = []
    for m in re.finditer(r"([\u4e00-\u9fa5·]+?)\s*\((\d+)/(\d+)\)", t):
        out.append({"name": m.group(1), "shards": int(m.group(2)),
                    "need": int(m.group(3))})
    return out


def parse_stones(html: str) -> list[dict]:
    """星盘：星石等级 + 属性"""
    t = text_of(html)
    out = []
    for m in re.finditer(r"(\d+)级([\u4e00-\u9fa5]+?石)\s*([\u4e00-\u9fa5]*[+\-]?[\d.]+%?[^ ]{0,8})", t):
        out.append({"level": m.group(1), "name": m.group(2), "attr": m.group(3)})
    return out[:15]


def parse_badges(html: str) -> list[dict]:
    """徽章馆：品质 + 阶 + 徽章名（文本模式）"""
    t = text_of(html)
    out = []
    for m in re.finditer(r"(钻石|白金|黄金|白银|青铜)\s*(\d+)阶\s*([\u4e00-\u9fa5]{2,8})徽章", t):
        out.append({"quality": m.group(1), "tier": m.group(2),
                    "name": m.group(3)})
    return out


def parse_disciples(html: str) -> list[dict]:
    """师徒：徒弟名 + 等级 + 状态"""
    t = text_of(html)
    out = []
    for m in re.finditer(r"([\u4e00-\u9fa5A-Za-z0-9·_]+?)\s*(\d+)级\s*(已乐斗|乐斗)?", t):
        out.append({"name": m.group(1), "level": m.group(2),
                    "status": m.group(3) or ""})
    return out[:10]


def parse_friends(html: str) -> list[dict]:
    """好友/侠：名字 + 等级 + 状态"""
    t = text_of(html)
    out = []
    for m in re.finditer(r"侠：\s*([\u4e00-\u9fa5A-Za-z0-9·_]+?)\s*(\d+)级\s*(已乐斗)?", t):
        out.append({"name": m.group(1), "level": m.group(2),
                    "fought": bool(m.group(3))})
    return out


def main():
    files = sorted(glob.glob(str(Path("log/snapshots") / "*.json")),
                   key=lambda p: Path(p).stat().st_mtime)
    if not files:
        print("没有快照，先运行 research/snapshot.py")
        sys.exit(1)
    data = json.loads(Path(files[-1]).read_text(encoding="utf-8"))
    qq = next(k for k in data if k != "_meta")
    p = data[qq]["pages"]
    html = {name: page["raw_html"] for name, page in p.items()}

    model = {
        "snapshot": Path(files[-1]).name,
        "character": data[qq]["character"],
        "today_tasks": data[qq]["available_tasks"],
        "bag": parse_bag(html.get("bag", "")),
        "weapons": parse_weapons(html.get("upgrade", "")),
        "mercenaries": parse_mercenaries(html.get("mercenary", "")),
        "astrolabe_stones": parse_stones(html.get("astrolabe", "")),
        "badges": parse_badges(html.get("badge", "")),
        "disciples": parse_disciples(html.get("disciple", "")),
        "friends_bosses": parse_friends(html.get("friendlist", "")),
        "battle_record_count": len(re.findall(r"\d+:", text_of(html.get("battle_records", "")))),
    }
    out = Path("log/account_model.json")
    out.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"实体模型已生成: {out}（快照 {Path(files[-1]).name}）")
    print(f"  角色: {model['character']}")
    print(f"  背包物品: {len(model['bag'])} 种（示例: {[i['name'] for i in model['bag'][:5]]}）")
    print(f"  武器: {len(model['weapons'])}（示例: {[w['name'] for w in model['weapons'][:3]]}）")
    print(f"  佣兵: {len(model['mercenaries'])}（示例: {[m['name'] for m in model['mercenaries'][:3]]}）")
    print(f"  星石: {len(model['astrolabe_stones'])} 徽章: {len(model['badges'])}")
    print(f"  徒弟: {len(model['disciples'])} 侠/BOSS: {len(model['friends_bosses'])} 战报: {model['battle_record_count']} 条")


if __name__ == "__main__":
    main()
