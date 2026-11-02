# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A static GitHub Pages site (https://leonmfvo.github.io/werewolf-endgame-12a-3/) giving village win rates for **12A猫** werewolf endgame boards (roles: 占い・霊能・狩人・猫又・狂人・狼3・村人4). The Python in `compute/` solves the games and writes JSON into `data/`. The single-page viewer (`index.html` + `app.js` + `style.css`) renders that JSON. There is no build step, package manager or test suite. Dependencies are plain Python 3 (`fractions`, `itertools`, `multiprocessing`) and the bundled KaTeX in `vendor/katex/`.

The user writes in Japanese. All page text, code comments and commit messages are Japanese. Keep that.

## Commands

Run these from the repo root. Python modules import each other by bare name, so either run scripts directly or `cd compute` first.

```sh
cd compute && DICT_PATH=../data/dict.work.json python3 -u rundaily.py 3 4 5   # solve every board × situation; resumable; writes data/daily{n}.json
cd compute && python3 -u daily_pages.py 5 ../data/d5.json      # page JSON (+ data/s5.json next-day states) from the dictionary (same for 3, 4)
python3 compute/merge_pages.py 5 data/d5.json data/s5.json d5.new:s5a.new d5b.new:s5b.new   # join page files made in parallel (renumbers next-day states)
python3 -m http.server 8766                                 # preview locally, open /#3-1 etc.
```

`rundaily.py` saves the dictionary after every board and every 10 minutes (`DICT_PATH`, use an ignored `*.work.json` while running, copy to `data/dict.json` at the end), and loads it on start, so a stopped run continues. Delete it whenever solver logic changes (stored values depend on it). Parallel runs: `PART=k/m/s`, `BOARDS='a,b,c;…'`, `SIT=i` select boards/situations; give each process its own dict copy and merge the JSON lists afterwards (entries never conflict). `daily_pages.py` is resumable too (`SKIP`, `REVERSE`, `SFILE`; next-state numbering kept in `*.keys.json`). 5人日 with many ギ took ~9 h per heavy situation on one core; keep a Monitor armed while waiting, or the idle container is reclaimed and running jobs die. Start long runs with `nohup … &` (the 2-hour background-task limit), and never `pkill -f` a pattern that also matches your own shell command (exit 144 kills the shell).

To check a page in a headless browser, use Playwright, which is preinstalled (`require('playwright')`, `chromium.launch()`). Pages must not scroll horizontally at 390px width.

## Board / notation model (shared by all solvers)

- **Board**: the list of alive people's visible labels, ordered `霊 → 猫 → ギ → 狩 → 灰` (霊能CO・猫又CO・ギドラCO・狩人CO・グレー). Seer results (白/黒) are deliberately not modelled yet.
- **Worlds**: every role assignment consistent with the board (`vote3.assignments`, `game.worlds`). Each is weighted by the role-card count (`weight`: 村人4・狼3・others 1).
- **Rules the user fixed**, all enforced in the world generators:
  - A single 猫/霊/狩 CO is the real one. With 2+ claims, exactly one 猫 claimant is real (猫又 has no 役欠け); 霊 and 狩 claims can all be fake.
  - ギドラ only appears with ≥2 claimants and never alongside 猫 or 狩 COs. When a ギ exists, no real 狩人/猫又 hides in 灰.
  - If a 狩 CO exists, the real 狩人 is not hiding in 灰.
  - PP: with ≥5 alive and the 狂人 alive, the 人外 majority wins; a tie is 1/2.
  - 白 (GJ target shown after a hunter CO) means the real hunter is the 狩 CO or dead, never hidden elsewhere.
- **Situation label** (`situation`): `1w1k生存（狩生存・猫生存）`. w = wolves, k = 狂人 alive, 狩生存 = the real hunter is alive (not written when a lone 狩 CO is the real one), 猫生存 = the real cat is alive outside 猫 COs (灰/ギ). The user chose the wk notation; don't switch to 狼/狂.

## Solvers: the important design decisions

These came out of correcting mistakes with the user. Don't regress them.

1. **Everyone knows the situation (the user's reference wiki convention).** The village, wolves and 狂人 know the wolf count, whether the 狂人 is alive and whether the real 狩人/猫又 is alive (`situation`); after a hang the new situation is known too. They don't know who is who. Each (board, situation) is solved separately with its own best village plan (`daily.board_keys`; next states carry the situation in their history). This replaced an earlier "nobody knows" model after the user decided to follow ゲヘナのwiki, whose pages are per (board, situation).
2. **Seats that public events distinguish can be named.** `daily.canon` strips labels to their base character, canonicalises, then splits same-label seats that are not interchangeable under the posterior into `狩A/狩B…` (`split_labels`); fresh boards never split. Village and adversaries can then target them by name. Plans also include a named guard chain (`chain`: claimant A guards B, …, the last guards the first `guard` class; order fixed by seat, recorded in history). Wolves know each other; the 狂人 does not know the wolves (but deduces what the situation implies, e.g. 猫・狼・狂 → the wolf knows the other is the 狂人 and can vote him).
   - Validated against the wiki: 霊猫灰灰灰 2w 1/3, 1w 2/3; 霊猫狩狩狩 2w 2/3; 霊猫狩狩灰 all 狩生存 situations 1; 霊猫灰灰 1w 1/2, 1w1k 1/4. Known wiki differences we believe are wiki mistakes: 霊猫灰灰灰 1w1k 7/12 (wiki counts 狂吊り as 村吊り), 霊猫狩狩狩 1w1k 3/4 (wiki misses the wolf voting the 狂人 on 猫・狼・狂).
3. **3人日 (`vote3.py`, `vote3g.py`) is exact.**
   - `vote3g.solve_board` searches one village plan per state: a vote distribution per (label, own role), grid of 1/4, 1/3… refined to 1/12 (when there are many types because of 狩A/狩B labels, it starts from 0/½/1 seeds instead of the full grid). Floats during search, Fraction at the end.
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
   - Adversary search starts from the "mimic" policy (adversaries vote like a villager of their label would, hiding their identity; `Node.mimic`), then random restarts, each followed by `KICKS` random perturb-and-redescend rounds. Without the mimic start the search missed hiding strategies (霊猫灰灰灰 2w came out 5/9 instead of 1/3).
   - `solve_day`: stage 1 screens every candidate with 1 adversary start and no kicks. Stage 2 re-solves plans in descending stage-1 value with 9 starts (forward / reverse / random orders, `adversary_min`) and stops once the stage-1 value is ≤ the best so far. Start 0 of the 9 is the stage-1 search, so a 9-start value never exceeds the stage-1 value. The result therefore equals the max over all candidates at 9 starts. (Fixed top-K cuts missed better plans: 5 boards on 4人日, 猫,猫,狩,狩,灰 on 5人日.) The final value is recomputed with Fraction.
   - `canon` merges worlds with the same (roles, known humans) before canonicalising, so one state never gets two keys.
   - `Flat` evaluates incrementally (only changed leaves and dirty next states); `FCACHE` caches float next-state values.
   - Validation: 4人日 dict equals max over all candidates (9 starts each) on all 68 boards. Old full-tree 4人日 values that were higher came from the old adversary search getting stuck (e.g. 霊,霊,霊,白: 31/135 → 101/540, and the full tree with the new search gives the same).
   - `daily_pages.py` recomputes per-world values (`world_values`, recursively for next states via the same plan and deterministic search) and asserts their mean equals the dictionary value.
6. Nodes carry `tag`s (`吊`, `噛み`, `GJ`, `翌日`…) used only by `analyze45.paths` to write the "how it ends" explanations. Tags must not change values.

## Page data and viewer

- `d3.json` entries come from `wikitext.board_text`:
  - `board`, `v`, `plan`, `va`/`plana` (the best other "all-in / 1/2-split" plan)
  - `secs[]`: a title like `1w1k生存で猫に狂`, a share, and `items[]`. Each item has `plan`, `best`, `fixed` votes and `terms` (factors + 猫飛び/ランダム outcome).
  - `summ[]`: per-situation values.
- `d3/d4/d5.json` all come from `daily_pages.board_page` (via `analyze45.assemble`): `plan` is null, `summ[]` has a `plan`/`plana` per situation, items have `paths` (`[label, prob, win, next-state id, next-state case title]`). `s<n>.json` holds the next-day states (same shape), opened via `#s<n>-<id>`; the board in a 翌日 path is a link. `wikitext.board_text` (fraction-product derivations) is no longer used for d3.
- `app.js` loads `data/d{3,4,5}.json` and ignores missing files. It sorts boards by counts of 霊 → 猫+ギ → 狩 → 灰, descending, and routes `#<n>-<id>[-c<k>|-sum]`. It renders fractions with `\tfrac` through KaTeX and falls back to plain text.
- Writing style follows the user's reference (ゲヘナのwiki, FC2): dense text, a heading per situation, a comparison of progressions, and derivations as fraction products such as `狼が真猫に入れる(1/2)×猫飛び(1/2)=1/4`. The user explicitly wants compact, FC2-like density, so keep spacing tight.

## Related repos

The sister project `leonmfvo/werewolf-endgame-10a` (10a狩) uses the same viewer format, but its data comes from the werewolf-tree-10a branch engine. Formatting changes here are often requested there too.
