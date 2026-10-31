# 日ごとに解く（辞書方式）：盤面の状態＝見た目＋内訳の割合＋狼だけが知っていること。
# その日の朝、村は状態に対して進め方の候補から最善を選び、人外は自分の視点で最善を返す。翌日の状態の村勝率は辞書から引く（なければ解いて足す）。
# 状態の村勝率 = Σ（その日の結果で次の状態になる確率 × 次の状態の村勝率）＋（その日のうちに決着する分）。定義上、参照と全部作り直しは一致する。
import itertools, json, os, random
from fractions import Fraction as F
from collections import defaultdict
import game as GM
from game import Game, agents_infosets
from plans import candidates
import vote3g as G3

ORDER = ['霊', '猫', 'ギ', '狩', '白', '灰']
DICT = {}   # 状態のキー → 村勝率（分数）
INFO = {}   # 状態のキー → 説明用（最善の進め方など）

def canon(labels, worlds):
    """状態の正規形：同じ見た目の人の並べ替えで、いちばん小さい形にそろえる。worlds = [(確率, 役, 知っている人)]"""
    n = len(labels)
    order = sorted(range(n), key=lambda i: ORDER.index(labels[i]))
    groups = []
    for i in order:
        if groups and labels[groups[-1][0]] == labels[i]: groups[-1].append(i)
        else: groups.append([i])
    perms = [list(itertools.permutations(g)) for g in groups]
    best = None
    tot = sum(p for p, _, _ in worlds)
    for combo in itertools.product(*perms):
        pos = [i for g in combo for i in g]          # 新しい並び
        inv = {old: new for new, old in enumerate(pos)}
        ws = tuple(sorted((tuple(r[i] for i in pos), tuple(sorted(inv[k] for k in know)), str(F(p) / tot)) for p, r, know in worlds))
        key = (tuple(labels[i] for i in pos), ws)
        if best is None or key < best: best = key
        if len(perms) and sum(len(x) for x in perms) > 5040: break
    return best

def from_key(key):
    labels, ws = key
    return list(labels), [(F(p), r, kn) for r, kn, p in ws]

def value(key):
    if key in DICT: return DICT[key]
    labels, worlds = from_key(key)
    n = len(labels)
    if n <= 3: v = solve3(labels, worlds)
    else: v = solve_day(key, labels, worlds)
    DICT[key] = v
    return v

def solve3(labels, worlds):
    R = G3.solve_board(labels, cases=[(p, r) for p, r, kn in worlds], extras=[kn for p, r, kn in worlds])
    return R['v'] if R else F(0)

def outcomes(root, pol, exact):
    """方針 pol のもとで：その日のうちの決着分と、翌日の状態ごとの（確率, 世界）"""
    num = (lambda x: x) if exact else float
    term = num(0); nxt = defaultdict(list)
    stack = [(root, num(1))]
    while stack:
        nd, p = stack.pop()
        if p == 0: continue
        if nd.kind == 'L': term += p * (nd.v if exact else float(nd.v))
        elif nd.kind == 'N':
            hist, al, lab, roles, know = nd.info
            nxt[(hist, al, lab)].append((p, roles, know))
        elif nd.kind == 'C':
            for q, c in nd.ch: stack.append((c, p * (q if exact else float(q))))
        else: stack.append((nd.ch[pol.get((nd.agent, nd.info), 0)], p))
    return term, nxt

def total(root, pol, exact=False):
    term, nxt = outcomes(root, pol, exact)
    v = term
    for (hist, al, lab), ws in nxt.items():
        mass = sum(p for p, _, _ in ws)
        idx = {old: new for new, old in enumerate(al)}
        worlds = [(F(p) if exact else F(p).limit_denominator(10**12), tuple(r[i] for i in al), tuple(idx[k] for k in kn)) for p, r, kn in ws]
        key = canon([lab[i] for i in al], worlds)
        x = value(key)
        v += mass * (x if exact else float(x))
    return v

def adversary_min(root, starts=6):
    byinfo, order = agents_infosets(root)
    keys = sorted(byinfo, key=lambda k: -order[k])
    best = None
    for s in range(starts):
        rnd = random.Random(s)
        pol = {k: (0 if s == 0 else rnd.randrange(len(byinfo[k][0].opts))) for k in keys}
        cur = total(root, pol)
        improved = True
        while improved:
            improved = False
            for k in keys:
                for a in range(len(byinfo[k][0].opts)):
                    if a == pol[k]: continue
                    old = pol[k]; pol[k] = a
                    v = total(root, pol)
                    if v < cur - 1e-12: cur = v; improved = True
                    else: pol[k] = old
        if best is None or cur < best[0] - 1e-12: best = (cur, dict(pol))
    return best

def solve_day(key, labels, worlds):
    best = None
    for plan in candidates(labels):
        GM.MODE.update(exact=True, tags=False)
        g = Game(labels, plan, start=[(p, r, kn) for p, r, kn in worlds]); root, _ = g.root()
        vf, pol = adversary_min(root)
        if best is not None and vf < float(best[0]) - 1e-9: continue
        v = total(root, pol, exact=True)
        if best is None or v > best[0]: best = (v, plan, pol)
    INFO[key] = dict(plan=best[1])
    return best[0]

def board_key(board):
    """盤面（最初の割合：役の札の数から）の状態キー"""
    ws = GM.worlds(board)
    return canon(board, [(F(w), roles, ()) for w, roles in ws])
