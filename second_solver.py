"""Second, independent brute-forcer for the maken game -- different algorithm.

maken_tasks.all_values uses multiset-reduction recursion (pick two values,
combine, recurse on the shrunken multiset). This module instead uses a
bottom-up bitmask dynamic program:

    reach[mask] = every value expressible by an expression using EXACTLY
                  the numbers whose bits are set in mask
    reach[{i}] = {numbers[i]}
    reach[mask] = union over proper submask splits (a, mask^a) of
                  combine(reach[a], reach[mask^a])

The answer "reachable over SOME subset" is the union of reach[mask] over all
non-empty masks. Same task rules, disjoint implementation strategy: an
agreement between the two is strong evidence the impossibility labels are
construction-bug-free.
"""

from fractions import Fraction
from functools import reduce


def all_values_dp(numbers):
    """Every Fraction reachable from any non-empty subset of `numbers`."""
    n = len(numbers)
    reach = [set() for _ in range(1 << n)]
    for i, x in enumerate(numbers):
        reach[1 << i] = {Fraction(x)}

    for mask in range(1, 1 << n):
        if mask & (mask - 1) == 0:  # single bit, already seeded
            continue
        acc = reach[mask]
        # enumerate proper submasks; each unordered split visited twice
        # (a, b) and (b, a) -- we add both orders of - and / anyway, so
        # restrict to a < b to halve the work
        a = (mask - 1) & mask
        while a:
            b = mask ^ a
            if a < b:
                for x in reach[a]:
                    for y in reach[b]:
                        acc.add(x + y)
                        acc.add(x - y)
                        acc.add(y - x)
                        acc.add(x * y)
                        if y != 0:
                            acc.add(x / y)
                        if x != 0:
                            acc.add(y / x)
            a = (a - 1) & mask
    return reduce(set.union, (reach[m] for m in range(1, 1 << n)), set())


def is_solvable_dp(numbers, target):
    return Fraction(target) in all_values_dp(numbers)


if __name__ == "__main__":
    # spot checks mirroring maken_tasks.selftest
    assert Fraction(9) in all_values_dp([1, 2, 3])
    assert all_values_dp([1, 1]) == {Fraction(1), Fraction(2), Fraction(0)}
    assert Fraction(7) in all_values_dp([7, 50, 3])
    assert Fraction(3, 7) in all_values_dp([3, 7])
    print("second_solver spot checks passed")
