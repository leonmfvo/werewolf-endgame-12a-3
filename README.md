# werewolf-endgame-12a-3

12A猫（占い・霊能・狩人・猫又・狂人・狼3・村人4）の盤面別勝率です。盤面（生きている人の見た目）ごとに、内訳（CO者の真偽・人外の残り・狩人や猫又の位置）ごとの村勝率と、村から見た最善の吊り先を厳密に（分数で）求めます。

- 公開ページ：https://leonmfvo.github.io/werewolf-endgame-12a-3/
- `index.html` / `app.js` / `style.css`：表示ページ（1枚）。`data/d<人数>.json` を読み、`#3-12` のような URL で盤面を開く。数式は同梱の KaTeX（`vendor/katex/`、MIT ライセンス）で表示
- `data/d3.json`：3人日の全盤面（霊・猫・ギ・狩・灰の組み合わせ。投票まで含めて各人の視点で解く）
- `compute/vote3.py`：3人日の計算（`python3 compute/vote3.py data/d3.json`）
- `compute/wikitext.py`：計算結果を wiki（ゲヘナのwiki）の書き方の文章にする

- `compute/game.py`：4・5人日の木（投票・道連れ・噛み・護衛・GJ・狩人CO）と、人外の最善応答の探索
- `compute/plans.py`：村の進め方の候補
- `compute/run45.py`：4・5人日の全盤面で候補を試す（`python3 compute/run45.py 4 data/plans4.json 4`）
- `compute/analyze45.py`：ページ用の説明（`python3 compute/analyze45.py 4 data/plans4.json data/d4.json`）

今後：6人日以上（11人日まで）を同じ形で足していく。
