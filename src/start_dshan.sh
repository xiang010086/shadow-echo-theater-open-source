#!/usr/bin/env bash
# Adapted to the verified DshanPi-A1 Armbian GNOME/Wayland image.
set -euo pipefail
cd -- "$(dirname -- "$0")"
mkdir -p logs
exec 9>.stage.lock
if ! flock -n 9; then
  echo '演示已在运行，请切回现有窗口。' >&2
  exit 1
fi
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"
if [[ -z "${WAYLAND_DISPLAY:-}" && -z "${DISPLAY:-}" && -S "$XDG_RUNTIME_DIR/wayland-0" ]]; then
  export WAYLAND_DISPLAY=wayland-0
fi
if [[ -z "${WAYLAND_DISPLAY:-}" && -z "${DISPLAY:-}" ]]; then
  echo '未发现已登录的图形桌面，无法显示演示。' >&2
  exit 1
fi
# The supplied MPP plugin fails initialization. Prefer the verified software
# decoder for these 720p test cards; this changes only this process environment.
export GST_PLUGIN_FEATURE_RANK="${GST_PLUGIN_FEATURE_RANK:-mppvideodec:0}"
# Capture on the board microphone; play through the user's HDMI screen.
# Allow an explicit environment override for a different physical output.
export PULSE_SOURCE="${PULSE_SOURCE:-alsa_input.platform-es8388-sound.stereo-fallback}"
export PULSE_SINK="${PULSE_SINK:-alsa_output.platform-hdmi-sound.stereo-fallback}"
server_pid=''
cleanup() {
  if [[ -n "$server_pid" ]]; then kill "$server_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
if ! python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=1)' 2>/dev/null; then
  python3 -u runtime.py >logs/runtime.log 2>&1 &
  server_pid=$!
  ready=0
  for attempt in 1 2 3 4 5; do
    if ! kill -0 "$server_pid" 2>/dev/null; then cat logs/runtime.log >&2; exit 1; fi
    if python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=1)' 2>/dev/null; then
      ready=1; break
    fi
    sleep 1
  done
  if [[ "$ready" != 1 ]]; then echo '本地服务启动失败。' >&2; exit 1; fi
fi
python3 -u board_webview.py "$@"
