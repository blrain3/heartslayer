#!/usr/bin/env python3
"""离线回放：复刻 bot 在某次 'Sending message: end' 前的决策，对比 end 与继续出牌两条线。

用法:
    python3 replay_decision.py <logfile> <end_idx>
"""
import json, sys, re, glob
from rs.machine.state import GameState
from rs.machine.the_bots_memory_book import TheBotsMemoryBook
from rs.calculator.enums.card_id import CardId
from rs.calculator.interfaces.memory_items import MemoryItem, ResetSchedule, StanceType
from rs.game.card import CardType
from rs.calculator.enums.power_id import PowerId
from rs.calculator.game_state_converter import create_battle_state
from rs.calculator.play_path import get_paths_bfs
from rs.common.comparators.big_fight_comparator import BigFightComparator
from rs.common.comparators.core.assessment import ComparatorAssessment as CA


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('--help', '-h'):
        print(__doc__)
        sys.exit(0)
    logfile, end_idx = sys.argv[1], int(sys.argv[2])
    lines = open(logfile, encoding='utf-8', errors='replace').read().splitlines()
    hi = next(i for i, l in enumerate(lines) if 'Corrupt Heart' in l)
    ends = [i for i in range(hi, len(lines)) if lines[i].startswith('Sending message: end')]
    E = ends[end_idx]
    resp_i = max(i for i in range(E) if lines[i].startswith('Response:'))
    mem_i = max(i for i in range(resp_i) if lines[i].startswith('Memory of next action:'))
    json_state = json.loads(lines[resp_i][lines[resp_i].find('{'):])
    import re as _re
    _raw = lines[mem_i].split('Memory of next action:', 1)[1].strip()
    _raw = _re.sub(r'<(\w+)\.(\w+): [^>]*>', r'\1.\2', _raw)
    mem = eval(compile(_raw, '<run_log_memory>', 'eval'), {'MemoryItem': MemoryItem, 'ResetSchedule': ResetSchedule, 'CardId': CardId, 'CardType': CardType, 'StanceType': StanceType, 'PowerId': PowerId})
    book = TheBotsMemoryBook(memory_general=mem['memory_general'], memory_by_card=mem['memory_by_card'])
    gs = GameState(json_state, book)
    bs = create_battle_state(gs)
    print('手牌:', [c.id.value for c in bs.hand])
    print('能量:', bs.player.energy, '| 格挡:', bs.player.block, '| HP:', bs.player.current_hp, '| 态势:', bs.get_stance())
    print('CARDS_THIS_TURN:', book.memory_general.get(MemoryItem.CARDS_THIS_TURN))
    cmp = BigFightComparator()
    paths = get_paths_bfs(bs, 11000)
    print('paths:', len(paths))
    best = None; best_ne = None
    for p in paths.values():
        p.state.end_turn()
        if best is None or cmp.does_challenger_defeat_the_best(best.state, p.state, bs): best = p
        if p.plays:
            if best_ne is None or cmp.does_challenger_defeat_the_best(best_ne.state, p.state, bs): best_ne = p
    print('BEST(含空):', best.plays)
    print('BEST(非空):', best_ne.plays if best_ne else None)
    def vals(st):
        c = CA(st, bs, cmp.assessment_config)
        d = {}
        for name in ['battle_lost','battle_won','incoming_damage','dead_monsters','intangible','cards_left_in_hand','energy','revive_option_count','total_monster_health']:
            try: d[name] = getattr(c, name)()
            except Exception as e: d[name] = f'?{e}'
        return d
    if best is not None: print('空线值:', vals(best.state))
    if best_ne is not None: print('非空线值:', vals(best_ne.state))
    if best is not None and best_ne is not None:
        a = CA(best_ne.state, bs, cmp.assessment_config); b = CA(best.state, bs, cmp.assessment_config)
        for c in cmp.comparisons:
            v = c(a, b)
            if v is not None:
                print('决定项:', c.__name__, '→', '非空线胜' if v else '空线胜')
                break


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
