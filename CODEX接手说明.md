# Codex 直接接手说明（Q宠大乐斗自动化）

> 本文件是给你的**完整交接文档**。请先通读，然后按里面的指令干活。
> 项目在你机器上的位置：`D:\Deepseek Harness\daledou`（所有操作都在这个目录下进行）。
> 你的登录凭证（cookie）已经在本地配置好，直接可用，不需要你再提供任何账号信息。

---

## 一、项目概况

这是一个 **Q宠大乐斗**（腾讯 QQ 网页游戏）的日常/周常任务自动化脚本，基于开源项目
[gaoyuanqi/daledou](https://github.com/gaoyuanqi/daledou)（MIT 协议，已克隆到本地并保持订阅更新）。

**工作原理**：不依赖浏览器，直接用 Python 请求游戏**文字版接口**：

- 游戏地址：`https://dld.qzapp.z.qq.com/qpet/cgi-bin/phonepk?cmd=index&style=1`
- 鉴权：HTTP Cookie（`openId`、`accessToken`、`newuin` 等）
- 每个"任务"= 若干次带参数的 GET 请求 + 用正则解析返回的 HTML，自动完成领奖/乐斗/兑换等操作
- 支持多账号并发、定时调度

**游戏账号 QQ：`1206423023`**（当前唯一配置的账号）

---

## 二、环境与关键值（直接调用）

| 项目 | 值 |
| --- | --- |
| 工作目录 | `D:\Deepseek Harness\daledou`（所有命令都在这里执行） |
| 运行器 | `uv`（已装），依赖在 `.venv`（Python 3.14） |
| Cookie 配置文件 | `config\dld_cookie.yaml` —— **已配置好且验证有效**，内有 `openId`/`accessToken`/`newuin` 等字段 |
| 账号级配置 | `config\accounts\1206423023.yaml`（自动生成，可覆盖默认配置） |
| 全局配置 | `config\default.yaml`（任务参数都在这里） |
| 运行日志 | `log\1206423023\YYYY-MM-DD.log`（每天一个，UTF-8） |
| 更新日志 | `log\update.log` |
| 定时任务输出 | `log\scheduler_noon.log`、`log\scheduler_evening.log` |
| 上游仓库 | `https://github.com/gaoyuanqi/daledou.git`（本地 `origin`） |

> ⚠️ **Cookie 使用方式**：读取 `config\dld_cookie.yaml` 即可（脚本自动加载）。
> **禁止**把 cookie 内容打印到对话、日志或 commit 里；cookie 文件已被 `.gitignore` 忽略，保持不动。

---

## 三、常用指令（Codex 直接发）

```bat
cd /d D:\Deepseek Harness\daledou

uv run main.py -h                               :: 查看全部模块和任务清单
uv run main.py noon                             :: 跑全部日常任务（第一轮，建议13:01后）
uv run main.py evening                          :: 跑收尾任务（第二轮，建议20:01后）
uv run main.py noon.邪神秘宝                    :: 只跑某一个任务
uv run main.py 1206423023.noon.幸运金蛋         :: 指定账号+任务
powershell -ExecutionPolicy Bypass -File update.ps1   :: 手动检查/合并上游更新
git log --oneline -10                          :: 查看最近提交
schtasks /Query /TN daledou-noon /FO LIST      :: 查定时任务
```

**任务模块说明**：
- `noon` 模块：第一轮日常任务（斗神塔、乐斗、竞技场、矿洞、帮派、深渊之潮等约 60 个）
- `evening` 模块：第二轮收尾任务（帮派商会、侠士客栈、每日宝箱、兑换等）
- 任务自动跳过：脚本先抓首页，只有首页出现该任务链接文本才执行（游戏下架的活动自动跳过）

---

## 四、每日自动化（已就绪，无需你干预）

Windows 任务计划程序已注册三个定时任务，电脑开着到点自动跑：

| 任务名 | 时间 | 干什么 |
| --- | --- | --- |
| `daledou-update` | 每天 09:00 | 订阅上游：fetch → rebase 合并 → 冒烟测试 |
| `daledou-noon` | 每天 13:05 | 跑全部日常任务 |
| `daledou-evening` | 每天 20:05 | 跑收尾任务 |

你的职责主要是：**检查结果、处理异常、游戏更新时补新任务、上游冲突时修复**。

---

## 五、怎么检查运行结果

```bat
:: 看今天某个任务的执行情况
Get-Content "D:\Deepseek Harness\daledou\log\1206423023\2026-08-20.log"

:: 看定时任务是否报错
Get-Content "D:\Deepseek Harness\daledou\log\scheduler_noon.log" -Tail 30
Get-Content "D:\Deepseek Harness\daledou\log\scheduler_evening.log" -Tail 30
```

每次运行结束会打印：`成功：N | 失败：M` + 失败原因统计。
典型正常输出（UTF-8，乱码是控制台代码页问题，读文件用 `-Encoding UTF8`）：
```
邪神秘宝：恭喜您获得蓝色奖励：三彩水晶石*6.
所有账号处理完成 | 成功：1 | 失败：0
```

---

## 六、维护上游项目（订阅与合并）

```bat
powershell -ExecutionPolicy Bypass -File update.ps1
```

`update.ps1` 会自动：fetch 上游 → 有更新则 `git rebase origin/main`（本地补丁自动保留）→
跑冒烟测试 → 结果写 `log\update.log`。

**冲突处理流程**（脚本遇到冲突会停止，绝不自动覆盖）：
1. `git status` 看冲突文件
2. 通常只需把 `src\utils\client.py` 里的**超时重试补丁**重新应用（上游若改了这个文件）
3. `git add -A` → `git rebase --continue`
4. 重新 `uv run main.py -h` 冒烟，确认正常

**本地维护的补丁清单**（rebase 时要保留）：
- `src\utils\client.py`：网络超时（ConnectTimeout/ReadTimeout）自动重试
- `run_noon.bat` / `run_evening.bat` / `update_run.bat` / `update.ps1`：Windows 定时调度
- `自动化说明.md`、`AGENTS.md`、`codex_prompts.md`、本文件：文档

---

## 七、游戏出新活动 → 写新任务（核心维护工作）

**机制（必须理解）**：任务注册名 = 游戏首页的链接文本。脚本抓首页 `cmd=index&style=1`，
HTML 里有 `>任务名<` 才执行该任务。所以新任务函数名必须和首页文本一致。

**步骤**：
1. **抓包**：浏览器打开 `https://dld.qzapp.z.qq.com/qpet/cgi-bin/phonepk?cmd=index&style=1`（用已有 cookie 登录），
   F12 → Network → Preserve log，手动点一遍新活动，记录每个请求的 `cmd=xxx&op=xxx&id=xxx` 参数和返回 HTML。
2. **确定注册名**：首页该活动的 `<a ...>活动名</a>` 文本。
3. **写任务**（加到 `src\tasks\noon.py` 或 `evening.py`，参考 `src\tasks\common.py` 风格）：

```python
@register()  # 函数名 = 首页链接文本
async def 新活动名(d: DaLeDou):
    await d.get("cmd=xxx&op=yyy")           # 打开活动页
    # 用 d.findall(正则) 从 HTML 提取按钮参数，逐个 d.get(...) 完成操作
    # 例：for _id, t in d.findall(r'gift_id=(\d+)&amp;type=(\d+)">点击领取'):
    #         await d.get(f"cmd=fac_corp&op=3&gift_id={_id}&type={t}")
    d.log(d.find(r"</p>(.*?)<br />"))        # 记录结果
```

4. 需要参数化时，在 `config\default.yaml` 对应模块下加配置，代码用 `d.config("键.子键")` 读取。
5. **测试**（只测新任务，别跑整个模块）：`uv run main.py noon.新活动名`
6. 提交：`git add -A && git commit -m "feat: 新增新活动名任务"`

**参考样例**（现有任务，可直接模仿）：
```python
async def c_邪神秘宝(d: DaLeDou):
    """高级秘宝/极品秘宝：免费抽奖"""
    for i in [0, 1]:
        await d.get(f"cmd=tenlottery&op=2&type={i}")
        d.log(d.find(r"】</p>(.*?)<br />"))
```

---

## 八、常用配置值（改任务行为时调用）

配置文件 `config\default.yaml`，键路径用 `.` 分隔（`d.config("矿洞.floor")`）：

| 配置键 | 含义 | 示例值 |
| --- | --- | --- |
| `noon.矿洞.floor` | 矿洞副本层数 | `1`（1~5） |
| `noon.矿洞.mode` | 矿洞难度 | `1`（简单/普通/困难） |
| `noon.竞技场.河图洛书.enabled` | 是否兑换河图洛书 | `true` |
| `noon.好友.贡献药水.count` | 每天用几次贡献药水 | `4` |
| `noon.历练` | BOSS 乐斗次数（id: 次数） | `6114: 3` |
| `noon.幻境.id` | 幻境副本 | `20`（鹅王的试炼） |
| `noon.华山论剑.战阵调整` | 挑战编队（侠士名单） | `[{count: 8, knights: [...]}]` |
| `noon.深渊之潮.深渊秘境.id` | 深渊秘境副本 | `1`（崎岖斗界） |
| `evening.背包.使用` | 自动使用物品关键字 | `[盒, 包, 箱, 锦囊...]` |
| `evening.兑换码` | 微信兑换码 | `161616` |
| `evening.生肖福卡.QQ` | 分享福卡给哪个好友 | QQ 号或 `null` |

> 改配置后不用重启任何东西，下次运行即生效。

---

## 九、授权与红线（重要）

**已授权**：你（Codex）可以直接使用本地 cookie 和脚本干活，包括：
- 运行任务、查看日志、诊断问题
- 合并上游更新、写新任务、修 bug、提交本地 commit

**红线（必须遵守）**：
1. **Cookie 保密**：`config\dld_cookie.yaml` 里的内容禁止打印/外传/commit。
2. **不消耗游戏货币**：默认不扣鹅币/斗豆/斗币。写新任务时，对可能扣费的入口
   （娃娃机、神魔转盘、深渊秘宝抽奖等）必须先做免费次数/余额判断（参考现有实现）。
3. **先测后跑**：新写的任务先用 `uv run main.py noon.新任务名` 单测，确认正常再提交；
   不要未经确认就跑整个 `noon` 模块。
4. **系统时区**：必须保持上海时间（UTC+8），游戏按自然日结算。
5. **改动最小化**：尽量不改上游逻辑，本地补丁越少，rebase 越省事。

---

## 十、交接后第一件事

启动后建议先做这 3 步，确认环境没问题：
1. `uv run main.py -h` —— 确认 CLI 能加载（会列出任务清单）
2. 读今天日志 `log\1206423023\` 下最新文件，向用户汇报运行情况
3. `git log --oneline -5` + 跑一次 `update.ps1` 确认上游是最新

然后就绪，随时等用户的指令（检查/写新任务/修问题/合上游）。
