# Report folder — start here

Everything from the 2026-08-19 curiosity/cheating experiment, written for a
reader with no RL background.

| read | to get |
|---|---|
| [RESULTS.md](RESULTS.md) | the four findings, tables, receipts, caveats — the thing to bring to the team |
| [METHODS.md](METHODS.md) | how each of the three instruments works and why it can be trusted |
| [figures/curiosity_vs_dishonesty.png](figures/curiosity_vs_dishonesty.png) | the two-panel summary figure |

## One-paragraph version

We measured five chat models (OpenAI, Anthropic, DeepSeek, Qwen, Moonshot;
one identical OpenRouter harness) on three instruments: our own arithmetic
puzzles with provably impossible items and a free private calculator
(curiosity + honesty), the published ImpossibleBench (coding tasks whose
tests are sabotaged, so passing = cheating), and the published CurioBench-1K
(virtual workspaces with planted gems, decoys, and shortcuts). Three
one-sentence manipulations were crossed in: false pressure ("you must
answer"), "verification is valued", and "comply exactly". Results: pressure
converts honest models into confident bluffers (deepseek: 5% -> 80%
false-answer rate, including rule-breaking hits that exactly satisfy the
target); nobody test-hacks (0/300 impossible coding episodes); noticing is
a one-sentence-deep default (the "valued" framing multiplies contradiction-
flagging and gem-reporting in three of five models); and the models that
notice most (kimi-k2, haiku-4.5) are the ones that never bluff.

## Where the raw data lives (repo root)

| path | contents |
|---|---|
| `results/summary.json` | arithmetic harness aggregates (per model x condition) |
| `results/runs_*.jsonl` | every harness episode with full transcripts (800) |
| `results/impossiblebench_summary.json` | IB accuracy per model x split x framing |
| `results/ib_flagging.json` | per-episode contradiction-flagging labels (152) |
| `results/curiobench_summary.json` | CurioBench metrics per model |
| `results/curiobench/cb_*.jsonl` | every CurioBench reply (500) |
| `results/cross_table.json` | the Finding-4 cross-model table |
| `logs/impossiblebench/*.eval` | full Inspect transcripts (browse: `inspect view`) |

## Regenerate everything

```bash
python analyze.py                                # harness tables
.venv/Scripts/python.exe ib_summarize.py          # IB cheating table
.venv/Scripts/python.exe ib_flagging.py           # IB noticing table
python curiobench_score.py                       # CurioBench table
python cross_table.py && python make_figure.py   # cross table + figure
```

Scoring is deterministic; only the `runs_*.jsonl` / `.eval` / `cb_*.jsonl`
files came from API calls.
