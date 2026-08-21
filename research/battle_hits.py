"""research/battle_hits.py — 战报字段结构化管道（第一档·4，为伤害回归铺路）

把全部战报源（battle_reports + 快照 battle_detail）解析成"命中级"结构化行，
字段对齐 Codex 审查要求的回归模型:
  battle_id / mode / opponent / scene / round / attacker /
  action(技能或普攻) / weapon / weapon_type(小型/中型/大型) /
  crit / dodge / damage / hp_after / target

输出: log/hits_dataset.json
用法: uv run python research/battle_hits.py
"""
import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path

SKILLS = ("雷霆一击", "炮拳", "无影手", "封穴", "暴击", "看家招数")
WEAPON_TYPES = ("小型", "中型", "大型")


def text_of(html: str) -> str:
    t = re.sub(r"<[^>]+>", "|", html)
    t = re.sub(r"&nbsp;?", " ", t)
    return re.sub(r"[|\s]+", " ", t).strip()


def parse_round(desc: str, opponent: str) -> dict:
    hit = {
        "round": None, "attacker": "", "action": "", "weapon": "",
        "weapon_type": "", "crit": False, "dodge": False,
        "damage": None, "hp_after": None, "target": "",
    }
    m = re.search(r"回合(\d+)[：:]", desc)
    if m:
        hit["round"] = int(m.group(1))
    desc = desc.split("：", 1)[-1] if "：" in desc else desc

    if desc.startswith("你"):
        hit["attacker"] = "player"
    else:
        hit["attacker"] = opponent or "opponent"

    # 武器 + 类型
    wm = re.search(r"([\u4e00-\u9fa5·]{2,10}?)(小型|中型|大型)武器", desc)
    if wm:
        hit["weapon"] = wm.group(1)
        hit["weapon_type"] = wm.group(2)
        hit["action"] = "武器攻击"
    # 技能
    for s in SKILLS:
        if s in desc:
            hit["action"] = s
            break
    if not hit["action"]:
        hit["action"] = "普攻"

    hit["crit"] = "暴击" in desc
    hit["dodge"] = any(w in desc for w in ("躲开", "闪过", "闪身"))
    dm = re.search(r"HP[-－](\d+)", desc)
    if dm:
        hit["damage"] = int(dm.group(1))
    hm = re.search(r"HP余(\d+)", desc)
    if hm:
        hit["hp_after"] = int(hm.group(1))
    hit["target"] = opponent if hit["attacker"] == "player" else "player"
    return hit


def load_battles() -> list[dict]:
    battles = []
    for f in glob.glob(str(Path("log/battle_reports") / "*.json")):
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
            battles.append({"source": Path(f).name, "html": d.get("raw_detail_html", "")})
        except Exception:
            pass
    for f in glob.glob(str(Path("log/snapshots") / "*.json")):
        try:
            data = json.loads(Path(f).read_text(encoding="utf-8"))
            for qq, s in data.items():
                if qq == "_meta":
                    continue
                bd = s.get("pages", {}).get("battle_detail")
                if bd and len(bd.get("raw_html", "")) > 500:
                    battles.append({"source": Path(f).name, "html": bd["raw_html"]})
        except Exception:
            pass
    return battles


def main():
    dataset = []
    seen_sigs = set()

    for b in load_battles():
        t = text_of(b["html"])
        scene = re.search(r"战斗场景：([^ ]+)", t)
        parts = re.search(r"参战角色：([^ ]+?)\s+vs\s+([^ ]+)", t)
        opponent = parts.group(2) if parts else ""
        # 去重（机制签名 = 伤害序列）
        dmg_seq = tuple(m.group(1) for m in re.finditer(r"HP[-－](\d+)", t))
        if not dmg_seq or dmg_seq in seen_sigs:
            continue
        seen_sigs.add(dmg_seq)

        battle = {
            "battle_id": Path(b["source"]).stem,
            "source": b["source"],
            "scene": scene.group(1) if scene else "",
            "opponent": opponent,
            "rounds": [],
        }
        for m in re.finditer(r"回合\d+[：:](.*?)(?=回合\d+[：:]|$)", t):
            battle["rounds"].append(parse_round(m.group(0), opponent))
        dataset.append(battle)

    out = Path("log/hits_dataset.json")
    out.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")

    # 统计
    total_hits = sum(len(b["rounds"]) for b in dataset)
    crits = sum(1 for b in dataset for r in b["rounds"] if r["crit"])
    dodges = sum(1 for b in dataset for r in b["rounds"] if r["dodge"])
    weapons = Counter(r["weapon"] for b in dataset for r in b["rounds"] if r["weapon"])
    actions = Counter(r["action"] for b in dataset for r in b["rounds"])

    print(f"战报 {len(dataset)} 场, 命中 {total_hits} 条 → {out}")
    print(f"暴击 {crits} 条 ({crits/max(total_hits,1)*100:.0f}%), 闪避 {dodges} 条")
    print(f"武器使用: {dict(weapons.most_common(6))}")
    print(f"行动类型: {dict(actions.most_common(6))}")
    print("\n字段样例（第一场第一回合）:")
    print(json.dumps(dataset[0]["rounds"][0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
