# 村の進め方の候補：指定の順（盤面にある区分の並べ方）× 本物のCO者は対抗に入れるか × 護衛の順 × GJ後に狩人がCOするか
import itertools
ORDER = ['霊', '猫', 'ギ', '狩', '灰']
def candidates(board, n_alive=None):
    present = sorted(set(board) - {'白'}, key=ORDER.index)
    out = []
    # 指定の順：1番目と2番目の区分を選び、残りは決まった順
    des_orders = []
    for a in present:
        for b in [x for x in present if x != a] or [None]:
            des_orders.append(tuple([a] + ([b] if b else []) + [x for x in present if x not in (a, b)]))
    # 護衛の順：1番目の区分を選び、残りは決まった順
    guard_orders = [tuple([a] + [x for x in present if x != a]) for a in present] if len(board) >= 4 else [tuple(present)]
    for des in des_orders:
        for counter in (True, False):
            if not counter and not any(board.count(l) >= 2 for l in ('霊', '猫', '狩', 'ギ')): 
                if counter is False: continue
            for guard in guard_orders:
                for co in ((True, False) if len(board) >= 4 else (True,)):
                    for mode in ('designate', 'spread'):
                        out.append(dict(des=des, counter=counter, guard=guard, co=co, mode=mode))
    # 対抗に入れるかが意味を持たない盤面では重複を除く
    seen = set(); res = []
    for p in out:
        k = (p['des'], p['counter'] if any(board.count(l) >= 2 for l in ('霊', '猫', '狩', 'ギ')) else None, p['guard'], p['co'], p['mode'])
        if k in seen: continue
        seen.add(k); res.append(p)
    return res
