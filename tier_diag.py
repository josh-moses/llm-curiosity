"""Diagnose pilot-2 failures: scaffold breakdown vs genuine difficulty."""
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

print(f"{'model':10}{'tier':>5}{'succ':>6}{'actions':>9}{'reads':>7}"
      f"{'hop_cov':>9}{'effic':>7}{'zero-action tasks':>19}")
for slug, short in MODELS.items():
    rows = [json.loads(l) for l in
            open(f"cbv2/runs/scored_{slug}__toolcall__test.jsonl", encoding="utf-8")]
    by = defaultdict(list)
    for r in rows:
        by[tasks[r["task_id"]]["tier"]].append(r)
    for t in (1, 2, 3, 4):
        rs = by[t]
        if not rs:
            continue
        def m(k):
            vals = [r[k] for r in rs if r.get(k) is not None]
            return sum(vals) / len(vals) if vals else float("nan")
        zero = sum(1 for r in rs if not r.get("total_actions"))
        print(f"{short:10}{t:>5}{m('success'):>6.2f}{m('total_actions'):>9.1f}"
              f"{m('total_reads'):>7.1f}{m('hop_coverage'):>9.2f}"
              f"{m('exploration_efficiency'):>7.2f}{zero:>10}/{len(rs)}")

# peek one llama failure reply
raw = [json.loads(l) for l in
       open("cbv2/runs/meta-llama__llama-3.1-8b-instruct__toolcall__test.jsonl",
            encoding="utf-8")]
r0 = raw[0]
print("\nllama sample keys:", sorted(r0.keys()))
print("llama sample reply (first 400 chars):",
      repr((r0.get("reply") or "")[:400]))
print("llama sample actions:", (r0.get("actions") or [])[:6])
