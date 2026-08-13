#!/usr/bin/env python3
"""Write a raw log file from an OBSERVED verdict pattern, instead of hand-typing each one.

WARNING. This file does NOT generate data. It is only a shorthand for recording a result that a
real agent run actually produced. If an agent's output does not match one of these patterns exactly,
that file MUST be written out by hand; it must never be forced into the nearest pattern.

Usage:
    python3 _write_raw.py <file> <pattern> [clean-ids-that-were-false-rejected ...]

Patterns:
    all-fail-cite-fail : 45 judgment defects FAIL + 6 citations FAIL  (strong checker)
    all-fail-cite-pass : 45 judgment defects FAIL + 6 citations PASS  (judgment-capable, citation-blind)
    scope-only         : only the 9 scope-gap items FAIL, rest PASS  (very weak checker)
Any extra clean IDs listed are written as FAIL (false-rejects).
"""
import sys, os

JUDGE = """G2-019 G2-020 G2-021 G2-028 G2-029 G2-030 G2-037 G2-038 G2-039 G2-046 G2-047 G2-048
G2-055 G2-056 G2-057 G2-022 G2-023 G2-024 G2-025 G2-026 G2-027 G2-031 G2-032 G2-033 G2-034
G2-035 G2-036 G2-040 G2-041 G2-042 G2-043 G2-044 G2-045 G2-049 G2-050 G2-051 G2-052 G2-053
G2-054 G2-058 G2-059 G2-060 G2-061 G2-062 G2-063""".split()
CITE = "G2-067 G2-068 G2-069 G2-070 G2-071 G2-072".split()
CLEAN = [f"G2-{i:03d}" for i in range(1, 19)]
ORDER = JUDGE + CITE + CLEAN
SCOPE = "G2-046 G2-047 G2-048 G2-049 G2-050 G2-051 G2-052 G2-053 G2-054".split()

PATTERNS = {
    "all-fail-cite-fail": (JUDGE, CITE),
    "all-fail-cite-pass": (JUDGE, []),
    "scope-only":         (SCOPE, []),
}


def main():
    if len(sys.argv) < 3 or sys.argv[2] not in PATTERNS:
        print(__doc__)
        return 2
    name, pat, fr = sys.argv[1], sys.argv[2], set(sys.argv[3:])
    fails = set(PATTERNS[pat][0]) | set(PATTERNS[pat][1]) | fr
    bad = fr - set(CLEAN)
    if bad:
        print(f"ERROR: {sorted(bad)} are not clean artifacts, so they cannot be false-rejects")
        return 2
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    with open(path, "w") as f:
        for i in ORDER:
            f.write(f"{i}: {'FAIL' if i in fails else 'PASS'}\n")
    nf = sum(1 for i in ORDER if i in fails)
    print(f"{name}: {len(ORDER)} verdicts, {nf} FAIL, false-rejects on clean: {len(fr)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
