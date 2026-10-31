# 日ごとに解く（辞書方式）で、人数ごとの全盤面を解く。辞書は data/dict.json にためて次回も使う
import sys, json, time, os
from fractions import Fraction as F
import daily as D
from run45 import boards

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'dict.json')

def load():
    if os.path.exists(PATH):
        for k, v, info in json.load(open(PATH)):
            key = (tuple(k[0]), tuple((tuple(a), tuple(b), c) for a, b, c in k[1]))
            D.DICT[key] = F(v)
            if info: D.INFO[key] = info

def save():
    out = [[[list(k[0]), [[list(a), list(b), c] for a, b, c in k[1]]], str(v), D.INFO.get(k)] for k, v in D.DICT.items()]
    json.dump(out, open(PATH + '.tmp', 'w'), ensure_ascii=False); os.replace(PATH + '.tmp', PATH)

if __name__ == '__main__':
    load()
    for n in map(int, sys.argv[1:]):
        res = {}
        for b in boards(n, white=(n <= 4)):
            if not D.GM.worlds(b): continue
            t = time.time(); k = D.board_key(b); v = D.value(k)
            res[','.join(b)] = str(v)
            print(n, ','.join(b), v, f'{float(v) * 100:.1f}%', round(time.time() - t, 1), 's', len(D.DICT), 'states', flush=True)
            save()
        json.dump(res, open(os.path.join(os.path.dirname(PATH), f'daily{n}.json'), 'w'), ensure_ascii=False)
