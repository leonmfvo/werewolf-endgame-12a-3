# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A static GitHub Pages site (https://leonmfvo.github.io/werewolf-endgame-12a-3/) giving village win rates for **12A猫** werewolf endgame boards (roles: 占い・霊能・狩人・猫又・狂人・狼3・村人4). The Python in `compute/` solves the games and writes JSON into `data/`. The single-page viewer (`index.html` + `app.js` + `style.css`) renders that JSON. There is no build step, package manager or test suite. Dependencies are plain Python 3 (`fractions`, `itertools`, `multiprocessing`) and the bundled KaTeX in `vendor/katex/`.

The user writes in Japanese. All page text, code comments and commit messages are Japanese. Keep that.

## Commands

Run these from the repo root. Python modules import each other by bare name, so either run scripts directly or `cd compute` first.

```sh
python3 compute/vote3.py data/d3.json                       # 3人日: exact solve + page text (~1 min)
cd compute && python3 -u rundaily.py 4 5                    # 4・5人日: daily dictionary method; grows data/dict.json (resumable), writes data/daily{n}.json
cd compute && python3 -u daily_pages.py 4 ../data/d4.json     # page JSON from the dictionary (same for 5)
python3 compute/run45.py 4 data/plans4.json 4               # OLD full-tree method (superseded; kept for comparison)
python3 -m http.server 8766                                 # preview locally, open /#3-1 etc.
```

`rundaily.py` saves `data/dict.json` after every board and loads it on start, so a stopped run continues. Delete `dict.json` whenever solver logic changes (the stored values depend on it). Start long runs with `nohup … &` (the 2-hour background-task limit), and never `pkill -f` a pattern that also matches your own shell command (exit 144 kills the shell).

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
   - Memory: `game.MODE` (`exact=False, tags=False`) builds the search tree with float probabilities and no tag nodes. The exact value of the chosen adversary policy is then recomputed world by world (`Game.exact_value`, `evaluate(..., default=0)`). `analyze45` does the same per world. This reproduced every 4人日 value and page exactly.
   - **No approximations in published values.** The user requires zero difference from the full computation (not even 0.001). `refs.py` / `Game(ref=…)` replace the next day by the stored 3・4人日 per-world values. That is only an approximation: the next day's 内訳 proportions, the wolves' private knowledge (whom they bit) and the village plan continuing from the previous day all differ from a fresh board. On 4人日 it gave mean 0.2pt, max 5.7pt differences, so it is off by default (`USE_REF=1` enables it). Exact decomposition into "next boards" would require next-day states to carry the posterior and private knowledge, and their solutions to use the same continuation strategies.
5. **Daily dictionary method (`daily.py`) is the current 4人日+ solver** (the user's design: reduce to fewer-person states, add missing states to a dictionary).
   - A state is (labels, posterior over (roles, humans the wolves know survived a bite)), canonicalised over permutations of same-label seats (`canon`). Same-looking boards with different 内訳 proportions are different states, so decomposition is exact by definition.
   - `value(key)`: ≤3 alive → `vote3g.solve_board(labels, cases, extras)` (exact); otherwise `solve_day`: `Game(start=…)` stops at the next morning ('N' nodes); the next state's value comes from the dictionary (solved on demand).
   - `solve_day`: stage 1 screens every candidate with 1 adversary start; stage 2 re-solves 8 plans with 9 starts in forward / reverse / random orders (`adversary_min`). Stage 2 merges plans of the same (des, counter, mode) with equal stage-1 value: otherwise guard/co variants with tied values filled the slots and better families were missed (5 boards on 4人日). The final value is recomputed with Fraction.
   - `Flat` evaluates incrementally (only changed leaves and dirty next states); `FCACHE` caches float next-state values.
   - Validation: 4人日 dict equals max over all candidates (9 starts each) on all 68 boards. Old full-tree 4人日 values that were higher came from the old adversary search getting stuck (e.g. 霊,霊,霊,白: 31/135 → 101/540, and the full tree with the new search gives the same).
   - `daily_pages.py` recomputes per-world values (`world_values`, recursively for next states via the same plan and deterministic search) and asserts their mean equals the dictionary value.
6. Nodes carry `tag`s (`吊`, `噛み`, `GJ`, `翌日`…) used only by `analyze45.paths` to write the "how it ends" explanations. Tags must not change values.

## Page data and viewer

- `d3.json` entries come from `wikitext.board_text`:
  - `board`, `v`, `plan`, `va`/`plana` (the best other "all-in / 1/2-split" plan)
  - `secs[]`: a title like `1w1k生存で猫に狂`, a share, and `items[]`. Each item has `plan`, `best`, `fixed` votes and `terms` (factors + 猫飛び/ランダム outcome).
  - `summ[]`: per-situation values.
- `d4.json` / `d5.json` come from `daily_pages.board_page` (via `analyze45.assemble`). Their items have `paths` (`[label, prob, win]`) instead of `terms`.
- `app.js` loads `data/d{3,4,5}.json` and ignores missing files. It sorts boards by counts of 霊 → 猫+ギ → 狩 → 灰, descending, and routes `#<n>-<id>[-c<k>|-sum]`. It renders fractions with `\tfrac` through KaTeX and falls back to plain text.
- Writing style follows the user's reference (ゲヘナのwiki, FC2): dense text, a heading per situation, a comparison of progressions, and derivations as fraction products such as `狼が真猫に入れる(1/2)×猫飛び(1/2)=1/4`. The user explicitly wants compact, FC2-like density, so keep spacing tight.

## Related repos

The sister project `leonmfvo/werewolf-endgame-10a` (10a狩) uses the same viewer format, but its data comes from the werewolf-tree-10a branch engine. Formatting changes here are often requested there too.
