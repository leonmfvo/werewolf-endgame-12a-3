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

FCACHE = {}   # 探索中（小数）の翌日の状態 → 村勝率（小数）。同じ状態を何度も正規形にしないため

def total(root, pol, exact=False):
    term, nxt = outcomes(root, pol, exact)
    v = term
    for (hist, al, lab), ws in nxt.items():
        mass = sum(p for p, _, _ in ws)
        idx = {old: new for new, old in enumerate(al)}
        labs = tuple(lab[i] for i in al)
        if not exact:
            fk = (labs, frozenset((tuple(r[i] for i in al), tuple(idx[k] for k in kn), round(p / mass, 12)) for p, r, kn in ws))
            x = FCACHE.get(fk)
            if x is None:
                worlds = [(F(p / mass).limit_denominator(10**9), tuple(r[i] for i in al), tuple(idx[k] for k in kn)) for p, r, kn in ws]
                x = float(value(canon(list(labs), worlds))); FCACHE[fk] = x
            v += mass * x
            continue
        worlds = [(F(p), tuple(r[i] for i in al), tuple(idx[k] for k in kn)) for p, r, kn in ws]
        v += mass * value(canon(list(labs), worlds))
    return v

class Flat:
    """1日分の木を「行き着く先」の並びに平らにして、人外の手を1か所変えたときに、影響する行き先だけを足し引きする（探索を速くする）"""
    def __init__(self, root):
        self.keys = {}; self.opts = []          # 情報集合 → 番号、選択肢の数
        self.leaves = []                       # (確率, 条件 [(情報集合番号, 手)], 決着の値 or None, 翌日の状態, 世界)
        stack = [(root, 1.0, ())]
        while stack:
            nd, p, req = stack.pop()
            if p == 0: continue
            if nd.kind == 'L': self.leaves.append((p, req, float(nd.v), None, None))
            elif nd.kind == 'N':
                hist, al, lab, roles, know = nd.info
                idx = {old: new for new, old in enumerate(al)}
                self.leaves.append((p, req, None, (hist, al, lab), (tuple(roles[i] for i in al), tuple(idx[k] for k in know))))
            elif nd.kind == 'C':
                for q, c in nd.ch: stack.append((c, p * float(q), req))
            else:
                k = (nd.agent, nd.info)
                if k not in self.keys: self.keys[k] = len(self.opts); self.opts.append(len(nd.opts))
                i = self.keys[k]
                for a, c in enumerate(nd.ch): stack.append((c, p, req + ((i, a),)))
        self.by = defaultdict(list)
        for li, (p, req, tv, ok, wd) in enumerate(self.leaves):
            for ia in req: self.by[ia].append(li)
        self.order = list(range(len(self.opts)))

    def setup(self, pol):
        self.pol = list(pol)
        self.term = 0.0; self.mass = defaultdict(lambda: defaultdict(float)); self.labs = {}
        self.active = [False] * len(self.leaves)
        self.contrib = {}; self.sumc = 0.0; self.dirty = set()
        for li, (p, req, tv, ok, wd) in enumerate(self.leaves):
            if all(self.pol[i] == a for i, a in req): self.add(li, 1)
        return self.value()

    def add(self, li, sgn):
        p, req, tv, ok, wd = self.leaves[li]
        self.active[li] = sgn > 0
        if tv is not None: self.term += sgn * p * tv
        else:
            self.mass[ok][wd] += sgn * p
            self.dirty.add(ok)

    def outcome_value(self, ok):
        ws = {w: m for w, m in self.mass[ok].items() if m > 1e-15}
        mass = sum(ws.values())
        if mass <= 1e-15: return 0.0
        hist, al, lab = ok
        labs = tuple(lab[i] for i in al)
        fk = (labs, frozenset((r, kn, round(m / mass, 12)) for (r, kn), m in ws.items()))
        x = FCACHE.get(fk)
        if x is None:
            worlds = [(F(m / mass).limit_denominator(10**9), r, kn) for (r, kn), m in ws.items()]
            x = float(value(canon(list(labs), worlds))); FCACHE[fk] = x
        return mass * x

    def value(self):
        """変わった行き先（dirty）だけ村勝率を求め直す"""
        for ok in self.dirty:
            new = self.outcome_value(ok)
            self.sumc += new - self.contrib.get(ok, 0.0); self.contrib[ok] = new
        self.dirty.clear()
        return self.term + self.sumc

    def change(self, i, a):
        """情報集合 i の手を a に変え、影響した分だけ足し引きする"""
        old = self.pol[i]
        for li in self.by[(i, old)]:
            if self.active[li]: self.add(li, -1)
        self.pol[i] = a
        for li in self.by[(i, a)]:
            p, req, tv, ok, wd = self.leaves[li]
            if all(self.pol[j] == b for j, b in req): self.add(li, 1)

def adversary_min(root, starts=9):
    fl = Flat(root)
    n = len(fl.opts)
    best = None
    for s in range(starts):
        rnd = random.Random(s)
        pol = [0 if s == 0 else rnd.randrange(fl.opts[i]) for i in range(n)]
        cur = fl.setup(pol)
        # 見る順番：前から・後ろから・ばらばら（順番しだいで行き着く手が変わるので、いくつか試して一番低いものを取る）
        order = list(range(n)) if s % 3 == 0 else (list(range(n))[::-1] if s % 3 == 1 else rnd.sample(range(n), n))
        improved = True
        while improved:
            improved = False
            for i in order:
                for a in range(fl.opts[i]):
                    old = fl.pol[i]
                    if a == old: continue
                    fl.change(i, a)
                    v = fl.value()
                    if v < cur - 1e-12: cur = v; improved = True
                    else: fl.change(i, old)
        if best is None or cur < best[0] - 1e-12:
            best = (cur, {k: fl.pol[i] for k, i in fl.keys.items()})
    return best

def solve_day(key, labels, worlds):
    start = [(p, r, kn) for p, r, kn in worlds]
    # 1段目：全候補を、人外の探索1回でふるう（人外の最善を見逃すと値は高めに出るので、上位を取りこぼしにくい）
    scr = []
    for plan in candidates(labels):
        GM.MODE.update(exact=False, tags=False)   # 探索は小数の木で
        g = Game(labels, plan, start=start); root, _ = g.root()
        vf, pol = adversary_min(root, starts=1)
        scr.append((vf, plan))
    scr.sort(key=lambda x: -x[0])
    # 2段目：上位5つを、やり直し6回で詰め直し、値は分数の木で厳密に
    best = None
    for vf0, plan in scr[:5]:
        GM.MODE.update(exact=False, tags=False)
        g = Game(labels, plan, start=start); root, _ = g.root()
        vf, pol = adversary_min(root)
        if best is not None and vf < float(best[0]) - 1e-9: continue
        GM.MODE.update(exact=True, tags=False)    # 値は分数の木で厳密に
        root, _ = g.root()
        v = total(root, pol, exact=True)
        if best is None or v > best[0]: best = (v, plan, pol)
    INFO[key] = dict(plan=best[1])
    return best[0]

def board_key(board):
    """盤面（最初の割合：役の札の数から）の状態キー"""
    ws = GM.worlds(board)
    return canon(board, [(F(w), roles, ()) for w, roles in ws])
