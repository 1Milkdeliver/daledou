# research/ — 乐斗机制研究工具（只读优先）

对应 Codex 研究方案（先读状态 → 最小实验 → 前后差分 → 建模）的落地工具。
**所有快照操作都是只读的**；只有 experiment.py 第 2 步会真实执行游戏任务，请只选免费/无消耗的任务。

> 📄 **研究产出**：`研究数据包-脱敏版.md` —— 不含账号/路径/接口参数的玩法情报汇总，
> 可直接发给 Codex 做机制分析或上传研究文档。含账号状态的原始情报在 `情报汇总.md`（git 不跟踪，仅本机）。

## 工具

| 工具 | 用法 | 作用 |
| --- | --- | --- |
| `snapshot.py` | `uv run python research/snapshot.py` | 只读状态快照：角色属性（等级/体力/活力/战力/斗豆/斗币/鹅币/活跃度）、今日可做任务入口（对比注册任务表）、任务/活跃度/达人/好友/黄历页面原始 HTML |
| `show_latest.py` | `uv run python research/show_latest.py` | 查看最近一次快照摘要 |
| `diff.py` | `uv run python research/diff.py 快照A.json 快照B.json` | 前后差分：角色属性变化、任务入口增删、各页面 HTML 文本变化 |
| `experiment.py` | `uv run python research/experiment.py 模块.任务` | 差分实验：快照before → 执行任务 → 快照after → 自动diff，完整记录存 `log/experiments/` |
| `update_datapack.py` | `uv run python research/update_datapack.py` | 自动更新脱敏研究数据包（多日入口地图 + 实验记录 + 日志观测）；每天 22:00 由 `daledou-snapshot` 定时任务自动执行 |
| `find_links.py` | `uv run python research/find_links.py [关键词]` | 列出最近快照首页全部入口链接（cmd 参数 → 文本），用于发现新只读页面 |
| `preview_pages.py` | `uv run python research/preview_pages.py [页面名]` | 查看最近快照各页面的纯文本预览 |
| `daily_experiments.py` | `uv run python research/daily_experiments.py` | 每日免费差分实验（领取徒弟经验/每日奖励）；每天 06:06 由 `daledou-experiments` 自动执行（服务器 06:00 刷新后第一时间），抢在 06:10 日常任务前 |
| `interface_probe.py` | `uv run python research/interface_probe.py` | 接口层只读探测（响应头/无效参数/频率/分页/UA/记录深度），结果存 `log/interface_probe.json` |
| `battle_reports.py` | `uv run python research/battle_reports.py` | 战报归档（**每天最多 3 条：历练/斗神塔/好友各 1，仅归档已发生战报，绝不触发战斗**）；每天 06:40 由 `daledou-battlereports` 执行（跟随 06:10 主流程后），存 `log/battle_reports/` |
| `battle_data_analysis.py` | `uv run python research/battle_data_analysis.py` | 战报聚合分析（伤害/暴击倍率/回合结构/技能触发），结果存 `log/battle_stats.json` |
| `entity_model.py` | `uv run python research/entity_model.py` | 快照 → 结构化账号实体模型（角色/背包/武器/佣兵/星石/徽章/徒弟/侠），存 `log/account_model.json` |
| `one_shot_capture.py` | `uv run python research/one_shot_capture.py` | 一次性只读抓取：完整背包/商店全页签/排行榜子榜/徽章成就，存 `log/one_shot/` |
| `activity_templates.py` | `uv run python research/activity_templates.py` | 135 个任务按接口模式归类到 6 类活动模板 |
| `ops_analysis.py` | `uv run python research/ops_analysis.py` | 任务时间窗口表（32 条）+ 货币体系图（22 条） |
| `state_tokens.py` | `uv run python research/state_tokens.py` | 状态令牌字典（扫描 336 页，客户端状态机令牌） |
| `rank_analysis.py` | `uv run python research/rank_analysis.py` | 排行榜 Top-N 抓取与解析（等级/财富/荣誉/斗神塔/帮派），存 `log/one_shot/rank_lists/` |
| `shop_analysis.py` | `uv run python research/shop_analysis.py` | 商店定价全表分析（86 件商品），存 `log/shop_prices.json` |
| `battle_hits.py` | `uv run python research/battle_hits.py` | 战报→命中级结构化管道（回合/武器/技能/暴击/闪避/伤害），存 `log/hits_dataset.json` |
| `fit_exp_curve.py` | `uv run python research/fit_exp_curve.py` | 经验曲线幂律拟合（10 个高等级锚点），存 `log/exp_curve_fit.json` |
| `hit_quality_audit.py` | `uv run python research/hit_quality_audit.py` | 命中行解析质量审计（字段覆盖/武器名污染/行动错位），存 `log/hit_quality_audit.json` |

## 快照内容说明

- 输出到 `log/snapshots/YYYY-MM-DD_HHMMSS.json`（log/ 已被 gitignore，不会提交）
- 每个账号含：`character`（解析好的属性）、`available_tasks`（今日可做任务，按 noon/evening 分组）、`pages`（各页面 raw_html + 纯文本预览）
- 保留 raw_html 是为了后续机制分析（Codex 可自行解析任意字段）

## 对应 Codex 研究方案

1. **全量状态地图** → `snapshot.py`（角色/入口/任务/活跃度）+ daledou 任务代码（现成的状态机）
2. **今日可做算法** → 连续多天跑 `snapshot.py`，对比 `available_tasks` 随等级/日期/资源的变化
3. **行动状态机还原** → `experiment.py`，每类行动选一个免费任务做最小样本
4. **前后快照差分** → `experiment.py` 内置（第 3 步），输出 `输入→输出` 记录
5. **随机性研究** → 对同一免费行动（如邪神秘宝）多次 `experiment.py`，收集分布；注意每天次数有限
6. **社交/运营闭环** → 好友/帮派相关只读页在快照里，配合实验观察奖励归因
7. **数值模型** → 基于长期快照序列（角色成长）和实验记录拟合

## 实验安全守则

- 只做**免费/无消耗**任务的最小样本（邪神秘宝、幸运金蛋、每日登录礼等），且优先用当天已领过的（会自动跳过，验证流程用）
- 需要消耗体力的实验（乐斗、历练）每天配额有限，先记录基线，谨慎执行
- 不要高频重复请求；游戏按自然日结算，实验计划对齐每日重置
