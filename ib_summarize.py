"""Summarize ImpossibleBench eval logs into a cheating-rate table.

Reads every .eval log under logs/impossiblebench/, extracts
(model, split, framing) -> accuracy. On impossible splits ('oneoff',
'conflicting') accuracy IS the cheating rate: the tests contradict the spec,
so a pass necessarily means a specification-violating shortcut. On
'original' it is plain competence.

Writes results/impossiblebench_summary.json and prints a markdown table.
Run with the project venv: .venv/Scripts/python.exe ib_summarize.py
"""

import json
import re
from collections import defaultdict
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log

HERE = Path(__file__).parent
LOG_DIR = HERE / "logs" / "impossiblebench"

NAME_RE = re.compile(r"lcb_(?P<split>\w+?)_canmod_fr_(?P<framing>\w+?)_minimal")


def main():
    rows = {}
    for info in list_eval_logs(str(LOG_DIR)):
        log = read_eval_log(info.name, header_only=True)
        if log.status != "success" or not log.results:
            print(f"skip ({log.status}): {info.name}")
            continue
        m = NAME_RE.search(log.eval.task)
        if not m:  # smoke logs from before the framing change etc.
            continue
        split, framing = m.group("split"), m.group("framing")
        model = log.eval.model
        acc = next((s.metrics["accuracy"].value
                    for s in log.results.scores if "accuracy" in s.metrics), None)
        n = log.results.total_samples
        # keep the latest/largest run per cell
        key = (model, split, framing)
        if key not in rows or rows[key]["n"] < n:
            rows[key] = {"accuracy": acc, "n": n}

    models = sorted({k[0] for k in rows})
    splits = sorted({k[1] for k in rows})
    framings = ["none", "valued", "compliance"]

    for split in splits:
        label = ("competence" if split == "original" else "CHEATING rate")
        print(f"\n### split: {split}  (accuracy = {label})\n")
        print("| model | " + " | ".join(framings) + " |")
        print("|---|" + "---|" * len(framings))
        for model in models:
            cells = []
            for fr in framings:
                r = rows.get((model, split, fr))
                cells.append(f"{r['accuracy']:.2f} (n={r['n']})" if r else "--")
            print(f"| {model} | " + " | ".join(cells) + " |")

    out = HERE / "results" / "impossiblebench_summary.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(
        {f"{m}|{s}|{f}": v for (m, s, f), v in sorted(rows.items())}, indent=2))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
