#!/usr/bin/env python3
"""验证运行分析：逐回合指标 + 低效回合计数 + 心脏决策逐点新旧对照（含预算越界检查）。"""
import json, re, sys, glob
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

f = sys.argv[1]
lines = open(f, encoding='utf-8', errors='replace').read().splitlines()
hi = next((i for i, l in enumerate(lines) if 'Corrupt Heart' in l), None)
if hi is None:
    print('NO-HEART-YET:', f.split('--')[-1])
    sys.exit(0)
# 逐回合指标
last = None; plays = 0; turn = 0
print('== 逐回合（HP, 格挡, 余能, 出牌数） ==')
for i in range(hi, len(lines)):
    l = lines[i]
    if '"game_state"' in l:
        try:
            st = json.loads(l[l.find('{'):])['game_state']
            pl = (st.get('combat_state') or {}).get('player') or {}
            last = (st.get('current_hp'), pl.get('block'), pl.get('energy'))
        except Exception: pass
    if l.startswith('Sending message: play'): plays += 1
    if l.startswith('Sending message: end') and last:
        turn += 1
        low = ' ⚠低效' if (last[2] or 0) >= 2 and plays <= 2 else ''
        print(f'  T{turn}: HP{last[0]} BLK{last[1]} EN{last[2]} plays={plays}{low}')
        plays = 0
# 决策对照
print()
print('== 心脏决策：离线对照（旧 BigFight vs 新 HeartFight，预算检查） ==')
ends = [i for i in range(hi, len(lines)) if lines[i].startswith('Sending message: end')]
tot_dmg = tot_inc = 0; changed = 0; over = 0
for e in range(len(ends)):
    E = ends[e]
    resp_i = max(i for i in range(E) if lines[i].startswith('Response:'))
    mem_i = max(i for i in range(resp_i) if lines[i].startswith('Memory of next action:'))
    js = json.loads(lines[resp_i][lines[resp_i].find('{'):])
    _raw = re.sub(r'<(\w+)\.(\w+): [^>]*>', r'\1.\2', lines[mem_i].split('Memory of next action:', 1)[1].strip())
    mem = eval(_raw, {'MemoryItem': MemoryItem, 'ResetSchedule': ResetSchedule, 'CardId': CardId,
                      'CardType': CardType, 'StanceType': StanceType, 'PowerId': PowerId})
    res = {}
    for tag, cls in [('old', BigFightComparator), ('new', HeartFightComparator)]:
        gs = GameState(js, TheBotsMemoryBook(memory_general=dict(mem['memory_general']), memory_by_card=dict(mem['memory_by_card'])))
        bs = create_battle_state(gs)
        cmp = cls()
        paths = get_paths_bfs(bs, 11000)
        best = None
        for p in paths.values():
            p.state.end_turn()
            if best is None or cmp.does_challenger_defeat_the_best(best.state, p.state, bs): best = p
        st = best.state
        ca = CA(st, bs, cmp.assessment_config)
        res[tag] = (len(best.plays), ca.incoming_damage(), ca.total_monster_health())
    (po, io, do_), (pn, iff, df) = res['old'], res['new']
    if po != pn or do_ != df:
        changed += 1
        dd = do_ - df; di = iff - io
        tot_dmg += dd; tot_inc += di
        flag = ''
        if di > 6:
            over += 1; flag = f' ⚠越界(Δ{di})'
        print(f'  end#{e}: old {po}张/伤{dd}/Δnet{di} | new {pn}张{flag}')
print(f'== 决策改变 {changed}/{len(ends)} | 累计+伤 {tot_dmg} | 累计Δnet {tot_inc} | 越界 {over}')
