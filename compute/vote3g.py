# 3人日：村は生存状況（狂人の生死・灰の狩人や猫又）を知らない。盤面ごとに1つの決め方（見た目と自分の役ごと）を選ぶ。
# 狼・狂人も自分の見た目と役しか分からない。村はすべての内訳（役の札の数からの重み）の平均で一番勝てる決め方を選び、
# 人外はそれを知ったうえで、2人で一番村に不利な投票をする。
import itertools
from fractions import Fraction as F
from collections import defaultdict
import vote3 as V3

COARSE = [0, 1/4, 1/3, 1/2, 2/3, 3/4, 1]

def solve_board(board):
    cases = list(V3.assignments(board))
    if not cases: return None
    vt = sorted({(board[i], r[i]) for _, r in cases for i in range(len(board)) if r[i] in V3.VILL}, key=lambda t: (V3.LABELS.index(t[0]), t[1]))
    at = sorted({(board[i], r[i]) for _, r in cases for i in range(len(board)) if r[i] in 'WX'}, key=lambda t: (V3.LABELS.index(t[0]), t[1]))
    tg = {t: V3.targets(board, board.index(t[0])) for t in vt + at}
    tot = sum(w for w, _ in cases)
    # 浮動小数で速く：各内訳について、各人の投票先（個人）の確率
    idx_of = {t: i for i, t in enumerate(vt)}
    def val(ps, ads, exact=False):
        num = (lambda x: F(x)) if exact else float
        s = num(0)
        for w, roles in cases:
            votes = []
            for i in range(len(board)):
                t = (board[i], roles[i])
                if roles[i] in V3.VILL:
                    labs = tg[t]; d = {labs[0]: num(ps[idx_of[t]]), labs[1]: 1 - num(ps[idx_of[t]])} if len(labs) == 2 else {labs[0]: num(1)}
                else: d = {ads[at.index(t)]: num(1)}
                votes.append(V3.vote_dist(board, i, d) if exact else {j: float(p) for j, p in V3.vote_dist(board, i, {k: F(v) if not isinstance(v, float) else F(v).limit_denominator(1000) for k, v in d.items()}).items()})
            hang, v = outcome(board, roles, votes, exact)
            s += num(w) / tot * v
        return s
    aopts = list(itertools.product(*[tg[t] for t in at]))
    def worst(ps):
        return min((val(ps, a), a) for a in aopts)
    nv = [len(tg[t]) == 2 for t in vt]
    grids = [COARSE if two else [1] for two in nv]
    best = None
    for ps in itertools.product(*grids):
        w = worst(ps)
        if best is None or w[0] > best[0] + 1e-12: best = (w[0], ps, w[1])
    # 1/12 刻みで、1つずつ動かして詰める
    improved = True
    ps = list(best[1])
    while improved:
        improved = False
        for k in range(len(vt)):
            if not nv[k]: continue
            for q in [x / 12 for x in range(13)]:
                trial = ps[:]; trial[k] = q
                w = worst(trial)
                if w[0] > best[0] + 1e-12: best = (w[0], tuple(trial), w[1]); ps = trial; improved = True
    ps = [F(p).limit_denominator(12) for p in best[1]]
    ads = min(aopts, key=lambda a: val(ps, a, True))
    # 比べる相手：「全部入れる／1/2ずつ」の決め方で、最善と違うもののうち一番よいもの（同じく人外の最善応答に対して）
    alt = None
    for q in itertools.product(*[[0, 1/2, 1] if two else [1] for two in nv]):
        qf = [F(x).limit_denominator(12) for x in q]
        if qf == ps: continue
        w = worst(q)
        if alt is None or w[0] > alt[0] + 1e-12: alt = (w[0], qf)
    altd = None
    if alt:
        a_ads = min(aopts, key=lambda a: val(alt[1], a, True))
        altd = dict(ps=alt[1], ads=a_ads, v=val(alt[1], a_ads, True))
    return dict(cases=cases, vt=vt, at=at, tg=tg, ps=ps, ads=ads, v=val(ps, ads, True), alt=altd)

def outcome(board, roles, votes, exact):
    n = len(board)
    hang = defaultdict(float if not exact else F)
    for combo in itertools.product(*[list(v.items()) for v in votes]):
        p = 1; cnt = [0] * n
        for t, q in combo: p *= q; cnt[t] += 1
        if p == 0: continue
        m = max(cnt); top = [k for k in range(n) if cnt[k] == m]
        for k in top: hang[k] += p / len(top)
    v = 0
    for k, p in hang.items():
        r = roles[k]
        x = 1 if r == 'W' else ((sum(1 for j in range(n) if j != k and roles[j] == 'W') / (n - 1)) if not exact else F(sum(1 for j in range(n) if j != k and roles[j] == 'W'), n - 1)) if r == 'C' else 0
        v += p * x
    return hang, v

def plan_dists(R, ps=None):
    out = {}
    for t, p in zip(R['vt'], ps if ps is not None else R['ps']):
        labs = R['tg'][t]
        out[t] = {labs[0]: p, labs[1]: 1 - p} if len(labs) == 2 else {labs[0]: F(1)}
    return out

if __name__ == '__main__':
    import time
    for b in V3.boards():
        t = time.time(); R = solve_board(b)
        if R: print(','.join(b), R['v'], {t: str(p) for t, p in zip(R['vt'], R['ps'])}, R['ads'], round(time.time() - t, 1), flush=True)
