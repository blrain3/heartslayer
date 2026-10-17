#!/bin/bash
cd ~/projects/bottled_ai
echo "T=$(date '+%F %T') bot=$(pgrep -f 'bottled_ai/main.py' >/dev/null && echo alive || echo gone)"
F=$(ls -t logs/runs/*.log 2>/dev/null | head -1)
echo "latest: $F"
echo "  keys: $(grep -o '"keys": *{[^}]*}' $F | tail -1)"
echo "  act: $(grep -o '"act": *[0-9]*' $F | tail -1) floor: $(grep -o '"floor": *[0-9]*' $F | tail -1)"
echo "  recall:$(grep -c 'choose recall' $F) emerald:$(grep -c 'choose emerald_key' $F) sapphire:$(grep -c 'choose sapphire_key' $F)"
echo "  act4: $(grep -c 'SpireHeart\|CorruptHeart\|TheEnding' $F)"
echo "== 今日深局史 =="
grep "OBSERVANT_HEARTSLAYER" logs/run_history.log | tail -6 | cut -c1-160
