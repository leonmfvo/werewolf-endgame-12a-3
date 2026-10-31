# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A static GitHub Pages site (https://leonmfvo.github.io/werewolf-endgame-12a-3/) giving village win rates for **12A猫** werewolf endgame boards (roles: 占い・霊能・狩人・猫又・狂人・狼3・村人4). The Python in `compute/` solves the games and writes JSON into `data/`. The single-page viewer (`index.html` + `app.js` + `style.css`) renders that JSON. There is no build step, package manager or test suite. Dependencies are plain Python 3 (`fractions`, `itertools`, `multiprocessing`) and the bundled KaTeX in `vendor/katex/`.

The user writes in Japanese. All page text, code comments and commit messages are Japanese. Keep that.

## Commands

Run these from the repo root. Python modules import each other by bare name, so either run scripts directly or `cd compute` first.

```sh
python3 compute/vote3.py data/d3.json                       # 3人日: exact solve + page text (~1 min)
python3 compute/run45.py 4 data/plans4.json 4               # 4人日: try all village plan candidates (4 procs)
python3 compute/analyze45.py 4 data/plans4.json data/d4.json  # 4人日: page JSON from the ranked plans
python3 compute/run45.py 5 data/plans5.json 1               # 5人日: resumable; checkpoints each candidate in data/plans5.json.partial/. Use 1 process: candidates with co=False (hunter stays hidden after GJ) build ~7GB trees, and parallel workers get OOM-killed and silently hang the Pool
python3 -m http.server 8766                                 # preview locally, open /#3-1 etc.
```

`run45.py` resumes from whatever is already in its output file. Boards that the role counts make impossible are stored as `[]`, and `analyze45.py` skips them. The 5人日 runs exceed the 2-hour background-task limit, so restart them and they continue where they stopped.

To check a page in a headless browser, use Playwright, which is preinstalled (`require('playwright')`, `chromium.launch()`). Pages must not scroll horizontally at 390px width.

## Board / notation model (shared by all solvers)

- **Board**: the list of alive people's visible labels, ordered `霊 → 猫 → ギ → 狩 → 灰` (霊能CO・猫又CO・ギドラCO・狩人CO・グレー). Seer results (白/黒) are deliberately not modelled yet.
- **Worlds**: every role assignment consistent with the board (`vote3.assignments`, `game.worlds`). Each is weighted by the role-card count (`weight`: 村人4・狼3・others 1).
- **Rules the user fixed**, all enforced in the world generators:
  - A single 猫/霊/狩 CO is the real one. With 2+ claims, exactly one 猫 claimant is real (猫又 has no 役欠け); 霊 and 狩 claims can all be fake.
  - ギドラ only appears with ≥2 claimants and never alongside 猫 or 狩 COs. When a ギ exists, no real 狩人/猫又 hides in 灰.
  - If a 狩 CO exists, the real 狩人 is not hiding in 灰.
  - PP: with ≥5 alive and the 狂人 alive, the 人外 majority wins; a tie is 1/2.
- **Situation label** (`situation`): `1w1k生存（狩生存・猫生存）`. Here w = wolves, k = 狂人 alive, and the parentheses mean a 狩人/猫又 is hidden in 灰. The user chose the wk notation; don't switch to 狼/狂.

## Solvers: the important design decisions

These came out of correcting mistakes with the user. Don't regress them.

1. **Nobody knows the situation.** The village, the wolves and the 狂人 decide only from the board, their own role and public events. Pages are split by situation for readability only. An earlier version optimised a separate plan per situation, which leaked hidden information; this was a real bug.
2. **Wolves and the 狂人 don't know each other.** Adversaries pick by *appearance group* (same label, and whether they are the designated person), uniformly at random within the group. They never pick a specific seat, because seat conventions let them coordinate unrealistically. This matches the reference wiki (猫猫灰: 狼 votes either cat 1/2).
3. **3人日 (`vote3.py`, `vote3g.py`) is exact.**
   - `vote3g.solve_board` searches one board-wide village plan: a vote distribution per (label, own role), grid of 1/4, 1/3… refined to 1/12.
   - Against each plan it takes the minimum over all joint adversary choices.
   - `vote3.solve_sit` is the older per-situation solver. It is now only used inside `wikitext` for the comparison text, and its values are not a valid "if known" bound.
4. **4・5人日 (`game.py`) use candidate plans.**
   - `plans.py` defines the candidates: designation order / designate-vs-spread voting / true claimants vote their 対抗 / guard order / hunter CO after GJ.
   - `game.Game` builds an explicit tree: public votes, ties random, 猫又 drag on hang, wolf death on 猫噛み, consecutive guard allowed, GJ, hunter CO.
   - Adversary best response is person-by-person search with random restarts (`solve_adv`, 15 starts). This is heuristic: a single start was shown to get stuck. `solve_adv_exact` (full enumeration) exists for small trees to validate it.
   - The search runs on floats (`to_float`, `evaluate_f`); only the final value of the chosen policy is recomputed exactly with `Fraction` (`evaluate`). This was about 50× faster and reproduced every 4人日 value.
   - `run45` screens all candidates with 2 restarts, then re-solves the top 8 with 15.
   - Validation targets: the 4人日 霊,猫,灰,灰 page must give 1w生存 1/2 and 1w1k生存 1/4 (matches the reference wiki). The 3人日 candidate solver must equal the exact one except where fine mixing matters.
5. Nodes carry `tag`s (`吊`, `噛み`, `GJ`, `翌日`…) used only by `analyze45.paths` to write the "how it ends" explanations. Tags must not change values.

## Page data and viewer

- `d3.json` entries come from `wikitext.board_text`:
  - `board`, `v`, `plan`, `va`/`plana` (the best other "all-in / 1/2-split" plan)
  - `secs[]`: a title like `1w1k生存で猫に狂`, a share, and `items[]`. Each item has `plan`, `best`, `fixed` votes and `terms` (factors + 猫飛び/ランダム outcome).
  - `summ[]`: per-situation values.
- `d4.json` / `d5.json` come from `analyze45.board_text`. Their items have `paths` (`[label, prob, win]`) instead of `terms`.
- `app.js` loads `data/d{3,4,5}.json` and ignores missing files. It sorts boards by counts of 霊 → 猫+ギ → 狩 → 灰, descending, and routes `#<n>-<id>[-c<k>|-sum]`. It renders fractions with `\tfrac` through KaTeX and falls back to plain text.
- Writing style follows the user's reference (ゲヘナのwiki, FC2): dense text, a heading per situation, a comparison of progressions, and derivations as fraction products such as `狼が真猫に入れる(1/2)×猫飛び(1/2)=1/4`. The user explicitly wants compact, FC2-like density, so keep spacing tight.

## Related repos

The sister project `leonmfvo/werewolf-endgame-10a` (10a狩) uses the same viewer format, but its data comes from the werewolf-tree-10a branch engine. Formatting changes here are often requested there too.
