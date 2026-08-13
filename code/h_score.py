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



def write_csv(by_tier):
    """Emit CSVs so claims.json can anchor to them. Every cell carries mean/min/max/n_runs."""
    import csv
    TBL = os.path.join(HERE, "..", "paper", "tables")
    rows = []
    for tier in ("opus", "sonnet", "haiku"):
        fs = by_tier.get(tier, [])
        if not fs:
            continue
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
    for tier in ("opus", "sonnet", "haiku"):
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

    print(f"\n{'defect class':30s} " + " ".join(f"{t:>16s}" for t in ("opus", "sonnet", "haiku")))
    for cls in H.H_CLASSES:
        ids = [i for i in EVALS if CLS[i] == cls]
        row = []
        for tier in ("opus", "sonnet", "haiku"):
            fs = by_tier.get(tier, [])
            if not fs:
                row.append("--"); continue
            xs = [sum(1 for i in ids if read(f)[i] == "FAIL") / len(ids) for f in fs]
            row.append(f"{min(xs):.2f}" if min(xs) == max(xs) else f"{min(xs):.2f}-{max(xs):.2f}")
        print(f"{cls:30s} " + " ".join(f"{x:>16s}" for x in row))
    write_csv(by_tier)
    return 0


if __name__ == "__main__":
    sys.exit(main())
