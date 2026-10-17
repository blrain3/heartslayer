#!/usr/bin/env python3
import json,glob,sys
def S(l):
    gs=json.loads(l[l.find('{'):]); st=gs.get('game_state',{}); return st, st.get('screen_state',{})
def aff(ss,gold):
    return [x for k in ('cards','relics','potions') for x in ss.get(k,[]) if x.get('price',10**9)<=gold]
files = sys.argv[1:] or glob.glob('logs/runs/*.log')
tot=ok=0
for f in sorted(files):
    src=None; st_s=None; ss_s=None; pend=None; bought=[]
    for l in open(f,encoding='utf-8',errors='replace').read().splitlines():
        if 'Response:' in l and '"screen_type"' in l:
            t=S(l)[0].get('screen_type')
            if t=='SHOP_SCREEN':
                st2,ss2=S(l)
                if pend is not None:
                    d=(st_s.get('gold') or 0)-(st2.get('gold') or 0)
                    bought.append((pend[0],pend[1],'✓' if d==pend[0] else f'✗d{d}')); pend=None
                st_s,ss_s=st2,ss2; src=t; continue
            src=t
        if l.startswith('Sending message:') and src=='SHOP_SCREEN':
            m=l.split('Sending message:',1)[1].strip()
            if m.startswith('choose'):
                try: n=int(m.split()[1])
                except: continue
                ss=ss_s; gold=st_s.get('gold')
                cp = ss.get('purge_available') and gold>=ss.get('purge_cost')
                if n==0 and cp: pend=(ss.get('purge_cost'),'PURGE')
                else:
                    off=1 if cp else 0
                    a=aff(ss,gold); j=n-off
                    if 0<=j<len(a):
                        it=a[j]
                        kind='card' if it in ss.get('cards',[]) else ('relic' if it in ss.get('relics',[]) else 'potion')
                        pend=(it.get('price'),kind+':'+str(it.get('id')))
                    else: pend=None
            elif m.startswith('return') or m.startswith('proceed'): src=None
    for b in bought: tot+=1; ok+=(b[2]=='✓')
    if bought: print(f.split('--')[-1][:12], len(bought),'笔:', bought)
print(f"TOTAL {ok}/{tot}")
