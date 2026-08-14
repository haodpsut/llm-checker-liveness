#!/usr/bin/env python3
"""Run the hard-corpus checker on a NON-Claude model family, and log it exactly like the others.

WHY THIS EXISTS. The study's sharpest limitation is not the number of runs; it is that all three
checker tiers come from ONE model family. For a claim about "LLM checkers" that is n=1 family, and
no additional run of a Claude tier can fix it. A single second family turns "three tiers of one
model" into a genuine cross-family comparison, which is the one thing multi-checker agreement
assumes and we never tested.

WHAT IT DOES NOT CHANGE. The prompt is read VERBATIM from h_neutral_prompt.txt, the same bytes the
Claude tiers were given, including the artifact order. If this script built its own prompt, any
difference in detection would be confounded with a difference in wording, and the comparison would
be worthless. It also writes into raw/ in the same `H-001: PASS` line format, so every downstream
script consumes it without special-casing.

WHAT IT FIXES. The Claude runs went through a launch interface with no sampling parameters, so
temperature was never recorded and is reported as unknown. Here we control the call, so temperature
is set explicitly and written into the log header. That makes this arm the one place where the
bimodality question can be asked properly: run the SAME prompt at temperature 0 and at temperature
1, and see whether the two-attractor behaviour is a property of the model or an artefact of
sampling. Neither answer is bad for the paper, but only one of them is currently assumed.

Usage:
    export GEMINI_API_KEY=...            # never passed on the command line, never logged
    python3 run_gemini_checker.py --list                     # what models the key can actually use
    python3 run_gemini_checker.py --model gemini-2.0-flash --runs 10 --temperature 0.0
    python3 run_gemini_checker.py --model gemini-2.0-flash --runs 10 --temperature 1.0

Exit 0 only if every requested run produced a complete, parseable verdict set.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

import h_corpus as H

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
PROMPT = os.path.join(HERE, "h_neutral_prompt.txt")
BASE = "https://generativelanguage.googleapis.com/v1beta"
WANTED = {a["id"] for a in H.ARTIFACTS}


def key():
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if not k:
        raise SystemExit("BLOCK: set GEMINI_API_KEY in the environment. It is never taken as an "
                         "argument, so it cannot end up in shell history or in a log.")
    return k


def call(url, payload=None, timeout=180):
    req = urllib.request.Request(
        url, headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode() if payload is not None else None)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def list_models():
    d = call(f"{BASE}/models?key={key()}")
    rows = []
    for m in d.get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            rows.append((m["name"].split("/")[-1], m.get("version", "?"),
                         m.get("displayName", "")))
    for name, ver, disp in sorted(rows):
        print(f"  {name:38s} version={ver:12s} {disp}")
    print(f"\n  {len(rows)} model(s) this key can call with generateContent.")
    return 0


def one_run(model, temperature, prompt, attempt_budget=5):
    """One checker run = one call, because the prompt already holds every artifact."""
    payload = {"contents": [{"parts": [{"text": prompt}]}],
               "generationConfig": {"temperature": temperature}}
    delay = 5
    for attempt in range(attempt_budget):
        try:
            d = call(f"{BASE}/models/{model}:generateContent?key={key()}", payload)
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            if e.code in (429, 500, 503) and attempt < attempt_budget - 1:
                print(f"      HTTP {e.code}, retry in {delay}s")
                time.sleep(delay)
                delay *= 2
                continue
            raise SystemExit(f"BLOCK: HTTP {e.code} from the API: {body}")
    else:
        raise SystemExit("BLOCK: exhausted retries")

    cands = d.get("candidates") or []
    if not cands:
        raise SystemExit(f"BLOCK: no candidate returned. Possibly a safety block: "
                         f"{json.dumps(d)[:300]}")
    parts = cands[0].get("content", {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts)
    verdicts = dict(re.findall(r"^\s*(H-\d{3})\s*:\s*(PASS|FAIL)\s*$", text, re.M))

    # Fail closed. A partial answer silently becomes a partial measurement otherwise, and the
    # missing rows would look like agreement with whatever the other checkers said.
    missing = sorted(WANTED - set(verdicts))
    extra = sorted(set(verdicts) - WANTED)
    if missing or extra:
        raise SystemExit(f"BLOCK: verdict set does not match the corpus. "
                         f"missing={missing[:6]} extra={extra[:6]} "
                         f"(got {len(verdicts)} of {len(WANTED)})")
    return verdicts, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="show callable models and exit")
    ap.add_argument("--model", default="gemini-2.0-flash")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--date", default=time.strftime("%Y%m%d"))
    ap.add_argument("--sleep", type=float, default=4.0, help="pause between runs, for free tiers")
    ap.add_argument("--tier", required=True,
                    help="short tier label used in the filename, e.g. gflite / gflash / gpro. "
                         "Required: without it two different models write the same filenames and "
                         "the second silently overwrites the first.")
    a = ap.parse_args()

    if a.list:
        return list_models()

    prompt = open(PROMPT, encoding="utf-8").read()
    if not prompt.strip():
        raise SystemExit(f"BLOCK: {PROMPT} is empty.")
    # The tag records the sampling setting, because a run at temperature 0 and a run at temperature
    # 1 are NOT repetitions of the same condition and must never be pooled by a later script.
    tag = f"{a.tier}T{str(a.temperature).replace('.', '')}"
    print(f"model={a.model} temperature={a.temperature} runs={a.runs} tag={tag}")
    print(f"prompt: {os.path.basename(PROMPT)}, {len(prompt)} bytes, VERBATIM (same bytes the "
          f"Claude tiers were given)\n")

    written = []
    for i in range(1, a.runs + 1):
        verdicts, _text = one_run(a.model, a.temperature, prompt)
        n_fail = sum(1 for v in verdicts.values() if v == "FAIL")
        path = os.path.join(RAW, f"h-{tag}-r{i}-{a.date}.txt")
        with open(path, "w", encoding="utf-8") as f:
            # A header the downstream parser ignores (it matches only `H-\d{3}:` lines) but a reader
            # does not. This is the provenance the Claude arms could not record.
            f.write(f"# model={a.model} temperature={a.temperature} date={a.date} run={i}\n")
            f.write(f"# prompt={os.path.basename(PROMPT)} sha_len={len(prompt)}\n")
            for k in sorted(verdicts):
                f.write(f"{k}: {verdicts[k]}\n")
        written.append(os.path.basename(path))
        print(f"  run {i}: {n_fail} FAIL of {len(verdicts)} -> {os.path.basename(path)}")
        if i < a.runs:
            time.sleep(a.sleep)

    print(f"\n{len(written)} run(s) written to raw/. Next: python3 h_score.py && "
          f"python3 h_matrix.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
