# heartslayer-kit

Operations & verification toolkit for **bottled_ai**'s `OBSERVANT_HEARTSLAYER` batches — driving the Watcher bot through the three keys → Act 4 → Corrupt Heart.

Guarded batch launch, run watching, stall self-healing, and offline decision verification, extracted from the project that achieved the first heart kill.

> **Companion toolkit, not a standalone bot.** This repo orchestrates and verifies a [bottled_ai](https://github.com/xaved88/bottled_ai) setup — it does **not** include the bot, the game mods, or the game. `scripts/` drives a *running* Steam + ModTheSpire + CommunicationMod + bottled_ai chain (and reads the run logs that bottled_ai writes); `tools/` imports the bottled_ai codebase directly (`rs.*`, including the `OBSERVANT_HEARTSLAYER` strategy from the `verify-localization-fix` fork branch). Pulling only this repo gives you the tooling layer — the bot itself still comes from bottled_ai.

> **Milestone** — first Corrupt Heart kill: 2026-10-05, seed `5N2LLKFRVCE5`, floor 56 / score 1180, 8-turn fight with zero idle turns.

**English** | [简体中文](README.zh-CN.md)

## Layout

```
scripts/   ops scripts (cross-referencing; keep them in the same directory)
tools/     analysis / verification scripts (import rs.* — run from the bottled_ai repo root)
docs/      batch archives (kill report, analysis dossiers, incident reports; Chinese)
```

## Highlights

- **Five-gate guarded launch** — CommunicationMod jar fingerprint → stale-process check → Steam login → mod-count check → OCR "Play" click. Catches Steam-wasn't-logged-in, Steam-rolled-back-the-mod-jar, and double-launch cases before they cost you a batch.
- **Three-layer anti-stall defense** — an external watchdog (`watchdog-stuck.sh`) + hardened CommunicationMod (command try/catch + state-send watchdog) + a `state`-probe timeout in the bot client. Two silent-deadlock classes were found and closed this way (see `docs/`).
- **Deterministic, replayable verification** — every heart-fight decision can be replayed offline against the old vs new comparators on real run logs (`tools/`).

## Requirements

Dependency checklist:

- [ ] Python 3.11+ and Bash
- [ ] Linux desktop with a Hyprland session, `grim`, `tesseract` + `tesseract-data-eng`, `xdotool`, and a systemd user session
- [ ] Steam logged in (`Logged On` in `connection_log.txt`; AutoLogin works)
- [ ] [ModTheSpire](https://github.com/kiooeht/ModTheSpire), [CommunicationMod](https://github.com/ForgottenArbiter/CommunicationMod), and a [bottled_ai](https://github.com/xaved88/bottled_ai) checkout

The Python package has no runtime dependencies. Install it with `python3 -m pip install -e .` to add the `check-shops` command.

Tested on CachyOS/Arch. Other setups work in principle — adjust the display/OCR chain and the environment variables below.

## Verification

```bash
bash -n scripts/*.sh && python3 -m compileall scripts tools
python3 scripts/check-shops.py --help
```

## Usage

### scripts/ — batch operations

| Script | Purpose |
| --- | --- |
| `launch-batch.sh [N] [--dry-run]` | Guarded launch of an N-run batch; starts the milestone watcher and the stuck watchdog |
| `stop-batch.sh [--all]` | Ordered stop: bot → game processes (ModTheSpire + Steam-reaped jre) → user units |
| `watchdog-stuck.sh [--once]` | Kill-and-restart a run when the bot is alive but its run log has gone quiet for >180 s (two samples) |
| `watch-milestones.sh` | Long-lived watcher: logs key events (emerald/sapphire/recall/heart/victory) to `milestones.log` |
| `check-shops.py [logs...]` | Shop purchase audit: for every `choose N`, the gold delta must equal the price |
| `status.sh` | One-glance current-run status |

```bash
# 1. make sure Steam is logged in
# 2. launch a 2-run batch behind all five gates
./scripts/launch-batch.sh 2
# 3. watch
tail -f scripts/milestones.log
# 4. stop everything
./scripts/stop-batch.sh --all
```

### tools/ — offline analysis

Run from the `bottled_ai` repo root (they `import rs.*`):

```bash
cd ~/projects/bottled_ai
python3 /path/to/tools/verify_live_run.py logs/runs/<run>.log
python3 /path/to/tools/replay_decision.py logs/runs/<run>.log 2     # decision index
python3 /path/to/tools/sim_batch_clean.py                           # old-vs-new comparator sweep
```

| Tool | Purpose |
| --- | --- |
| `verify_live_run.py <log>` | Per-turn energy/plays/idle flags + old-vs-new comparator decision comparison + budget-overrun check |
| `replay_decision.py <log> <idx>` | Replay one decision offline; compare the end-turn line vs playing on |
| `sim_batch_clean.py` | Clean batch replay: `BigFightComparator` vs `HeartFightComparator` across historical heart fights |
| `sim_fix_test.py` | Candidate-fix simulation (HP-trade budgets 5/8) on historical decisions |
| `sim_decode.py` | Full play sequence + per-step damage/HP-loss evolution for one decision |
| `verify_file_version.py` | Historical case study (paired trace + synthetic cases) for the comparator fix |


## Tools prerequisites

All `tools/` scripts import the `rs.*` codebase directly. Run them from the root of a [bottled_ai](https://github.com/xaved88/bottled_ai) checkout that includes the `OBSERVANT_HEARTSLAYER` strategy (the `verify-localization-fix` branch on `blrain3/bottled_ai` carries the required ports and comparator fixes).

## Environment variables

All scripts default to the standard layout; override as needed:

| Variable | Default | Meaning |
| --- | --- | --- |
| `STEAM_DIR` | `~/.local/share/Steam` | Steam root |
| `STS_DIR` / `MTS_JAR` / `CM_JAR` | standard workshop paths | Game dir and jar paths |
| `EXPECT_CM_SHA` | hardened-build fingerprint | Gate fingerprint for the CommunicationMod jar (update when you rebuild) |
| `BOTTLED_REPO` | `~/projects/bottled_ai` | Bot checkout (run logs are read from here) |
| `BOTTLED_WATCH_OUT` | script directory | Where `milestones.log` is written |
| `THRESH` / `INTERVAL` / `MAX_RECOVERIES` | `180` / `30` / `5` | Watchdog thresholds |

## How it works

**Five-gate launch.** Each gate exists because of a real failure mode observed while running batches: MTS happily loads *zero* mods when Steam isn't logged in; game updates re-validate and revert the workshop CommunicationMod jar; a half-dead previous batch poisons the next. The gates fail loudly (`GUARD-FAIL: …`) before any state is touched. `--dry-run` exercises every check without launching.

**Stall watchdog.** Two silent-deadlock classes hit the project (both documented in `docs/`): an uncaught exception on a shop command, and a state-send suppression where the mod stayed alive but mute. The defense is deliberately layered:

1. hardened CommunicationMod — a catch-all around command execution that logs and forces a state update, plus a 15 s state-flow watchdog;
2. bot-side reply timeout — after 25 s with no reply, the client probes with `state` up to 3 times;
3. the external `watchdog-stuck.sh` — last resort: kill and relaunch a fresh small batch (bounded at 5 recoveries), turning "whole batch hangs" into "one run lost".

**OCR click.** `grim` → `tesseract tsv` → find the `play` word → `xdotool` click. The MTS window must be visible on the current workspace; a covered window means `GUARD-FAIL: 未找到 Play 按钮` (put other fullscreen windows away first).

## Notes & troubleshooting

- A game update can overwrite the workshop CommunicationMod jar — the fingerprint gate will block the launch until the hardened build is reinstalled and `EXPECT_CM_SHA` updated.
- Steam must be **fully logged in** before MTS starts; otherwise the mod list comes up empty.
- The watchdog's recovery relaunches a fresh batch — it will not resume a wedged run.
- `tools/` need a `bottled_ai` checkout with the `OBSERVANT_HEARTSLAYER` strategy (the fork branch `verify-localization-fix` on `blrain3/bottled_ai` carries the port, the comparator fix, and the hardened-mod recipe).

## Archives

`docs/` (Chinese) — first-kill report, batch summary, heart-fight analysis, records summary, and the two stall-incident write-ups.

## Credits

- [bottled_ai](https://github.com/xaved88/bottled_ai) — the bot; this kit exists to run and verify it.
- [CommunicationMod](https://github.com/ForgottenArbiter/CommunicationMod) / [spirecomm](https://github.com/ForgottenArbiter/spirecomm) — the game↔process protocol and its ecosystem.
- Slay the Spire © MegaCrit Games. This project is unaffiliated; it automates a personal copy of the game.

## License

[MIT](LICENSE)
