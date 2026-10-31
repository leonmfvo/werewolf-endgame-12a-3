# 4・5人日：盤面ごとに村の進め方の候補をすべて試し、人外の最善応答（各自の視点）に対して一番勝てるものを選ぶ
import sys, json
import refs, time, itertools
from multiprocessing import Pool
from fractions import Fraction as F
import os
import game as GM
from game import Game, solve_adv, agents_infosets, evaluate, LABELS
from plans import candidates

def boards(n, white=None):
    if white is None: white = n <= 4
    out = []
    for c in itertools.combinations_with_replacement(LABELS, n):
        c = list(c)
        if 'ギ' in c and ('猫' in c or '狩' in c): continue
        if c.count('ギ') == 1: continue
        if c.count('白') > (2 if white else 0): continue   # 白（狩人COで出た護衛先）は、少ない人数の参照用にだけ使う
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
        GM.MODE.update(exact=False, tags=False)   # 探索は小数の木で
        g = Game(board, plan, ref=REF); root, ws = g.root()
        if not ws: return board, None, 0, 0
        v, pol = solve_adv(root, starts=2); v = F(v).limit_denominator(10**9)
        del root
        done1[key(plan)] = v; st['s1'].append([str(v), plan])
        if path: _save(path, st)
    res = sorted(((done1[key(p)], p) for p in cands), key=lambda x: -x[0])
    # 2段目：上位8つをやり直し15回で詰め直す
    done2 = {key(p): F(v) for v, p in st['s2']}
    top = []
    for v0, plan in res[:8]:
        if key(plan) not in done2:
            GM.MODE.update(exact=False, tags=False)
            g = Game(board, plan, ref=REF); root, ws = g.root()
            vf, pol = solve_adv(root, starts=15)
            del root
            v = g.exact_value(pol)   # 値は分数で厳密に（内訳ごとに作り直す）
            done2[key(plan)] = v; st['s2'].append([str(v), plan])
            if path: _save(path, st)
        top.append((done2[key(plan)], plan))
    top.sort(key=lambda x: -x[0])
    res = top + res[8:]
    return board, [(str(v), p) for v, p in res], time.time() - t, len(res)

REF = {}
def load_refs(n):
    for k in (3, 4):
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', f'ref{k}.json')
        if k < n and os.path.exists(p): REF[k] = refs.load(p)

if __name__ == '__main__':
    n = int(sys.argv[1]); out = sys.argv[2]
    if os.environ.get('USE_REF'): load_refs(n)   # 参照（近似）は使わないのが既定。厳密な値と差が出るため
    import os
    results = json.load(open(out)) if os.path.exists(out) else {}   # 途中から再開
    bs = [b for b in boards(n) if ','.join(b) not in results]
    print(len(results), 'done,', len(bs), 'to do', flush=True)
    partial = out + '.partial'
    os.makedirs(partial, exist_ok=True)
    npar = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    from game import worlds
    # 内訳が多い盤面は木が数GBになるので1つずつ（並列だとメモリ不足で止まる）。軽い盤面は並列で
    light = [b for b in bs if len(worlds(b)) <= 60]; heavy = [b for b in bs if len(worlds(b)) > 60]
    def runs():
        if light:
            with Pool(npar) as pool:
                yield from pool.imap_unordered(job, [(b, partial) for b in light])
        for b in heavy: yield job((b, partial))
    if True:
        for board, res, dt, k in runs():
            results[','.join(board)] = res or []   # 配役から起こらない盤面は空で記録
            if not res:
                json.dump(results, open(out + '.tmp', 'w'), ensure_ascii=False); os.replace(out + '.tmp', out)
                continue
            print(','.join(board), res[0][0], round(float(F(res[0][0])) * 100, 1), '%', k, 'plans', round(dt), 's', flush=True)
            json.dump(results, open(out + '.tmp', 'w'), ensure_ascii=False); os.replace(out + '.tmp', out)
