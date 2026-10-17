#!/bin/bash
cd ~/projects/bottled_ai
P=~/hermes-study/heart-loop-valid-20261005
M=$P/milestones.log
mkdir -p $P/.wstate
while true; do
  L=$(ls -t logs/runs/*.log 2>/dev/null | head -1)
  [ -n "$L" ] || { sleep 30; continue; }
  for ev in "emerald:choose emerald_key" "sapphire:choose sapphire_key" "recall:choose recall" "act4:\"act\": 4" "spireelite:Spire Shield" "heart:Corrupt Heart" "victory:\"victory\":true"; do
    k=${ev%%:*}; pat=${ev#*:}
    c=$(grep -c "$pat" "$L" 2>/dev/null || echo 0)
    mark="$P/.wstate/$k"
    last=$(cat "$mark" 2>/dev/null)
    cur="$L:$c"
    if [ "$cur" != "$last" ] && [ "$c" -gt 0 ]; then
      echo "$(date '+%F %T') [$k] $c in $L" >> $M
      echo "$cur" > "$mark"
    fi
  done
  sleep 30
done
