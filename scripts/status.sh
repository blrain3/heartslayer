#!/bin/bash
# bottled_ai 当前局一查（act/floor/keys/钥匙动作/心脏止点/victory + run_history 尾）。
# 用法: BOTTLED_REPO=~/projects/bottled_ai bash status.sh
set -euo pipefail
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "Usage: $0"
  echo "  Reads the latest run log from BOTTLED_REPO and prints status."
  exit 0
fi
R="${BOTTLED_REPO:-$HOME/projects/bottled_ai}"
[ -d "$R" ] || { echo "bottled_ai 仓库不存在: $R（用 BOTTLED_REPO=... 指定）"; exit 1; }
cd "$R" || exit 1
echo "T=$(date '+%F %T') bot=$(pgrep -f 'bottled_ai/main.py' >/dev/null && echo alive || echo gone)"
F=$(ls -t logs/runs/*.log 2>/dev/null | head -1)
echo "latest: $F"
[ -n "$F" ] || exit 0
echo "  keys: $(grep -o '"keys": *{[^}]*}' "$F" | tail -1)"
echo "  act: $(grep -o '"act": *[0-9]*' "$F" | tail -1)  floor: $(grep -o '"floor": *[0-9]*' "$F" | tail -1)"
echo "  recall:$(grep -c 'choose recall' "$F") emerald:$(grep -c 'choose emerald_key' "$F") sapphire:$(grep -c 'choose sapphire_key' "$F")"
echo "  heart-end: $(grep -o 'Corrupt Heart","current_hp":[0-9]*' "$F" | tail -1)"
echo "  victory: $(grep -c '"victory":true' "$F")"
echo "== run_history 尾 3 =="
tail -3 logs/run_history.log | grep -v '^--' | cut -c1-150
