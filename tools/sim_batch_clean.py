#!/usr/bin/env python3
"""干净版批量回放：BigFightComparator(原) vs HeartFightComparator(新，真实文件)。两个类均不修改共享列表。

用法:
    python3 sim_batch_clean.py
"""
import argparse
import sys

_parser = argparse.ArgumentParser(description='Compare old and heart-fight comparators over saved batch logs.')
_parser.parse_args()


def _exit_with_status_2(exc_type, exc, traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, traceback)
        return
    print(f'{exc_type.__name__}: {exc}', file=sys.stderr)
    sys.exit(2)


sys.excepthook = _exit_with_status_2

import json, re, glob
from rs.machine.state import GameState
from rs.machine.the_bots_memory_book import TheBotsMemoryBook
from rs.calculator.interfaces.memory_items import MemoryItem, ResetSchedule, StanceType
from rs.game.card import CardType
from rs.calculator.enums.card_id import CardId
from rs.calculator.enums.power_id import PowerId
from rs.calculator.game_state_converter import create_battle_state
from rs.calculator.play_path import get_paths_bfs
from rs.ai.observant_heartslayer.comparators.heart_fight_comparator import HeartFightComparator
from rs.common.comparators.big_fight_comparator import BigFightComparator
from rs.common.comparators.core.assessment import ComparatorAssessment as CA


def run_one(f, end_idx, cls):
    lines = open(f, encoding='utf-8', errors='replace').read().splitlines()
    hi = next(i for i, l in enumerate(lines) if 'Corrupt Heart' in l)
    ends = [i for i in range(hi, len(lines)) if lines[i].startswith('Sending message: end')]
    E = ends[end_idx]
    resp_i = max(i for i in range(E) if lines[i].startswith('Response:'))
    mem_i = max(i for i in range(resp_i) if lines[i].startswith('Memory of next action:'))
    js = json.loads(lines[resp_i][lines[resp_i].find('{'):])
    _raw = re.sub(r'<(\w+)\.(\w+): [^>]*>', r'\1.\2', lines[mem_i].split('Memory of next action:', 1)[1].strip())
    mem = eval(compile(_raw, '<run_log_memory>', 'eval'), {'MemoryItem': MemoryItem, 'ResetSchedule': ResetSchedule, 'CardId': CardId, 'CardType': CardType, 'StanceType': StanceType, 'PowerId': PowerId})
    gs = GameState(js, TheBotsMemoryBook(memory_general=mem['memory_general'], memory_by_card=mem['memory_by_card']))
    bs = create_battle_state(gs)
    cmp = cls()
    paths = get_paths_bfs(bs, 11000)
    best = None
    for p in paths.values():
        p.state.end_turn()
        if best is None or cmp.does_challenger_defeat_the_best(best.state, p.state, bs):
            best = p
    st = best.state
    ca = CA(st, bs, cmp.assessment_config)
    plays = [bs.hand[i].id.value if i < len(bs.hand) else f'#{i}' for (i, t) in best.plays]
    return plays, ca.incoming_damage(), ca.total_monster_health()


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('--help', '-h'):
        print(__doc__)
        sys.exit(0)
    for seed in ['XDMVJN', 'W3G8QK9', '5W8JLWDU']:
        f = [x for x in glob.glob('logs/runs/*.log') if seed in x][0]
        lines = open(f, encoding='utf-8', errors='replace').read().splitlines()
        hi = next(i for i, l in enumerate(lines) if 'Corrupt Heart' in l)
        n_ends = sum(1 for i in range(hi, len(lines)) if lines[i].startswith('Sending message: end'))
        changed = 0; dmg_delta = 0; inc_delta = 0
        for e in range(n_ends):
            po, io, do = run_one(f, e, BigFightComparator)
            pf, iff, df = run_one(f, e, HeartFightComparator)
            same = (po == pf and do == df)
            mark = '(不变)' if same else '→改变'
            if not same:
                changed += 1; dmg_delta += (do - df); inc_delta += (iff - io)
            print(f'{seed} end#{e}: orig出牌数={len(po)} 心HP={do} | NEW出牌数={len(pf)} 心HP={df} {mark}', flush=True)
        print(f'== {seed}: {changed}/{n_ends} 决策改变 | 累计心伤推进={dmg_delta} | 累计净损增量={inc_delta}', flush=True)
        print(flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
