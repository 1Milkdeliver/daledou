"""research/snapshot.py — 只读账号状态快照（不执行任何游戏操作）

用法:
    uv run python research/snapshot.py [--out 输出路径]

输出:
    JSON 文件，默认 log/snapshots/YYYY-MM-DD_HHMMSS.json
    包含: 角色信息、今日可用任务入口、任务列表、活跃度、好友数等
    并保留每个页面的原始 HTML，供机制研究/差分实验使用。
"""
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# 先初始化任务注册表，避免 config 循环导入（与 main.py 的导入顺序保持一致）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import src.tasks.register  # noqa: F401
from src.tasks.register import get_all_modules, get_module_tasks
from src.utils.config import Config
from src.utils.client import Client

# 只读页面清单: (名称, cmd 参数)
PAGES = [
    ("index", "cmd=index&style=1"),             # 首页：角色信息 + 今日入口
    ("task", "cmd=task&sub=1"),                 # 任务列表
    ("liveness", "cmd=liveness"),               # 今日活跃度
    ("ledouvip", "cmd=ledouvip"),               # 乐斗达人等级
    ("friendlist", "cmd=friendlist&page=1"),    # 好友列表
    ("calender", "cmd=calender&op=2"),          # 乐斗黄历
    # —— 研究扩展页（对应 Codex 研究主题，均为首页导航级只读页）——
    ("battle_records", "cmd=info"),             # 乐斗记录（战报）
    ("bag", "cmd=store"),                       # 背包（材料清单）
    ("shop", "cmd=viewshop&type=3&shop=1&page=1"),   # 商店
    ("upgrade", "cmd=viewupdate"),              # 强化（成长树）
    ("blacksmith", "cmd=black_smith&op=0&type_id=0"),  # 铁匠铺（成长树）
    ("astrolabe", "cmd=astrolabe"),             # 星盘（成长树）
    ("ancient_gods", "cmd=ancient_gods&op=1&id=1"),    # 神魔录（保底机制）
    ("mercenary", "cmd=newmercenary"),          # 佣兵（成长树）
    ("enchant", "cmd=enchant"),                 # 器魂附魔（成长树）
    ("formation", "cmd=formation"),             # 助阵（成长树）
    ("inlaypearl", "cmd=inlaypearl&subcmd=index"),     # 镶嵌（成长树）
    ("badge", "cmd=achievement"),               # 徽章馆（外观收藏）
    ("glory", "cmd=glory"),                     # 荣耀成就（外观收藏）
    ("rank", "cmd=perrank&sev=-1"),             # 排行（社交/榜单）
    ("fame_hall", "cmd=fame_hall"),             # 名人堂（社交/榜单）
    ("disciple", "cmd=disinfo"),                # 师徒（异步社交）
]


def parse_character(html: str) -> dict:
    """从首页解析角色属性（结构来自实际抓包: 等级:86(73401/118350) 等）"""
    info = {}
    for pattern, key in [
        (r"等级:(\d+)\((\d+)/(\d+)\)", "level"),        # 等级:86(73401/118350)
        (r"体力:(\d+)/(\d+)", "stamina"),               # 体力:93/100
        (r"活力:(\d+)/(\d+)", "vitality"),              # 活力:1/50
        (r"阅历:(\d+)", "exp"),                         # 阅历:135779
        (r"战斗力[^：:]{0,30}[：:]([\d.]+)", "power"),   # 战斗力</tag>:1359.4
        (r"斗豆[^：:]{0,30}[：:]([\d]+)", "doucoin"),   # 斗豆:74
        (r"斗币[^：:]{0,30}[：:]([\d]+)", "doubi"),     # 斗币:4940
        (r"鹅币[^：:]{0,30}[：:]([\d.]+)", "ebi"),      # 鹅币：0.00
        (r"今日活跃度[^：:]{0,30}[：:]([\d]+)", "liveness"),  # 今日活跃度:55
        (r"当前级别[^：:]{0,30}[：:]([\d]+)", "vip_level"),   # 达人页面
    ]:
        m = re.search(pattern, html)
        if m:
            groups = m.groups()
            info[key] = groups[0] if len(groups) == 1 else groups
    return info


def available_tasks(index_html: str) -> dict[str, list[str]]:
    """对比首页链接与注册任务，得到“今日可做”任务清单"""
    result = {}
    for module in get_all_modules():
        registry = get_module_tasks(module)
        result[module.value] = [
            name for name in registry if f">{name}<" in index_html
        ]
    return result


async def fetch_all(cookies: dict[str, dict[str, str]]):
    """为每个账号抓取全部只读页面"""
    snapshots = {}
    for qq, cookie in cookies.items():
        pages = {}
        async with Client(qq, cookie) as client:
            for name, cmd in PAGES:
                try:
                    html = await client.get(cmd)
                except Exception as e:  # 单页失败不影响整体
                    html = f"<error>{e}</error>"
                pages[name] = {
                    "raw_html": html,
                    "preview": re.sub(r"<[^>]+>", " ", html)[:300],
                }

            # 战报详情：从乐斗记录里取第一条战报的完整 href 查询串（含 zapp_uin/sid 前缀，只读）
            try:
                records_html = pages["battle_records"]["raw_html"]
                m = re.search(r'phonepk\?([^"\'<>]+)"[^>]*>查看乐斗过程', records_html)
                if m:
                    detail_html = await client.get(m.group(1).replace("&amp;", "&"))
                    pages["battle_detail"] = {
                        "raw_html": detail_html,
                        "preview": re.sub(r"<[^>]+>", " ", detail_html)[:300],
                    }
            except Exception:
                pass

        index_html = pages["index"]["raw_html"]
        snapshots[qq] = {
            "character": parse_character(index_html),
            "available_tasks": available_tasks(index_html),
            "pages": pages,
        }
    return snapshots


def main():
    out_arg = None
    if "--out" in sys.argv:
        out_arg = sys.argv[sys.argv.index("--out") + 1]

    cookies = Config.load_cookies()
    if not cookies:
        print("未加载到 cookie，请检查 config/dld_cookie.yaml")
        sys.exit(1)

    data = asyncio.run(fetch_all(cookies))
    data["_meta"] = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "note": "只读快照：不执行任何游戏操作",
    }

    out_path = Path(out_arg) if out_arg else (
        Path("log/snapshots") / datetime.now().strftime("%Y-%m-%d_%H%M%S.json")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 控制台摘要
    for qq, s in data.items():
        if qq == "_meta":
            continue
        print(f"=== {qq} ===")
        print(f"角色: {s['character']}")
        for module, tasks in s["available_tasks"].items():
            print(f"[{module}] 今日可做 {len(tasks)} 个: {', '.join(tasks[:10])}{'...' if len(tasks) > 10 else ''}")
    print(f"\n快照已保存: {out_path}")


if __name__ == "__main__":
    main()
