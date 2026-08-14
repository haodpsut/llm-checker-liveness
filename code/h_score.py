#!/usr/bin/env python3
"""Score corpus H from the raw logs in raw/, broken down by defect CLASS.

Reads `raw/h-<tier>-r<N>-*.txt` in `ID: PASS|FAIL` form and reports:
  - detection on the SEED pool and the HELD-OUT pool, per class
  - false-reject on the 15 clean artifacts
  - the range across runs (min-max); never a single number

Fail-closed: a missing ID, an unknown ID, or zero files all BLOCK.
"""
import glob
import os
import re
import sys
from collections import defaultdict

import h_corpus as H

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
GT = {a["id"]: a["ground_truth"] for a in H.ARTIFACTS}
CLS = {a["id"]: a["defect_class"] for a in H.ARTIFACTS}
SEEDS = {a["id"] for a in H.SEED}
EVALS = {a["id"] for a in H.EVAL}
CLEANS = {a["id"] for a in H.CLEAN}
ALL = set(GT)


def read(path):
    v = {m.group(1): m.group(2) for m in re.finditer(r"^(H-\d{3}):\s*(PASS|FAIL)", open(path).read(), re.M)}
    miss, extra = ALL - set(v), set(v) - ALL
    if miss or extra:
        raise SystemExit(f"BLOCK {os.path.basename(path)}: missing {sorted(miss)[:5]} unknown {sorted(extra)[:5]}")
    return v



# The tier list used to be the literal tuple ("opus", "sonnet", "haiku"), while main() globbed
# every h-*.txt into by_tier. Adding a second model family therefore produced 18 logs that were read
# and then silently dropped, and the printed table still looked complete. Derive the order from the
# data instead, and make an unscored tier an error rather than an omission.
CLAUDE_ORDER = ("opus", "sonnet", "haiku")


def tier_order(by_tier):
    """Claude tiers first for continuity, then any other family, alphabetically."""
    known = [t for t in CLAUDE_ORDER if t in by_tier]
    other = sorted(t for t in by_tier if t not in CLAUDE_ORDER)
    return known + other


def write_csv(by_tier):
    """Emit CSVs so claims.json can anchor to them. Every cell carries mean/min/max/n_runs."""
    import csv
    TBL = os.path.join(HERE, "..", "paper", "tables")
    rows = []
    scored = []
    for tier in tier_order(by_tier):
        fs = by_tier.get(tier, [])
        if not fs:
            continue
        scored.append(tier)
        vs = [read(f) for f in fs]
        mets = {
            "seed_detect":  lambda v: sum(1 for i in SEEDS if v[i] == "FAIL") / len(SEEDS),
            "held_detect":  lambda v: sum(1 for i in EVALS if v[i] == "FAIL") / len(EVALS),
            "false_reject": lambda v: sum(1 for i in CLEANS if v[i] == "FAIL") / len(CLEANS),
        }
        for m, fn in mets.items():
            xs = [fn(v) for v in vs]
            rows.append([tier, m, f"{sum(xs)/len(xs):.4f}", f"{min(xs):.4f}", f"{max(xs):.4f}", len(xs)])
        for cls in H.H_CLASSES:
            ids = [i for i in EVALS if CLS[i] == cls]
            xs = [sum(1 for i in ids if v[i] == "FAIL") / len(ids) for v in vs]
            rows.append([tier, "class:" + cls, f"{sum(xs)/len(xs):.4f}",
                         f"{min(xs):.4f}", f"{max(xs):.4f}", len(xs)])
    with open(os.path.join(TBL, "hard-corpus.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tier", "metric", "mean", "min", "max", "n_runs"])
        w.writerows(rows)
    print(f"\n  wrote hard-corpus.csv: {len(rows)} rows")

    # the MOVING blind spot: the most-missed class in each run of the cheap tier
    shift = []
    for f in sorted(by_tier.get("haiku", [])):
        v = read(f)
        missed = [i for i in EVALS | SEEDS if GT[i] == "FAIL" and v[i] == "PASS"]
        from collections import Counter
        c = Counter(CLS[i] for i in missed)
        top = c.most_common(1)[0][0] if c else "none"
        shift.append([os.path.basename(f), len(missed), top,
                      sum(1 for i in CLEANS if v[i] == "FAIL")])
    with open(os.path.join(TBL, "hard-blindspot-shift.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "n_missed", "dominant_missed_class", "n_false_reject"])
        w.writerows(shift)
    print(f"  wrote hard-blindspot-shift.csv: {len(shift)} rows")

    # Cross-family cells. The point of emitting EVERY (checker, class, run) cell rather than a mean
    # is that the finding is about the SHAPE of the failure: cells sit at exactly 0 or exactly 1 far
    # more often than a per-instance error model predicts, and a mean of 0.6 describes a state that
    # never occurred. `extremal` marks the cells that are exactly 0 or exactly 1.
    cells = []
    for tier in tier_order(by_tier):
        for ri, f in enumerate(sorted(by_tier[tier]), 1):
            v = read(f)
            for cls in H.H_CLASSES:
                ids = [i for i in EVALS if CLS[i] == cls]
                if not ids:
                    continue
                r = sum(1 for i in ids if v[i] == "FAIL") / len(ids)
                cells.append([tier, cls, ri, len(ids), f"{r:.4f}",
                              "yes" if r in (0.0, 1.0) else "no"])
    with open(os.path.join(TBL, "hard-crossfamily.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["checker", "defect_class", "run", "n_in_class", "detect", "extremal"])
        w.writerows(cells)
    ext = sum(1 for c in cells if c[5] == "yes")
    print(f"  wrote hard-crossfamily.csv: {len(cells)} cells, {ext} extremal "
          f"({100.0 * ext / len(cells):.1f}%)")
    return scored

def main():
    files = sorted(glob.glob(os.path.join(RAW, "h-*.txt")))
    if not files:
        print("BLOCK: 0 log files for corpus H. Empty is broken, not clean.")
        return 2
    by_tier = defaultdict(list)
    for f in files:
        by_tier[os.path.basename(f).split("-")[1]].append(f)

    print(f"h_score -- {len(files)} runs, {len(H.ARTIFACTS)} artifacts "
          f"({len(SEEDS)} seed, {len(EVALS)} held-out, {len(CLEANS)} clean)\n")
    print(f"{'tier':8s} {'n':>2s} {'seed-det':>18s} {'held-det':>18s} {'false-reject':>18s}")
    for tier in tier_order(by_tier):
        fs = by_tier.get(tier, [])
        if not fs:
            continue
        vs = [read(f) for f in fs]
        def rng_(fn):
            xs = [fn(v) for v in vs]
            return f"{min(xs):.2f}" if min(xs) == max(xs) else f"{min(xs):.2f}-{max(xs):.2f}"
        sd = lambda v: sum(1 for i in SEEDS if v[i] == "FAIL") / len(SEEDS)
        hd = lambda v: sum(1 for i in EVALS if v[i] == "FAIL") / len(EVALS)
        fr = lambda v: sum(1 for i in CLEANS if v[i] == "FAIL") / len(CLEANS)
        print(f"{tier:8s} {len(fs):2d} {rng_(sd):>18s} {rng_(hd):>18s} {rng_(fr):>18s}")

    order = tier_order(by_tier)
    print(f"\n{'defect class':30s} " + " ".join(f"{t:>16s}" for t in order))
    for cls in H.H_CLASSES:
        ids = [i for i in EVALS if CLS[i] == cls]
        row = []
        for tier in order:
            fs = by_tier.get(tier, [])
            if not fs:
                row.append("--"); continue
            xs = [sum(1 for i in ids if read(f)[i] == "FAIL") / len(ids) for f in fs]
            row.append(f"{min(xs):.2f}" if min(xs) == max(xs) else f"{min(xs):.2f}-{max(xs):.2f}")
        print(f"{cls:30s} " + " ".join(f"{x:>16s}" for x in row))
    scored = write_csv(by_tier)
    missed = sorted(set(by_tier) - set(scored))
    if missed:
        print(f"\nBLOCK: {len(missed)} tier(s) present in raw/ but never scored: "
              f"{', '.join(missed)}. A log that is read and then dropped is worse than a log that "
              f"is absent, because the table still looks complete.")
        return 2
    print(f"\n  scored {len(scored)} tier(s) over {len(files)} runs: {', '.join(scored)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
