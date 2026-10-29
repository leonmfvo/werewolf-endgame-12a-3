# 3人日の計算結果を、wiki（ゲヘナのwiki）の書き方に合わせた文章にする。
#   見出し「1狼1狂生存で猫に狂」、1行目「〇〇なら村勝率1/4、△△なら3/8」、導出「村勝ちは狼が真猫に入れる(1/2)×猫飛び(1/2)=1/4」
import itertools
from fractions import Fraction as F
from collections import defaultdict
import vote3 as V3

def fs(x):
    x = F(x); return str(x.numerator) if x.denominator == 1 else f'{x.numerator}/{x.denominator}'

def pname(board, roles, i):
    """人の呼び名（真猫・狂・狼・村 など）"""
    l, r = board[i], roles[i]
    if r == 'W': return '狼'
    if r == 'X': return '狂'
    if l == '猫': return '真猫'
    if l == '霊': return '真霊'
    if l == '狩': return '真狩'
    if l == 'ギ': return {'H': 'ギの狩', 'C': 'ギの猫'}[r]
    return {'V': '村', 'H': '灰の狩', 'C': '灰の猫'}[r]

def names(board, roles):
    ns = [pname(board, roles, i) for i in range(len(board))]
    for x in set(ns):
        idx = [i for i, y in enumerate(ns) if y == x]
        if len(idx) > 1:
            for k, i in enumerate(idx): ns[i] = x + 'ABC'[k]
    return ns

def tname(own, x):
    if x == own and x != '灰': return '対抗'
    if x == own: return 'もう1人の灰'
    return x

def tname_p(board, i, j, ns):
    return ns[j]

def plan_text(board, vt, vs, only=None):
    out = []
    for (l, r), d in zip(vt, vs):
        if only is not None and (l, r) not in only: continue
        who = {('猫', 'C'): '真猫', ('霊', 'M'): '真霊', ('狩', 'H'): '真狩', ('ギ', 'H'): 'ギの狩', ('ギ', 'C'): 'ギの猫',
               ('灰', 'V'): '村', ('灰', 'H'): '灰の狩', ('灰', 'C'): '灰の猫'}[(l, r)]
        items = [(x, p) for x, p in d.items() if p > 0]
        if len(items) == 1: out.append(f'{who}が{tname(l, items[0][0])}に投票')
        else:
            (a, pa), (b, pb) = sorted(items, key=lambda t: -t[1])
            if pa == pb: out.append(f'{who}が{tname(l, a)}と{tname(l, b)}に1/2ずつで投票')
            else: out.append(f'{who}が{tname(l, a)}に{fs(pa)}・{tname(l, b)}に{fs(pb)}で投票')
    return '、'.join(out) if out else '村の票は決まっている'

def case_title(board, roles, sit, single):
    if single: return sit
    parts = []
    for l in ('霊', '猫', 'ギ', '狩', '灰'):
        rs = [r for b, r in zip(board, roles) if b == l]
        if 'X' in rs and l != '灰': parts.append(f'{l}に狂')
        if 'W' in rs and l != '灰': parts.append(f'{l}に狼')
    if not parts:
        rs = [r for b, r in zip(board, roles) if b == '灰']
        x = ('狼' if 'W' in rs else '') + ('と狂' if 'W' in rs and 'X' in rs else ('狂' if 'X' in rs else ''))
        if x: parts.append('灰に' + x)
    return sit + 'で' + '・'.join(parts) if parts else sit

def derivation(board, roles, votes):
    """村勝ちになる票の入り方を、確率の掛け算で書く"""
    n = len(board); ns = names(board, roles)
    fixed = []; terms = []
    for i, v in enumerate(votes):
        if len(v) == 1 and roles[i] in 'WX':
            j = next(iter(v)); fixed.append(f'{ns[i]}→{ns[j]}')
    total = F(0)
    for combo in itertools.product(*[sorted(v.items()) for v in votes]):
        p = F(1); cnt = [0] * n; fac = []
        for i, (t, q) in enumerate(combo):
            p *= q; cnt[t] += 1
            if q != 1: fac.append(f'{ns[i]}が{ns[t]}に入れる({fs(q)})')
        if p == 0: continue
        m = max(cnt); top = [k for k in range(n) if cnt[k] == m]
        wins = []; wv = F(0)
        for k in sorted(top, key=lambda k: roles[k] != 'W'):
            if roles[k] == 'W': wins.append(f'1/{len(top)}' if len(top) > 1 else ''); wv += F(1, len(top))
            elif roles[k] == 'C':
                dr = F(sum(1 for j in range(n) if j != k and roles[j] == 'W'), n - 1)
                if dr: wins.append((f'1/{len(top)}×' if len(top) > 1 else '') + f'{fs(dr)}'); wv += dr / len(top)
        if wv == 0: continue
        total += p * wv
        if len(top) > 1: out = f'ランダム({"+".join(wins)})'
        elif roles[top[0]] == 'C': out = f'猫飛び({wins[0]})'
        else: out = ''
        f = '×'.join(fac + ([out] if out else []))
        terms.append((f or '確実', p * wv))
    if not terms: return fixed, '村勝ちはない（0）', total
    if len(terms) == 1:
        t, v = terms[0]
        return fixed, (f'村勝ちは{t}={fs(v)}' if t != '確実' else '必ず狼が吊られる（1）'), total
    return fixed, '村勝ちは' + 'と、'.join(f'{t}={fs(v)}' for t, v in terms) + f'の合計={fs(total)}', total

def board_text(board):
    sits = defaultdict(list)
    for w, roles in V3.assignments(board): sits[V3.situation(board, roles)].append((w, roles))
    if not sits: return None
    secs = []; summ = []
    for st in sorted(sits, key=lambda s: ('1狂' not in s, s)):
        cases = sits[st]
        vt, at, best, allv, value = V3.solve_sit(board, cases)
        bv, vs, ads = best
        # 比べる進め方：最善と、値の違う次の進め方
        plans = [(bv, vs, ads)]
        natural = lambda vsx: all(p in (0, F(1, 2), 1) for d in vsx for p in d.values())   # 比べるのは「全部入れる／1/2ずつ」の進め方
        for v, vs2, ads2 in sorted(allv, key=lambda x: -x[0]):
            if not natural(vs2): continue
            if plan_text(board, vt, vs2) != plan_text(board, vt, vs) and all(plan_text(board, vt, vs2) != plan_text(board, vt, p[1]) for p in plans):
                plans.append((v, vs2, ads2))
            if len(plans) >= 2: break
        # 内訳ごと（同じ見出しはまとめる：同じ形の内訳は値も同じ）
        groups = {}
        for w, roles in cases:
            t = case_title(board, roles, st, False)
            groups.setdefault(t, (w, roles))
        single = len(groups) == 1
        for t, (w, roles) in groups.items():
            title = st if single else t
            lines = []; ders = []
            vals = []
            for v, vsx, adsx in plans:
                Vd = dict(zip(vt, vsx)); A = dict(zip(at, adsx))
                votes = [V3.vote_dist(board, i, Vd[(board[i], roles[i])] if roles[i] in V3.VILL else A[(board[i], roles[i])]) for i in range(len(board))]
                fixed, der, tot = derivation(board, roles, votes)
                pt = plan_text(board, vt, vsx, {(board[i], roles[i]) for i in range(len(board))})
                if any(pt == x[0] for x in ders): continue   # この内訳では同じ進め方になる
                vals.append(f'{pt}なら{"村勝率" if not vals else ""}{fs(tot)}')
                ders.append((pt, fixed, der))
            lines.append('、'.join(vals))
            for pt, fixed, der in ders:
                lines.append(f'{pt}なら' + (f'、{"・".join(fixed)}の投票は固定なので、' if fixed else '、') + der)
            if not any(x['title'] == title and x['lines'] == lines for x in secs): secs.append(dict(title=title, lines=lines))
        summ.append(f'{st} → {fs(bv)}（{plan_text(board, vt, vs)}）')
    return dict(board=board, secs=secs, summ=summ)

if __name__ == '__main__':
    import sys, json
    b = sys.argv[1].split(',')
    r = board_text(b)
    for s in r['secs']:
        print('■', s['title'])
        for l in s['lines']: print('  ', l)
    print('まとめ'); [print('  ', x) for x in r['summ']]
