"""research/hit_quality_audit.py — 命中行解析质量审计（任务1）

审计 battle_hits 管道的输出 hits_dataset.json:
  字段完整率 / 武器名污染(叙事前缀) / 行动类型错位 / 攻击者判定
输出: 控制台表格 + log/hit_quality_audit.json

用法: uv run python research/hit_quality_audit.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

# 叙事动词/前缀（武器名污染来源）
FLAVOR_PREFIXES = ("忽然", "把", "你摸出", "轮起", "使起", "拿出", "摸出",
                   "舞得", "蓄势待发，一记", "长啸一声", "面沉如水", "你凝神")

FLAVOR_VERBS = re.compile(r"^(忽然|把|摸出|拿出|轮起|使起|舞起|捡起|掏出)")


def main():
    f = Path("log/hits_dataset.json")
    if not f.exists():
        print("hits_dataset.json 不存在，先跑 research/battle_hits.py")
        sys.exit(1)
    dataset = json.loads(f.read_text(encoding="utf-8"))

    total = sum(len(b["rounds"]) for b in dataset)
    fields = {"damage": 0, "hp_after": 0, "weapon": 0, "weapon_type": 0,
              "crit": 0, "dodge": 0}
    polluted = []
    action_counts = Counter()
    attacker_misalign = []
    missing_all = []

    for b in dataset:
        for r in b["rounds"]:
            if r["damage"] is not None:
                fields["damage"] += 1
            if r["hp_after"] is not None:
                fields["hp_after"] += 1
            if r["weapon"]:
                fields["weapon"] += 1
            if r["weapon_type"]:
                fields["weapon_type"] += 1
            if r["crit"]:
                fields["crit"] += 1
            if r["dodge"]:
                fields["dodge"] += 1
            action_counts[r["action"]] += 1
            if r["weapon"] and FLAVOR_VERBS.search(r["weapon"]):
                polluted.append(r["weapon"])
            if r["attacker"] == "opponent" and r["damage"] is None and r["dodge"]:
                attacker_misalign.append(r)

    report = {
        "battles": len(dataset), "total_hits": total,
        "field_coverage": {k: round(v / total, 3) for k, v in fields.items()},
        "weapon_pollution": {"count": len(polluted), "samples": polluted[:8]},
        "action_types": dict(action_counts),
        "attacker_checks": {"opponent_dodge_no_damage": len(attacker_misalign)},
    }
    Path("log/hit_quality_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"战报 {len(dataset)} 场 / 命中 {total} 条")
    print("\n字段覆盖率（占全部命中）:")
    for k, v in report["field_coverage"].items():
        print(f"  {k}: {v*100:.0f}%")
    print(f"\n武器名污染（叙事前缀混入）: {len(polluted)} 条，样本: {polluted[:6]}")
    print(f"行动类型分布: {report['action_types']}")
    print(f"攻击者判定检查（对手回合无伤害且闪避）: {len(attacker_misalign)} 条")
    print(f"\n审计结果已保存: log/hit_quality_audit.json")


if __name__ == "__main__":
    main()
