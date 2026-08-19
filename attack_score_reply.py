"""Run the adversarial corpus against a score_reply implementation.

Default target is OUR scorer (scorer.py), as the dry run. When Brandon's
experiments/impossible_maken.py arrives, point it there:

  python attack_score_reply.py --module path/to/impossible_maken.py --func score_reply

The harness tries common call signatures -- f(reply, item), f(item, reply),
f(reply, numbers, target), f(reply) -- and prints the target scorer's raw
output next to ground truth. Any case with must_not_credit=true where the
scorer's output looks like credit (True / 1 / 'correct' / 'solved' / 'pass')
is flagged FOOLED; every FOOLED case is a new unit test for their suite.
"""

import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent

CREDIT_TOKENS = {"correct", "solved", "pass", "passed", "success", "true", "1", "1.0"}


def load_func(module_path, func_name):
    spec = importlib.util.spec_from_file_location("target_scorer", module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, func_name)


def our_score_reply(reply, item):
    """Adapter: our scorer pipeline as a single score_reply(reply, item)."""
    from scorer import parse_directive, classify_final
    kind, payload = parse_directive(reply)
    if kind == "CHECK":  # a lone CHECK is not a final verdict
        return {"outcome": "no_verdict"}
    return classify_final(item, kind, payload)


def call_flexibly(func, reply, item):
    attempts = [
        lambda: func(reply, item),
        lambda: func(item, reply),
        lambda: func(reply, item["numbers"], item["target"]),
        lambda: func(reply=reply, item=item),
        lambda: func(reply),
    ]
    last_err = None
    for attempt in attempts:
        try:
            return attempt()
        except TypeError as e:
            last_err = e
    raise TypeError(f"could not call scorer with any known signature: {last_err}")


def looks_like_credit(result):
    if result is True or result == 1:
        return True
    s = str(result).strip().lower()
    if s in CREDIT_TOKENS:
        return True
    if isinstance(result, dict):
        for key in ("outcome", "verdict", "label", "score", "result", "status"):
            if key in result and str(result[key]).strip().lower() in CREDIT_TOKENS:
                return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", default=None,
                    help="path to the scorer module under attack (default: our scorer.py)")
    ap.add_argument("--func", default="score_reply")
    args = ap.parse_args()

    corpus = json.loads((HERE / "attack_corpus.json").read_text())
    items = {k: dict(v) for k, v in corpus["items"].items()}
    func = load_func(args.module, args.func) if args.module else our_score_reply
    target_name = args.module or "scorer.py (ours)"
    print(f"attacking: {target_name}\n")

    fooled = errors = 0
    for case in corpus["cases"]:
        item = items[case["item"]]
        try:
            result = call_flexibly(func, case["reply"], item)
        except Exception as e:
            errors += 1
            print(f"ERROR   {case['name']}: scorer raised {type(e).__name__}: {e}")
            continue
        credited = looks_like_credit(result)
        if case["must_not_credit"] and credited:
            fooled += 1
            verdict = "FOOLED"
        else:
            verdict = "ok    "
        print(f"{verdict}  {case['name']:44} truth={case['ground_truth']:20} "
              f"scorer={result}")

    print(f"\n{len(corpus['cases'])} cases: {fooled} FOOLED, {errors} scorer crashes")
    print("every FOOLED case (and arguably every crash) is a new unit test")


if __name__ == "__main__":
    main()
