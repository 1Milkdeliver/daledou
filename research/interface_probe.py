"""research/interface_probe.py — 接口数据交互层探测（全部只读，安全）

探测项：
  1. 响应头 / 协议版本（Server、Cache、Set-Cookie、http_version）
  2. 无效 cmd 的错误处理行为
  3. 缺省参数行为（cmd=index 不带 style）
  4. 频率限制：快速连续请求 cmd=index，统计"系统繁忙"与延迟
  5. 分页边界：背包/好友列表 page=999
  6. User-Agent 校验：curl UA / 无 UA
  7. 乐斗记录保留深度（今天/昨天/更早）
  8. 动作级限流证据：从日志找"刷新过于频繁"等提示

用法: uv run python research/interface_probe.py
"""
import asyncio
import json
import re
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import src.tasks.register  # noqa: F401
from src.utils.config import Config

BASE = "https://dld.qzapp.z.qq.com/qpet/cgi-bin/phonepk?"
CHROME_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0")


def make_client(cookies: dict, ua: str | None = CHROME_UA) -> httpx.AsyncClient:
    headers = {"User-Agent": ua} if ua else {}
    return httpx.AsyncClient(headers=headers, cookies=cookies, timeout=10.0,
                             follow_redirects=True)


async def probe_headers(client: httpx.AsyncClient, path: str = "cmd=index&style=1"):
    r = await client.get(BASE + path)
    return {
        "http_version": getattr(r, "http_version", "?"),
        "status": r.status_code,
        "server": r.headers.get("server"),
        "cache_control": r.headers.get("cache-control"),
        "expires": r.headers.get("expires"),
        "content_type": r.headers.get("content-type"),
        "set_cookie": r.headers.get_list("set-cookie")[:3],
        "size": len(r.text),
        "has_系统繁忙": "系统繁忙" in r.text,
    }


async def probe_invalid_cmd(client: httpx.AsyncClient, cmd: str):
    r = await client.get(BASE + f"cmd={cmd}")
    text = re.sub(r"<[^>]+>", "|", r.text)
    text = re.sub(r"\s+", " ", text).strip()
    return {"cmd": cmd, "status": r.status_code, "size": len(r.text),
            "text_head": text[:120]}


async def probe_rate(client: httpx.AsyncClient, n: int = 20):
    """快速连发 n 次只读请求，统计繁忙/耗时"""
    results = {"total": n, "busy": 0, "ok": 0, "times_ms": [], "min_ms": None,
               "max_ms": None, "avg_ms": None}
    for i in range(n):
        t0 = time.perf_counter()
        r = await client.get(BASE + "cmd=index&style=1")
        ms = (time.perf_counter() - t0) * 1000
        results["times_ms"].append(round(ms, 1))
        if "系统繁忙" in r.text:
            results["busy"] += 1
        else:
            results["ok"] += 1
        if i < n - 1:
            await asyncio.sleep(0)  # 不主动间隔，测原始吞吐
    ts = results["times_ms"]
    results["min_ms"], results["max_ms"] = min(ts), max(ts)
    results["avg_ms"] = round(sum(ts) / len(ts), 1)
    return results


async def probe_pagination(client: httpx.AsyncClient):
    out = {}
    for name, path in [("bag_p999", "cmd=store&page=999"),
                       ("friendlist_p999", "cmd=friendlist&page=999"),
                       ("friendlist_p0", "cmd=friendlist&page=0")]:
        r = await client.get(BASE + path)
        text = re.sub(r"<[^>]+>", "|", r.text)
        text = re.sub(r"\s+", " ", text).strip()
        out[name] = {"size": len(r.text), "head": text[:100]}
    return out


async def probe_ua(client_no_ua: httpx.AsyncClient, client_curl: httpx.AsyncClient):
    out = {}
    r1 = await client_no_ua.get(BASE + "cmd=index&style=1")
    out["no_ua"] = {"size": len(r1.text), "busy": "系统繁忙" in r1.text}
    r2 = await client_curl.get(BASE + "cmd=index&style=1")
    out["curl_ua"] = {"size": len(r2.text), "busy": "系统繁忙" in r2.text}
    return out


async def probe_record_depth(client: httpx.AsyncClient):
    r = await client.get(BASE + "cmd=info")
    text = re.sub(r"<[^>]+>", "|", r.text)
    text = re.sub(r"\s+", " ", text).strip()
    records = re.findall(r"\d+:([^|]{3,80})", text)
    dates = re.findall(r"(今天|昨天|\d+月\d+日)", text)
    return {"record_count": len(records), "date_labels": sorted(set(dates)),
            "sample": records[:3]}


async def main():
    cookies = Config.load_cookies()
    qq, cookie = next(iter(cookies.items()))
    print(f"=== 接口数据交互层探测（账号已脱敏）===")
    report = {}

    async with make_client(cookie) as c, \
               make_client(cookie, ua=None) as c_no_ua, \
               make_client(cookie, ua="curl/8.0.0") as c_curl:
        report["headers"] = await probe_headers(c)
        print("\n[1] 响应头/协议:", json.dumps(report["headers"], ensure_ascii=False))

        report["invalid"] = []
        for cmd in ["__no_such_cmd_xyz__", "", "index&style=1;cat", "login"]:
            report["invalid"].append(await probe_invalid_cmd(c, cmd))
        print("\n[2] 无效 cmd 行为:")
        for x in report["invalid"]:
            print("   ", json.dumps(x, ensure_ascii=False))

        report["rate"] = await probe_rate(c)
        print("\n[3] 频率限制（20 连发 cmd=index）:")
        print("   ", json.dumps({k: v for k, v in report["rate"].items()
                                 if k != "times_ms"}, ensure_ascii=False))
        print("    前8次耗时(ms):", report["rate"]["times_ms"][:8])

        report["pagination"] = await probe_pagination(c)
        print("\n[4] 分页边界:")
        for k, v in report["pagination"].items():
            print(f"   {k}: {v}")

        report["ua"] = await probe_ua(c_no_ua, c_curl)
        print("\n[5] User-Agent 校验:", json.dumps(report["ua"], ensure_ascii=False))

        report["record_depth"] = await probe_record_depth(c)
        print("\n[6] 乐斗记录深度:", json.dumps(report["record_depth"], ensure_ascii=False))

    out = Path("log/interface_probe.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完整报告: {out}")


if __name__ == "__main__":
    asyncio.run(main())
