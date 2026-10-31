# 翌日の盤面を、保存済みの少ない人数の結果で置き換えるための表。
# 盤面（見た目）と、その内訳（見た目ごとの本当の役）→ 村勝率。キーは並び順によらない形にする。
import json, os
from fractions import Fraction as F

def key_of(labels, roles):
    pairs = tuple(sorted(zip(labels, roles)))
    return tuple(sorted(labels)), pairs

def table3():
    """3人日：盤面全体で1つの決め方（vote3g）と人外の最善のもとで、内訳ごとの村勝率"""
    import vote3g as G, vote3 as V3
    tab = {}
    for board in V3.boards():
        R = G.solve_board(board)
        if not R: continue
        P = G.plan_dists(R); A = {t: {a: F(1)} for t, a in zip(R['at'], R['ads'])}
        for w, roles in R['cases']:
            votes = [V3.vote_dist(board, i, P[(board[i], roles[i])] if roles[i] in V3.VILL else A[(board[i], roles[i])]) for i in range(len(board))]
            tab[key_of(board, roles)] = G.outcome(board, roles, votes, True)[1]
    return tab

def table_n(plans_file, ref=None):
    """4人日など：保存した最善の進め方で解き直し、内訳ごとの村勝率"""
    from game import Game, solve_adv, evaluate
    tab = {}
    for key, ranked in json.load(open(plans_file)).items():
        if not ranked: continue
        board = key.split(','); plan = ranked[0][1]
        g = Game(board, plan, ref=ref); root, ws = g.root()
        v, pol = solve_adv(root)
        for (p, ch), (w, roles) in zip(root.ch, ws):
            tab[key_of(board, roles)] = evaluate(ch, pol)
    return tab

def save(tab, path):
    json.dump([[list(k[0]), [list(x) for x in k[1]], str(v)] for k, v in tab.items()], open(path, 'w'), ensure_ascii=False)

def load(path):
    return {(tuple(a), tuple(tuple(x) for x in b)): F(v) for a, b, v in json.load(open(path))}
