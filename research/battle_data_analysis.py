"""research/battle_data_analysis.py — 战报数据聚合分析（战斗算法逆向第一步）

从 log/battle_reports/*.json 与各快照的 battle_detail 页聚合全部战报：
  - 按"机制签名"（HP 变化序列）去重（同战斗的叙事文案随机变化）
  - 统计: 回合数、伤害序列、暴击 vs 普攻、闪避、技能触发、对手 HP
输出: log/battle_stats.json + 控制台统计

用法: uv run python research/battle_data_analysis.py
"""
import glob
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def text_of(html: str) -> str:
    t = re.sub(r"<[^>]+>", "|", html)
    t = re.sub(r"&nbsp;?", " ", t)
    return re.sub(r"[|\s]+", " ", t).strip()


def parse_round(detail_text: str) -> list[dict]:
    """从完整战报文本解析回合：伤害/HP余/暴击/技能/闪避"""
    rounds = []
    for m in re.finditer(r"回合(\d+)[：:](.*?)(?=回合\d+[：:]|$)", detail_text):
        desc = m.group(2).strip()
        dmg_m = re.search(r"HP[-－](\d+)", desc)
        hp_m = re.search(r"HP余(\d+)", desc)
        rounds.append({
            "round": int(m.group(1)),
            "desc": desc[:180],
            "damage": int(dmg_m.group(1)) if dmg_m else None,
            "hp_after": int(hp_m.group(1)) if hp_m else None,
            "crit": "暴击" in desc,
            "dodge": any(w in desc for w in ("躲开", "闪过", "闪身")),
            "skill": next((s for s in ("雷霆一击", "封穴", "炮拳", "无影手",
                                       "五雷轰顶", "狂魔镰") if s in desc), ""),
        })
    return rounds


def load_all_battles() -> list[dict]:
    """聚合战报（归档 + 快照 battle_detail），按机制签名去重"""
    battles = []

    # 1) log/battle_reports/*.json
    for f in glob.glob(str(Path("log/battle_reports") / "*.json")):
        try:
            rec = json.loads(Path(f).read_text(encoding="utf-8"))
            battles.append({"source": Path(f).name,
                            "scene": rec.get("scene", ""),
                            "participants": rec.get("participants", ""),
                            "rounds": parse_round(text_of(rec.get("raw_detail_html", ""))),
                            "summary": rec.get("record_text", "")[:80]})
        except Exception:
            pass

    # 2) 快照里的 battle_detail
    for f in glob.glob(str(Path("log/snapshots") / "*.json")):
        try:
            data = json.loads(Path(f).read_text(encoding="utf-8"))
            for qq, s in data.items():
                if qq == "_meta":
                    continue
                bd = s.get("pages", {}).get("battle_detail")
                if bd and len(bd.get("raw_html", "")) > 500:
                    battles.append({"source": Path(f).name,
                                    "scene": "", "participants": "",
                                    "rounds": parse_round(text_of(bd["raw_html"])),
                                    "summary": ""})
        except Exception:
            pass

    # 去重：按 (round 数, 伤害序列) 签名
    seen, unique = set(), []
    for b in battles:
        sig = tuple(r["damage"] for r in b["rounds"])
        if sig and sig not in seen:
            seen.add(sig)
            unique.append(b)
    return unique


def analyze():
    battles = load_all_battles()
    print(f"聚合到 {len(battles)} 场唯一战报（按伤害签名去重）\n")

    all_damage = []
    crit_damage, normal_damage = [], []
    turn_counts = []
    skill_counter = Counter()
    dodge_count = 0
    opp_hp_samples = []

    for b in battles:
        rs = b["rounds"]
        if not rs:
            continue
        turn_counts.append(len(rs))
        for r in rs:
            if r["damage"]:
                all_damage.append(r["damage"])
                (crit_damage if r["crit"] else normal_damage).append(r["damage"])
            if r["skill"]:
                skill_counter[r["skill"]] += 1
            if r["dodge"]:
                dodge_count += 1
            if r["hp_after"]:
                opp_hp_samples.append(r["hp_after"])

    stats = {
        "battle_count": len(battles),
        "turn_stats": {"min": min(turn_counts), "max": max(turn_counts),
                       "avg": round(sum(turn_counts) / len(turn_counts), 1)},
        "damage": {"n": len(all_damage), "min": min(all_damage),
                   "max": max(all_damage),
                   "avg": round(sum(all_damage) / len(all_damage), 1)},
        "crit": {"n": len(crit_damage),
                 "avg": round(sum(crit_damage) / len(crit_damage), 1) if crit_damage else 0},
        "normal": {"n": len(normal_damage),
                   "avg": round(sum(normal_damage) / len(normal_damage), 1) if normal_damage else 0},
        "crit_ratio": round(sum(crit_damage) / len(crit_damage) /
                            (sum(normal_damage) / len(normal_damage)), 2)
                      if crit_damage and normal_damage else None,
        "skills": dict(skill_counter),
        "dodge_events": dodge_count,
        "opponent_hp_samples": sorted(opp_hp_samples)[:3],
        "damage_histogram": dict(sorted(Counter(all_damage).items())),
    }

    out = Path("log/battle_stats.json")
    out.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== 战斗统计 ===")
    print(f"回合数: {stats['turn_stats']}")
    print(f"伤害: 共{stats['damage']['n']}次 min={stats['damage']['min']} "
          f"max={stats['damage']['max']} avg={stats['damage']['avg']}")
    print(f"暴击: n={stats['crit']['n']} avg={stats['crit']['avg']} | "
          f"普攻: n={stats['normal']['n']} avg={stats['normal']['avg']} | "
          f"暴击倍率≈{stats['crit_ratio']}")
    print(f"技能触发: {stats['skills']}")
    print(f"闪避事件: {stats['dodge_events']}")
    print(f"对手HP样本: {stats['opponent_hp_samples']}（推测BOSS满血≈5000万）")
    print(f"伤害分布: {stats['damage_histogram']}")
    print(f"\n统计已保存: {out}")


if __name__ == "__main__":
    analyze()
