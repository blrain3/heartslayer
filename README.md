# heartslayer

Production-grade Slay the Spire Watcher automation — six interchangeable strategies, hardened batch operations, offline decision verification, and a 1,284-test suite.

Evolved from [bottled_ai](https://github.com/xaved88/bottled_ai) into an independent, deployable bot with its own identity, tooling, and engineering standards.

> **Milestone** — first Corrupt Heart kill: 2026-10-05, seed `5N2LLKFRVCE5`, floor 56 / score 1180, 8-turn fight with zero idle turns.

---

## What it is

`heartslayer` is a complete, self-contained Watcher bot for Slay the Spire. It ships the full bot engine, six play strategies, batch operations, and offline analysis tools in a single repository.

| Dimension | Detail |
| --- | --- |
| **Strategies** | `claw_is_law`, `observant_heartslayer`, `peaceful_pummeling`, `pwnder_my_orbs`, `requested_strike`, `shivs_and_giggles` |
| **Batch ops** | Guarded launch (5 gates), stall watchdog, milestone watcher, ordered teardown |
| **Verification** | Offline replay, comparator sweep, shop audit, live-run validator |
| **Tests** | 1,284 unit tests covering handlers, calculator, comparators, and game-state conversion |
| **Packaging** | `pyproject.toml` (`flit_core>=3.9`), installable with `pip install -e .` |
| **License** | MIT — upstream `bottled_ai` license retained in `heartslayer/LICENSE.md`; see `NOTICE.md` for attribution |

---

## Repository layout

```
heartslayer/
  heartslayer/          bot engine, strategies, machine, calculator, common handlers
  scripts/              guarded launch, watchdogs, status, shop audit
  tools/                offline replay, comparator, simulator, live-run validator
  tests/                1,284 unit tests (unittest)
  docs/                 strategy notes, winrate details, hardening receipts
  main.py               CommunicationMod entry point
  presentation_config.py run configuration

pyproject.toml         project metadata, dependencies, entry points
CHANGELOG.md           version history
CONTRIBUTING.md        lint, commit, dry-run rules
NOTICE.md              upstream attribution
README.md              this file
LICENSE                MIT license (blrain)
```

---

## Requirements

- Python 3.11+, Bash, `git`
- Linux desktop with a Hyprland session, `grim`, `tesseract` + `tesseract-data-eng`, `xdotool`, and a systemd user session
- Steam logged in (`Logged On` in `connection_log.txt`; AutoLogin works)
- [ModTheSpire](https://github.com/kiooeht/ModTheSpire), [CommunicationMod](https://github.com/ForgottenArbiter/CommunicationMod)

Install Python deps:

```bash
python3 -m pip install -e .
```

Runtime dependency on the game protocol library:

```toml
dependencies = [
    "spirecomm>=0.3",
]
```

---

## Verification

```bash
bash -n scripts/*.sh
python3 -m compileall heartslayer scripts tools
cd heartslayer && python3 -m unittest discover -s ./tests/
python3 scripts/check-shops.py --help
```

Expected output: `1284 tests, 0 failures, 0 errors`.

---

## Usage

### Batch operations

| Script | Purpose |
| --- | --- |
| `scripts/launch-batch.sh [N] [--dry-run]` | Guarded launch of an N-run batch; starts milestone watcher and stuck watchdog |
| `scripts/stop-batch.sh [--all]` | Ordered stop: bot → game processes → user units |
| `scripts/watchdog-stuck.sh [--once]` | Kill-and-restart a run when the bot is alive but its run log has gone quiet for >180 s |
| `scripts/watch-milestones.sh` | Long-lived watcher: logs key events to `milestones.log` |
| `scripts/check-shops.py [logs...]` | Shop purchase audit: for every `choose N`, gold delta must equal the price |
| `scripts/status.sh` | One-glance current-run status |

```bash
# 1. make sure Steam is logged in
# 2. launch a 2-run batch behind all five gates
./scripts/launch-batch.sh 2
# 3. watch
tail -f scripts/milestones.log
# 4. stop everything
./scripts/stop-batch.sh --all
```

### Offline analysis

Run from this repo root (they `import heartslayer.*`):

```bash
python3 tools/verify_live_run.py logs/runs/<run>.log
python3 tools/replay_decision.py logs/runs/<run>.log 2     # decision index
python3 tools/sim_batch_clean.py                           # old-vs-new comparator sweep
```

| Tool | Purpose |
| --- | --- |
| `verify_live_run.py <log>` | Per-turn energy/plays/idle flags + old-vs-new comparator decision comparison + budget-overrun check |
| `replay_decision.py <log> <idx>` | Replay one decision offline; compare the end-turn line vs playing on |
| `sim_batch_clean.py` | Clean batch replay: `BigFightComparator` vs `HeartFightComparator` across historical heart fights |
| `sim_fix_test.py` | Candidate-fix simulation (HP-trade budgets 5/8) on historical decisions |
| `sim_decode.py` | Full play sequence + per-step damage/HP-loss evolution for one decision |
| `verify_file_version.py` | Historical case study (paired trace + synthetic cases) for the comparator fix |

---

## Bot setup

1. Clone this repo into the game's install folder: `~/Steam/steamapps/common/SlayTheSpire/heartslayer`
2. Get/subscribe these mods via the Steam Workshop:
   - [BaseMod](https://steamcommunity.com/sharedfiles/filedetails/?id=1605833019)
   - [StSLib](https://steamcommunity.com/sharedfiles/filedetails/?id=1609158507)
   - [ModTheSpire](https://steamcommunity.com/sharedfiles/filedetails/?id=1605060445)
   - [Communication Mod](https://steamcommunity.com/sharedfiles/filedetails/?id=2131373661)
3. Run the game with the mods enabled — this will create your spire mod config files.
4. Navigate to your CommunicationMod folder. On Linux it is typically `~/.local/share/ModTheSpire/`
5. Modify `config.properties` in the CommunicationMod folder:
   - Add `command=python3 ./heartslayer/main.py`

Run the bot from the game's main menu:
- → Mods
- → Communication Mod
- → Config (next to "Return")
- → Start external process

You can configure run settings in [main.py](main.py) and [presentation_config.py](presentation_config.py).

---

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `STEAM_DIR` | `~/.local/share/Steam` | Steam root |
| `STS_DIR` / `MTS_JAR` / `CM_JAR` | standard workshop paths | Game dir and jar paths |
| `EXPECT_CM_SHA` | hardened-build fingerprint | Gate fingerprint for the CommunicationMod jar |
| `BOTTLED_REPO` | script directory | Where `milestones.log` is written |
| `THRESH` / `INTERVAL` / `MAX_RECOVERIES` | `180` / `30` / `5` | Watchdog thresholds |

---

## How it works

**Five-gate launch.** Each gate exists because of a real failure mode observed while running batches: MTS happily loads zero mods when Steam isn't logged in; game updates re-validate and revert the workshop CommunicationMod jar; a half-dead previous batch poisons the next. The gates fail loudly (`GUARD-FAIL: ...`) before any state is touched. `--dry-run` exercises every check without launching.

**Stall watchdog.** Two silent-deadlock classes were found and closed:

1. hardened CommunicationMod — a catch-all around command execution that logs and forces a state update, plus a 15 s state-flow watchdog;
2. bot-side reply timeout — after 25 s with no reply, the client probes with `state` up to 3 times;
3. the external `watchdog-stuck.sh` — last resort: kill and relaunch a fresh small batch (bounded at 5 recoveries), turning "whole batch hangs" into "one run lost".

**OCR click.** `grim` → `tesseract tsv` → find the `play` word → `xdotool` click. The MTS window must be visible on the current workspace; a covered window means `GUARD-FAIL: 未找到 Play 按钮`.

**Strategy system.** Six interchangeable Watcher strategies share a common handler framework. Each strategy defines its own config, event handlers, shop logic, and (where needed) custom comparators for heart-fight decision quality.

---

## Notes & troubleshooting

- A game update can overwrite the workshop CommunicationMod jar — the fingerprint gate will block the launch until the hardened build is reinstalled and `EXPECT_CM_SHA` updated.
- Steam must be **fully logged in** before MTS starts; otherwise the mod list comes up empty.
- The watchdog's recovery relaunches a fresh batch — it will not resume a wedged run.
- `tools/` import the bundled `heartslayer.*` codebase directly; no external checkout required.

---

## Credits

- [bottled_ai](https://github.com/xaved88/bottled_ai) — the original project this fork is based on.
- [CommunicationMod](https://github.com/ForgottenArbiter/CommunicationMod) / [spirecomm](https://github.com/ForgottenArbiter/spirecomm) — the game↔process protocol and its ecosystem.
- Slay the Spire © MegaCrit Games. This project is unaffiliated; it automates a personal copy of the game.

---

## License

[MIT](LICENSE)

See `NOTICE.md` for upstream attribution and `heartslayer/LICENSE.md` for the original bottled_ai license.
