# -*- coding: utf-8 -*-
"""清空脚本：只跑 历练(清活力) + 消耗体力(清体力)，供定时多次清空。
用法: uv run python log/consume.py
2026-08-31 用户指令"定时多次清空"：午后/晚间体力恢复满后再次清空，避免浪费自然恢复。
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.config import Config, ConfigResolver
from src.utils.client import Client
from src.utils.daledou import DaLeDou
from src.tasks.noon import 历练
from src.tasks.common import c_消耗体力
from src.tasks.register import TaskModule


async def run_account(qq: str, cookie: dict):
    async with Client(qq, cookie) as client:
        cr = ConfigResolver(qq, TaskModule.noon)
        d = DaLeDou(qq, client, cr)
        index_html = await d.get("cmd=index&style=1")
        if "邪神秘宝" not in index_html:
            print(f"{qq}: 非大乐斗首页(繁忙/维护)，跳过")
            return
        # 1) 历练清活力（遍历所有可挑战BOSS）
        d.task_name = "历练"
        await 历练(d)
        # 2) 消耗体力清空（打所有好友+补体力药水直到0）
        d.task_name = "消耗体力"
        await c_消耗体力(d)
        print(f"{qq}: 清空完成")


async def main():
    cookies = Config.load_cookies()
    if not cookies:
        print("未配置大乐斗 Cookie")
        sys.exit(1)
    for qq, cookie in cookies.items():
        try:
            await run_account(qq, cookie)
        except Exception as e:
            print(f"{qq}: 清空失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
