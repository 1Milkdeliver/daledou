# daledou 自动更新脚本
# 作用：订阅上游 https://github.com/gaoyuanqi/daledou
#       1. git fetch 上游最新代码
#       2. 有更新则 rebase 合并（保留本地补丁：超时重试、定时脚本、文档）
#       3. 合并后做冒烟测试（验证 CLI 能正常加载，不做任何游戏操作）
#       4. 全部结果写入 log\update.log
# 冲突时：停止并提示需要手动/AI 处理，绝不自动覆盖

$ErrorActionPreference = "Stop"
$repo = "D:\Deepseek Harness\daledou"
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

# 1. 拉取上游（含 tag）
git fetch origin --tags 2>&1 | Out-File -Append -Encoding utf8 $log

$local = git rev-parse HEAD
$remote = git rev-parse origin/main

# 仅统计上游独有（HEAD..origin/main）的提交；本地自己的提交不算"上游更新"
$incoming = git log --oneline "HEAD..origin/main"
if (-not $incoming) {
    Write-Log "上游无新提交，当前已是最新（$($remote.Substring(0, 8))）"
    exit 0
}

# 2. 有更新：列出新提交
Write-Log "发现上游更新，开始合并："
$incoming | Out-File -Append -Encoding utf8 $log

# 3. rebase 合并（保留本地提交）
git rebase origin/main 2>&1 | Out-File -Append -Encoding utf8 $log
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

exit 0
