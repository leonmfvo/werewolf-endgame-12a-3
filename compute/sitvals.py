# 決めた進め方と人外の応答のもとで、生存状況ごとの村勝率
from fractions import Fraction as F
from collections import defaultdict
from game import Game, solve_adv, evaluate, situation

def per_situation(board, plan):
    g = Game(board, plan); root, ws = g.root()
    v, pol = solve_adv(root)
    tot = sum(w for w, _ in ws)
    acc = defaultdict(lambda: [F(0), F(0)])
    for (p, ch), (w, roles) in zip(root.ch, ws):
        s = situation(board, roles)
        acc[s][0] += p; acc[s][1] += p * evaluate(ch, pol)
    return v, {s: (a[0], a[1] / a[0]) for s, a in acc.items()}

if __name__ == '__main__':
    import sys, json
    r = json.load(open(sys.argv[1]))
    key = sys.argv[2]
    for vs, plan in r[key][:4]:
        v, d = per_situation(key.split(','), plan)
        print(vs, plan)
        for s, (sh, x) in sorted(d.items()): print('   ', s, f'{float(sh)*100:.1f}%', x, f'{float(x)*100:.1f}%')
