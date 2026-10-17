#!/usr/bin/env python3
"""核对 bottled_ai 商店购买：每个 SHOP_SCREEN 的 choose N，比对「购买前后 gold 差 == 标价」。

用法（在仓库根，先 cd ~/projects/bottled_ai）:
    python3 check-shops.py [logs/runs/xxx.log ...]    # 缺省扫 logs/runs/*.log

原理: choice_list = ['purge'(仅可用且买得起)] + 可负担物品(price<=gold, 卡→遗物→药水)；
购买下标 = purge 位(0/1) + 可负担序位。
注意: 记录一笔后必须复位 pending，否则同一笔会在后续每个商店状态重复计数（d=0 伪影）。
"""
import argparse
import glob
import json
import sys


def state_of(line):
    gs = json.loads(line[line.find('{'):])
    st = gs.get('game_state', {})
    return st, st.get('screen_state', {})


def affordable(ss, gold):
    return [x for k in ('cards', 'relics', 'potions')
            for x in ss.get(k, []) if x.get('price', 10 ** 9) <= gold]


def _exit_with_status_2(exc_type, exc, traceback):
    print(f'{exc_type.__name__}: {exc}', file=sys.stderr)
    sys.exit(2)


sys.excepthook = _exit_with_status_2


def main(argv=None):
    parser = argparse.ArgumentParser(description='Audit bottled_ai shop purchases against their listed prices.')
    parser.add_argument('logs', nargs='*', metavar='LOG', help='run log files (defaults to logs/runs/*.log)')
    args = parser.parse_args(argv)
    files = args.logs or glob.glob('logs/runs/*.log')
    tot = ok = 0
    for f in sorted(files):
        src = st_s = ss_s = pend = None
        bought = []
        for l in open(f, encoding='utf-8', errors='replace').read().splitlines():
            if 'Response:' in l and '"screen_type"' in l:
                t = state_of(l)[0].get('screen_type')
                if t == 'SHOP_SCREEN':
                    st2, ss2 = state_of(l)
                    if pend is not None:
                        d = (st_s.get('gold') or 0) - (st2.get('gold') or 0)
                        bought.append((pend[0], pend[1], 'OK' if d == pend[0] else 'BAD(d=%s)' % d))
                        pend = None
                    st_s, ss_s, src = st2, ss2, t
                    continue
                src = t
            if l.startswith('Sending message:') and src == 'SHOP_SCREEN':
                m = l.split('Sending message:', 1)[1].strip()
                if m.startswith('choose'):
                    try:
                        n = int(m.split()[1])
                    except (IndexError, ValueError):
                        continue
                    gold = st_s.get('gold')
                    can_purge = ss_s.get('purge_available') and gold >= ss_s.get('purge_cost')
                    if n == 0 and can_purge:
                        pend = (ss_s.get('purge_cost'), 'PURGE')
                    else:
                        off = 1 if can_purge else 0
                        a = affordable(ss_s, gold)
                        j = n - off
                        if 0 <= j < len(a):
                            it = a[j]
                            kind = ('card' if it in ss_s.get('cards', []) else
                                    'relic' if it in ss_s.get('relics', []) else 'potion')
                            pend = (it.get('price'), kind + ':' + str(it.get('id')))
                        else:
                            pend = None
                elif m.startswith('return') or m.startswith('proceed'):
                    src = None
        for b in bought:
            tot += 1
            ok += (b[2] == 'OK')
        if bought:
            print(f.split('--')[-1][:12], len(bought), '笔:', bought)
    print('TOTAL %d/%d' % (ok, tot))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
