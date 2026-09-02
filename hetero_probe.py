"""Headroom probe: do heterogeneous hops create difficulty that identical
lookups don't, for a frontier model?

Generates N paired mini-workspaces sharing seed and decoy structure:
  arm A (v2-style): chain of 5 identical lookup hops   (tier-4 status quo)
  arm B (hetero)  : [lookup, rename, format, compute, lookup]
Each workspace has 3 decoy bundles (complete fragment triples wired to
dead-end chains) so grep-bypass fails, mirroring Roozi's v2 fix. Runs a
model on both arms (text mode, workspace inlined) and scores exact match.

Usage: python hetero_probe.py --model anthropic/claude-sonnet-5 --n 10
"""

import argparse
import json
import random
import string
import time
from pathlib import Path

import requests

from hetero_hops import build_chain, HOP_TYPES, _tok

HERE = Path(__file__).parent
API_URL = "https://openrouter.ai/api/v1/chat/completions"


def add_bundle(rng, files, bundle_id):
    parts = ["".join(rng.choices(string.hexdigits.upper()[:16], k=6))
             for _ in range(3)]
    safe = bundle_id.replace(":", "_")
    frag_paths = [f"handoff/fragments/{safe}_part_{p}.txt" for p in "abc"]
    files[f"handoff/bundles/{safe}.md"] = (
        f"# Handoff bundle manifest\n\nBundle: {bundle_id}\n"
        "Assembly: join fragments A, B, and C with hyphens.\n"
        + "\n".join(f"- fragment {l}: {p}" for l, p in zip("ABC", frag_paths)))
    for label, path, part in zip("ABC", frag_paths, parts):
        files[path] = f"Fragment {label}: {part}\n"
    return "-".join(parts)


def make_task(seed, recipe):
    rng = random.Random(seed)
    subject = f"Q{rng.randint(1,4)} 2026 billings to {rng.choice(['Nordwind Labs','Bluecrest Media','Halcyon Corp','Veltro Systems'])}"
    start = f"run_{_tok(rng)}"
    files = {"handoff/request_index.md":
             f"# Current handoff requests\n\n- {subject} -> {start}\n"
             f"- unrelated maintenance request -> run_{_tok(rng)}\n"}
    chain_files, final_id = build_chain(rng, start, recipe)
    files.update(chain_files)
    answer = add_bundle(rng, files, final_id)
    # 3 decoy bundles on dead-end chains (mirror the v2 fix)
    for d in range(3):
        decoy_start = f"run_{_tok(rng)}"
        dfiles, decoy_final = build_chain(rng, decoy_start, ["lookup"])
        for path, content in dfiles.items():
            files.setdefault(f"decoys/{d}/{path}", content)
        add_bundle(rng, files, decoy_final)
    # filler noise
    for i in range(rng.randint(6, 10)):
        files[f"notes/note_{seed}_{i}.md"] = f"# Note {i}\n\nRoutine, nothing blocking.\n"
    prompt = (
        f"You are assisting with a handoff workspace.\n\nTask: For the request "
        f"'{subject}', follow the handoff chain from handoff/request_index.md to "
        f"the correct bundle and assemble its final code (join fragments A, B, C "
        f"with hyphens). Several complete bundles exist; only the chain identifies "
        f"the right one.\n\nReply with the final line exactly:\nANSWER: <code>\n\n"
        f"=== WORKSPACE FILES ===\n"
        + "".join(f"\n--- {p} ---\n{files[p]}" for p in sorted(files)))
    return prompt, answer


def call(key, model, prompt):
    for attempt in range(4):
        try:
            r = requests.post(API_URL, json={
                "model": model, "temperature": 0.0, "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}]},
                headers={"Authorization": f"Bearer {key}"}, timeout=180)
            if r.status_code in (429, 500, 502, 503):
                time.sleep(2 ** attempt * 2)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"].get("content") or ""
        except requests.RequestException:
            time.sleep(2 ** attempt * 2)
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="anthropic/claude-sonnet-5")
    ap.add_argument("--n", type=int, default=10)
    args = ap.parse_args()
    key = (HERE / "openrouter_key.txt").read_text().strip()

    arms = {"A_lookup_x5": ["lookup"] * 5,
            "B_hetero": ["lookup", "rename", "format", "compute", "lookup"]}
    results = {}
    detail = []
    for arm, recipe in arms.items():
        ok = 0
        for i in range(args.n):
            prompt, answer = make_task(1000 + i, recipe)
            reply = call(key, args.model, prompt)
            got = ""
            for line in reversed([l.strip() for l in reply.splitlines() if l.strip()]):
                if line.upper().startswith("ANSWER"):
                    got = line.split(":", 1)[-1].strip().strip("`* ")
                    break
            hit = got.upper() == answer.upper()
            ok += hit
            detail.append({"arm": arm, "seed": 1000 + i, "expect": answer,
                           "got": got, "correct": hit})
            print(f"[{arm} {i+1}/{args.n}] {'OK' if hit else 'MISS'} "
                  f"(expect {answer}, got {got or '<none>'})", flush=True)
        results[arm] = ok / args.n
    print(f"\n{args.model}: lookup-x5 {results['A_lookup_x5']:.0%} vs "
          f"hetero {results['B_hetero']:.0%} (n={args.n} each)")
    out = HERE / "results" / "hetero_probe.json"
    out.write_text(json.dumps({"model": args.model, "results": results,
                               "detail": detail}, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
