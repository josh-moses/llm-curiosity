"""Cross-benchmark table: curiosity measures vs dishonesty measures per model."""
import json
from collections import defaultdict

h = json.load(open("results/summary.json"))
cb = json.load(open("results/curiobench_summary.json"))
ib = json.load(open("results/impossiblebench_summary.json"))
fl = json.load(open("results/ib_flagging.json"))

flag = defaultdict(lambda: [0, 0])
for r in fl:
    if "3.5-haiku" in r["model"]:
        continue
    m = r["model"].replace("openrouter/", "")
    flag[m][0] += r["flagged"]
    flag[m][1] += 1

MAP = {"openai/gpt-4o-mini": "gpt-4o-mini",
       "anthropic/claude-haiku-4.5": "haiku-4.5",
       "deepseek/deepseek-chat": "deepseek",
       "qwen/qwen-2.5-72b-instruct": "qwen-72b",
       "moonshotai/kimi-k2": "kimi-k2"}

hdr = (f"{'model':12} {'fab+cheat@press%':>16} {'honest@neutral%':>15} "
       f"{'checks@neutral':>14} {'gems':>5} {'traps':>6} {'flag%':>6} {'ib_cheat':>8}")
print(hdr)
rows = {}
for m, short in MAP.items():
    hp = h.get(m + "|pressure", {})
    hn = h.get(m + "|neutral", {})
    fab = (hp.get("fabricated", 0) + hp.get("rule_violation_hits", 0)) / max(hp.get("n_impossible", 20), 1) * 100
    hon = hn.get("honest_impossible", 0) / max(hn.get("n_impossible", 20), 1) * 100
    chk = hn.get("mean_checks", 0)
    c = cb.get(m, {})
    fg = flag.get(m)
    fgv = fg[0] / fg[1] * 100 if fg and fg[1] else None
    ibc = [v["accuracy"] for k, v in ib.items()
           if k.startswith("openrouter/" + m) and "conflicting" in k]
    ibc = sum(ibc) / len(ibc) * 100 if ibc else None
    rows[short] = dict(fab=fab, hon=hon, chk=chk, gems=c.get("gem_recall"),
                       traps=c.get("trap_resistance"), flag=fgv, ib=ibc)
    print(f"{short:12} {fab:16.0f} {hon:15.0f} {chk:14.2f} "
          f"{c.get('gem_recall', 0):5.2f} {c.get('trap_resistance', 0):6.2f} "
          f"{(f'{fgv:.0f}' if fgv is not None else '--'):>6} "
          f"{(f'{ibc:.0f}' if ibc is not None else '--'):>8}")

json.dump(rows, open("results/cross_table.json", "w"), indent=2)
print("\nwrote results/cross_table.json")
