# daledou 自动更新脚本
# 作用：订阅上游 https://github.com/gaoyuanqi/daledou（upstream remote）
#       1. git fetch upstream 上游最新代码
#       2. 有更新则 rebase 合并（保留本地增强：资源管理、消耗闭环、研究工具链）
#       3. 合并后做冒烟测试（验证 CLI 能正常加载，不做任何游戏操作）
#       4. 全部结果写入 log\update.log
# 冲突时：停止并提示需要手动/AI 处理，绝不自动覆盖
#
# remote 约定：
#   origin   = 本仓库（你的 GitHub 仓库）
#   upstream = gaoyuanqi/daledou（上游原始项目）
# 首次使用需添加：
#   git remote add upstream https://github.com/gaoyuanqi/daledou.git

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$logDir = Join-Path $repo "log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "update.log"
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Set-Location $repo

function Write-Log($msg) {
    $line = "$stamp | $msg"
    Write-Host $line
    $line | Out-File -Append -Encoding utf8 $log
}

# 检查 upstream remote 是否存在
$hasUpstream = git remote | Select-String -Pattern "^upstream$"
if (-not $hasUpstream) {
    Write-Log "[提示] 未配置 upstream remote，跳过上游检查（仅本仓库运行）。"
    Write-Log "如需订阅上游：git remote add upstream https://github.com/gaoyuanqi/daledou.git"
    exit 0
}

# 1. 拉取上游（含 tag）
git fetch upstream --tags 2>&1 | Out-File -Append -Encoding utf8 $log

$local = git rev-parse HEAD
$remote = git rev-parse upstream/main

# 仅统计上游独有（HEAD..upstream/main）的提交；本地自己的提交不算"上游更新"
$incoming = git log --oneline "HEAD..upstream/main"
if (-not $incoming) {
    Write-Log "上游无新提交，当前已是最新（$($remote.Substring(0, 8))）"
    exit 0
}

# 2. 有更新：列出新提交
Write-Log "发现上游更新，开始合并："
$incoming | Out-File -Append -Encoding utf8 $log

# 3. rebase 合并（保留本地提交）
git rebase upstream/main 2>&1 | Out-File -Append -Encoding utf8 $log
if ($LASTEXITCODE -ne 0) {
    Write-Log "[冲突] rebase 失败！本地修改已保留，但需要人工/AI 处理冲突后手动 git rebase --continue。"
    exit 1
}

# 4. 冒烟测试：CLI 能加载（无游戏副作用）
$smoke = & uv run main.py -h 2>&1 | Out-String
if ($LASTEXITCODE -eq 0) {
    Write-Log "冒烟测试通过，更新完成。当前版本：$(git log --oneline -1)"
} else {
    Write-Log "[警告] 冒烟测试失败，代码可能有问题，请检查！"
    $smoke | Out-File -Append -Encoding utf8 $log
    exit 1
}

# 5. 推送到自己的 origin（含本地增强 + 上游更新）
git push origin main 2>&1 | Out-File -Append -Encoding utf8 $log
if ($LASTEXITCODE -eq 0) {
    Write-Log "已推送到 origin/main。"
} else {
    Write-Log "[警告] 推送到 origin 失败，请检查网络/权限。"
}

exit 0
