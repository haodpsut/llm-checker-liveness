#!/usr/bin/env python3
"""Build g2_verdicts.json FROM THE RAW LOGS in raw/, replacing the hand-transcribed version.

Why this file exists. The earlier `g2_build_verdicts.py` encoded results as RANGE RULES:

    for i in range(19, 64):  strict[f"G2-{i:03d}"] = "FAIL"   # "verbatim from agent"

That encoding makes the claim "all 45 items FAIL" UNVERIFIABLE from the artifact: if the real run
had one deviation inside that span, the rule erased it and nobody could tell. For a paper whose
central claim is "a gate must prove it is still live", that is where an adversarial reviewer aims.

This file enforces the opposite: every verdict must correspond to ONE LINE in a raw/ file, and the
raw file is the checker's verbatim output. No line, no verdict: nothing inferred, filled in, or
rounded.

Fail-closed. It blocks on:
  - a missing ID (the log does not cover the corpus that was sent)
  - a repeated ID carrying two different verdicts
  - an ID that was never sent (the checker invented an identifier)
  - a verdict that is neither PASS nor FAIL
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")

# rig -> raw log file. Change the filename here for a new run; never hand-edit a verdict.
SOURCES = {
    "strict":   "g2-strict-b-20260813.txt",
    "moderate": "g2-moderate-20260813.txt",
    "lenient":  "g2-lenient-20260813.txt",
}

LINE = re.compile(r"^\s*(G2-\d{3})\s*:\s*(PASS|FAIL)\s*$", re.I)


def sent_ids():
    """The IDs actually sent to the checker, read from the prompt file itself."""
    p = os.path.join(HERE, "g2_checker_prompt_strict.txt")
    return [m.group(1) for m in re.finditer(r"^(G2-\d{3}):", open(p).read(), re.M)]


def parse(path, expected):
    out, dup = {}, []
    bad = []
    for ln, line in enumerate(open(path, encoding="utf-8"), 1):
        if not line.strip():
            continue
        m = LINE.match(line)
        if not m:
            bad.append(f"line {ln}: not a verdict line: {line.strip()[:60]!r}")
            continue
        aid, verdict = m.group(1), m.group(2).upper()
        if aid in out and out[aid] != verdict:
            dup.append(f"{aid}: {out[aid]} then {verdict}")
        out[aid] = verdict
    missing = [i for i in expected if i not in out]
    extra = [i for i in out if i not in expected]
    return out, missing, extra, dup, bad


def main():
    expected = sent_ids()
    print(f"g2_parse_raw -- {len(expected)} IDs were sent to the checker (read from the strict prompt)\n")
    verdicts, fatal = {}, []
    for rig, fn in SOURCES.items():
        path = os.path.join(RAW, fn)
        if not os.path.exists(path):
            fatal.append(f"{rig}: MISSING RAW LOG {fn}")
            continue
        v, missing, extra, dup, bad = parse(path, expected)
        n_fail = sum(1 for x in v.values() if x == "FAIL")
        print(f"  {rig:9s} {fn:28s} {len(v)} verdict ({n_fail} FAIL, {len(v)-n_fail} PASS)")
        for label, items in (("MISSING ID", missing), ("UNKNOWN ID", extra),
                             ("CONTRADICTORY DUPLICATE", dup), ("MALFORMED LINE", bad)):
            if items:
                fatal.append(f"{rig}: {label} -> {items[:8]}{' ...' if len(items) > 8 else ''}")
        verdicts[rig] = v

    if fatal:
        print("\nFAIL -- the raw logs are not usable:")
        for f in fatal:
            print("  " + f)
        return 2

    out = os.path.join(HERE, "g2_verdicts.json")
    json.dump(verdicts, open(out, "w"), indent=0, sort_keys=True)
    print(f"\nPASS -- {len(verdicts)} rigs x {len(expected)} IDs; every verdict has a line in raw/.")
    print(f"wrote {os.path.relpath(out, HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
