"""research/update_datapack.py — 自动更新研究数据包（脱敏版）

把动态观测数据合并进 research/研究数据包-脱敏版.md：
  1. 多日入口地图（每天快照的 noon/evening 开放数 + 增删）
  2. 差分实验记录（log/experiments/*.json，脱敏后格式化）
  3. 近期日志观测（log/<qq>/*.log 最近 7 天关键行，去重截断）

手工维护的知识库部分（文档前半）保持不变；自动部分在
<!-- AUTO-DATA-START --> 与 <!-- AUTO-DATA-END --> 之间，每次全量重建。

用法: uv run python research/update_datapack.py
"""
import glob
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import src.tasks.register  # noqa: F401
from src.utils.config import Config

REPO = Path(__file__).resolve().parent.parent
DATAPACK = REPO / "research" / "研究数据包-脱敏版.md"
START_MARK = "<!-- AUTO-DATA-START -->"
END_MARK = "<!-- AUTO-DATA-END -->"
OBSERVE_DAYS = 7
MAX_OBSERVATIONS = 50
MAX_EXPERIMENTS = 20

# 日志里值得记录的“观测”关键词
INTERESTING = re.compile(
    r"恭喜|获得|不足|上限|失败|成功|战胜|领取|兑换|恢复|体力值不足|次数|首通|开放|下架"
)


def redact(text: str) -> str:
    """脱敏：去掉 QQ 号与超长数字串"""
    for qq in Config.load_cookies():
        if qq:
            text = text.replace(qq, "***")
    text = re.sub(r"\d{10,}", "***", text)
    return text


def list_snapshots() -> list[dict]:
    """返回按时间排序的每日快照（跳过 before_/after_/demo_ 等实验快照）"""
    result = []
    for f in sorted(glob.glob(str(REPO / "log/snapshots" / "*.json"))):
        name = Path(f).name
        if not re.match(r"^\d{4}-\d{2}-\d{2}_", name):
            continue
        try:
            data = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        for qq, s in data.items():
            if qq == "_meta":
                continue
            result.append({"file": name, "qq": qq, "data": s})
    return result


def entry_map_table() -> str:
    """生成多日入口地图表格"""
    snaps = list_snapshots()
    if not snaps:
        return "_暂无快照（今晚 22:00 后开始积累）_"
    lines = ["| 快照时间 | noon 开放 | evening 开放 | 说明 |",
             "| --- | --- | --- | --- |"]
    prev = None
    for s in snaps[-14:]:  # 最近 14 天
        at = s["data"].get("available_tasks", {})
        n_noon = len(at.get("noon", []))
        n_eve = len(at.get("evening", []))
        note = ""
        if prev is not None:
            added = set(at.get("noon", [])) - set(prev.get("noon", []))
            removed = set(prev.get("noon", [])) - set(at.get("noon", []))
            if added or removed:
                note = f"+{len(added)} -{len(removed)}"
        lines.append(f"| {s['file']} | {n_noon} | {n_eve} | {note} |")
        prev = at
    return "\n".join(lines)


def character_diff(before: dict, after: dict) -> str:
    """角色属性差分（只输出有变化的字段）"""
    cb = before.get("character", {})
    ca = after.get("character", {})
    changed = {k: (cb.get(k), ca.get(k)) for k in set(cb) | set(ca) if cb.get(k) != ca.get(k)}
    if not changed:
        return "无变化（幂等验证）"
    return "; ".join(f"{k}: {v[0]}→{v[1]}" for k, v in changed.items())


def experiments_section() -> str:
    """格式化实验记录（脱敏）"""
    files = sorted(glob.glob(str(REPO / "log/experiments" / "*.json")))
    if not files:
        return "_暂无实验记录（重置后可跑 research/experiment.py 积累）_"
    out = []
    for f in files[-MAX_EXPERIMENTS:]:
        try:
            rec = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        task = rec.get("task", "?")
        t = rec.get("time", "")
        output = redact(rec.get("task_output", ""))[-600:]
        diff = ""
        try:
            b = json.loads(Path(rec["before"]).read_text(encoding="utf-8"))
            a = json.loads(Path(rec["after"]).read_text(encoding="utf-8"))
            qq = next((k for k in b if k != "_meta"), None)
            if qq and qq in a:
                diff = character_diff(b[qq], a[qq])
        except Exception:
            diff = "（快照缺失）"
        out.append(f"#### 实验: {task}（{t}）")
        out.append(f"- 角色差分: {diff}")
        out.append("- 输出(脱敏):")
        out.append("```")
        out.append(output.strip() or "（无输出）")
        out.append("```")
    return "\n".join(out)


def observations_section() -> str:
    """最近 N 天日志里的关键观测（脱敏、去重、截断）"""
    since = datetime.now() - timedelta(days=OBSERVE_DAYS)
    seen = set()
    lines = []
    for f in sorted(glob.glob(str(REPO / "log" / "*" / "*.log"))):
        try:
            text = Path(f).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line in seen:
                continue
            if not INTERESTING.search(line):
                continue
            # 只保留包含玩法名/数值的行，去时间戳格式差异
            cleaned = re.sub(r"^\d{2}:\d{2}:\d{2}\s*\|\s*", "", line)
            cleaned = redact(cleaned)
            if len(cleaned) < 6 or len(cleaned) > 120:
                continue
            seen.add(line)
            lines.append(cleaned)
            if len(lines) >= MAX_OBSERVATIONS:
                break
        if len(lines) >= MAX_OBSERVATIONS:
            break
    if not lines:
        return "_近期无观测_"
    return "\n".join(f"- {l}" for l in lines)


def regenerate() -> None:
    text = DATAPACK.read_text(encoding="utf-8")
    head = text.split(START_MARK)[0].rstrip() if START_MARK in text else text.rstrip()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    auto = "\n\n".join([
        f"## 九、自动观测数据（脚本生成，更新于 {now}）",
        "### 9.1 多日入口地图",
        entry_map_table(),
        "### 9.2 差分实验记录",
        experiments_section(),
        "### 9.3 近期日志观测",
        observations_section(),
    ])
    body = f"{head}\n\n{START_MARK}\n{auto}\n{END_MARK}\n"
    DATAPACK.write_text(body, encoding="utf-8")
    print(f"研究数据包已更新: {DATAPACK}")


if __name__ == "__main__":
    regenerate()
