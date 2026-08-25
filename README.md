# Q宠大乐斗自动化助手（daledou）

基于 [gaoyuanqi/daledou](https://github.com/gaoyuanqi/daledou)（MIT）增强版：**日常/周常任务全自动 + 定时调度 + 多账号并发 + 游戏机制研究工具链**。

- 原理：直接请求大乐斗**文字版接口**（不依赖浏览器），`cmd=index&style=1` 获取首页 → 按注册任务逐项执行
- 特点：任务自动感知活动上下架（入口不在首页自动跳过）、体力/活力智能补满、攻击增益道具全用、体力消耗闭环
- 附带：只读快照、战报归档、数值公式研究、活动模板分析等研究工具（`research/`）

## 目录结构

```
daledou/
├── main.py                  # 入口
├── src/
│   ├── cli.py               # 命令行解析
│   ├── run.py               # 任务执行器（多账号并发 + 午间体力消耗收尾）
│   ├── timing.py            # 内置定时调度（13:01 / 20:01）
│   ├── tasks/
│   │   ├── noon.py          # 第一轮任务（日常，建议 13:01 后）
│   │   ├── evening.py       # 第二轮任务（收尾，建议 20:01 后）
│   │   ├── common.py        # 可复用任务函数（体力/活力/拳套/帮派/历练...）
│   │   └── register.py      # 任务注册表
│   └── utils/
│       ├── client.py        # HTTP 客户端（网络超时自动重试）
│       ├── config.py        # YAML 配置 + Cookie 解析
│       ├── daledou.py       # DaLeDou 类（get/find/findall/config/log）
│       └── date_time.py
├── config/
│   ├── default.yaml         # 全局默认配置（任务参数）
│   ├── accounts/<qq>.yaml   # 账号级配置覆盖
│   └── dld_cookie.yaml      # ⚠️ Cookie 凭证（gitignore，需手动创建）
├── research/                # 游戏机制研究工具链 + 文档
│   ├── snapshot.py          # 只读状态快照
│   ├── diff.py              # 快照差分
│   ├── experiment.py        # 免费差分实验
│   ├── battle_reports.py    # 战报归档（逐回合）
│   ├── monitor_claims.py    # 活动监控 + 免费领取
│   ├── 数值公式研究报告.md  # 游戏数值逆向结论（F1-F14）
│   └── ...                  # 更多研究工具/文档
└── run_*.bat                # Windows 定时任务包装脚本
```

## 环境要求

- **Python 3.13+**（推荐 3.14）
- **[uv](https://hellowac.github.io/uv-zh-cn/)** 包管理器
- 系统时区：**上海时间（Asia/Shanghai，UTC+8）**——游戏按自然日结算

## 快速开始

**1、获取项目**

```bash
git clone <你的仓库地址> daledou
cd daledou
```

**2、安装依赖**

```bash
uv sync
```

**3、配置 Cookie**

创建 `config/dld_cookie.yaml`，添加你的大乐斗 Cookie（获取方法见文末 FAQ）：

```yaml
# 大乐斗Cookie，每行一个账号
DALEDOU_COOKIES:
  # - openId=..; accessToken=..; newuin=..
  # - openId=..; accessToken=..; newuin=..
```

**4、验证**

```bash
# 查看全部模块和任务
uv run main.py -h

# 测试单个任务
uv run main.py noon.邪神秘宝
```

**5、启动定时任务（可选）**

```bash
uv run main.py          # 内置调度：13:01 午间 / 20:01 晚间
```

> Windows 下推荐用任务计划程序（schtasks）注册，见 `自动化说明.md` 或研究文档。

## 常用命令

```bash
uv run main.py noon                          # 跑全部午间任务
uv run main.py evening                       # 跑全部晚间任务
uv run main.py noon.幸运金蛋                 # 跑单个任务
uv run main.py 123456789.noon.幸运金蛋       # 指定账号+任务
uv run python research/snapshot.py           # 只读快照（不操作游戏）
uv run python research/battle_reports.py     # 战报归档
```

## 核心机制（扩展任务必读）

### 任务注册名 = 首页链接文本

执行时：请求首页 `cmd=index&style=1` → 检查 HTML 是否存在 `>任务名<` → 存在则执行，不存在静默跳过（活动下架自动失效）。

### 两种注册方式

| 方式 | 适用场景 | 示例 |
|---|---|---|
| **隐式注册**（推荐） | 链接文本是合法 Python 标识符 | `@register()` + `async def 邪神秘宝()` |
| **显式注册** | 链接文本含特殊字符 | `@register("5.1礼包")` |

```python
# ✅ 隐式注册：函数名 = 链接文本 = "邪神秘宝"
@register()
async def 邪神秘宝(d: DaLeDou):
    await c_邪神秘宝(d)

# ❌ 错误：注册名与首页文本不一致，任务永远不会执行
@register("邪神宝藏")
async def 邪神秘宝(d: DaLeDou):
    ...
```

### 配置系统

- 优先级：账号配置 `config/accounts/<qq>.yaml` → 默认配置 `config/default.yaml` → 抛异常
- 读取：`d.config("矿洞.floor")`（键路径用 `.` 分隔，禁止包含模块名前缀）

```python
floor = d.config("矿洞.floor")
enabled = d.config("门派.门派高香.enabled")
```

### 本仓库特色功能（相对上游新增）

| 功能 | 位置 | 说明 |
|---|---|---|
| **恢复** | `noon.py` | 体力补满 100 / 活力补满 50，按缺口选最小药水不浪费；拳套全用 |
| **变强** | `noon.py` | 周日集中强化（铁匠铺/星石/武器必成），记录战力变化 |
| **开通达人** | `noon.py` | 斗豆月卡领取 + 达人周卡续费 |
| **九宫宝库 / 幸运鹅** | `noon.py` | 活动白嫖（实测黄金卷轴等） |
| **消耗体力收尾** | `run.py` | 午间所有任务后，好友战循环打空体力+药水（不浪费自然恢复） |
| **活动监控** | `research/monitor_claims.py` | 每小时检测活动上下架 + 自动领取免费奖励 |
| **研究工具链** | `research/` | 快照/差分/实验/战报/数值公式/接口字典 |

## 研究文档（research/）

| 文档 | 内容 |
|---|---|
| `数值公式研究报告.md` | 游戏数值逆向：经验曲线/体力恢复/药水性价比等（F1-F14） |
| `接口字典.md` | 94 个游戏接口参数与返回结构 |
| `数据结构与服务器层面研究.md` | 服务器数据契约、每日观测 |
| `活动模板对照表.md` | 活动抽象结构与入口免费性审计 |
| `任务时间窗口与货币表.md` | 四资源账本审计 |
| `每日流程与产出说明.md` | 每日自动化流程与实测产出 |
| `研究数据包-脱敏版.md` | 对外安全的研究数据摘要 |

> 研究文档为原创桌宠游戏设计提供数值参考，已在文档中标注"不可迁移"边界。

## 常见问题

**Q: 大乐斗文字版链接**

**A:** https://dld.qzapp.z.qq.com/qpet/cgi-bin/phonepk?cmd=index&style=1

**Q: 如何获取大乐斗 Cookie**

**A:** 以安卓为例
1. 应用商店安装 **Via 浏览器** 并设为默认浏览器
2. 用 Via 访问文字版链接，选择**一键登录**（不要账号密码登录）
3. 登录后等 5 秒，Via 左上角出现 ✓ 图标，点击它
4. 选择 **查看 cookies**，复制 cookie 即可

**Q: 脚本是否会扣除鹅币/斗豆/斗币**

**A:** 不会。对娃娃机、神魔转盘、深渊秘宝等可能扣费的入口有前置判断；但页面更新可能导致失效，发现请提交 Issue。

**Q: 定时任务如何配置**

**A:** Windows 任务计划程序（schtasks）注册 `run_*.bat`，注意路径含空格时 `/TR` 需用 `\"` 转义。示例见研究文档。

## 许可证

[MIT License](LICENSE) — 上游原作者 [gaoyuanqi](https://github.com/gaoyuanqi)（雨园），本仓库为增强维护版。

## 致谢

- 上游项目：[gaoyuanqi/daledou](https://github.com/gaoyuanqi/daledou)
- 本仓库在保留全部上游任务的基础上，增加了资源管理、体力消耗闭环、活动监控与游戏机制研究工具链
