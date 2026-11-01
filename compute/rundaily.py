# 日ごとに解く（辞書方式）で、人数ごとの全盤面を解く。辞書は data/dict.json にためて次回も使う
import sys, json, time, os
from fractions import Fraction as F
import daily as D
from run45 import boards

PATH = os.environ.get('DICT_PATH') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'dict.json')   # 長い計算中は DICT_PATH（git管理外）に保存し、終わってから dict.json へ

def load():
    if os.path.exists(PATH):
        for k, v, info in json.load(open(PATH)):
            key = (tuple(k[0]), tuple((tuple(a), tuple(b), c) for a, b, c in k[1]))
            D.DICT[key] = F(v)
            if info: D.INFO[key] = info

def save():
    out = [[[list(k[0]), [[list(a), list(b), c] for a, b, c in k[1]]], str(v), D.INFO.get(k)] for k, v in D.DICT.items()]
    json.dump(out, open(PATH + '.tmp', 'w'), ensure_ascii=False); os.replace(PATH + '.tmp', PATH)

def board_list(n):
    if n == 3:
        import vote3 as V3
        return list(V3.boards())
    return boards(n, white=(n <= 4))

if __name__ == '__main__':
    load()
    for n in map(int, sys.argv[1:]):
        res = {}
        sel = os.environ.get('PART')   # 並行して解くとき：'k/m/s' なら s 番目以降の盤面のうち、番号を m で割った余りが k のものだけ
        bl = [b for b in board_list(n) if D.GM.worlds(b)]
        if sel and n >= 5:
            k, m, s0 = map(int, sel.split('/'))
            bl = [b for i, b in enumerate(bl) if i >= s0 and (i - s0) % m == k]
        for b in bl:
            res[','.join(b)] = {}
            for sit, k in D.board_keys(b).items():   # 生存状況ごと（全員が知っている）
                t = time.time(); v = D.value(k)
                res[','.join(b)][sit] = str(v)
                print(n, ','.join(b), sit, v, f'{float(v) * 100:.1f}%', round(time.time() - t, 1), 's', len(D.DICT), 'states', flush=True)
            save()
        if not sel: json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', f'daily{n}.json'), 'w'), ensure_ascii=False)
