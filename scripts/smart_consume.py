# -*- coding: utf-8 -*-
"""智能清空脚本(仓库版)：查体力/活力+恢复速率，预测恢复满时间，≥阈值则清空。
2026-09-01 用户指令"体力/活力自动预测时间自动清空"。由 hermes cron 每30分钟调用。
清空逻辑: 调 scripts/consume.py (跑历练+消耗体力)。未清空时静默。
"""
import subprocess
import sys
import re
import html
import datetime

PROJ = r"D:\Deepseek Harness\daledou"

# 恢复速率(点/小时) - 2026-09-01 实测: 体力/活力均 4/小时
TL_RATE, HUO_RATE = 4, 4
TL_MAX, HUO_MAX = 100, 50
COOKIE = "newuin=1206423023; uin=o1206423023; accessToken=DF155E62D0E8C079054B43481A62A2A1; eas_sid=P1D7q877l260o6M8K0F5W094G1; gameapi_access_token=7F34913C38001FDF33D246C118847F0C; openId=1A5FCD805FFE6AB3BBA6E89AABE2E00D; ptcz=3b26b587796166a4358d6152bc5d4ad2608df011c95d750bfef6403730efd4e5"


def get_vals():
    import requests
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/120", "Cookie": COOKIE, "Referer": "https://dld.qq.com/"})
    r = s.get("https://dld.qzapp.z.qq.com/qpet/cgi-bin/phonepk?cmd=index&style=1", timeout=15)
    t = r.content.decode("utf-8", "ignore")
    if len(re.findall(r'[\u4e00-\u9fff]', t)) < 5:
        t = r.content.decode("gbk", "ignore")
    c = re.sub(r'<[^>]+>', ' ', t); c = html.unescape(c); c = re.sub(r'\s+', ' ', c)
    tl = re.search(r"体力[^\d]*(\d+)/(\d+)", c)
    hu = re.search(r"活力[^\d]*(\d+)/(\d+)", c)
    return int(tl.group(1)), int(hu.group(1))


def predict_full(now_val, rate, mx, now):
    left = mx - now_val
    if left <= 0:
        return None, "已满"
    return now + datetime.timedelta(hours=left / rate), f"{left / rate:.1f}小时"


def main():
    threshold = int(sys.argv[1]) if len(sys.argv) > 1 else 85
    now = datetime.datetime.now()
    try:
        tl, hu = get_vals()
    except Exception:
        return  # 网络错误静默
    tl_pct = tl / TL_MAX * 100
    hu_pct = hu / HUO_MAX * 100
    if tl_pct >= threshold or hu_pct >= threshold:
        tp, ts = predict_full(tl, TL_RATE, TL_MAX, now)
        hp, hs = predict_full(hu, HUO_RATE, HUO_MAX, now)
        print(f"[{now.strftime('%m-%d %H:%M')}] 体力{tl}/{TL_MAX}({tl_pct:.0f}%) 活力{hu}/{HUO_MAX}({hu_pct:.0f}%) >= {threshold}% 触发清空")
        print(f"  预测体力恢复满: {ts}({tp.strftime('%m-%d %H:%M')}) 活力: {hs}({hp.strftime('%m-%d %H:%M')})")
        try:
            r = subprocess.run(["uv", "run", "python", "scripts/consume.py"], cwd=PROJ, capture_output=True, text=True, timeout=400)
            print(f"  清空完成 (exit {r.returncode})")
        except Exception as e:
            print(f"  清空失败: {e}")
    # else: 静默


if __name__ == "__main__":
    main()
