"""research/fit_exp_curve.py — 经验曲线拟合（F7 升级）

数据: 等级榜 Top10 的 (等级, 累计经验) + 本号 86 级单级需求
方法: 幂律 least-squares（log-log 回归）:
      total_exp(level) ≈ a × level^b
输出: 拟合参数 + 残差 + 86 级单级需求交叉验证

用法: uv run python research/fit_exp_curve.py
"""
import json
import math
import sys
from pathlib import Path

# 等级榜 Top10: (等级, 累计经验)
POINTS = [
    (255, 113518147), (253, 109903582), (251, 106955689),
    (250, 105454306), (245, 96091675), (242, 91196861),
    (240, 88095627), (239, 85816158), (237, 82385698), (236, 81500037),
]
# 本号锚点: 86 级升级需求
KNOWN_REQ = (86, 118350)


def power_fit(points):
    """y = a·x^b → ln y = ln a + b·ln x，最小二乘"""
    n = len(points)
    sx = sum(math.log(p[0]) for p in points)
    sy = sum(math.log(p[1]) for p in points)
    sxx = sum(math.log(p[0]) ** 2 for p in points)
    sxy = sum(math.log(p[0]) * math.log(p[1]) for p in points)
    b = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    lna = (sy - b * sx) / n
    return math.exp(lna), b


def main():
    a, b = power_fit(POINTS)
    print(f"=== 幂律拟合 total_exp ≈ {a:.3f} × level^{b:.3f} ===")
    print(f"\n样本 {len(POINTS)} 点 (等级 {POINTS[-1][0]}~{POINTS[0][0]}):")
    print("| 等级 | 实际经验 | 拟合值 | 相对误差 |")
    print("| --- | --- | --- | --- |")
    errs = []
    for lv, exp in sorted(POINTS):
        fit = a * lv ** b
        err = (fit - exp) / exp * 100
        errs.append(abs(err))
        print(f"| {lv} | {exp:,} | {fit:,.0f} | {err:+.1f}% |")
    print(f"\n平均绝对误差: {sum(errs)/len(errs):.1f}%")

    # 交叉验证: 86 级单级需求 = 总经验导数 ≈ b·a·x^(b-1)（近似，幂律导数）
    # 但单级需求是差分 total(lv+1)-total(lv)，幂律下 ≈ a·b·x^(b-1)
    lv = KNOWN_REQ[0]
    delta = a * b * lv ** (b - 1)
    print(f"\n交叉验证: 模型预测 86 级单级需求 ≈ {delta:,.0f}，实际 {KNOWN_REQ[1]:,} "
          f"（误差 {(delta-KNOWN_REQ[1])/KNOWN_REQ[1]*100:+.0f}%）")
    print("\n⚠️ 适用范围: 236~255 级区间拟合；低等级可能偏差，需更多低等级样本验证")

    out = Path("log/exp_curve_fit.json")
    out.write_text(json.dumps({"a": a, "b": b, "points": POINTS,
                               "formula": f"total_exp = {a:.3f} * level^{b:.3f}",
                               "known_req_86": KNOWN_REQ[1]}, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"已保存: {out}")


if __name__ == "__main__":
    main()
