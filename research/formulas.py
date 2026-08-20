"""research/formulas.py — Q宠大乐斗 数值公式假设模块（第一轮，待拟合）

每个公式标注: [★实测] [☆推断] [⬜假设]
数据积累后（log/battle_stats.json / log/numeric_data.json 多日合并），
用 fit_* 系列函数校准未知参数。

用法: uv run python research/formulas.py   # 打印当前参数与用法示例
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ---------- 战斗 ----------

CRIT_MULT = 3.4  # [☆] 暴击倍率（870.2/255.5，5样本粗糙估计）
WEAPON_MULT = {  # [☆] 武器类型倍率（单样本，待校准）
    "small": 1.0,   # 小型（土豪金490→归一）
    "medium": 1.99,  # 中型（真·金砖978/490≈1.99）
    "large": 1.99,   # 大型（狂魔镰979/490≈1.99）
}


def battle_damage(attack: float, weapon_type: str = "small",
                  skill_mult: float = 1.0, crit: bool = False,
                  random_pct: float = 0.0) -> float:
    """[⬜ F8] 伤害 = 攻击 × 武器倍率 × 技能倍率 × 暴击倍率 × (1+随机浮动)"""
    dmg = attack * WEAPON_MULT.get(weapon_type, 1.0) * skill_mult
    if crit:
        dmg *= CRIT_MULT
    return dmg * (1 + random_pct)


# ---------- 成长 ----------

def smith_upgrades_per_star() -> int:
    """[★ F2] 铁匠铺每星升级次数 = 进度上限/每次进度 = 20/2 = 10"""
    return 20 // 2


def god_guarantee_count() -> int:
    """[★ F5] 神魔录保底次数 = 祝福值上限 = 20"""
    return 20


def merc_shard_tiers() -> dict:
    """[☆ F6] 佣兵碎片需求分档"""
    return {"common": 150, "rare": 250, "epic": 300}


def exp_needed(level: int, a: float = 0.0, b: float = 0.0) -> float:
    """[⬜ F7] 经验需求曲线（占位：二次多项式，参数待多点拟合）
    已知点: exp_needed(86) ≈ 118350
    """
    # 先用单点比例粗估: 118350 / 86² ≈ 16.0
    if a == 0 and b == 0:
        return 16.0 * level * level
    return a * level * level + b * level


# ---------- 经济 ----------

def guild_exchange_rate() -> float:
    """[★ F3] 商会兑换率 = 10 银币/件"""
    return 10.0


def liveness_bonus_threshold() -> int:
    """[★ F4] 活跃大礼包门槛 = 80 分"""
    return 80


# ---------- 拟合入口（数据积累后使用） ----------

def fit_crit_mult(battle_stats_path: Path = Path("log/battle_stats.json")) -> float:
    """用积累的战报统计校准暴击倍率"""
    if not battle_stats_path.exists():
        return CRIT_MULT
    s = json.loads(battle_stats_path.read_text(encoding="utf-8"))
    if s.get("crit_ratio"):
        return s["crit_ratio"]
    return CRIT_MULT


if __name__ == "__main__":
    print("=== 公式模块自检 ===")
    print(f"F2 铁匠铺每星次数: {smith_upgrades_per_star()} [★]")
    print(f"F3 商会兑换率: {guild_exchange_rate()} 银币/件 [★]")
    print(f"F4 活跃礼包门槛: {liveness_bonus_threshold()} 分 [★]")
    print(f"F5 神魔录保底: {god_guarantee_count()} 次 [★]")
    print(f"F6 佣兵碎片档: {merc_shard_tiers()} [☆]")
    print(f"F7 经验需求(86级): {exp_needed(86):.0f}（目标118350）[⬜]")
    print(f"F1 暴击倍率(当前): {fit_crit_mult()} [☆]")
    print("示例: battle_damage(attack=300, weapon_type='medium', crit=True) =",
          round(battle_damage(300, "medium", crit=True), 1))
