#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo '缺少 python3。请先提供板型和系统，不要盲目安装或刷机。' >&2
  exit 1
fi
python3 -c 'import sys; assert sys.version_info >= (3,8), "Python 3.8+ required"'
browser=''
for candidate in chromium chromium-browser google-chrome microsoft-edge firefox firefox-esr; do
  if command -v "$candidate" >/dev/null 2>&1; then browser="$candidate"; break; fi
done
if [[ -z "$browser" || ( -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ) ]]; then
  echo '需要图形桌面和现代 Chromium/Firefox 浏览器。请先运行 bash check_device.sh。' >&2
  exit 1
fi
mkdir -p logs
: >logs/runtime.log
python3 runtime.py >logs/runtime.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT
ready=0
for attempt in 1 2 3 4 5; do
  if ! kill -0 "$server_pid" 2>/dev/null; then cat logs/runtime.log >&2; exit 1; fi
  if grep -q '^Stage test:' logs/runtime.log && python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=1)' 2>/dev/null; then ready=1; break; fi
  sleep 1
done
if [[ "$ready" != 1 ]]; then echo '本地服务未就绪，请查看 logs/runtime.log' >&2; exit 1; fi
echo '请点一次“开始测试”启用声音，1/2选分支，0复位，空闲时G模拟欢迎。'
case "$browser" in
  firefox|firefox-esr)
    mkdir -p firefox-profile
    "$browser" --new-instance --profile "$PWD/firefox-profile" --kiosk http://127.0.0.1:8765
    ;;
  *)
    "$browser" --user-data-dir="$PWD/browser-profile" --app=http://127.0.0.1:8765
    ;;
esac
