"""CurioBench-1K runner: single-turn text-only mode via OpenRouter.

Implements 'Option B -- bring your own harness' from the dataset card:
present prompt + environment.files (inlined), collect the three-line
protocol reply, write a resume-safe run log for deterministic scoring.

Usage:
  python curiobench_runner.py --model openai/gpt-4o-mini --split dev
"""

import argparse
import json
import time
from pathlib import Path

import requests

HERE = Path(__file__).parent
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_NEW_TOKENS = 2048


def load_key():
    import os
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    f = HERE / "openrouter_key.txt"
    if f.exists():
        return f.read_text().strip()
    raise SystemExit("no OpenRouter key")


def build_prompt(task):
    files = task["environment"]["files"]
    parts = [task["prompt"], "\n\n=== WORKSPACE FILES ===\n"]
    for path in sorted(files):
        parts.append(f"\n--- {path} ---\n{files[path]}")
    return "".join(parts)


def call_model(key, model, prompt, retries=4):
    payload = {"model": model,
               "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.0, "max_tokens": MAX_NEW_TOKENS}
    for attempt in range(retries):
        try:
            r = requests.post(API_URL, json=payload, timeout=180,
                              headers={"Authorization": f"Bearer {key}",
                                       "X-Title": "curiobench-run"})
            if r.status_code in (429, 500, 502, 503):
                time.sleep(2 ** attempt * 2)
                continue
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                raise RuntimeError(data["error"])
            c = data["choices"][0]
            return (c["message"].get("content") or "",
                    c.get("finish_reason"), data.get("usage", {}))
        except (requests.RequestException, RuntimeError) as e:
            if attempt == retries - 1:
                return None, f"error: {e}", {}
            time.sleep(2 ** attempt * 2)
    return None, "error: retries exhausted", {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    key = load_key()
    tasks = [json.loads(l) for l in
             (HERE / "curiobench_data" / f"{args.split}.jsonl").open(encoding="utf-8")]
    if args.limit:
        tasks = tasks[:args.limit]

    outdir = HERE / "results" / "curiobench"
    outdir.mkdir(parents=True, exist_ok=True)
    slug = args.model.replace("/", "_")
    out = outdir / f"cb_{slug}__{args.split}.jsonl"

    done = set()
    if out.exists():
        done = {json.loads(l)["task_id"] for l in out.open(encoding="utf-8")}
        print(f"resuming: {len(done)} already recorded")

    with out.open("a", encoding="utf-8") as fh:
        for i, task in enumerate(tasks):
            if task["task_id"] in done:
                continue
            reply, finish, usage = call_model(key, args.model, build_prompt(task))
            rec = {"task_id": task["task_id"], "model": args.model,
                   "reply": reply, "finish_reason": finish, "usage": usage}
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            err = f"  <<< {finish}" if reply is None else ""
            print(f"[{i + 1}/{len(tasks)}] {task['task_id']}{err}", flush=True)
    print("done ->", out)


if __name__ == "__main__":
    main()
