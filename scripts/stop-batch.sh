#!/bin/bash
# 碎心批次安全停止：bot → 游戏（MTS + Steam 接管的 jre） → user units
set -euo pipefail
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "Usage: $0 [--all]"
  echo "  --all   also stop the stuck-watch unit"
  exit 0
fi
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
pkill -TERM -f "bottled_ai/main.py" 2>/dev/null && echo "bot TERM" || echo "bot 已不在"
sleep 3
for p in $(pgrep -f "ModTheSpire.jar"); do kill -TERM $p 2>/dev/null; done
sleep 6
systemctl --user stop mts-ui 2>/dev/null
systemctl --user stop heart-watch 2>/dev/null
if [ "${1:-}" = "--all" ]; then systemctl --user stop stuck-watch 2>/dev/null; fi
for g in $(pgrep -f "SlayTheSpire/jre/bin/java"); do kill -TERM $g 2>/dev/null; done
sleep 5
for g in $(pgrep -f "SlayTheSpire/jre/bin/java"); do kill -KILL $g 2>/dev/null; done
sleep 2
if pgrep -f "ModTheSpire.jar" >/dev/null || pgrep -f "SlayTheSpire/jre/bin/java" >/dev/null; then
  echo "仍有残留进程!"
  exit 1
else
  echo "已停止 ✓"
fi
