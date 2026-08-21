"""离线数值校准工具。

只读取已经导出的观察样本；不包含网络、Cookie 或游戏操作。
输入可以来自 JSON/CSV 的转换结果。样本不足时抛出 ValueError，避免把单点推断伪装成公式。
"""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import median
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class CritEstimate:
    multiplier: float
    pairs: int
    median_ratio: float
    ci95_low: float
    ci95_high: float


def _quantile(sorted_values: Sequence[float], probability: float) -> float:
    """线性插值分位数；避免引入第三方数值依赖。"""
    if not sorted_values:
        raise ValueError("没有可用样本")
    position = (len(sorted_values) - 1) * probability
    lo, hi = int(position), min(int(position) + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (position - lo)


def estimate_crit_multiplier(rows: Iterable[Mapping[str, object]]) -> CritEstimate:
    """按同构筑层配对估计暴击倍率。

    每行至少含 ``damage``、``crit``，并包含用于配对的
    ``mode/opponent_id/weapon_id/weapon_level/skill_id/buffs/debuffs``。
    同一层中的暴击与非暴击以中位数配对，避免将不同武器或技能混为倍率。
    """
    required = {"damage", "crit", "mode", "opponent_id", "weapon_id", "weapon_level", "skill_id"}
    grouped: dict[tuple[object, ...], dict[bool, list[float]]] = {}
    for row in rows:
        absent = required - row.keys()
        if absent:
            raise ValueError(f"命中行缺少字段：{', '.join(sorted(absent))}")
        key = tuple(row[name] for name in ("mode", "opponent_id", "weapon_id", "weapon_level", "skill_id"))
        # 状态是可选列，但缺失与空状态必须当成同一类。
        key += (str(row.get("buffs", "")), str(row.get("debuffs", "")))
        grouped.setdefault(key, {True: [], False: []})[bool(row["crit"])].append(float(row["damage"]))

    ratios: list[float] = []
    for values in grouped.values():
        if len(values[True]) >= 30 and len(values[False]) >= 30:
            normal = median(values[False])
            if normal > 0:
                ratios.append(median(values[True]) / normal)
    if not ratios:
        raise ValueError("没有满足门槛的同构筑层：每层需至少 30 条暴击与 30 条非暴击命中")

    ratios.sort()
    # 这是“层间估计”的经验区间，不替代严格的重采样置信区间。
    return CritEstimate(
        multiplier=median(ratios),
        pairs=len(ratios),
        median_ratio=median(ratios),
        ci95_low=_quantile(ratios, 0.025),
        ci95_high=_quantile(ratios, 0.975),
    )


@dataclass(frozen=True)
class ExpModel:
    name: str
    coefficients: tuple[float, ...]
    loocv_mae: float
    max_relative_error: float
    sample_size: int

    def predict(self, level: float) -> float:
        return sum(coefficient * level**power for power, coefficient in enumerate(self.coefficients))


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """高斯消元，供小规模最小二乘法使用。"""
    size = len(vector)
    augmented = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for pivot in range(size):
        candidate = max(range(pivot, size), key=lambda i: abs(augmented[i][pivot]))
        if abs(augmented[candidate][pivot]) < 1e-12:
            raise ValueError("样本等级不够分散，无法拟合")
        augmented[pivot], augmented[candidate] = augmented[candidate], augmented[pivot]
        scale = augmented[pivot][pivot]
        augmented[pivot] = [value / scale for value in augmented[pivot]]
        for row in range(size):
            if row == pivot:
                continue
            factor = augmented[row][pivot]
            augmented[row] = [a - factor * b for a, b in zip(augmented[row], augmented[pivot])]
    return [augmented[i][-1] for i in range(size)]


def _fit_polynomial(points: Sequence[tuple[float, float]], degree: int) -> tuple[float, ...]:
    columns = degree + 1
    normal_matrix = [[sum(x ** (r + c) for x, _ in points) for c in range(columns)] for r in range(columns)]
    normal_vector = [sum(y * x**r for x, y in points) for r in range(columns)]
    return tuple(_solve(normal_matrix, normal_vector))


def _evaluate(points: Sequence[tuple[float, float]], degree: int) -> ExpModel:
    errors: list[float] = []
    relative_errors: list[float] = []
    for index, (_, actual) in enumerate(points):
        training = points[:index] + points[index + 1 :]
        coefficients = _fit_polynomial(training, degree)
        level = points[index][0]
        predicted = sum(c * level**power for power, c in enumerate(coefficients))
        errors.append(abs(predicted - actual))
        relative_errors.append(abs(predicted - actual) / actual)
    coefficients = _fit_polynomial(points, degree)
    return ExpModel(
        name=("linear" if degree == 1 else "quadratic"),
        coefficients=coefficients,
        loocv_mae=sum(errors) / len(errors),
        max_relative_error=max(relative_errors),
        sample_size=len(points),
    )


def fit_experience_curve(samples: Iterable[Mapping[str, object]]) -> ExpModel:
    """拟合经验需求，自动在一次/二次模型中选择留一误差较低者。

    每行需有 ``level`` 和 ``required_exp``。至少 6 个不同等级；同级矛盾记录会报错。
    """
    by_level: dict[float, float] = {}
    for sample in samples:
        if "level" not in sample or "required_exp" not in sample:
            raise ValueError("经验样本需要 level 与 required_exp")
        level, required = float(sample["level"]), float(sample["required_exp"])
        if level in by_level and abs(by_level[level] - required) > 1e-9:
            raise ValueError(f"等级 {level:g} 的升级需求互相矛盾；请先按 ruleset_version 分层")
        by_level[level] = required
    points = sorted(by_level.items())
    if len(points) < 6:
        raise ValueError("经验曲线至少需要 6 个不同等级；单点或单等级样本不得拟合")
    linear, quadratic = _evaluate(points, 1), _evaluate(points, 2)
    # 仅当二次在交叉验证中显著（至少 5%）改善时才提高复杂度。
    return quadratic if quadratic.loocv_mae < linear.loocv_mae * 0.95 else linear


if __name__ == "__main__":
    print("该模块需要导入观察样本后调用 estimate_crit_multiplier / fit_experience_curve。")
