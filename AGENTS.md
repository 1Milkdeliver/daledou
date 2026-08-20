# AGENTS.md — Codex 操作手册（Q宠大乐斗自动化）

> 本文件由 Codex CLI 在启动时自动读取。请先完整阅读本文件再执行任何操作。
>
> **📌 完整交接文档见同目录 `CODEX接手说明.md`**——包含全部具体路径、调用值、
> 指令清单、维护流程和授权范围。开工前务必通读它；本文件是速查版。

## 这是什么

Q宠大乐斗（腾讯 QQ 网页游戏）的日常/周常任务**自动化脚本**，基于开源项目
[gaoyuanqi/daledou](https://github.com/gaoyuanqi/daledou)（MIT）。
原理：直接请求游戏**文字版接口**，不依赖浏览器：

- 游戏地址：`https://dld.qzapp.z.qq.com/qpet/cgi-bin/phonepk?cmd=index&style=1`
- 鉴权方式：HTTP Cookie（`openId` / `accessToken` / `newuin` 等）
- 每个"任务"就是若干次带参数的 GET 请求 + 对返回 HTML 的正则解析

## 目录结构（本仓库 = 上游 + 本地补丁）

```
daledou/
├── main.py                  # 入口
├── src/
│   ├── cli.py               # 命令行解析
│   ├── run.py               # 任务执行器（多账号并发）
│   ├── timing.py            # 内置定时调度（13:01 / 20:01）
│   ├── tasks/
│   │   ├── noon.py          # 第一轮任务（日常，建议 13:01 后）
│   │   ├── evening.py       # 第二轮任务（收尾，建议 20:01 后）
│   │   ├── common.py        # 可复用任务函数
│   │   └── register.py      # 任务注册表（TaskModule: noon/evening）
│   └── utils/
│       ├── client.py        # HTTP 客户端（本地补丁：网络超时自动重试）
│       ├── config.py        # YAML 配置 + Cookie 解析
│       ├── daledou.py       # DaLeDou 类（get/find/findall/config/log）
│       └── date_time.py
├── config/
│   ├── default.yaml         # 全局默认配置（任务参数）
│   ├── accounts/<qq>.yaml   # 账号级配置覆盖（gitignore）
│   └── dld_cookie.yaml      # ⚠️ Cookie 凭证（gitignore，勿外传）
├── log/                     # 运行日志（按账号/日期）
├── update.ps1               # 订阅上游自动更新脚本
├── run_noon.bat / run_evening.bat / update_run.bat   # Windows 定时任务包装
└── 自动化说明.md            # 中文使用文档
```

## 核心机制（扩展任务必读）

**任务注册名 = 游戏首页链接文本。** 执行时：

1. 请求首页 `cmd=index&style=1`
2. 检查 HTML 里是否存在 `>任务名<`
3. 存在 → 执行对应注册函数；不存在 → 静默跳过（活动下架自动失效）

所以**新增/改名任务时，注册名必须与首页链接文本完全一致**，否则永不执行。

## 常用命令（工作目录必须是 D:\Deepseek Harness\daledou）

```bat
uv run main.py -h                              :: 列出全部模块和任务
uv run main.py noon.邪神秘宝                   :: 单任务（所有账号）
uv run main.py noon                            :: noon 模块全部任务
uv run main.py evening                         :: evening 模块全部任务
uv run main.py 1206423023.noon.幸运金蛋        :: 指定账号+任务
uv run main.py                                 :: 内置定时守护（13:01/20:01）
powershell -File update.ps1                    :: 手动检查上游更新
```

运行环境：`uv` 已装，依赖在 `.venv`（Python 3.14，由 uv 管理）。

## 日志

- `log/1206423023/2026-08-20.log` — 每个账号每天一个文件（loguru，UTF-8）
- `log/update.log` — 上游订阅更新日志
- `log/scheduler_noon.log`、`log/scheduler_evening.log` — 定时任务输出
- 每次运行结束打印统计：`成功：N | 失败：M`，失败会带原因

## Windows 定时任务（已注册，勿重复创建）

| 任务名 | 时间 | 作用 |
| --- | --- | --- |
| `daledou-update` | 每天 09:00 | `update.ps1`：fetch 上游 → rebase → 冒烟测试 |
| `daledou-noon` | 每天 13:05 | `run_noon.bat`：跑全部日常 |
| `daledou-evening` | 每天 20:05 | `run_evening.bat`：跑收尾任务 |
| `daledou-snapshot` | 每天 22:00 | `run_snapshot.bat`：只读快照 + 研究数据包自动更新 |

查询：`schtasks /Query /TN daledou-noon /FO LIST`；删除：`schtasks /Delete /TN xxx /F`

## 上游订阅 / git 工作流

- `origin` = 上游 `https://github.com/gaoyuanqi/daledou.git`
- 本地在 `main` 上维护少量自己的 commit（超时重试补丁、bat、文档、AGENTS.md）
- `update.ps1`：`git fetch origin --tags` → 有上游提交则 `git rebase origin/main`（本地提交自动保留）→ `uv run main.py -h` 冒烟 → 写 `log/update.log`
- **冲突时 update.ps1 会停止并写日志，绝不自动覆盖**。处理流程：
  1. `git status` 查看冲突文件
  2. 多数情况只需把 `src/utils/client.py` 的超时重试补丁重新应用
  3. `git add -A && git rebase --continue`
  4. 重新跑冒烟测试
- 提交规范：本地 commit 用 `chore:` / `docs:` / `fix:` 前缀，保持简洁。

## 如何新增游戏任务（游戏出新活动时）

1. **抓包**：浏览器登录文字版页面（README 里有 Via 浏览器获取 cookie 的方法），
   F12 → Network → Preserve log，手动点一遍新活动，记录每个请求的
   `cmd=xxx&op=xxx&id=xxx` 参数和返回 HTML 结构。
2. **确认注册名**：首页该活动的 `<a ...>活动名</a>` 链接文本。
3. **写任务函数**（在 `src/tasks/noon.py` 或 `evening.py`，参考 `common.py` 风格）：

```python
@register()  # 函数名必须 = 首页链接文本
async def 新活动名(d: DaLeDou):
    await d.get("cmd=xxx&op=yyy")           # 打开活动页
    # 用 d.findall(正则) 提取 HTML 里的按钮参数，逐个 d.get(...) 完成操作
    d.log(d.find(r"</p>(.*?)<br />"))        # 记录操作结果
```

4. 可选：在 `config/default.yaml` 对应模块下加配置键，代码里 `d.config("键.子键")` 读取。
5. **测试**：`uv run main.py noon.新活动名`（确认无报错、结果符合预期）。
6. `git add -A && git commit -m "feat: 新增新活动名任务"`。

## ⚠️ 安全与红线（必须遵守）

1. **Cookie 是账号凭证**：`config/dld_cookie.yaml` 已在 `.gitignore`，**禁止**把它
   commit、打印到日志/回复、或贴到任何外部渠道。涉及 cookie 内容的操作只在本地。
2. **禁止消耗游戏货币**：默认不扣鹅币/斗豆/斗币。写新任务时对可能扣费的入口
   （娃娃机、神魔转盘、深渊秘宝抽奖等）必须先判断余额/免费次数，参考 common.py 现有实现。
3. **运行任务已获用户授权**：用户已明确授权你直接用本地 cookie 和脚本干活——
   `uv run main.py noon` / `evening` / 单任务 等**现有任务可以运行**，这是它的日常用途。
   仍需遵守：
   - 新写的任务代码先用单任务测试（`uv run main.py noon.新任务名`），确认无异常后再提交；
     未经确认不要整模块跑你自己新写的、未测试过的代码。
   - 永远不要主动引入消耗鹅币/斗豆/斗币的行为（默认不扣费）。
   - 只读操作（`-h`、看日志、`git log`、分析抓包）随时可做。
4. 系统时区必须为上海时间（UTC+8）——游戏按自然日结算。
5. 不要改动上游的 `src/tasks/*.py` 里与本仓库无关的逻辑；本地改动保持最小，
   便于 rebase 无冲突。

## 常见运维任务（用户可能会让你做）

- **检查今天任务执行情况**：读 `log/1206423023/` 下今天的日志，汇总成功/失败/异常
- **游戏更新了新活动**：按"如何新增游戏任务"流程，帮用户写任务代码
- **上游更新了**：跑 `update.ps1`；有冲突则按 git 工作流处理
- **cookie 失效**（页面提示登录/重定向）：提示用户重新抓取 cookie 更新
  `config/dld_cookie.yaml`，不要试图用旧 cookie 硬闯
- **定时任务状态**：`schtasks /Query /TN daledou-noon /FO LIST`

## 机制研究工具（research/ 目录）

用户在做乐斗机制研究（为原创游戏设计参考 + 自动化优化），有现成工具：

- `uv run python research/snapshot.py` — 只读状态快照（角色属性/今日可做入口/各页面 HTML）
- `uv run python research/diff.py 快照A 快照B` — 前后差分
- `uv run python research/experiment.py 模块.任务` — 差分实验（快照→跑任务→快照→diff）

详见 `research/README.md`。注意：只有 experiment.py 会真实操作游戏，选免费任务且遵守每日次数。
