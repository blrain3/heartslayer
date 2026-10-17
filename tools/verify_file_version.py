#!/usr/bin/env python3
"""历史用例：针对 XDMVJN 日志第 3 次 end 的「文件版」对照验证（旧 BigFight vs 新 HeartFight）。
需先将 XDMVJN 日志恢复到 logs/runs/ 下（归档在 docs/ 或批次包里），并从 bottled_ai 仓库根运行。

用法:
    python3 verify_file_version.py
"""
import argparse
import sys

_parser = argparse.ArgumentParser(description='Compare comparator versions on the archived XDMVJN decision.')
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


def make_bs(lines, resp_i, mem):
    gs = GameState(json.loads(lines[resp_i][lines[resp_i].find('{'):]),
                   TheBotsMemoryBook(memory_general=dict(mem['memory_general']), memory_by_card=dict(mem['memory_by_card'])))
    return create_battle_state(gs)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('--help', '-h'):
        print(__doc__)
        sys.exit(0)
    f = [x for x in glob.glob('logs/runs/*.log') if 'XDMVJN' in x][0]
    lines = open(f, encoding='utf-8', errors='replace').read().splitlines()
    hi = next(i for i, l in enumerate(lines) if 'Corrupt Heart' in l)
    ends = [i for i in range(hi, len(lines)) if lines[i].startswith('Sending message: end')]
    E = ends[2]
    resp_i = max(i for i in range(E) if lines[i].startswith('Response:'))
    mem_i = max(i for i in range(resp_i) if lines[i].startswith('Memory of next action:'))
    js = json.loads(lines[resp_i][lines[resp_i].find('{'):])
    _raw = re.sub(r'<(\w+)\.(\w+): [^>]*>', r'\1.\2', lines[mem_i].split('Memory of next action:', 1)[1].strip())
    mem = eval(compile(_raw, '<run_log_memory>', 'eval'), {'MemoryItem': MemoryItem, 'ResetSchedule': ResetSchedule, 'CardId': CardId, 'CardType': CardType, 'StanceType': StanceType, 'PowerId': PowerId})

    for cmp in [BigFightComparator(), HeartFightComparator()]:
        bs = make_bs(lines, resp_i, mem)
        paths = get_paths_bfs(bs, 11000)
        best = None
        for p in paths.values():
            p.state.end_turn()
            if best is None or cmp.does_challenger_defeat_the_best(best.state, p.state, bs): best = p
        st = best.state
        ca = CA(st, bs, cmp.assessment_config)
        print(f'{type(cmp).__name__}: 出牌={[bs.hand[i].id.value for (i,t) in best.plays]} 净损失={ca.incoming_damage()} 心HP={ca.total_monster_health()}')

    print()
    print('=== 3) 合成用例 ===')
    from rs.ai.observant_heartslayer.comparators.heart_fight_comparator import trade_hp_for_damage
    class Fake:
        def __init__(s, inc, dmg): s.i, s.d = inc, dmg
        def incoming_damage(s): return s.i
        def total_monster_health(s): return s.d
    # 场景A: 代价 +3, 伤害进步 (652->596) → 应 True（挑战者胜）
    print('A 小代价换伤害:', trade_hp_for_damage(Fake(9, 652), Fake(12, 596)))
    # 场景B: 代价 +6 (超预算) → None（回退原逻辑）
    print('B 超预算:', trade_hp_for_damage(Fake(9, 652), Fake(15, 596)))
    # 场景C: 无伤害差异 → None
    print('C 无伤害差:', trade_hp_for_damage(Fake(9, 652), Fake(11, 652)))
    # 场景D: 反向——挑战者伤害更差但略省血 → False（守住伤害线）
    print('D 反向保护:', trade_hp_for_damage(Fake(12, 596), Fake(9, 652)))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
