"""Aggregate pilot-2 per-task scores into tier calibration curves."""
import json
from collections import defaultdict

tasks = {}
for split in ("dev", "test"):
    for l in open(f"cbv2/data/{split}.jsonl", encoding="utf-8"):
        r = json.loads(l)
        tasks[r["task_id"]] = r

MODELS = {"meta-llama__llama-3.1-8b-instruct": "llama-8b",
          "deepseek__deepseek-chat": "deepseek",
          "anthropic__claude-sonnet-5": "sonnet-5"}

first = json.loads(open("cbv2/runs/scored_anthropic__claude-sonnet-5__toolcall__test.jsonl",
                        encoding="utf-8").readline())
print("scored fields:", sorted(first.keys()), "\n")

header = f"{'model':10}" + "".join(f"   tier{t}" for t in (1, 2, 3, 4)) + \
         "    mean actions t1..t4"
print(header)
for slug, short in MODELS.items():
    rows = [json.loads(l) for l in
            open(f"cbv2/runs/scored_{slug}__toolcall__test.jsonl", encoding="utf-8")]
    acc = defaultdict(lambda: [0, 0])
    steps = defaultdict(list)
    for r in rows:
        t = tasks[r["task_id"]]["tier"]
        ok = None
        for key in ("multihop_completion", "success", "answer_correct", "correct"):
            if key in r:
                ok = r[key]
                break
        acc[t][0] += bool(ok)
        acc[t][1] += 1
        for key in ("n_actions", "actions", "tool_calls", "steps"):
            if key in r:
                v = r[key]
                steps[t].append(len(v) if isinstance(v, list) else v)
                break
    cells = "".join(f"  {acc[t][0]:>2}/{acc[t][1]:<3}" for t in (1, 2, 3, 4))
    sc = " ".join(f"{sum(steps[t])/len(steps[t]):5.1f}" if steps[t] else "  -  "
                  for t in (1, 2, 3, 4))
    print(f"{short:10}{cells}    {sc}")
