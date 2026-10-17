#!/bin/bash
# 碎心批次守护式启动：CM-sha 门控 + Steam 登录门控 + 模组数门控 + OCR 点击 + 守望器
# 用法: ./launch-batch.sh [RUN_AMOUNT=15] [--dry-run]
# 可移植性：以下路径均可经环境变量覆盖（默认适配标准 Steam 安装）
#   STEAM_DIR   Steam 根目录（默认 ~/.local/share/Steam）
#   STS_DIR     游戏目录、MTS_JAR / CM_JAR  workshop 内路径
#   EXPECT_CM_SHA  加固版 CM jar 指纹（换版本后同步更新）
set -euo pipefail
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "Usage: $0 [RUN_AMOUNT=15] [--dry-run]"
  echo "  --dry-run   exercise all five launch gates without starting anything"
  exit 0
fi
RA=${1:-15}; DRY=0; [ "${2:-}" = "--dry-run" ] && DRY=1
P="$(cd "$(dirname "$0")" && pwd)"
STEAM="${STEAM_DIR:-$HOME/.local/share/Steam}"
S="${STS_DIR:-$STEAM/steamapps/common/SlayTheSpire}"
JAR="${MTS_JAR:-$STEAM/steamapps/workshop/content/646570/1605060445/ModTheSpire.jar}"
CMJAR="${CM_JAR:-$STEAM/steamapps/workshop/content/646570/2131373661/CommunicationMod.jar}"
EXPECT_CM_SHA="${EXPECT_CM_SHA:-e2d51ad02b3face3dd4cb83d}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
fail(){ echo "GUARD-FAIL: $1"; exit 1; }
if [ "${WATCHDOG_RECOVER:-}" != "1" ]; then mkdir -p "$P/watchdog-state"; echo 0 > "$P/watchdog-state/recoveries"; fi
[ -f "$CMJAR" ] || fail "CM jar 不存在: $CMJAR（检查 CM_JAR / STEAM_DIR 环境变量）"
have=$(sha256sum "$CMJAR" | cut -c1-24)
[ "$have" = "$EXPECT_CM_SHA" ] || fail "CM jar sha=${have}（预期 ${EXPECT_CM_SHA}）——可能被 Steam 回滚，先处理"
pgrep -f "bottled_ai/main.py" >/dev/null && fail "bot 残留"
pgrep -f "ModTheSpire.jar" >/dev/null && fail "MTS 残留"
pgrep -x steam >/dev/null || fail "Steam 未运行"
last_ev=$(tail -c 300000 $STEAM/logs/connection_log.txt | tr '\r' '\n' | grep -E "Logged On|Logged off|Logged Off|Disconnected|LogOff" | tail -1); echo "$last_ev" | grep -q "Logged On" || fail "Steam 未登录完成 (最近事件: $last_ev)"
if [ $DRY = 1 ]; then echo "DRY-OK: CM/残留/Steam 前置全过 (RA=$RA)"; exit 0; fi
systemctl --user reset-failed mts-ui 2>/dev/null
systemd-run --user --unit=mts-ui --collect \
  --setenv=DISPLAY=:0 --setenv=WAYLAND_DISPLAY=wayland-1 --setenv=XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR \
  --setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus --setenv=RUN_AMOUNT=$RA \
  --working-directory="$S" \
  --property=StandardOutput=append:/tmp/mts-batch.out --property=StandardError=append:/tmp/mts-batch.out \
  "$S/jre/bin/java" -jar "$JAR" >/dev/null
sleep 32
grep -q "Got 10 workshop items" /tmp/mts-batch.out || fail "模组未加载（检查 Steam 登录/订阅）"
SIG=$(ls $XDG_RUNTIME_DIR/hypr/ | head -1)
export HYPRLAND_INSTANCE_SIGNATURE=$SIG WAYLAND_DISPLAY=wayland-1
grim /tmp/ui-launch.png 2>/dev/null && tesseract /tmp/ui-launch.png /tmp/ui-launch -l eng tsv 2>/dev/null
read L T <<EOF2
$(awk -F'\t' 'NR>1 && tolower($12)=="play" {printf "%d %d", $7+12, $8+6; exit}' /tmp/ui-launch.tsv)
EOF2
[ -n "$L" ] || fail "未找到 Play 按钮"
DISPLAY=:0 xdotool mousemove $L $T click 1
systemctl --user stop heart-watch 2>/dev/null; sleep 1
systemd-run --user --unit=heart-watch --collect $P/watch-milestones.sh >/dev/null
if [ -x "$P/watchdog-stuck.sh" ] && ! systemctl --user is-active stuck-watch >/dev/null 2>&1; then
  systemctl --user reset-failed stuck-watch 2>/dev/null
  systemd-run --user --unit=stuck-watch --collect $P/watchdog-stuck.sh >/dev/null
fi
echo "LAUNCHED: RUN_AMOUNT=$RA"
