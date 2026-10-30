# 4・5人日：盤面ごとに村の進め方の候補をすべて試し、人外の最善応答（各自の視点）に対して一番勝てるものを選ぶ
import sys, json, time, itertools
from multiprocessing import Pool
from fractions import Fraction as F
from game import Game, solve_adv, agents_infosets, evaluate, LABELS
from plans import candidates

def boards(n):
    out = []
    for c in itertools.combinations_with_replacement(LABELS, n):
        c = list(c)
        if 'ギ' in c and ('猫' in c or '狩' in c): continue
        if c.count('ギ') == 1: continue
        out.append(c)
    return out

def job(board):
    t = time.time()
    # 1段目：やり直し2回で全候補をふるいにかける（人外の最善を見逃すと値は高めに出るので、上位を取りこぼしにくい）
    res = []
    for plan in candidates(board):
        g = Game(board, plan); root, ws = g.root()
        if not ws: return board, None, 0, 0
        v, pol = solve_adv(root, starts=2)
        res.append((v, plan))
    res.sort(key=lambda x: -x[0])
    # 2段目：上位8つをやり直し15回で詰め直す
    top = []
    for v0, plan in res[:8]:
        g = Game(board, plan); root, ws = g.root()
        v, pol = solve_adv(root, starts=15)
        top.append((min(v, v0), plan))
    top.sort(key=lambda x: -x[0])
    res = top + res[8:]
    return board, [(str(v), p) for v, p in res], time.time() - t, len(res)

if __name__ == '__main__':
    n = int(sys.argv[1]); out = sys.argv[2]
    import os
    results = json.load(open(out)) if os.path.exists(out) else {}   # 途中から再開
    bs = [b for b in boards(n) if ','.join(b) not in results]
    print(len(results), 'done,', len(bs), 'to do', flush=True)
    with Pool(int(sys.argv[3]) if len(sys.argv) > 3 else 4) as pool:
        for board, res, dt, k in pool.imap_unordered(job, bs):
            if res is None: continue
            results[','.join(board)] = res
            print(','.join(board), res[0][0], round(float(F(res[0][0])) * 100, 1), '%', k, 'plans', round(dt), 's', flush=True)
            json.dump(results, open(out + '.tmp', 'w'), ensure_ascii=False); os.replace(out + '.tmp', out)
