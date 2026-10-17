#!/bin/bash
# 里程碑守望器：常驻监听 bottled_ai 最新 run 日志，把关键事件（按 文件:计数 去重）追加到 milestones.log。
# 用法（launch-batch 会以 heart-watch 单元自动拉起；默认输出到本脚本所在目录）:
#   BOTTLED_REPO=~/projects/bottled_ai BOTTLED_WATCH_OUT=/some/dir ./watch-milestones.sh
# 事件列表可按需增删（k:grep模式 对）。
set -euo pipefail
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "Usage: $0"
  echo "  Long-lived watcher that logs milestone events to milestones.log."
  exit 0
fi
P="${BOTTLED_WATCH_OUT:-$(cd "$(dirname "$0")" && pwd)}"
R="${BOTTLED_REPO:-$HOME/projects/bottled_ai}"
M=$P/milestones.log
mkdir -p $P/.wstate
while true; do
  L=$(ls -t $R/logs/runs/*.log 2>/dev/null | head -1)
  [ -n "$L" ] || { sleep 30; continue; }
  for ev in "emerald:choose emerald_key" "sapphire:choose sapphire_key" "recall:choose recall" "act4:\"act\": 4" "spireelite:Spire Shield" "heart:Corrupt Heart" "victory:\"victory\":true"; do
    k=${ev%%:*}; pat=${ev#*:}
    c=$(grep -c "$pat" "$L" 2>/dev/null || echo 0)
    mark="$P/.wstate/$k"
    cur="$L:$c"
    if [ "$cur" != "$(cat "$mark" 2>/dev/null)" ] && [ "$c" -gt 0 ]; then
      echo "$(date '+%F %T') [$k] $c in $L" >> $M
      echo "$cur" > "$mark"
    fi
  done
  sleep 30
done
