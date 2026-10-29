# 12A猫（占い・霊能・狩人・猫又・狂人・狼3・村人4）の3人日：見た目の盤面すべてについて、内訳ごとの村勝率と最善の吊り先を厳密に求める。
#
# 3人日は狼1人（狼2人なら決着済み）。この日の吊りで狼を吊れば村の勝ち、人間を吊れば残り2人で狼の勝ち。
# 本物の猫又を吊ると、残りの2人からランダムに1人を道連れにする（狼なら村の勝ち）。
# 村は盤面の見た目しか分からないので、吊る区分（灰・白・猫…）を1つ決め、区分の中からランダムに吊る。
# 最善の吊り先＝ありうる内訳の平均（役の数からの重み）が一番高い区分。PP は5人日以上なので3人日には起きない。
import json, itertools, sys
from fractions import Fraction as F
from collections import defaultdict

ROLES = {'S': 1, 'M': 1, 'H': 1, 'C': 1, 'X': 1, 'W': 3, 'V': 4}
RN = {'S': '占い師', 'M': '霊能者', 'H': '狩人', 'C': '猫又', 'X': '狂人', 'W': '狼', 'V': '村人'}
HUMAN = 'SMHCXV'
LABELS = ['占', '霊', '狩', '猫', '確白', '白', '黒', '灰']
CAN = {'占': 'SXW', '霊': 'MXW', '狩': 'HXW', '猫': 'CXW', '確白': 'VHCX', '灰': 'VHCXW'}

def boards(n=3):
    out = []
    for combo in itertools.combinations_with_replacement(LABELS, n):
        c = list(combo)
        if (('白' in c) or ('黒' in c)) and c.count('占') > 1: continue   # 結果は1人の占い師のもの（2人いるときは載せない）
        if max(c.count(x) for x in ('占', '霊', '狩', '猫')) > 3: continue
        out.append(c)
    return out

def weight(roles):
    """役の数からの重み（生き残っている役の組み合わせが、役の札から選ばれる数）"""
    cnt = defaultdict(int); w = 1
    for r in roles:
        w *= ROLES[r] - cnt[r]; cnt[r] += 1
    return w

def cases(board):
    """[(重み, 役の並び, 占いの結果の出どころ)]。結果の出どころ：生きている占いCO者 / 死んだ本物 / 死んだ偽（狂人・狼）"""
    res = '白' in board or '黒' in board
    srcs = [None]
    if res: srcs = ['alive'] if '占' in board else ['deadS', 'deadX', 'deadW']
    out = []
    for src in srcs:
        opts = []
        for i, l in enumerate(board):
            if l in CAN: opts.append(CAN[l])
            else: opts.append('VHCXW')   # 白・黒：あとで結果の出どころと照らす
        for roles in itertools.product(*opts):
            if roles.count('W') != 1: continue
            if any(roles.count(r) > ROLES[r] for r in ROLES): continue
            # 占いの結果の真偽
            if res:
                if src == 'alive':
                    sr = roles[board.index('占')]
                    true_seer = sr == 'S'
                else:
                    true_seer = src == 'deadS'
                    if src == 'deadS' and 'S' in roles: continue
                    if src == 'deadX' and 'X' in roles: continue
                if true_seer:
                    if any(l == '白' and r == 'W' for l, r in zip(board, roles)): continue
                    if any(l == '黒' and r != 'W' for l, r in zip(board, roles)): continue
            w = weight(roles) * (3 if src == 'deadW' else 1)
            out.append((w, roles, src))
    return out

def hang_value(board, roles, cls):
    """区分 cls の中からランダムに吊ったときの村勝率"""
    idx = [i for i, l in enumerate(board) if l == cls]
    v = F(0)
    for i in idx:
        r = roles[i]
        if r == 'W': x = F(1)
        elif r == 'C':   # 本物の猫又：残りからランダムに道連れ
            others = [roles[j] for j in range(len(roles)) if j != i]
            x = F(others.count('W'), len(others))
        else: x = F(0)
        v += x / len(idx)
    return v

def describe(board, roles, src):
    """内訳の見出し：生存状況（1狼1狂生存・灰に狩 など）と、CO者の真偽・狼の位置"""
    mad = 'X' in roles
    st = '1狼' + ('1狂' if mad else '') + '生存'
    hpos = [l for l, r in zip(board, roles) if r == 'H']
    cpos = [l for l, r in zip(board, roles) if r == 'C']
    st += ('・' + hpos[0] + 'に狩') if hpos and hpos[0] != '狩' else ('・狩CO（本物）' if hpos else '')
    st += ('・' + cpos[0] + 'に猫又') if cpos and cpos[0] != '猫' else ('・猫CO（本物）' if cpos else '')
    st = st.replace('灰に狩', '灰に狩').replace('確白に狩', '確白が狩人').replace('白に狩', '白が狩人').replace('黒に狩', '黒が狩人')
    st = st.replace('確白に猫又', '確白が猫又').replace('白に猫又', '白が猫又').replace('黒に猫又', '黒が猫又')
    det = []
    for l in ('占', '霊', '狩', '猫'):
        rs = sorted(r for b, r in zip(board, roles) if b == l)
        if rs: det.append(l + ''.join({'S': '真', 'M': '真', 'H': '真', 'C': '真', 'X': '狂', 'W': '狼'}[r] for r in rs))
    if src and src != 'alive': det.append({'deadS': '結果は死んだ本物の占い師のもの', 'deadX': '結果は死んだ偽の占い（狂人）のもの', 'deadW': '結果は死んだ偽の占い（狼）のもの'}[src])
    wl = [l for l, r in zip(board, roles) if r == 'W'][0]
    if wl in ('白', '黒', '灰', '確白'): det.append(f'{wl}が狼' if board.count(wl) == 1 else f'{wl}に狼')
    return st, '、'.join(det)

def solve(board):
    cs = cases(board)
    if not cs: return None
    classes = [l for l in LABELS if l in board]
    # 同じ見え方の人の入れ替えをまとめる（見出しが同じ内訳）
    groups = defaultdict(lambda: dict(w=0, vals=defaultdict(F)))
    tot = sum(w for w, _, _ in cs)
    avg = {c: F(0) for c in classes}
    for w, roles, src in cs:
        key = describe(board, roles, src)
        g = groups[key]; g['w'] += w
        for c in classes:
            v = hang_value(board, roles, c)
            g['vals'][c] += w * v; avg[c] += F(w, tot) * v
    best = max(classes, key=lambda c: (avg[c], -classes.index(c)))
    out = []
    for (st, det), g in groups.items():
        out.append(dict(sit=st, det=det, share=str(F(g['w'], tot)), vals={c: str(g['vals'][c] / g['w']) for c in classes}))
    out.sort(key=lambda x: (x['sit'], -F(x['share'])))
    return dict(board=board, avg={c: str(avg[c]) for c in classes}, best=best, cases=out)

if __name__ == '__main__':
    res = [r for r in (solve(b) for b in boards()) if r]
    print(len(res), 'boards', sum(len(r['cases']) for r in res), 'cases')
    json.dump(res, open(sys.argv[1], 'w'), ensure_ascii=False, separators=(',', ':'))
    for r in res[:5] + [x for x in res if x['board'] == ['猫', '灰', '灰']]:
        print(','.join(r['board']), {c: float(F(v)) for c, v in r['avg'].items()}, r['best'])
        for c in r['cases'][:4]: print('   ', c['sit'], '|', c['det'], c['share'], c['vals'])
