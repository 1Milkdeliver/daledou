"""research/build_interface_dict.py — 从任务代码生成"接口字典矩阵"

把 src/tasks/*.py 里所有 d.get("cmd=...") 调用整理成:
  接口 × 参数键 × 动态参数 × 出现次数 × 使用任务 × 疑似类型

用法: uv run python research/build_interface_dict.py
输出: research/接口字典.md
"""
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def parse_task_files() -> list[dict]:
    """解析每个任务的接口调用"""
    entries = []
    for f in sorted((REPO / "src/tasks").glob("*.py")):
        if f.name in ("__init__.py", "register.py"):
            continue
        lines = f.read_text(encoding="utf-8").splitlines()
        current_func = None
        current_comment = ""
        for line in lines:
            m_func = re.match(r"async def (\w+)", line)
            if m_func:
                current_func = m_func.group(1)
                current_comment = ""
                continue
            m_cmt = re.match(r"\s*#\s*(.+)", line)
            if m_cmt and not current_comment:
                current_comment = m_cmt.group(1).strip()[:40]
            m = re.search(r'd\.get\((f?)"cmd=([^"]+)"', line)
            if m and current_func:
                is_fstring = m.group(1) == "f"
                raw = m.group(2)
                # 拆 cmd= 名和其余参数
                parts = raw.split("&")
                cmd = parts[0][len("cmd="):] if parts[0].startswith("cmd=") else parts[0]
                params = []
                for p in parts[1:]:
                    if not p:
                        continue
                    if "=" in p:
                        k, v = p.split("=", 1)
                        params.append((k, v))
                    else:
                        params.append((p, ""))
                entries.append({
                    "file": f.name,
                    "task": current_func,
                    "cmd": cmd,
                    "params": params,
                    "dynamic": is_fstring,
                    "comment": current_comment,
                })
    return entries


def classify(cmd: str, params: list, comment: str) -> str:
    """粗略分类：视图 / 动作 / 未知"""
    view_words = ("view", "index", "show", "get", "draw", "list", "relicindex")
    action_words = ("fight", "challenge", "signup", "exchange", "use", "drawreward",
                    "claim", "roll", "exchange", "submit", "begin", "end", "open",
                    "refresh", "buy", "act", "op=1", "op=2", "op=3", "op=4")
    text = cmd + " " + " ".join(k + "=" + v for k, v in params) + " " + comment
    if any(w in text for w in action_words):
        return "动作"
    if any(w in text for w in view_words):
        return "视图"
    return "未知"


def main():
    entries = parse_task_files()
    by_cmd = defaultdict(list)
    for e in entries:
        by_cmd[e["cmd"]].append(e)

    lines = [
        "# 接口字典矩阵（由任务代码自动生成）",
        "",
        f"> 生成时间：{__import__('datetime').datetime.now():%Y-%m-%d %H:%M} ｜ "
        f"来源：src/tasks/ 共 {len(entries)} 处 d.get() 调用，{len(by_cmd)} 个接口",
        "> 类型为启发式猜测（视图/动作），供研究参考；动态参数标记 {var}",
        "",
        "| 接口 cmd | 类型 | 次数 | 参数键 | 动态参数 | 使用任务示例 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for cmd in sorted(by_cmd):
        es = by_cmd[cmd]
        param_keys = Counter()
        dynamic = set()
        samples = []
        for e in es:
            for k, v in e["params"]:
                if "{" in v or "}" in v:
                    dynamic.add(k)
                else:
                    param_keys[k] += 1
            if len(samples) < 3 and e["task"] not in samples:
                samples.append(e["task"])
        if dynamic:
            dyn_str = ", ".join(sorted(dynamic))
        else:
            dyn_str = "-"
        type_ = classify(cmd, es[0]["params"], es[0]["comment"])
        keys = ", ".join(f"{k}" for k, _ in param_keys.most_common(8))
        lines.append(
            f"| `{cmd}` | {type_} | {len(es)} | {keys or '-'} | {dyn_str} | {', '.join(samples)} |"
        )

    out = REPO / "research" / "接口字典.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"接口字典已生成: {out}（{len(by_cmd)} 个接口）")


if __name__ == "__main__":
    main()
