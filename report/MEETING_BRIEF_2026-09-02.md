# Meeting brief: CurioBench v2 review + pilots (Josh, 2026-09-02)

## What I verified about Roozi's v2 (all independent, my machine, his official tools)

- Tests 21/21 pass; validator clears all 1,000 tasks; scripted-policy
  ordering holds (curious 0.896 > grinder > gullible > timid; curious >
  spammer on H_eff, so read-everything loses by construction).
- The multihop bypass I found in round 1 (150/150 tasks solvable by
  grepping the only fragment triple) is fixed: now 0/150 bypassable, every
  task has tier-scaled decoy bundles (1/2/4/8), chains deepened to 0/1/3/5
  hops, and new validator hard-checks lock the fix in.
- A second attack (pick the most-mentioned bundle id, skip the chain)
  fails on all 150 tasks. Construction is robust.

## Pilot 1 -- regression / discrimination (5 models, dev split, official scorer)

| model | H | control | gems | traps |
|---|---|---|---|---|
| kimi-k2 | 0.816 | 0.940 | 0.293 | 1.000 |
| claude-haiku-4.5 | 0.813 | 0.930 | 0.244 | 0.917 |
| deepseek-chat | 0.497 | 0.810 | 0.000 | 0.583 |
| qwen-2.5-72b | 0.486 | 0.740 | 0.000 | 0.500 |
| gpt-4o-mini | 0.388 | 0.550 | 0.000 | 0.333 |

- Rankings match our v1 baseline (top pair statistically tied). **No
  regression; discrimination retained.** (Julius's ask #1: answered.)
- Gem floor: rose only for models that ever volunteer (kimi .20->.29,
  haiku .03->.24). The other three are still exactly 0.000 -> the floor is
  model policy, not gem design. Frame as a finding, not a to-do.

## Pilot 2 -- multihop tier calibration (toolcall, 60 tasks, size ladder)

| model | t1 | t2 | t3 | t4 | mean actions t1->t4 | diagnosis |
|---|---|---|---|---|---|---|
| sonnet-5 | 100% | 100% | 100% | 100% | 12.6 -> 23.2 | tiers cost effort, not success: **no headroom** |
| deepseek | 6% | 7% | 6% | 0% | ~3-5 | quits chains early (hop coverage ~0.17): persistence, not difficulty |
| llama-8b | 0% | 0% | 0% | 0% | ~0 | **harness bug**: emits pseudo-toolcall text, never explores |

(Julius's ask #2: tiers are NOT calibrated at either end, with receipts.)

Also caught: compliance metric (CC) looks broken on the text-mode
leaderboard (0.13-0.50 for everyone) because text mode pastes restricted
dirs into the prompt. CC should be toolcall-only or footnoted.

## Decisions to make in the meeting

1. How to create frontier headroom at tier 4. IMPORTANT UPDATE: I tested my
   own hetero-hop proposal before recommending it (paired probe, n=10/arm,
   sonnet-5, decoy bundles present): lookup-x5 100% vs heterogeneous chain
   100%. **As prototyped, hop heterogeneity does NOT add frontier
   difficulty** -- when the workspace is readable, every hop type is easy.
   So the discussion should be about the remaining levers: (a) step-budget
   pressure in toolcall mode (sonnet used 23 actions at tier 4; cap at ~12
   and success must drop), (b) much larger haystacks (my probe envs were
   ~25 files), (c) near-miss decoy chains sharing prefixes with the true
   chain, (d) hops requiring verification/computation that cannot be done
   by reading alone. Evidence: `results/hetero_probe.json`.
2. Small-model scaffold: lenient parser for hermes-style pseudo-toolcalls,
   or documented text-mode fallback for sub-10B models? (Without one,
   "easy enough for small models" is unmeasurable.)
3. Compliance metric: restrict to toolcall mode, or re-define for text?
4. Multihop guessing floors (50/33/20/11% by tier from finite candidate
   sets): raise tier-1 decoys or report guess-corrected scores?
5. Which workshop deadline; whether the paper is benchmark-only or also
   folds in the curiosity-vs-cheating findings.
6. Who reruns the tier ladder after the hop patch (I can, ~$10).

## Where everything lives

Branch `joshua-llm-curiosity` on the team repo: ablation + attack scripts,
tier curves + diagnostics (`tier_curves.py`, `tier_diag.py`), scored run
logs, `hetero_hops.py` prototype, `hetero_probe.py` headroom probe,
full report folder.
