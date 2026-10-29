# 12A猫（占い・霊能・狩人・猫又・狂人・狼3・村人4）の3人日：霊・狩・ギドラ・猫・灰の見た目の盤面すべてについて、内訳ごとの村勝率と最善の吊り先を厳密に求める。
#
# 3人日は狼1人（狼2人なら決着済み）。この日の吊りで狼を吊れば村の勝ち、人間を吊れば残り2人で狼の勝ち。
# 本物の猫又を吊ると、残りの2人からランダムに1人を道連れにする（狼なら村の勝ち）。
# 村は盤面の見た目しか分からないので、吊る区分（灰・白・猫…）を1つ決め、区分の中からランダムに吊る。
# 最善の吊り先＝ありうる内訳の平均（役の数からの重み）が一番高い区分。PP は5人日以上なので3人日には起きない。
import json, itertools, sys
from fractions import Fraction as F
from collections import defaultdict

ROLES = {'M': 1, 'H': 1, 'C': 1, 'X': 1, 'W': 3, 'V': 4}   # 占い師は扱わない（占いの白黒は無視）
RN = {'M': '霊能者', 'H': '狩人', 'C': '猫又', 'X': '狂人', 'W': '狼', 'V': '村人'}
LABELS = ['霊', '狩', 'ギドラ', '猫', '灰']
# CO者の正体の候補。猫は特別：猫又は役欠けがないので、猫COが1人なら本物（道連れが起きていない前提）。2人以上なら1人が本物、残りは偽（狂人・狼）
CAN = {'霊': 'MXW', '狩': 'HXW', 'ギドラ': 'HCXW', '灰': 'VHCXW'}
SHORT = {'M': '真', 'H': '狩', 'C': '猫', 'X': '狂', 'W': '狼'}

def boards(n=3):
    return [list(c) for c in itertools.combinations_with_replacement(LABELS, n)]

def weight(roles):
    """役の数からの重み（生き残っている役の組み合わせが、役の札から選ばれる数）"""
    cnt = defaultdict(int); w = 1
    for r in roles:
        w *= ROLES[r] - cnt[r]; cnt[r] += 1
    return w

def cases(board):
    """[(重み, 役の並び, None)]"""
    opts = [('CXW' if l == '猫' else CAN[l]) for l in board]
    out = []
    for roles in itertools.product(*opts):
        if roles.count('W') != 1: continue
        if any(roles.count(r) > ROLES[r] for r in ROLES): continue
        cats = [r for l, r in zip(board, roles) if l == '猫']
        if cats and cats.count('C') != 1: continue          # 猫CO者の中に本物の猫又が必ず1人
        out.append((weight(roles), roles, None))
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
    """生存状況（1狼1狂生存（狩生存） など）と、CO者の正体・狼の位置"""
    st = '1狼' + ('1狂' if 'X' in roles else '') + '生存'
    hid = []
    if any(l == '灰' and r == 'H' for l, r in zip(board, roles)): hid.append('狩生存')
    if any(l == '灰' and r == 'C' for l, r in zip(board, roles)): hid.append('猫生存')
    if hid: st += '（' + '・'.join(hid) + '）'
    det = []
    for l in ('霊', '狩', 'ギドラ', '猫'):
        rs = [r for b, r in zip(board, roles) if b == l]
        if not rs: continue
        if l == '猫' and len(rs) == 1: continue          # 1人なら本物で決まり
        if l == 'ギドラ': det.append('ギドラ' + ''.join(SHORT[r] for r in sorted(rs, key='HCXW'.index)))
        elif l == '猫': det.append('猫' + ''.join({'C': '真', 'X': '狂', 'W': '狼'}[r] for r in sorted(rs, key='CXW'.index)))
        else: det.append(l + ''.join({'M': '真', 'H': '真', 'X': '狂', 'W': '狼'}[r] for r in sorted(rs, key='MHXW'.index)))
    if any(l == '灰' and r == 'W' for l, r in zip(board, roles)): det.append('灰に狼' if board.count('灰') > 1 else '灰が狼')
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
