#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
exec bash start_dshan.sh --page lure/index.html
