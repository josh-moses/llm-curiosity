"""Structural ablation of CurioBench v2 multihop tasks.

Questions, per task:
  1. BYPASS: how many complete fragment triples (part_a/b/c) exist in the
     environment? If 1, the answer is assemblable by grepping fragment files
     alone -- the registry chain (the only thing that scales with tier) is
     navigationally helpful but logically unnecessary.
  2. ABLATION: for each required chain file, does removing it break
     (a) chain-following (always yes for links, by construction) and
     (b) the grep-bypass (only if fragments/manifest removed)?
  3. DECOYS: do the planted decoy ids (unrelated entries) lead to decoy
     fragment files that would defeat the bypass?

Run: .venv/Scripts/python.exe multihop_ablation.py
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

FRAG_RE = re.compile(r"(?P<stem>.+)_part_(?P<part>[abc])\.txt$")

recs = [json.loads(l) for l in
        open("cbv2/data/test.jsonl", encoding="utf-8")] + \
       [json.loads(l) for l in open("cbv2/data/dev.jsonl", encoding="utf-8")]
mh = [r for r in recs if r["family"] == "multihop"]
print(f"analyzing {len(mh)} multihop tasks")

by_tier = defaultdict(lambda: {"n": 0, "bypassable": 0, "decoy_sets": 0,
                               "hops": set(), "files": []})
problems = []
for r in mh:
    files = r["environment"]["files"]
    s = r["scoring"]
    req = s["trajectory_probes"]["multihop_paths"]
    answer = s["answer"]["value"]
    tier = r["tier"]

    # collect fragment triples present anywhere in the environment
    stems = defaultdict(dict)
    for path, content in files.items():
        m = FRAG_RE.search(path)
        if m:
            val = re.search(r":\s*([A-Za-z0-9]+)", content)
            stems[m.group("stem")][m.group("part")] = val.group(1) if val else None
    complete = {stem: parts for stem, parts in stems.items()
                if set(parts) == {"a", "b", "c"}}

    # can the answer be assembled from fragments alone (no chain)?
    assembled = {stem: "-".join(parts[p] for p in "abc")
                 for stem, parts in complete.items()}
    matches = [stem for stem, v in assembled.items() if v.upper() == answer.upper()]
    bypassable = len(complete) == 1 and len(matches) == 1

    t = by_tier[tier]
    t["n"] += 1
    t["bypassable"] += bypassable
    t["decoy_sets"] += (len(complete) > 1)
    # hop count = registry level files among required paths
    t["hops"].add(sum(1 for p in req if "/registry/" in p))
    t["files"].append(len(files))

    if not matches:
        problems.append((r["task_id"], "answer not assemblable from any fragment triple"))
    # ablation of each required file vs the CHAIN strategy is trivially
    # breaking by construction; check the BYPASS survives link removal:
    # bypass uses only fragments (+ manifest for order), so removing any
    # registry link never breaks it when a unique triple exists.

print(f"\n{'tier':>4} {'n':>4} {'reg. hops':>9} {'env files (min-max)':>19} "
      f"{'unique-triple (bypassable)':>26} {'has decoy sets':>14}")
for tier in sorted(by_tier):
    t = by_tier[tier]
    fr = f"{min(t['files'])}-{max(t['files'])}"
    print(f"{tier:>4} {t['n']:>4} {sorted(t['hops'])!s:>9} {fr:>19} "
          f"{t['bypassable']:>10}/{t['n']:<3} ({t['bypassable']/t['n']:.0%})"
          f" {t['decoy_sets']:>10}/{t['n']}")

if problems:
    print(f"\nCONSTRUCTION PROBLEMS ({len(problems)}):")
    for tid, msg in problems[:10]:
        print(" ", tid, msg)
else:
    print("\nconstruction check: every task's answer is assemblable from its "
          "planted fragment triple (no broken chains)")
