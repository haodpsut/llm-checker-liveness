#!/usr/bin/env python3
"""Build a raw log file from a checker's compact `FAIL: <id>, <id>, ...` reply.

Why the compact form exists. From run 42 onward the checker was asked to return THE LIST OF FAILED
IDs instead of 69 `ID: PASS|FAIL` lines. The ID set is FIXED and is read from the prompt file, so
both forms carry the SAME information: any ID absent from the FAIL list is a PASS. The change
reduces transfer volume, not content.

THE COST, recorded so it is not forgotten: if the checker OMITS an ID (says neither PASS nor FAIL),
the full form exposes it immediately as a missing line, whereas the compact form silently treats it
as PASS. This script therefore BLOCKS on an unknown or repeated ID, and prints how many IDs were
inferred to be PASS so the inference is never invisible.

Usage:
    python3 _from_faillist.py <output-file> "FAIL: G2-019, G2-020, ..."
    python3 _from_faillist.py <output-file> "FAIL: none"
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPT = os.path.join(HERE, "..", "g2_checker_prompt_strict.txt")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    name, payload = sys.argv[1], " ".join(sys.argv[2:])
    order = [m.group(1) for m in re.finditer(r"^(G2-\d{3}):", open(PROMPT).read(), re.M)]
    body = payload.split("FAIL:", 1)[1] if "FAIL:" in payload else payload
    fails = [] if body.strip().lower() == "none" else re.findall(r"G2-\d{3}", body)

    unknown = [f for f in fails if f not in order]
    if unknown:
        print("BLOCK: the FAIL list contains IDs that were never in the prompt: %s" % unknown)
        return 2
    dup = len(fails) - len(set(fails))
    if dup:
        print("BLOCK: the FAIL list repeats %d ID(s)" % dup)
        return 2

    fs = set(fails)
    with open(os.path.join(HERE, name), "w") as f:
        for i in order:
            f.write("%s: %s\n" % (i, "FAIL" if i in fs else "PASS"))
    print("%s: %d declared FAIL, %d inferred PASS, %d total"
          % (name, len(fs), len(order) - len(fs), len(order)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
