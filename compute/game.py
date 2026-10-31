# 12A猫 終盤（4・5人日）：盤面と村の進め方（候補）から、ゲーム木を作り、狼・狂人の最善応答（各自の視点）で村勝率を求める。
#
# 規則：投票は公開・最多票を吊る（同票はランダム）。本物の猫又は吊られると生存者からランダムに1人道連れ、噛まれると狼がランダムに1人死ぬ。
#       狩人は毎晩1人を護衛（連続護衛あり）、護衛先が噛まれたらGJ（誰も死なない）。GJの翌朝、狩人はCOして護衛先を出せる（村の進め方の一部）。
#       PP：5人以上・狂人が生きていて人外が過半数なら狼の勝ち（同数なら半々）。狼が全滅で村、狼が半数以上で狼の勝ち。
# 視点：村は進め方の決まり（誰を指定するか等）に従う。狼は仲間と自分の噛み先を知り、狂人は自分しか知らない。投票と死者は全員に見える。
import itertools
from fractions import Fraction as F
from collections import defaultdict

ROLES = {'M': 1, 'H': 1, 'C': 1, 'X': 1, 'W': 3, 'V': 4}
VILL = set('MHCV')
LABELS = ['霊', '猫', 'ギ', '狩', '白', '灰']
CAN = {'霊': 'MXW', '狩': 'HXW', 'ギ': 'HCXW', '白': 'VCX', '灰': 'VHCXW'}   # 白：GJの翌朝に狩人が出した護衛先（人間確定）

def weight(roles):
    cnt = defaultdict(int); w = 1
    for r in roles:
        w *= ROLES[r] - cnt[r]; cnt[r] += 1
    return w

def worlds(board):
    """[(重み, 役の並び)]（狼は1〜2人。始まった時点で決着・PP確定のものは除く）"""
    opts = [('CXW' if l == '猫' else CAN[l]) for l in board]
    n = len(board); out = []
    for roles in itertools.product(*opts):
        w = roles.count('W')
        if w == 0 or 2 * w >= n: continue
        if any(roles.count(r) > ROLES[r] for r in ROLES): continue
        cats = [r for l, r in zip(board, roles) if l == '猫']
        if cats and cats.count('C') != 1: continue
        # 霊COが1人・狩COが1人なら本物（偽のCOには本物が対抗する）
        if board.count('霊') == 1 and roles[board.index('霊')] != 'M': continue
        if board.count('狩') == 1 and roles[board.index('狩')] != 'H': continue
        if '狩' in board and any(l == '灰' and r == 'H' for l, r in zip(board, roles)): continue
        if 'ギ' in board and any(l == '灰' and r in 'HC' for l, r in zip(board, roles)): continue
        if 'X' in roles and n >= 5 and 2 * (w + 1) > n: continue   # PP 確定
        out.append((weight(roles), roles))
    return out

def situation(board, roles, alive=None):
    alive = range(len(board)) if alive is None else alive
    w = sum(1 for i in alive if roles[i] == 'W'); x = any(roles[i] == 'X' for i in alive)
    st = f'{w}w' + ('1k' if x else '') + '生存'
    hid = []
    if any(board[i] == '灰' and roles[i] == 'H' for i in alive): hid.append('狩生存')
    if any(board[i] == '灰' and roles[i] == 'C' for i in alive): hid.append('猫生存')
    return st + ('（' + '・'.join(hid) + '）' if hid else '')

# ---------------------------------------------------------------- 木
class Node:
    __slots__ = ('kind', 'ch', 'v', 'info', 'agent', 'opts', 'tag', 'fch', 'fv')
    # kind: 'L' 終局（v）/ 'C' 偶然（ch=[(p, node)]）/ 'A' 人外の選択（agent, info, opts=[label], ch=[node]）
    def __init__(self, kind, **kw):
        self.kind = kind; self.ch = None; self.v = None; self.info = None; self.agent = None; self.opts = None; self.tag = None
        self.fch = None; self.fv = None
        for k, x in kw.items(): setattr(self, k, x)

# EXACT=False のときは、探索用に木を小数で作り、説明用の目印の節も作らない（メモリを大きく減らす）。
# 値は最後に exact_value で、内訳ごとに分数の木を作り直して厳密に求める。
MODE = {'exact': True, 'tags': True}

def leaf(v): return Node('L', v=F(v) if MODE['exact'] else float(v))

def tagged(tag, node):
    """説明用の目印（吊り・噛み・GJ など）をつけた1本道の節"""
    if not MODE['tags']: return node
    return Node('C', ch=[(F(1) if MODE['exact'] else 1.0, node)], tag=tag)

def chance(lst):
    lst = [(p, c) for p, c in lst if p > 0]
    if len(lst) == 1: return lst[0][1]
    if not MODE['exact']: lst = [(float(p), c) for p, c in lst]
    return Node('C', ch=lst)

class Game:
    """plan: dict(des=('灰', ...), counter=True, self='next', guard=('霊', ...), co=True)"""
    def __init__(self, board, plan, ref=None, start=None):
        """ref：{生存人数: 表}。翌日の盤面がその表にあれば、その内訳の村勝率で置き換える（refs.py）
        start：[(確率, 役, 狼が知っている人間)] を与えると、その割合から始めて、翌日の手前で止める（daily.py 用。翌日は 'N' の節）"""
        self.board = list(board); self.plan = plan; self.n = len(board)
        self.memo = {}; self.ref = ref or {}; self.start = start

    def labels(self, st):
        return st['lab']

    def wins(self, roles, alive):
        w = sum(1 for i in alive if roles[i] == 'W')
        if w == 0: return F(1)
        if 2 * w >= len(alive): return F(0)
        return None

    def root(self):
        if self.start is not None:
            st0 = dict(alive=tuple(range(self.n)), lab=tuple(self.board), hist=())
            cv = (lambda x: x) if MODE['exact'] else float
            return Node('C', ch=[(cv(p), self.day(roles, dict(st0, bites=tuple(know)))) for p, roles, know in self.start]), None
        ws = worlds(self.board)
        tot = sum(w for w, _ in ws)
        st0 = dict(alive=tuple(range(self.n)), lab=tuple(self.board), hist=(), bites=())
        cv = (lambda x: x) if MODE['exact'] else float
        return Node('C', ch=[(cv(F(w, tot)), self.day(roles, st0)) for w, roles in ws]), ws   # 内訳ごとの枝（1つでもまとめない）

    def exact_value(self, pol):
        """人外の手 pol のもとで、村勝率を分数で厳密に（内訳ごとに分数の木を作っては捨てる）"""
        old = dict(MODE); MODE.update(exact=True, tags=False)
        try:
            ws = worlds(self.board); tot = sum(w for w, _ in ws)
            st0 = dict(alive=tuple(range(self.n)), lab=tuple(self.board), hist=(), bites=())
            v = F(0)
            for w, roles in ws:
                nd = self.day(roles, st0)
                v += F(w, tot) * evaluate(nd, pol, default=0)
            return v
        finally:
            MODE.update(old)

    # ---- 昼
    def day(self, roles, st):
        alive = st['alive']
        t = self.wins(roles, alive)
        if t is not None: return leaf(t)
        n = len(alive); w = sum(1 for i in alive if roles[i] == 'W')
        if any(roles[i] == 'X' for i in alive) and n >= 5 and 2 * (w + 1) >= n:
            if 2 * (w + 1) > n: return leaf(0)
            return chance([(F(1, 2), leaf(0)), (F(1, 2), self.vote(roles, st))])
        return self.vote(roles, st)

    def classes(self, st):
        return {l: [i for i in st['alive'] if st['lab'][i] == l] for l in set(st['lab'][i] for i in st['alive'])}

    def designations(self, st):
        """[(確率, 指定された人)]：指定の順で最初にいる区分から等確率"""
        cl = self.classes(st)
        for l in self.plan['des']:
            if cl.get(l): return [(F(1, len(cl[l])), d) for d in cl[l]]
        rest = [i for i in st['alive'] if st['lab'][i] not in ('白',)]
        return [(F(1, len(rest)), d) for d in rest]

    def village_vote(self, roles, st, i, d):
        """村の人 i の投票先の分布（指定 d のとき）"""
        lab = st['lab']; cl = self.classes(st)
        mine = [j for j in cl.get(lab[i], []) if j != i]
        if self.plan.get('counter') and lab[i] in ('霊', '猫', '狩', 'ギ') and mine:
            return {j: F(1, len(mine)) for j in mine}
        if d is not None and i != d: return {d: F(1)}
        for l in self.plan['des']:
            c = [j for j in cl.get(l, []) if j != i]
            if c: return {j: F(1, len(c)) for j in c}
        c = [j for j in st['alive'] if j != i]
        return {j: F(1, len(c)) for j in c}

    def vote(self, roles, st):
        alive = st['alive']
        if self.plan.get('mode') == 'spread':   # 指定なし：各自が区分の中からランダムに入れる
            return self.vote_d(roles, st, None)
        out = []
        for pd, d in self.designations(st):
            out.append((pd, self.vote_d(roles, st, d)))
        return chance(out)

    def vote_d(self, roles, st, d):
        alive = st['alive']
        vill = {i: self.village_vote(roles, st, i, d) for i in alive if roles[i] in VILL}
        adv = [i for i in alive if roles[i] not in VILL]
        wolves = tuple(i for i in alive if roles[i] == 'W'); mad = [i for i in alive if roles[i] == 'X']
        # 人外の投票：見分けのつかない人（同じ見た目・指定されたかどうかが同じ）の中からはランダム。狼（全員まとめて1つの選択）→ 狂人
        wopts = list(itertools.product(*[self.groups(st, i, d) for i in wolves]))
        wnode = Node('A', agent='W', info=('V', st['hist'], st['lab'], wolves, st['bites'], d), opts=wopts, ch=[])
        for wv in wopts:
            wd = {i: {j: F(1, len(g)) for j in g} for i, g in zip(wolves, wv)}
            if mad:
                m = mad[0]
                mo = self.groups(st, m, d)
                mnode = Node('A', agent='X', info=('V', st['hist'], st['lab'], m, d), opts=mo, ch=[])
                for g in mo:
                    mnode.ch.append(self.resolve(roles, st, vill, wd | {m: {j: F(1, len(g)) for j in g}}))
                wnode.ch.append(mnode)
            else:
                wnode.ch.append(self.resolve(roles, st, vill, wd))
        return wnode

    def groups(self, st, i, d=None, excl_wolves=None):
        """i から見て見分けのつかない人のまとまり（見た目＋指定されたか）。i 自身は除く"""
        g = defaultdict(list)
        for j in st['alive']:
            if j == i or (excl_wolves and j in excl_wolves): continue
            g[(st['lab'][j], j == d)].append(j)
        return [tuple(v) for k, v in sorted(g.items(), key=lambda kv: (LABELS.index(kv[0][0]) if kv[0][0] in LABELS else 9, not kv[0][1]))]

    def resolve(self, roles, st, vill, advv):
        """票の分布 → 吊り"""
        alive = st['alive']
        dists = [list(vill[i].items()) if i in vill else list(advv[i].items()) for i in alive]
        out = []
        for combo in itertools.product(*dists):
            p = F(1); cnt = defaultdict(int)
            for t, q in combo: p *= q; cnt[t] += 1
            m = max(cnt.values()); top = sorted(k for k, c in cnt.items() if c == m)
            prof = tuple(t for t, _ in combo)
            for k in top:
                out.append((p / len(top), tagged(('吊', k), self.after_hang(roles, st, k, prof))))
        return chance(out)

    def after_hang(self, roles, st, k, prof):
        alive = tuple(i for i in st['alive'] if i != k)
        hist = st['hist'] + (('vote', prof, k),)
        st2 = dict(st, alive=alive, hist=hist)
        if roles[k] == 'C':   # 猫又の道連れ
            out = []
            for j in alive:
                al = tuple(x for x in alive if x != j)
                out.append((F(1, len(alive)), tagged(('道連れ', j), self.check_then(roles, dict(st2, alive=al, hist=hist + (('drag', j),)), 'N'))))
            return chance(out)
        return self.check_then(roles, st2, 'N')

    def next_day(self, roles, st):
        """翌日：保存済みの少ない人数の結果があれば、その内訳の村勝率を使う"""
        al = st['alive']
        if self.start is not None:   # 日ごとに解く：翌日の状態をそのまま返す（狼が知っている人間＝噛んで生き残った人）
            know = tuple(sorted(set(st['bites']) & set(al)))
            return Node('N', info=(st['hist'], al, st['lab'], roles, know))
        tab = self.ref.get(len(al))
        if tab is not None:
            from refs import key_of
            v = tab.get(key_of([st['lab'][i] for i in al], [roles[i] for i in al]))
            if v is not None: return tagged(('翌日', al, st['lab'], 'ref'), leaf(v))
        return tagged(('翌日', al, st['lab']), self.day(roles, st))

    def check_then(self, roles, st, nxt):
        t = self.wins(roles, st['alive'])
        if t is not None: return leaf(t)
        return self.night(roles, st) if nxt == 'N' else self.next_day(roles, st)

    # ---- 夜
    def guard_dist(self, roles, st, h):
        cl = self.classes(st)
        for l in self.plan['guard']:
            c = [j for j in cl.get(l, []) if j != h]
            if c: return [(F(1, len(c)), j) for j in c]
        c = [j for j in st['alive'] if j != h]
        return [(F(1, len(c)), j) for j in c]

    def night(self, roles, st):
        alive = st['alive']
        wolves = tuple(i for i in alive if roles[i] == 'W')
        tgroups = self.groups(st, None, None, excl_wolves=set(wolves))
        node = Node('A', agent='W', info=('N', st['hist'], st['lab'], wolves, st['bites']), opts=tgroups, ch=[])
        h = next((i for i in alive if roles[i] == 'H'), None)
        for grp in tgroups:
            node.ch.append(chance([(F(1, len(grp)), tagged(('噛み', b), self.bite(roles, st, wolves, h, b))) for b in grp]))
        return node

    def bite(self, roles, st, wolves, h, b):
        alive = st['alive']
        if True:
            st2 = dict(st, bites=st['bites'] + (b,))
            gd = self.guard_dist(roles, st, h) if h is not None and h != b else []
            pgj = sum((p for p, j in gd if j == b), F(0))
            out = []
            if pgj > 0: out.append((pgj, tagged(('GJ',), self.gj_morning(roles, st2, h, b))))
            if pgj < 1:
                al = tuple(x for x in alive if x != b)
                hist = st2['hist'] + (('dead', b),)
                if roles[b] == 'C':   # 猫噛み：狼がランダムに1人死ぬ
                    sub = []
                    for wv in wolves:
                        al2 = tuple(x for x in al if x != wv)
                        sub.append((F(1, len(wolves)), self.check_then(roles, dict(st2, alive=al2, hist=hist + (('catbite', wv),)), 'D')))
                    out.append((1 - pgj, tagged(('死亡', b), tagged(('猫噛み',), chance(sub)))))
                else:
                    out.append((1 - pgj, tagged(('死亡', b), self.check_then(roles, dict(st2, alive=al, hist=hist), 'D'))))
            return chance(out)

    def gj_morning(self, roles, st, h, b):
        hist = st['hist'] + (('gj',),)
        if not self.plan.get('co') or st['lab'][h] == '狩':
            lab = st['lab']
            if st['lab'][h] == '狩' and self.plan.get('co'):   # COずみの狩人は護衛先を出す
                lab = tuple('白' if j == b and l == '灰' else l for j, l in enumerate(lab))
                hist = hist + (('guard', h, b),)
            st3 = dict(st, hist=hist, lab=lab)
            return self.next_day(roles, st3)
        lab = tuple('狩' if j == h else ('白' if j == b and l == '灰' else l) for j, l in enumerate(st['lab']))   # 灰の護衛先だけが白になる
        st3 = dict(st, hist=hist + (('hco', h, b),), lab=lab)
        return tagged(('狩人CO',), self.next_day(roles, st3))

# ---------------------------------------------------------------- 最善応答（人外：狼と狂人を交互に）
def agents_infosets(root):
    byinfo = defaultdict(list); order = {}
    def walk(nd, depth):
        if nd.kind == 'A':
            byinfo[(nd.agent, nd.info)].append(nd); order[(nd.agent, nd.info)] = max(order.get((nd.agent, nd.info), 0), depth)
            for c in nd.ch: walk(c, depth + 1)
        elif nd.kind == 'C':
            for _, c in nd.ch: walk(c, depth + 1)
    walk(root, 0)
    return byinfo, order

def evaluate(root, pol, default=None):
    """厳密な値（分数）。default を与えると、pol にない情報集合（その内訳だけで出る）ではその手を使う"""
    memo = {}
    def v(nd):
        k = id(nd)
        if k in memo: return memo[k]
        if nd.kind == 'L': r = nd.v
        elif nd.kind == 'C': r = sum((p * v(c) for p, c in nd.ch), F(0))
        else: r = v(nd.ch[pol.get((nd.agent, nd.info), default) if default is not None else pol[(nd.agent, nd.info)]])
        memo[k] = r; return r
    return v(root)

def to_float(root):
    """探索用に確率と値を小数にしておく（探索は小数で速く、最後の値だけ分数で求める）"""
    stack = [root]; seen = set()
    while stack:
        nd = stack.pop()
        if id(nd) in seen: continue
        seen.add(id(nd))
        if nd.kind == 'L': nd.fv = float(nd.v)
        elif nd.kind == 'C':
            nd.fch = nd.ch if not MODE['exact'] else [(float(p), c) for p, c in nd.ch]; stack.extend(c for _, c in nd.ch)
        else: stack.extend(nd.ch)

def evaluate_f(root, pol):
    memo = {}
    def v(nd):
        k = id(nd)
        if k in memo: return memo[k]
        if nd.kind == 'L': r = nd.fv
        elif nd.kind == 'C': r = sum(p * v(c) for p, c in nd.fch)
        else: r = v(nd.ch[pol[(nd.agent, nd.info)]])
        memo[k] = r; return r
    return v(root)

def reach_others(root, pol, agent):
    """agent 以外（偶然・ほかの人外）の到達確率（小数）"""
    reach = defaultdict(float)
    def walk(nd, p):
        if p == 0: return
        if nd.kind == 'C':
            for q, c in nd.fch: walk(c, p * q)
        elif nd.kind == 'A':
            reach[id(nd)] += p
            if nd.agent == agent:
                for c in nd.ch: walk(c, p)
            else: walk(nd.ch[pol[(nd.agent, nd.info)]], p)
    walk(root, 1.0)
    return reach

def best_response(root, pol, agent, byinfo, order):
    pol = dict(pol)
    reach = reach_others(root, pol, agent)
    infos = sorted([k for k in byinfo if k[0] == agent], key=lambda k: -order[k])
    for key in infos:
        nds = byinfo[key]
        best = None
        for a in range(len(nds[0].opts)):
            pol[key] = a
            tot = 0.0
            for nd in nds:
                r = reach.get(id(nd), 0)
                if r: tot += r * evaluate_f(nd.ch[a], pol)
            if best is None or tot < best[0] - 1e-12: best = (tot, a)
        pol[key] = best[1]
    return pol

def solve_adv(root, starts=15):
    if root.fch is None: to_float(root)
    byinfo, order = agents_infosets(root)
    best = None
    import random
    for s in range(starts):
        rnd = random.Random(s)
        pol = {k: (0 if s == 0 else rnd.randrange(len(nds[0].opts))) for k, nds in byinfo.items()}
        prev = None
        for it in range(20):
            for ag in ('W', 'X'):
                pol = best_response(root, pol, ag, byinfo, order)
            v = evaluate_f(root, pol)
            if prev is not None and v >= prev - 1e-12: break
            prev = v
        if best is None or v < best[0] - 1e-12: best = (v, pol)
    if not MODE['exact']: return best[0], best[1]   # 小数の木：厳密な値は Game.exact_value で
    return evaluate(root, best[1]), best[1]   # 値は分数で厳密に

def solve_adv_exact(root, limit=200000):
    """人外の手をすべて試す（情報集合が少ないときだけ）。各自の視点の範囲で2人で一番村に不利な組み合わせ"""
    byinfo, order = agents_infosets(root)
    keys = list(byinfo)
    sizes = [len(byinfo[k][0].opts) for k in keys]
    tot = 1
    for s in sizes: tot *= s
    if tot > limit: return None
    best = None
    for combo in itertools.product(*[range(s) for s in sizes]):
        pol = dict(zip(keys, combo))
        v = evaluate(root, pol)
        if best is None or v < best[0]: best = (v, pol)
    return best
