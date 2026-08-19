"""Task generator + exhaustive solver for the 'maken' arithmetic game.

Rules of the game (written independently from the task rules alone):
  Given a list of integers, use SOME of them -- each at most once --
  combined with binary + - * / (exact rational arithmetic, parentheses
  allowed) to produce an expression equal to the target.

Impossibility is proven by exhaustive enumeration: `all_values` generates
every value reachable by ANY expression over ANY non-empty subset of the
numbers. If the target is not in that set, no expression exists, period.

Usage:
  python maken_tasks.py            # generate items/items.json (seeded)
  python maken_tasks.py --selftest # sanity checks on the solver
"""

import argparse
import json
import random
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).parent
N_NUMBERS = 5
TARGET_LO, TARGET_HI = 100, 999


def all_values(numbers):
    """Every Fraction reachable from any non-empty subset of `numbers`.

    State = multiset of available values. At each step, remove two values,
    combine them with one op, put the result back. Every intermediate value
    is itself an expression over some subset, so we record all of them.
    Memoized on the sorted state tuple.
    """
    seen_states = set()
    values = set()

    def rec(state):
        if state in seen_states:
            return
        seen_states.add(state)
        n = len(state)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = state[i], state[j]
                rest = state[:i] + state[i + 1:j] + state[j + 1:]
                results = {a + b, a - b, b - a, a * b}
                if b != 0:
                    results.add(a / b)
                if a != 0:
                    results.add(b / a)
                for r in results:
                    values.add(r)
                    rec(tuple(sorted(rest + (r,))))

    init = tuple(sorted(Fraction(x) for x in numbers))
    values.update(init)  # a bare given number is a subset-of-size-1 expression
    rec(init)
    return values


def find_solution(numbers, target):
    """Return one witness expression string hitting `target`, or None."""
    t = Fraction(target)

    def rec(items):
        for v, e in items:
            if v == t:
                return e
        n = len(items)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                (a, ea), (b, eb) = items[i], items[j]
                rest = tuple(items[k] for k in range(n) if k not in (i, j))
                cands = [
                    (a + b, f"({ea}+{eb})"),
                    (a - b, f"({ea}-{eb})"),
                    (a * b, f"({ea}*{eb})"),
                ]
                if b != 0:
                    cands.append((a / b, f"({ea}/{eb})"))
                for c in cands:
                    r = rec(rest + (c,))
                    if r:
                        return r
        return None

    return rec(tuple((Fraction(x), str(x)) for x in numbers))


def integer_targets(values):
    return {int(v) for v in values
            if v.denominator == 1 and TARGET_LO <= v <= TARGET_HI}


def generate_items(n_solvable=20, n_impossible=20, seed=42):
    rng = random.Random(seed)
    items = []
    iid = 0
    while sum(1 for it in items if it["solvable"]) < n_solvable or \
          sum(1 for it in items if not it["solvable"]) < n_impossible:
        numbers = sorted(rng.choices(range(1, 26), k=N_NUMBERS))
        reachable = integer_targets(all_values(numbers))
        if not reachable:
            continue
        need_solvable = sum(1 for it in items if it["solvable"]) < n_solvable
        need_impossible = sum(1 for it in items if not it["solvable"]) < n_impossible

        if need_solvable:
            target = rng.choice(sorted(reachable))
            witness = find_solution(numbers, target)
            assert witness is not None, f"solver contradiction on {numbers} -> {target}"
            items.append({"id": f"S{iid:02d}", "numbers": numbers, "target": target,
                          "solvable": True, "witness": witness})
            iid += 1

        if need_impossible:
            # near-miss targets: unreachable but within 2 of something reachable,
            # so the item looks temptingly solvable
            gaps = [t for t in range(TARGET_LO, TARGET_HI + 1)
                    if t not in reachable
                    and any(abs(t - r) <= 2 for r in reachable)]
            if gaps:
                target = rng.choice(gaps)
                assert find_solution(numbers, target) is None, \
                    f"solver contradiction on {numbers} -> {target}"
                items.append({"id": f"I{iid:02d}", "numbers": numbers, "target": target,
                              "solvable": False, "witness": None})
                iid += 1
    return items


def selftest():
    # 1. a known-solvable case: 1,2,3 -> 9 = (1+2)*3
    vals = all_values([1, 2, 3])
    assert Fraction(9) in vals
    assert find_solution([1, 2, 3], 9) is not None
    # 2. a known-impossible case: 1,1 can reach only 1, 2, 0 -> 5 unreachable
    vals = all_values([1, 1])
    assert vals == {Fraction(1), Fraction(2), Fraction(0)}, vals
    assert find_solution([1, 1], 5) is None
    # 3. subset rule: 7,50,3 -> 7 reachable as a bare number
    assert Fraction(7) in all_values([7, 50, 3])
    # 4. division produces fractions: 3,7 -> 3/7 reachable
    assert Fraction(3, 7) in all_values([3, 7])
    # 5. cross-check: for 200 random (numbers, target) pairs, find_solution
    #    and all_values must agree on solvability
    rng = random.Random(0)
    for _ in range(200):
        numbers = sorted(rng.choices(range(1, 26), k=4))
        target = rng.randint(TARGET_LO, TARGET_HI)
        by_values = Fraction(target) in all_values(numbers)
        by_search = find_solution(numbers, target) is not None
        assert by_values == by_search, (numbers, target)
    print("selftest: all solver checks passed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    items = generate_items(seed=args.seed)
    out = HERE / "items"
    out.mkdir(exist_ok=True)
    path = out / "items.json"
    path.write_text(json.dumps(items, indent=2))
    n_solv = sum(1 for it in items if it["solvable"])
    print(f"wrote {len(items)} items ({n_solv} solvable, "
          f"{len(items) - n_solv} impossible) to {path}")


if __name__ == "__main__":
    main()
