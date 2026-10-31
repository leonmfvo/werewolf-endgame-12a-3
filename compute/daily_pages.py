# 日ごとに解いた辞書（data/dict.json）から、4・5人日のページ用の説明（data/d<n>.json）を作る。
# 内訳ごとの村勝率は「その日のうちの決着」＋「翌日の状態での、その内訳の村勝率」。翌日の状態も同じ辞書の進め方で解き直す。
import sys, json, os
from fractions import Fraction as F
from collections import defaultdict
import game as GM
from game import Game
from plans import candidates
import daily as D, rundaily as RD
import vote3g as G3
from run45 import boards
from analyze45 import assemble, who

WV = {}   # 状態のキー → {(役, 狼が知っている人): 村勝率}

def adv_policy(labels, worlds, plan):
    GM.MODE.update(exact=False, tags=False)
    g = Game(labels, plan, start=worlds); root, _ = g.root()
    return D.adversary_min(root)

def next_states(g, pol):
    """翌日の状態ごとに（正規形, 並び）"""
    GM.MODE.update(exact=True, tags=False)
    root, _ = g.root()
    term, nxt = D.outcomes(root, pol, True)
    out = {}
    for (hist, al, lab), ws in nxt.items():
        idx = {old: new for new, old in enumerate(al)}
        labs = [lab[i] for i in al]
        worlds = [(p, tuple(r[i] for i in al), tuple(idx[k] for k in kn)) for p, r, kn in ws]
        key, pos = D.canon(labs, worlds, with_pos=True)
        out[(hist, al, lab)] = (key, pos)
    return out

def next_value(ns, info):
    hist, al, lab, roles, know = info
    key, pos = ns[(hist, al, lab)]
    idx = {old: new for new, old in enumerate(al)}
    inv = {idx[al[old]]: new for new, old in enumerate(pos)}
    r = tuple(roles[al[i]] for i in pos)
    kn = tuple(sorted(inv[idx[k]] for k in know))
    return key, world_values(key)[(r, kn)]

def walk(board, roles, node, pol, ns):
    """決着か翌日までの道すじ：{説明: [確率, 確率×その先の村勝率]}"""
    out = defaultdict(lambda: [F(0), F(0)])
    def go(nd, p, labs):
        if p == 0: return
        if nd.tag:
            t = nd.tag
            if t[0] == '吊': labs = labs + [f'{who(board, roles, t[1])}を吊る']
            elif t[0] == '道連れ': labs = labs + [f'道連れで{who(board, roles, t[1])}']
            elif t[0] == '噛み': labs = labs + [f'{who(board, roles, t[1])}を噛む']
            elif t[0] == 'GJ': labs = labs + ['GJ']
            elif t[0] == '猫噛み': labs = labs + ['猫噛みで狼が死ぬ']
            elif t[0] == '狩人CO': labs = labs + ['狩人CO']
        if nd.kind == 'N':
            key, v = next_value(ns, nd.info)
            k = ' → '.join(labs + ['翌日 ' + ','.join(key[0])])
            out[k][0] += p; out[k][1] += p * v; return
        if nd.kind == 'L':
            k = ' → '.join(labs) + (' → 村勝ち' if nd.v == 1 else ' → 狼勝ち' if nd.v == 0 else '')
            out[k][0] += p; out[k][1] += p * nd.v; return
        if nd.kind == 'C':
            for q, c in nd.ch: go(c, p * q, labs)
        elif nd.kind == 'T': go(nd.ch[0], p, labs)
        else: go(nd.ch[pol.get((nd.agent, nd.info), 0)], p, labs)
    go(node, F(1), [])
    return out

def run_plan(labels, worlds, plan, pol=None, with_paths=False):
    """進め方 plan での内訳ごとの村勝率（と道すじ）"""
    if pol is None: pol = adv_policy(labels, worlds, plan)[1]
    g = Game(labels, plan, start=worlds)
    ns = next_states(g, pol)
    GM.MODE.update(exact=True, tags=with_paths)
    st0 = dict(alive=tuple(range(len(labels))), lab=tuple(labels), hist=())
    per = []
    for p, roles, know in worlds:
        nd = g.day(roles, dict(st0, bites=tuple(know)))
        pt = walk(labels, roles, nd, pol, ns)
        per.append((sum(x[1] for x in pt.values()), pt))
    return per

def world_values(key):
    if key in WV: return WV[key]
    labels, worlds = D.from_key(key)
    if len(labels) <= 3:
        R = G3.solve_board(labels, cases=[(p, r) for p, r, kn in worlds], extras=[kn for p, r, kn in worlds])
        vals = R['per'] if R else [F(0)] * len(worlds)
    else:
        vals = [v for v, _ in run_plan(labels, worlds, D.INFO[key]['plan'])]
    WV[key] = {(r, tuple(kn)): v for (p, r, kn), v in zip(worlds, vals)}
    tot = sum(p * v for (p, r, kn), v in zip(worlds, vals))
    assert tot == D.DICT[key], (key[0], tot, D.DICT[key])   # 辞書の値と一致すること
    return WV[key]

def alt_plan(labels, worlds, best):
    """比べる相手：最善と「指定の順番の先頭・投票の仕方」が違う候補のうち一番よいもの"""
    scr = []
    for plan in candidates(labels):
        if (plan['des'][0], plan['mode']) == (best['des'][0], best['mode']): continue
        vf, pol = adv_policy_1(labels, worlds, plan)
        scr.append((vf, plan))
    if not scr: return None
    scr.sort(key=lambda x: -x[0])
    return max(((adv_policy(labels, worlds, p)[0], p) for _, p in scr[:3]), key=lambda x: x[0])[1]

def adv_policy_1(labels, worlds, plan):
    GM.MODE.update(exact=False, tags=False)
    g = Game(labels, plan, start=worlds); root, _ = g.root()
    return D.adversary_min(root, starts=1)

def board_page(board):
    key = D.board_key(board)
    labels, worlds = D.from_key(key)
    best = D.INFO[key]['plan']
    plans = [('g', best)]
    a = alt_plan(labels, worlds, best)
    if a: plans.append(('a', a))
    runs = []
    for tag, plan in plans:
        per = run_plan(labels, worlds, plan, with_paths=True)
        runs.append((tag, plan, per, sum(p * v for (p, _, _), (v, _) in zip(worlds, per))))
    assert runs[0][3] == D.DICT[key]
    ws0 = [(p, r) for p, r, kn in worlds]
    return assemble(labels, ws0, runs)

if __name__ == '__main__':
    n = int(sys.argv[1]); dst = sys.argv[2]
    RD.load()
    out = []
    for b in boards(n, white=(n <= 4)):
        if not GM.worlds(b): continue
        out.append(board_page(b))
        print(','.join(b), out[-1]['v'], out[-1]['va'], flush=True)
        json.dump(out, open(dst, 'w'), ensure_ascii=False, separators=(',', ':'))
