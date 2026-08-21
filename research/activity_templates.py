"""research/activity_templates.py — 活动模板对照表（B组·代码静态分析）

把全部注册任务按"接口调用模式 + 任务名"归类到 6 类活动模板：
  每日领取 / 免费机会 / 自动PvE / 连续目标 / 报名赛季 / 兑换商店 / 成长强化

输出: research/活动模板对照表.md

用法: uv run python research/activity_templates.py
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from research.build_interface_dict import parse_task_files
from src.tasks.register import get_all_modules, get_module_tasks


def classify(task: str, cmds: list[str]) -> tuple[str, str]:
    """返回 (模板类型, 依据)"""
    # 兑换商店
    if any(k in task for k in ("兑换", "商店", "黑市", "商会")) and any(
        c.startswith(("exchange", "fac_corp", "viewshop")) for c in cmds):
        return "兑换商店", f"兑换类任务 {cmds[0][:30]}"
    # 报名赛季
    if any(k in task for k in ("报名", "争霸", "大赛", "武林", "盟主", "巅峰之战",
                               "结拜", "群侠", "会武", "问鼎", "帮战", "掠夺", "踢馆")):
        return "报名赛季", f"赛季/报名类任务 {cmds[0][:30]}"
    # 免费机会
    if any(k in cmds_str for k in ("lottery", "draw", "roll", "wheel")) or any(
        k in task for k in ("神秘宝", "金蛋", "转盘", "刮刮", "娃娃机", "宝箱", "抽奖")):
        return "免费机会", f"抽取类 {cmds_str[:40]}"
    # 自动PvE
    if any(k in cmds_str for k in ("fight", "tower", "历练", "challenge",
                                   "dungeon", "副本", "扫荡", "闯关", "渊")) or any(
        k in task for k in ("历练", "斗神塔", "副本", "挑战", "幻境", "江湖长梦")):
        return "自动PvE", f"战斗类 {cmds_str[:40]}"
    # 成长强化
    if any(k in task for k in ("强化", "升级", "合成", "镶嵌", "附魔", "还童",
                               "修炼", "专精", "星盘", "神魔录", "兵法", "经脉", "锻造")):
        return "成长强化", f"养成类 {cmds_str[:40]}"
    # 连续目标
    if any(k in task for k in ("许愿", "签到", "游记", "连续", "任务派遣")):
        return "连续目标", f"连续/签到类 {cmds_str[:40]}"
    return "每日领取", f"领取类 {cmds_str[:40]}"


# 预收集: 任务名 -> 用到的 cmd 前缀
entries = parse_task_files()
task_cmds = defaultdict(list)
for e in entries:
    task_cmds[f"{e['task']}"] = []
for e in entries:
    task_cmds[e["task"]].append(e["cmd"])

rows = []
for module in get_all_modules():
    for task_name in get_module_tasks(module):
        cmds = task_cmds.get(task_name, [])
        cmds_str = ",".join(cmds)
        tpl, why = classify(task_name, cmds)
        rows.append((module.value, task_name, tpl, why))

# 统计
count = defaultdict(int)
for _, _, tpl, _ in rows:
    count[tpl] += 1

lines = [
    "# 活动模板对照表（代码静态分析，启发式分类）",
    "",
    f"> 生成：{__import__('datetime').datetime.now():%Y-%m-%d %H:%M} ｜ "
    f"{len(rows)} 个任务 → 按接口模式+任务名归类，标注为启发式（非官方）",
    "",
    "## 模板分布",
    "| 模板 | 任务数 |",
    "| --- | --- |",
]
for tpl, c in sorted(count.items(), key=lambda x: -x[1]):
    lines.append(f"| {tpl} | {c} |")

lines += ["", "## 全量对照表", "", "| 模块 | 任务 | 模板 | 依据 |", "| --- | --- | --- | --- |"]
for mod, task, tpl, why in sorted(rows):
    lines.append(f"| {mod} | {task} | {tpl} | {why} |")

out = Path("research/活动模板对照表.md")
out.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines[:14]))
print(f"\n已保存: {out}")
