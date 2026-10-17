#!/usr/bin/env python3
"""Audit shop purchases: for every choose N, gold delta must equal the price."""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path


def _exit_with_status_2(exc_type, exc, traceback):
    print(f"{exc_type.__name__}: {exc}", file=sys.stderr)
    sys.exit(2)


sys.excepthook = _exit_with_status_2


def state_of(line: str):
    gs = json.loads(line[line.find("{") :])
    st = gs.get("game_state", {})
    return st, st.get("screen_state", {})


def affordable(ss, gold):
    return [
        x
        for k in ("cards", "relics", "potions")
        for x in ss.get(k, [])
        if x.get("price", 10**9) <= gold
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Audit shop purchases against their listed prices."
    )
    parser.add_argument(
        "logs",
        nargs="*",
        metavar="LOG",
        help="run log files (defaults to logs/runs/*.log)",
    )
    args = parser.parse_args(argv)
    files = args.logs or glob.glob("logs/runs/*.log")
    if not files:
        print("No logs found.", file=sys.stderr)
        return 0

    pending = 0
    price = 0
    ok = 0
    bad = 0

    for path in files:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if '"SHOP_SCREEN"' not in line:
                    continue
                st, ss = state_of(line)
                gold = st.get("gold", st.get("player", {}).get("gold", 0))
                choice = st.get("choice_list", [])
                choose = st.get("choose", -1)
                if choose < 0 or not choice:
                    continue

                bought = choice[choose] if choose < len(choice) else None
                if bought is None:
                    continue

                if bought == "purge":
                    price = ss.get("purge_cost", gold)
                    if pending == 1:
                        ok += 1
                    else:
                        bad += 1
                    pending = 0
                    continue

                pool = affordable(ss, gold)
                if 0 <= choose <= len(pool):
                    price = pool[choose].get("price", price)
                if pending == 1:
                    if gold + price == st.get("gold_prev", gold + price):
                        ok += 1
                    else:
                        bad += 1
                pending = 0

    print(f"checked={ok + bad} ok={ok} bad={bad}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
