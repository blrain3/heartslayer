#!/usr/bin/env python3
"""在离线回放上模拟验证候选修复：允许小额生命换击杀进度 (预算5)。

用法:
    python3 sim_fix_test.py
"""
import argparse
import sys

_parser = argparse.ArgumentParser(description='Simulate candidate comparator fixes on saved decisions.')
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
import rs.common.comparators.big_fight_comparator as bfc
from rs.common.comparators.big_fight_comparator import BigFightComparator
from rs.common.comparators.core.comparisons import least_incoming_damage_over_1
from rs.common.comparators.core.assessment import ComparatorAssessment as CA


def trade_hp_for_damage(best, challenger, budget):
    bi, ci = best.incoming_damage(), challenger.incoming_damage()
    bd, cd = best.total_monster_health(), challenger.total_monster_health()
    if abs(bi - ci) <= budget and bd != cd:
        return cd < bd
    return None


def replay(f, end_idx, mode):
    lines = open(f, encoding='utf-8', errors='replace').read().splitlines()
    hi = next(i for i, l in enumerate(lines) if 'Corrupt Heart' in l)
    ends = [i for i in range(hi, len(lines)) if lines[i].startswith('Sending message: end')]
    E = ends[end_idx]
    resp_i = max(i for i in range(E) if lines[i].startswith('Response:'))
    mem_i = max(i for i in range(resp_i) if lines[i].startswith('Memory of next action:'))
    js = json.loads(lines[resp_i][lines[resp_i].find('{'):])
    _raw = lines[mem_i].split('Memory of next action:', 1)[1].strip()
    _raw = re.sub(r'<(\w+)\.(\w+): [^>]*>', r'\1.\2', _raw)
    mem = eval(compile(_raw, '<run_log_memory>', 'eval'), {'MemoryItem': MemoryItem, 'ResetSchedule': ResetSchedule, 'CardId': CardId, 'CardType': CardType, 'StanceType': StanceType, 'PowerId': PowerId})
    gs = GameState(js, TheBotsMemoryBook(memory_general=mem['memory_general'], memory_by_card=mem['memory_by_card']))
    bs = create_battle_state(gs)
    cmp = BigFightComparator()
    if mode == 'fix5' or mode == 'fix8':
        budget = 5 if mode == 'fix5' else 8
        idx = cmp.comparisons.index(least_incoming_damage_over_1)
        cmp.comparisons.insert(idx, lambda b, c: trade_hp_for_damage(b, c, budget))
    paths = get_paths_bfs(bs, 11000)
    best = None
    for p in paths.values():
        p.state.end_turn()
        if best is None or cmp.does_challenger_defeat_the_best(best.state, p.state, bs):
            best = p
    plays = []
    for (idx0, tgt) in best.plays:
        plays.append(bs.hand[idx0].id.value if 0 <= idx0 < len(bs.hand) else f'#{idx0}')
    st = best.state
    return dict(plays=plays, hp=st.player.current_hp, hearthp=None, inc=CA(st, bs, cmp.assessment_config).incoming_damage(),
                energy=st.player.energy)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('--help', '-h'):
        print(__doc__)
        sys.exit(0)
    targets = [('logs/runs/2026-10-05-15-25-16--XDMVJN66WFC7.log', 2),
               ('logs/runs/2026-10-05-15-58-44--W3G8QK9L95XW.log', 1),
               ('logs/runs/2026-10-05-15-50-44--5W8JLWDU1LYS.log', 1),
               ('logs/runs/2026-10-05-15-50-44--5W8JLWDU1LYS.log', 2),
               ('logs/runs/2026-10-05-15-50-44--5W8JLWDU1LYS.log', 3)]
    for f, e in targets:
        name = f.split('--')[1][:12]
        for mode in ['orig', 'fix5', 'fix8']:
            r = replay(f, e, mode)
            print(f"{name} end#{e} [{mode}]: 出牌={r['plays']} | 净损失={r['inc']} | 余能={r['energy']}")
        print()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
