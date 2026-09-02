# CurioBench leaderboard (toolcall, split=test, n=60 runs/model)

| model | H_eff | H | CI | K | succ | XR | DR | GR | MH | HR | Eff | TR | CC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `meta-llama/llama-3.1-8b-instruct` | 0.000 | 0.000 | 0.500 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.993 | 1.000 | 1.000 |
| `deepseek/deepseek-chat` | 0.000 | 0.000 | 0.500 | 0.000 | 0.050 | 0.000 | 0.683 | 0.000 | 0.000 | 0.167 | 0.995 | 1.000 | 1.000 |
| `anthropic/claude-sonnet-5` | 0.000 | 0.000 | 0.650 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.867 | 1.000 | 1.000 |

H = sqrt(CI x control_success); CI = 0.20·XR + 0.15·GR + 0.15·MH + 0.30·TR + 0.20·CC.
H_eff = H x sqrt(Eff). DR, HR, Eff, and H_eff require trajectory data.
See docs/EVALUATION.md for metric definitions.
