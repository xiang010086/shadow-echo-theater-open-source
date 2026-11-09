#!/usr/bin/env bash
set -u
cd -- "$(dirname -- "$0")"
{
  echo '=== Read-only device report; no system changes ==='
  date -Is
  uname -a
  for item in /proc/device-tree/model /proc/device-tree/compatible /etc/os-release /proc/meminfo /proc/asound/cards; do
    echo "--- $item"
    if [[ -r "$item" ]]; then tr '\000' '\n' < "$item"; else echo 'unavailable'; fi
  done
  echo '--- display environment'
  printf 'DISPLAY=%s\nWAYLAND_DISPLAY=%s\n' "${DISPLAY:-}" "${WAYLAND_DISPLAY:-}"
  echo '--- programs'
  for item in python3 chromium chromium-browser google-chrome firefox firefox-esr gst-play-1.0 gst-inspect-1.0 mpv ffmpeg aplay arecord; do command -v "$item" || true; done
  python3 --version 2>&1 || true
  echo '--- storage'
  df -h .
  echo '--- serial device names (no port opened)'
  find /dev -maxdepth 1 \( -name 'ttyUSB*' -o -name 'ttyACM*' -o -name 'ttyS*' \) -print 2>/dev/null
} 2>&1 | tee device-report.txt
