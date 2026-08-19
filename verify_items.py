"""Independently verify impossibility labels in a maken items file.

Runs TWO algorithmically independent exhaustive solvers over every item:
  1. maken_tasks.all_values   -- multiset-reduction recursion
  2. second_solver.all_values_dp -- bottom-up bitmask DP over subsets
and reports, per item, whether the target is reachable over ANY subset.
Both solvers must agree with each other AND with the item's label.

Schema-flexible so it can consume Brandon's
results/ablations/impossible_maken_items.json sight-unseen: it auto-detects
the numbers / target / solvability keys and, if no solvability flag exists,
assumes all items are claimed impossible (that file's contract).

Usage:
  python verify_items.py items/items.json
  python verify_items.py path/to/impossible_maken_items.json --assume-impossible
"""

import argparse
import json
import sys
import time
from pathlib import Path

from maken_tasks import all_values, find_solution
from second_solver import all_values_dp

from fractions import Fraction

NUMBER_KEYS = ["numbers", "nums", "cards", "values", "inputs"]
TARGET_KEYS = ["target", "goal", "total"]
SOLVABLE_KEYS = ["solvable", "is_solvable", "possible", "is_possible"]
IMPOSSIBLE_KEYS = ["impossible", "is_impossible", "unsolvable"]


def detect(record, keys):
    for k in keys:
        if k in record:
            return k
    return None


def extract_items(data):
    """Accept a bare list of items or a dict wrapping one."""
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        raise SystemExit(f"could not find an item list in dict keys {list(data)}")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--assume-impossible", action="store_true",
                    help="no solvability field: treat every item as claimed impossible")
    args = ap.parse_args()

    items = extract_items(json.loads(Path(args.path).read_text()))
    first = items[0]
    nk = detect(first, NUMBER_KEYS)
    tk = detect(first, TARGET_KEYS)
    sk = detect(first, SOLVABLE_KEYS)
    ik = detect(first, IMPOSSIBLE_KEYS)
    if not nk or not tk:
        raise SystemExit(f"could not detect numbers/target keys in {list(first)}")
    print(f"schema: numbers={nk!r} target={tk!r} "
          f"solvable={sk!r} impossible={ik!r} ({len(items)} items)\n")

    bad = agree_fail = 0
    for idx, it in enumerate(items):
        numbers = list(it[nk])
        target = it[tk]
        if sk is not None:
            claimed_solvable = bool(it[sk])
        elif ik is not None:
            claimed_solvable = not bool(it[ik])
        elif args.assume_impossible:
            claimed_solvable = False
        else:
            raise SystemExit("no solvability field found; pass --assume-impossible "
                             "if every item is claimed impossible")

        t0 = time.time()
        v1 = Fraction(target) in all_values(numbers)          # solver 1
        v2 = Fraction(target) in all_values_dp(numbers)       # solver 2
        dt = time.time() - t0

        label = it.get("id", idx)
        if v1 != v2:
            agree_fail += 1
            print(f"FAIL [{label}] SOLVER DISAGREEMENT on {numbers} -> {target}: "
                  f"recursion={v1} dp={v2}")
            continue
        if v1 != claimed_solvable:
            bad += 1
            witness = find_solution(numbers, target) if v1 else None
            print(f"FAIL [{label}] {numbers} -> {target}: claimed "
                  f"{'solvable' if claimed_solvable else 'IMPOSSIBLE'} but both "
                  f"solvers say {'solvable' if v1 else 'impossible'}"
                  + (f" (witness: {witness})" if witness else ""))
        else:
            status = "impossible over every subset" if not v1 else "solvable"
            print(f"PASS [{label}] {numbers} -> {target}: {status} "
                  f"(both solvers, {dt:.2f}s)")

    print(f"\n{len(items)} items: {len(items) - bad - agree_fail} verified, "
          f"{bad} label errors, {agree_fail} solver disagreements")
    sys.exit(1 if (bad or agree_fail) else 0)


if __name__ == "__main__":
    main()
