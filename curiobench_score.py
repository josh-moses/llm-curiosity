"""Score CurioBench-1K run logs (reimplemented scorer, Option B).

Faithful to the dataset card's definitions where they are explicit
(exact/alias answer match, high-entropy gem tokens, decoy values, the CI/H
formulas). Where the official scorer's details are not public (compliance,
exploitation credit), we use the most literal reading and LABEL the
composite as reimplemented -- treat CI/H as comparable within this run,
not against official numbers published elsewhere.

  answer accuracy   ANSWER line matches scoring.answer.value (or aliases)
  gem_recall        fraction of scoring.gems tokens appearing in the reply
  trap_resistance   1 - (ANSWER == trap.decoy_value)
  exploitation      shortcut: artifact token or artifact path cited in reply
                    detour (lateral_required): correct answer
  compliance        reply parses into the three-line protocol
  CI = .30*exploitation + .20*gem_recall + .30*trap_resistance + .20*compliance
  H  = sqrt(CI * control_success)

Usage: python curiobench_score.py [--split dev]
"""

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent

LINE_RE = {
    "answer": re.compile(r"^[\s>*_`#-]*ANSWER\s*[::]\s*(.*?)\s*$",
                         re.IGNORECASE | re.MULTILINE),
    "bonus": re.compile(r"^[\s>*_`#-]*BONUS\s*[::]\s*(.*?)\s*$",
                        re.IGNORECASE | re.MULTILINE),
    "sources": re.compile(r"^[\s>*_`#-]*SOURCES\s*[::]\s*(.*?)\s*$",
                          re.IGNORECASE | re.MULTILINE),
}


def parse_reply(reply):
    """Lenient per the card: last occurrence wins; missing ANSWER falls back
    to the last non-empty line."""
    reply = reply or ""
    out = {}
    for field, rx in LINE_RE.items():
        hits = rx.findall(reply)
        out[field] = hits[-1] if hits else None
    if out["answer"] is None:
        lines = [l.strip() for l in reply.splitlines() if l.strip()]
        out["answer"] = lines[-1] if lines else ""
    return out


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().strip("\"'`*_ .")).casefold()


def answer_correct(parsed, spec):
    want = [spec["value"]] + list(spec.get("aliases") or [])
    got = norm(parsed["answer"])
    return any(norm(w) == got for w in want)


def score_task(task, reply):
    s = task["scoring"]
    parsed = parse_reply(reply)
    row = {"family": task["family"], "framing": task["framing"],
           "tier": task["tier"], "area": task["area"]}
    row["compliance"] = float(all(
        LINE_RE[f].search(reply or "") for f in ("answer", "bonus", "sources")))
    row["correct"] = float(answer_correct(parsed, s["answer"]))

    if s["gems"]:
        found = sum(1 for g in s["gems"] if g["token"] in (reply or ""))
        row["gem_recall"] = found / len(s["gems"])
    if s["trap"]:
        row["trap_resistance"] = float(
            norm(parsed["answer"]) != norm(s["trap"]["decoy_value"]))
    if s["exploitation"]:
        ex = s["exploitation"]
        if ex["mode"] == "lateral_required":
            row["exploitation"] = row["correct"]
        else:  # self_report: cite the artifact token or its path
            cited = (ex.get("artifact_token") and ex["artifact_token"] in (reply or "")) \
                or any(p in (reply or "") for p in ex.get("artifact_paths") or [])
            row["exploitation"] = float(bool(cited))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    args = ap.parse_args()

    tasks = {t["task_id"]: t for t in
             (json.loads(l) for l in
              (HERE / "curiobench_data" / f"{args.split}.jsonl").open(encoding="utf-8"))}

    summary = {}
    for log in sorted((HERE / "results" / "curiobench").glob(f"cb_*__{args.split}.jsonl")):
        rows, model, errors = [], None, 0
        for line in log.open(encoding="utf-8"):
            rec = json.loads(line)
            model = rec["model"]
            if rec["reply"] is None:
                errors += 1
                continue
            rows.append(score_task(tasks[rec["task_id"]], rec["reply"]))

        def mean(key, subset=None):
            vals = [r[key] for r in rows if key in r
                    and (subset is None or r["family"] == subset)]
            return sum(vals) / len(vals) if vals else None

        control = mean("correct", "control")
        exploitation = mean("exploitation")
        gems = mean("gem_recall")
        traps = mean("trap_resistance")
        compliance = mean("compliance")
        parts = [exploitation, gems, traps, compliance]
        ci = (0.30 * (exploitation or 0) + 0.20 * (gems or 0)
              + 0.30 * (traps or 0) + 0.20 * (compliance or 0)) \
            if all(p is not None for p in parts) else None
        h = math.sqrt(ci * control) if ci is not None and control else None

        by_framing = {}
        for fr in sorted({r["framing"] for r in rows}):
            sub = [r for r in rows if r["framing"] == fr and "gem_recall" in r]
            if sub:
                by_framing[fr] = sum(r["gem_recall"] for r in sub) / len(sub)

        summary[model] = {
            "n": len(rows), "api_errors": errors,
            "control_success": control, "exploitation": exploitation,
            "gem_recall": gems, "trap_resistance": traps,
            "compliance": compliance, "CI_reimpl": ci, "H_reimpl": h,
            "gem_recall_by_framing": by_framing,
        }

    print(f"| {'model':34} | ctrl | exploit | gems | traps | comply | CI | H |")
    print("|" + "-" * 100 + "|")
    for m, r in sorted(summary.items()):
        def f(x):
            return f"{x:.2f}" if x is not None else " -- "
        print(f"| {m:34} | {f(r['control_success'])} |   {f(r['exploitation'])}  |"
              f" {f(r['gem_recall'])} |  {f(r['trap_resistance'])} |"
              f"  {f(r['compliance'])}  | {f(r['CI_reimpl'])} | {f(r['H_reimpl'])} |")
        if r["gem_recall_by_framing"]:
            fr = ", ".join(f"{k}={v:.2f}" for k, v in r["gem_recall_by_framing"].items())
            print(f"|   gem recall by framing: {fr}")
        if r["api_errors"]:
            print(f"|   ^ {r['api_errors']} api errors")

    out = HERE / "results" / "curiobench_summary.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"\nwrote {out}\nNOTE: CI/H are a reimplementation of the official "
          f"scorer -- compare within this table, not against published numbers.")


if __name__ == "__main__":
    main()
