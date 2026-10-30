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

PARTIAL = None   # 盤面の途中経過を置くフォルダ（候補1つごとに保存。止まっても進んだ分は残る）

def _load(path):
    import os
    return json.load(open(path)) if os.path.exists(path) else dict(s1=[], s2=[])

def _save(path, d):
    import os
    json.dump(d, open(path + '.tmp', 'w'), ensure_ascii=False); os.replace(path + '.tmp', path)

def job(args):
    board, partial = args
    import os
    t = time.time()
    path = os.path.join(partial, ','.join(board) + '.json') if partial else None
    st = _load(path) if path else dict(s1=[], s2=[])
    key = lambda p: json.dumps(p, sort_keys=True, ensure_ascii=False)
    # 1段目：やり直し2回で全候補をふるいにかける（人外の最善を見逃すと値は高めに出るので、上位を取りこぼしにくい）
    done1 = {key(p): F(v) for v, p in st['s1']}
    cands = candidates(board)
    for plan in cands:
        if key(plan) in done1: continue
        g = Game(board, plan); root, ws = g.root()
        if not ws: return board, None, 0, 0
        v, pol = solve_adv(root, starts=2)
        done1[key(plan)] = v; st['s1'].append([str(v), plan])
        if path: _save(path, st)
    res = sorted(((done1[key(p)], p) for p in cands), key=lambda x: -x[0])
    # 2段目：上位8つをやり直し15回で詰め直す
    done2 = {key(p): F(v) for v, p in st['s2']}
    top = []
    for v0, plan in res[:8]:
        if key(plan) not in done2:
            g = Game(board, plan); root, ws = g.root()
            v, pol = solve_adv(root, starts=15)
            done2[key(plan)] = v; st['s2'].append([str(v), plan])
            if path: _save(path, st)
        top.append((min(done2[key(plan)], v0), plan))
    top.sort(key=lambda x: -x[0])
    res = top + res[8:]
    return board, [(str(v), p) for v, p in res], time.time() - t, len(res)

if __name__ == '__main__':
    n = int(sys.argv[1]); out = sys.argv[2]
    import os
    results = json.load(open(out)) if os.path.exists(out) else {}   # 途中から再開
    bs = [b for b in boards(n) if ','.join(b) not in results]
    print(len(results), 'done,', len(bs), 'to do', flush=True)
    partial = out + '.partial'
    os.makedirs(partial, exist_ok=True)
    with Pool(int(sys.argv[3]) if len(sys.argv) > 3 else 4) as pool:
        for board, res, dt, k in pool.imap_unordered(job, [(b, partial) for b in bs]):
            results[','.join(board)] = res or []   # 配役から起こらない盤面は空で記録
            if not res:
                json.dump(results, open(out + '.tmp', 'w'), ensure_ascii=False); os.replace(out + '.tmp', out)
                continue
            print(','.join(board), res[0][0], round(float(F(res[0][0])) * 100, 1), '%', k, 'plans', round(dt), 's', flush=True)
            json.dump(results, open(out + '.tmp', 'w'), ensure_ascii=False); os.replace(out + '.tmp', out)
