#!/usr/bin/env python3
"""解码 XDMVJN end#2 fix5 的完整出牌序列 + 每步伤害/净损演化; 并统计全批低效率回合。

用法:
    python3 sim_decode.py
"""
import argparse
import sys

_parser = argparse.ArgumentParser(description='Decode a saved heart-fight decision and summarize batch efficiency.')
_parser.parse_args()


def _exit_with_status_2(exc_type, exc, traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, traceback)
        return
    print(f'{exc_type.__name__}: {exc}', file=sys.stderr)
    sys.exit(2)


sys.excepthook = _exit_with_status_2

import json, re, glob
import logging
from heartslayer.machine.state import GameState
from heartslayer.machine.the_bots_memory_book import TheBotsMemoryBook
from heartslayer.calculator.interfaces.memory_items import MemoryItem, ResetSchedule, StanceType
from heartslayer.game.card import CardType
from heartslayer.calculator.enums.card_id import CardId
from heartslayer.calculator.enums.power_id import PowerId
from heartslayer.calculator.game_state_converter import create_battle_state
from heartslayer.calculator.play_path import get_paths_bfs
from heartslayer.common.comparators.big_fight_comparator import BigFightComparator
from heartslayer.common.comparators.core.comparisons import least_incoming_damage_over_1
from heartslayer.common.comparators.core.assessment import ComparatorAssessment as CA
from heartslayer.calculator.battle_state import PLAY_DISCARD, PLAY_EXHAUST


def trade(best, challenger, budget=5):
    bi, ci = best.incoming_damage(), challenger.incoming_damage()
    bd, cd = best.total_monster_health(), challenger.total_monster_health()
    if abs(bi - ci) <= budget and bd != cd:
        return cd < bd
    return None


def load(f, end_idx):
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
    return create_battle_state(gs)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('--help', '-h'):
        print(__doc__)
        sys.exit(0)
    f='logs/runs/2026-10-05-15-25-16--XDMVJN66WFC7.log'
    bs = load(f, 2)
    cmp = BigFightComparator()
    idx = cmp.comparisons.index(least_incoming_damage_over_1)
    cmp.comparisons.insert(idx, lambda b, c: trade(b, c))
    paths = get_paths_bfs(bs, 11000)
    best = None
    for p in paths.values():
        p.state.end_turn()
        if best is None or cmp.does_challenger_defeat_the_best(best.state, p.state, bs): best = p
    print('fix5 最佳线（解码）:')
    for (i, t) in best.plays:
        if i < len(bs.hand):
            c = bs.hand[i]
            tag = c.id.value
        else:
            tag = f'#{i}'
        if t == PLAY_DISCARD: tag += ' [弃牌]'
        elif t == PLAY_EXHAUST: tag += ' [消耗]'
        elif t >= 0: tag += f' →怪{t}'
        print('  ', tag)
    st = best.state
    ca = CA(st, bs, cmp.assessment_config)
    print('结算: 净损失=%s 心脏HP=%s 心伤=%s' % (ca.incoming_damage(), ca.total_monster_health(), None))
    print()
    # 全批低效率回合统计: end 时 EN>=2 且最后3秒内 play 数<=2
    for seed in ['XDMVJN','F7LEA71','5W8JLWDU','W3G8QK9','Z3ZV8A']:
        fn=[x for x in glob.glob('logs/runs/*.log') if seed in x][0]
        lines=open(fn,encoding='utf-8',errors='replace').read().splitlines()
        hi=next(i for i,l in enumerate(lines) if 'Corrupt Heart' in l)
        lows=0; tot=0; cur_plays=0; last=None
        for i in range(hi,len(lines)):
            l=lines[i]
            if l.startswith('Sending message: play'): cur_plays+=1
            if '"game_state"' in l:
                try:
                    stt=json.loads(l[l.find('{'):])['game_state']; cs=stt.get('combat_state') or {}
                    last=(cs.get('player') or {}).get('energy')
                except Exception:
                    logging.debug("sim_decode: skip malformed game_state line")
            if l.startswith('Sending message: end'):
                tot+=1
                if (last or 0)>=2 and cur_plays<=2: lows+=1
                cur_plays=0
        print(f'{seed}: 回合={tot} 低效回合(EN>=2且出牌≤2)={lows}')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
