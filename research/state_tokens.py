"""research/state_tokens.py — 状态令牌字典完整化（B组）

扫描全部快照页面 + one_shot 抓取页，提取客户端状态机令牌
（已X / X不足 / 上限 / 次数 / 未X / 第x/y页 / 错误提示），统计出现面数。

输出: research/状态令牌字典.md
用法: uv run python research/state_tokens.py
"""
import glob
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def page_texts() -> list[str]:
    """汇总所有可用页面的纯文本"""
    texts = []
    files = []
    files += sorted(glob.glob(str(Path("log/snapshots") / "*.json")))
    files += sorted(glob.glob(str(Path("log/one_shot") / "*" / "*.json")))
    for f in files:
        try:
            data = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        if "raw_html" in data:
            texts.append(re.sub(r"<[^>]+>", "|", data["raw_html"]))
        else:
            for qq, s in data.items():
                if qq == "_meta" or not isinstance(s, dict):
                    continue
                for page in s.get("pages", {}).values():
                    texts.append(re.sub(r"<[^>]+>", "|", page.get("raw_html", "")))
    return texts


def main():
    texts = page_texts()
    n_pages = len(texts)
    tokens = Counter()

    patterns = [
        r"已\w{1,6}",                      # 已乐斗/已领取/已兑换
        r"[^ ，。；、\d]\w{1,4}(?:不足|不够)",  # 体力不足/材料不够
        r"\w{0,4}(?:上限|已用完|已满)",       # 上限/次数已用完
        r"未\w{1,4}(?:达成|开通|完成|领取|激活)",  # 未达成/未开通
        r"第\d+/\d+页",                     # 分页
        r"很抱歉[^。]*",                    # 错误提示
        r"请稍后再试",
        r"刷新过于频繁[^。]*",
        r"当前进度.*",
    ]
    for t in texts:
        for pat in patterns:
            for m in re.findall(pat, t):
                m = m.strip()
                if 1 < len(m) <= 18:
                    tokens[m] += 1

    lines = [
        "# 状态令牌字典（客户端状态机）",
        "",
        f"> 生成：{datetime.now():%Y-%m-%d %H:%M} ｜ 扫描 {n_pages} 个页面文本",
        "> 令牌 = 页面中驱动客户端决策的状态标记；出现面数 = 在多少个页面中出现",
        "",
        "| 令牌 | 出现面数 | 含义 |",
        "| --- | --- | --- |",
    ]
    for token, cnt in tokens.most_common(60):
        meaning = ""
        if token.startswith("已"):
            meaning = "今日已做/已拥有（幂等守卫）"
        elif "不足" in token or "不够" in token:
            meaning = "资源/前置门槛"
        elif "上限" in token or "用完" in token:
            meaning = "每日/次数限制"
        elif token.startswith("未"):
            meaning = "未达成/等级门槛"
        elif token.startswith("第"):
            meaning = "分页位置"
        elif "抱歉" in token:
            meaning = "通用错误（参数/限流/故障）"
        elif "频繁" in token:
            meaning = "动作级限流"
        lines.append(f"| {token} | {cnt} | {meaning} |")

    out = Path("research/状态令牌字典.md")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"扫描 {n_pages} 页，提取 {len(tokens)} 个令牌 → {out}")
    for token, cnt in tokens.most_common(12):
        print(f"  {token} ×{cnt}")


if __name__ == "__main__":
    main()
