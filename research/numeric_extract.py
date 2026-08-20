"""research/numeric_extract.py — 数值全量提取（从最新快照 + 日志榨取所有数字）

输出: log/numeric_data.json — 结构化数值表:
  character / upgrade(武器升级成本表) / liveness(活跃度分值表) /
  shop(商店定价) / stones(星石属性) / mercenaries(佣兵碎片) /
  blacksmith(铁匠铺) / gods(神魔录) / badges(徽章) / log_rewards(日志奖励)

用法: uv run python research/numeric_extract.py
"""
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def text_of(html: str) -> str:
    t = re.sub(r"<[^>]+>", "|", html)
    t = re.sub(r"&nbsp;?", " ", t)
    return re.sub(r"[|\s]+", " ", t).strip()


def parse_upgrade(html: str) -> list[dict]:
    """武器/技能升级表：名称/等级/效果/卷轴/成功率"""
    t = text_of(html)
    items = []
    for m in re.finditer(
        r"([\u4e00-\u9fa5A-Za-z0-9·\-]{2,16}?)\s*(\d+)级\s*升级\s*[（(]([^）)]{0,30})[）)]\s*需卷轴:(\d+)\s*成功率:(\S+)",
        t,
    ):
        items.append({"name": m.group(1), "level": int(m.group(2)),
                      "effect": m.group(3).strip(), "scrolls": int(m.group(4)),
                      "rate": m.group(5)})
    return items


def parse_liveness(html: str) -> list[dict]:
    """活跃度任务表：任务/完成数/需求数/分值"""
    t = text_of(html)
    items = []
    for m in re.finditer(r"(\d+)\.\s*\[(\d+)/(\d+)\]\s*(.{2,14}?)\s*[（(](\d+)分[）)]", t):
        items.append({"seq": int(m.group(1)), "done": int(m.group(2)),
                      "need": int(m.group(3)), "task": m.group(4).strip(),
                      "points": int(m.group(5))})
    return items


def parse_shop(html: str) -> list[dict]:
    """商店定价：物品/价格/货币"""
    t = text_of(html)
    items = []
    for m in re.finditer(r"([\u4e00-\u9fa5A-Za-z0-9·\-]{2,20}?)\s*([\d.]+)/([\d.]+)\s*鹅币", t):
        items.append({"name": m.group(1).strip(), "price": float(m.group(2)),
                      "unit": float(m.group(3))})
    return items


def parse_progress(html: str, name: str) -> dict:
    """通用进度解析（铁匠铺/神魔录）：当前值/进度/消耗/产出"""
    t = text_of(html)
    out = {"system": name}
    m = re.search(r"战斗力：([\d.]+)", t)
    if m:
        out["power"] = float(m.group(1))
    m = re.search(r"进度：(\d+)/(\d+)", t)
    if m:
        out["progress"] = int(m.group(1))
        out["progress_max"] = int(m.group(2))
    m = re.search(r"每次升级增加\s*(\d+)\s*点进度", t)
    if m:
        out["per_step"] = int(m.group(1))
    m = re.search(r"升级消耗：\s*([\u4e00-\u9fa5]+)\s*\*\s*(\d+)\s*\((\d+)\)", t)
    if m:
        out["material"] = m.group(1)
        out["material_cost"] = int(m.group(2))
        out["material_owned"] = int(m.group(3))
    m = re.search(r"祝福值：(\d+)/(\d+)", t)
    if m:
        out["blessing"] = int(m.group(1))
        out["blessing_max"] = int(m.group(2))
    m = re.search(r"消耗：([\u4e00-\u9fa5]+)\*(\d+)（(\d+)）", t)
    if m:
        out["consume"] = m.group(1)
        out["consume_qty"] = int(m.group(2))
        out["consume_owned"] = int(m.group(3))
    return out


def parse_log_rewards() -> list[dict]:
    """从当日日志提取数值奖励行"""
    rewards = []
    for f in glob.glob(str(Path("log") / "*" / "*.log")):
        for line in Path(f).read_text(encoding="utf-8", errors="replace").splitlines():
            if any(k in line for k in ("获得", "经验值", "阅历", "积分", "门贡", "银币", "斗币")):
                line = re.sub(r"^\d{2}:\d{2}:\d{2}\s*\|\s*", "", line).strip()
                if line and len(line) < 140:
                    rewards.append(line)
    return rewards[:80]


def main():
    files = sorted(glob.glob(str(Path("log/snapshots") / "*.json")),
                   key=lambda p: Path(p).stat().st_mtime)
    if not files:
        print("没有快照")
        sys.exit(1)
    data = json.loads(Path(files[-1]).read_text(encoding="utf-8"))
    qq = next(k for k in data if k != "_meta")
    h = {n: p.get("raw_html", "") for n, p in data[qq]["pages"].items()}

    numeric = {
        "snapshot": Path(files[-1]).name,
        "character": data[qq]["character"],
        "upgrade": parse_upgrade(h.get("upgrade", "")),
        "liveness": parse_liveness(h.get("liveness", "")),
        "shop": parse_shop(h.get("shop", "")),
        "blacksmith": parse_progress(h.get("blacksmith", ""), "铁匠铺"),
        "gods": parse_progress(h.get("ancient_gods", ""), "神魔录"),
        "stones": _stones(h.get("astrolabe", "")),
        "mercenaries": _mercs(h.get("mercenary", "")),
        "log_rewards": parse_log_rewards(),
    }
    out = Path("log/numeric_data.json")
    out.write_text(json.dumps(numeric, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"数值提取完成: {out}")
    print(f"  武器升级: {len(numeric['upgrade'])} 条")
    for u in numeric["upgrade"][:6]:
        print(f"    {u['name']} Lv{u['level']} [{u['rate']}] 卷轴{u['scrolls']} 效果:{u['effect']}")
    print(f"  活跃度任务: {len(numeric['liveness'])} 条")
    for l in numeric["liveness"]:
        print(f"    [{l['done']}/{l['need']}] {l['task']} = {l['points']}分")
    print(f"  商店: {len(numeric['shop'])} 件")
    for s in numeric["shop"][:6]:
        print(f"    {s['name']} {s['price']}鹅币")
    print(f"  铁匠铺: {numeric['blacksmith']}")
    print(f"  神魔录: {numeric['gods']}")


def _stones(html: str) -> list[dict]:
    t = text_of(html)
    out = []
    for m in re.finditer(r"(\d+)级([\u4e00-\u9fa5]+?石)\s*([\u4e00-\u9fa5]*[+\-]?[\d.]+%?[^ ]{0,8})", t):
        out.append({"level": int(m.group(1)), "name": m.group(2),
                    "attr": m.group(3)})
    return out[:15]


def _mercs(html: str) -> list[dict]:
    t = text_of(html)
    out = []
    for m in re.finditer(r"([\u4e00-\u9fa5·]+?)\s*\((\d+)/(\d+)\)", t):
        out.append({"name": m.group(1), "shards": int(m.group(2)),
                    "need": int(m.group(3))})
    return out


if __name__ == "__main__":
    main()
