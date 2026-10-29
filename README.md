# werewolf-endgame-12a-3

12A猫（占い・霊能・狩人・猫又・狂人・狼3・村人4）の盤面別勝率です。盤面（生きている人の見た目）ごとに、内訳（CO者の真偽・人外の残り・狩人や猫又の位置）ごとの村勝率と、村から見た最善の吊り先を厳密に（分数で）求めます。

- 公開ページ：https://leonmfvo.github.io/werewolf-endgame-12a-3/
- `index.html` / `app.js` / `style.css`：表示ページ（1枚）。`data/d<人数>.json` を読み、`#3-12` のような URL で盤面を開く
- `data/d3.json`：3人日の全盤面（117盤面・2,256内訳）
- `compute/three.py`：3人日の計算（`python3 compute/three.py data/d3.json`）

今後：4人日以上（11人日まで）を同じ形で足していく。
