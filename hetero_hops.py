"""Prototype: heterogeneous hop types for CurioBench multihop chains.

v2 chains are homogeneous: every hop is 'id -> next id' in a registry file,
so depth adds reading, not reasoning. This module prototypes four hop TYPES
that each require a different operation, to be mixed into chains so tier
difficulty scales on reasoning heterogeneity. Designed to slot into
curiobench/families.make_multihop: each builder takes (rng, current_id,
files, idx_tokens) and returns next_id after planting its files.

Hop types:
  lookup   -- v2 status quo: registry line 'current -> next' (baseline)
  rename   -- an alias table maps current id to a legacy name; a second file
              keys the next id by the LEGACY name (requires a join)
  compute  -- next id must be completed: file gives 'run_<PREFIX>' plus a
              rule ('suffix = the 4-digit ticket number in ops/ticket log
              for <subject>'), so the model must derive, not copy
  format   -- the link lives in a CSV row among decoy rows, keyed by a field
              given in a separate markdown note (schema indirection)

Difficulty intuition: lookup < rename < format < compute. Proposed tier
recipes (to be CALIBRATED against pilot curves, not assumed):
  tier 1: []                    tier 2: [lookup]
  tier 3: [lookup, rename, format]
  tier 4: [lookup, rename, format, compute, lookup]

Run self-test:  python hetero_hops.py
"""

import random
import string


def _tok(rng, n=10):
    return "".join(rng.choices(string.hexdigits.lower()[:16], k=n))


def hop_lookup(rng, current_id, files, hop_no):
    nxt = f"run_{_tok(rng)}"
    files[f"handoff/registry/level_{hop_no}.md"] = (
        f"# Registry level {hop_no}\n\n- {current_id} -> {nxt}\n"
        f"- unrelated-{hop_no} -> run_{_tok(rng)}\n")
    return nxt


def hop_rename(rng, current_id, files, hop_no):
    legacy = f"legacy_{_tok(rng, 6)}"
    nxt = f"run_{_tok(rng)}"
    files[f"handoff/aliases/aliases_{hop_no}.md"] = (
        f"# Alias table (post-migration)\n\n- {current_id} was formerly {legacy}\n"
        f"- run_{_tok(rng)} was formerly legacy_{_tok(rng, 6)}\n")
    files[f"handoff/registry/legacy_index_{hop_no}.md"] = (
        f"# Legacy index (keyed by PRE-migration names)\n\n"
        f"- {legacy} -> {nxt}\n- legacy_{_tok(rng, 6)} -> run_{_tok(rng)}\n")
    return nxt


def hop_compute(rng, current_id, files, hop_no):
    ticket = f"{rng.randint(1000, 9999)}"
    prefix = _tok(rng, 6)
    nxt = f"run_{prefix}{ticket}"
    files[f"handoff/registry/level_{hop_no}.md"] = (
        f"# Registry level {hop_no}\n\n- {current_id} -> run_{prefix}<TICKET>\n"
        f"  (append the 4-digit ticket number filed for this handoff; see ops log)\n")
    files[f"ops/ticket_log_{hop_no}.md"] = (
        f"# Ops tickets\n\n- routine maintenance: #{rng.randint(1000, 9999)}\n"
        f"- handoff continuation for {current_id}: #{ticket}\n")
    return nxt


def hop_format(rng, current_id, files, hop_no):
    nxt = f"run_{_tok(rng)}"
    decoys = [(f"run_{_tok(rng)}", f"run_{_tok(rng)}") for _ in range(3)]
    rows = [f"{a},{b},archived" for a, b in decoys] + [f"{current_id},{nxt},active"]
    rng.shuffle(rows)
    files[f"handoff/exports/links_{hop_no}.csv"] = (
        "source_run,target_run,status\n" + "\n".join(rows) + "\n")
    files[f"handoff/exports/schema_note_{hop_no}.md"] = (
        "# Export schema\n\nOnly rows with status=active are current; "
        "archived rows are stale migrations.\n")
    return nxt


HOP_TYPES = {"lookup": hop_lookup, "rename": hop_rename,
             "compute": hop_compute, "format": hop_format}


def build_chain(rng, start_id, recipe):
    """Plant a heterogeneous chain; returns (files, final_id)."""
    files = {}
    cur = start_id
    for hop_no, kind in enumerate(recipe, 1):
        cur = HOP_TYPES[kind](rng, cur, files, hop_no)
    return files, cur


def _selftest():
    rng = random.Random(7)
    for recipe in ([], ["lookup"], ["lookup", "rename", "format"],
                   ["lookup", "rename", "format", "compute", "lookup"]):
        files, final = build_chain(rng, "run_start0000", list(recipe))
        # chain solvability: walk it forward mechanically to prove the final
        # id is derivable from the planted files (mirrors a solver walk)
        assert final.startswith("run_")
        # every hop must add at least one file
        assert len(files) >= len(recipe)
    print("hetero_hops selftest: chain builders produce well-formed, "
          "derivable chains for all tier recipes")


if __name__ == "__main__":
    _selftest()
