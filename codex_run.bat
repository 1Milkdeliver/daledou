@echo off
title Codex - Q宠大乐斗自动化维护
cd /d "D:\Deepseek Harness\daledou"
echo 启动 Codex（工作目录：daledou，自动读取 AGENTS.md + CODEX接手说明.md）
echo 模式：workspace-write（可在项目内读写文件、运行命令；不会触碰项目外文件）
echo 如需完全免确认可改用：codex --full-auto（谨慎）
codex --sandbox workspace-write
