# 4・5人日の結果（data/plans<n>.json）から、ページ用の説明（data/d<n>.json）を作る：
#   盤面の最善の進め方と比較の進め方、生存状況ごとの村勝率、内訳ごとに「どう決着するか」の道すじと確率
import sys, json
from fractions import Fraction as F
from collections import defaultdict, OrderedDict
from game import Game, solve_adv, evaluate, situation
import wikitext as WT

RN = {'M': '霊能者', 'H': '狩人', 'C': '猫又', 'X': '狂人', 'W': '狼', 'V': '村人'}
def fs(x): return WT.fs(x)

def who(board, roles, i):
    return WT.pname(board, roles, i)

def plan_text(plan):
    d = plan['des']; out = []
    if plan.get('mode') == 'spread':
        out.append(f'昼：各自が{d[0]}の中からランダムに投票')
    else:
        out.append(f'昼：{d[0]}から1人を指定して全員で投票（指定された人は{d[1] if len(d) > 1 else d[0]}に投票）')
    if plan.get('counter'): out.append('本物のCO者は対抗に投票')
    g = plan['guard']
    out.append(f'夜：狩人は{g[0]}を護衛')
    out.append('GJの翌朝に狩人がCO' if plan.get('co') else 'GJが出ても狩人は潜伏')
    return '、'.join(out)

def paths(board, roles, node, pol):
    """決着か翌日までの道すじ：[(説明, 確率, その先の村勝率)]"""
    out = defaultdict(lambda: [F(0), F(0)])
    def walk(nd, p, labs):
        if p == 0: return
        if nd.tag and nd.tag[0] == '翌日':
            alive, lab = nd.tag[1], nd.tag[2]
            v = evaluate(nd, pol)
            name = f"翌日 {','.join(sorted((lab[i] for i in alive), key=['霊', '猫', 'ギ', '狩', '白', '灰'].index))}"
            k = ' → '.join(labs + [name])
            out[k][0] += p; out[k][1] += p * v
            return
        if nd.tag:
            t = nd.tag
            if t[0] == '吊': labs = labs + [f'{who(board, roles, t[1])}を吊る']
            elif t[0] == '道連れ': labs = labs + [f'道連れで{who(board, roles, t[1])}']
            elif t[0] == '噛み': labs = labs + [f'{who(board, roles, t[1])}を噛む']
            elif t[0] == 'GJ': labs = labs + ['GJ']
            elif t[0] == '死亡': pass
            elif t[0] == '猫噛み': labs = labs + ['猫噛みで狼が死ぬ']
            elif t[0] == '狩人CO': labs = labs + ['狩人CO']
        if nd.kind == 'L':
            k = ' → '.join(labs) + (' → 村勝ち' if nd.v == 1 else ' → 狼勝ち' if nd.v == 0 else '')
            out[k][0] += p; out[k][1] += p * nd.v; return
        if nd.kind == 'C':
            for q, c in nd.ch: walk(c, p * q, labs)
        else: walk(nd.ch[pol[(nd.agent, nd.info)]], p, labs)
    walk(node, F(1), [])
    return out

def board_text(board, ranked):
    best_v, best_plan = ranked[0]
    alt = None
    for v, p in ranked[1:]:
        if (p['des'][0], p['mode']) != (best_plan['des'][0], best_plan['mode']): alt = (v, p); break
    if alt is None:
        for v, p in ranked[1:]:
            if p['guard'][0] != best_plan['guard'][0] or p['co'] != best_plan['co']: alt = (v, p); break
    plans = [('g', best_plan)] + ([('a', alt[1])] if alt else [])
    runs = []
    for tag, plan in plans:
        g = Game(board, plan); root, ws = g.root()
        v, pol = solve_adv(root)
        runs.append((tag, plan, root, ws, pol, v))
    _, _, root0, ws0, _, _ = runs[0]
    tot = sum(w for w, _ in ws0)
    sits = OrderedDict()
    for k, (w, roles) in enumerate(ws0):
        sits.setdefault(situation(board, roles), []).append(k)
    secs = []; summ = []
    for st in sorted(sits, key=lambda s: (s[0], '1k' not in s, s)):
        ks = sits[st]
        groups = OrderedDict()
        for k in ks:
            roles = ws0[k][1]
            groups.setdefault(WT.case_title(board, roles, st, False), []).append(k)
        single = len(groups) == 1
        vals = []
        for tag, plan, root, ws, pol, v in runs:
            num = sum(root.ch[k][0] * evaluate(root.ch[k][1], pol) for k in ks); den = sum(root.ch[k][0] for k in ks)
            vals.append(fs(num / den))
        summ.append(dict(sit=st, share=fs(F(sum(ws0[k][0] for k in ks), tot)), v=vals[0], va=vals[1] if len(vals) > 1 else None))
        for t, lst in groups.items():
            items = []
            for tag, plan, root, ws, pol, v in runs:
                agg = defaultdict(lambda: [F(0), F(0)]); den = F(0)
                for k in lst:
                    p, ch = root.ch[k]; den += p
                    for lab, (q, qv) in paths(board, ws[k][1], ch, pol).items():
                        agg[lab][0] += p * q; agg[lab][1] += p * qv
                lines = sorted(([lab, fs(q / den), fs(qv / q) if q else '0'] for lab, (q, qv) in agg.items()), key=lambda x: -F(x[1]))
                total = sum(F(x[1]) * F(x[2]) for x in lines)
                items.append(dict(tag=tag, best=(tag == 'g'), plan=plan_text(plan), paths=lines, v=fs(total)))
            secs.append(dict(title=st if single else t, share=fs(F(sum(ws0[k][0] for k in lst), tot)), items=items))
    return dict(board=board, v=fs(runs[0][5]), plan=plan_text(best_plan),
                va=fs(runs[1][5]) if len(runs) > 1 else None, plana=plan_text(runs[1][1]) if len(runs) > 1 else None,
                secs=secs, summ=summ)

if __name__ == '__main__':
    n = int(sys.argv[1]); src = sys.argv[2]; dst = sys.argv[3]
    R = json.load(open(src))
    out = []
    for key, ranked in R.items():
        if not ranked: continue
        ranked = [(F(v), p) for v, p in ranked]
        out.append(board_text(key.split(','), ranked))
        print(key, out[-1]['v'], flush=True)
    json.dump(out, open(dst, 'w'), ensure_ascii=False, separators=(',', ':'))
