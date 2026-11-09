@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 请保持窗口打开，并打开 http://127.0.0.1:8765 后点击开始测试。
py runtime.py
pause
