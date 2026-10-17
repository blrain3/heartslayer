#!/bin/bash
# 卡死看护 v1：bot 存活但 run 日志连续两个采样窗口 > THRESH 秒无写入 → 止损并重开小批（上限 MAX）
P=/home/blrain/hermes-study/heart-loop-valid-20261005
R=/home/blrain/projects/bottled_ai
LOG=$P/watchdog.log
S=$P/watchdog-state
mkdir -p $S
THRESH=${THRESH:-180}
INTERVAL=${INTERVAL:-30}
MAX=${MAX_RECOVERIES:-5}
count=$(cat $S/recoveries 2>/dev/null || echo 0)
log(){ echo "$(date '+%F %T') $*" >> $LOG; }

if [ "${1:-}" = "--once" ]; then
  G=$(ls -t $R/logs/runs/*.log 2>/dev/null | head -1)
  if ! pgrep -f "bottled_ai/main.py" >/dev/null; then echo "once: 无 bot -> 跳过"; exit 0; fi
  [ -z "$G" ] && { echo "once: 无日志"; exit 0; }
  age=$(( $(date +%s) - $(stat -c %Y "$G") ))
  echo "once: bot=有 | 日志陈旧=${age}s | 阈值=${THRESH}s -> $([ $age -gt $THRESH ] && echo 判定陈旧将恢复 || echo 正常)"
  exit 0
fi

log "看护启动 (阈值 ${THRESH}s / 上限 ${MAX} / 已有恢复 ${count})"
while true; do
  sleep $INTERVAL
  if ! pgrep -f "bottled_ai/main.py" >/dev/null; then continue; fi
  G=$(ls -t $R/logs/runs/*.log 2>/dev/null | head -1)
  [ -z "$G" ] && continue
  age=$(( $(date +%s) - $(stat -c %Y "$G") ))
  if [ $age -gt $THRESH ]; then
    sleep 20
    G2=$(ls -t $R/logs/runs/*.log 2>/dev/null | head -1)
    age2=$(( $(date +%s) - $(stat -c %Y "$G2") ))
    if [ $age2 -gt $THRESH ] && pgrep -f "bottled_ai/main.py" >/dev/null; then
      last=$(grep -oE "Sending message: .{1,40}" "$G2" | tail -1)
      count=$((count+1)); echo $count > $S/recoveries
      log "STUCK: $G2 陈旧 ${age2}s | 最后动作: ${last} | 恢复#$count"
      $P/stop-batch.sh >> $LOG 2>&1
      sleep 8
      WATCHDOG_RECOVER=1 $P/launch-batch.sh 2 >> $LOG 2>&1
      log "恢复#$count 重开后: $(ls -t $R/logs/runs/*.log | head -1)"
      if [ $count -ge $MAX ]; then
        log "已达恢复上限($MAX)，看护退出（需人工处理）"
        $P/stop-batch.sh >> $LOG 2>&1
        exit 0
      fi
    fi
  fi
done
