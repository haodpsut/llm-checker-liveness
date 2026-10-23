#!/usr/bin/env python3
"""Count, per ablation, the cells in which it differs from ATTEST. Emits ablation-nulls.csv.

WHY THIS EXISTS. Ca 23/10/2026. The abstract claimed that removing honest-negative blocking left
"all 18 measured cells unchanged" and that a single checker "never raised false-pass in any cell".
Neither number had a home: `claims.json` had no entry for either, no CSV held them, and nobody
could check them without re-deriving the comparison by hand.

Re-derived here, both statements needed correcting:

  * honest-negative blocking is identical in 24 cells, not 18. The 18 matched no table.
  * the single-checker claim was TRUE but told only the favourable half. A single checker never
    raised false-pass, which is what multi-checker agreement was proposed to prevent. It DID raise
    false-reject on clean artifacts in 3 of 10 cells, in one of them from no clean artifact
    rejected to every clean artifact rejected. Reporting only the false-pass half makes an
    ablation with a large measured cost look free.

So this producer reports BOTH error directions separately, and never a single summary figure: a
count that merges false-pass with false-reject cannot answer the question the paper asks.
"""
import collections
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TBL = os.path.join(ROOT, "paper", "tables")

# The three released ablation matrices. Every one of them must be present: a count taken over a
# subset of the matrices is a different number, and silently dropping one is how "18" happened.
NGUON = ("hard-matrix.csv", "rerun-g3-matrix.csv", "rerun-g2-matrix.csv")
GOC = "ATTEST"
PHE = ("-honest-neg-block", "-multichecker (single)")

# Columns that identify the measurement rather than the configuration or the value.
KHONG_PHAI_O = {"config", "mean", "min", "max", "n_runs", "mean_pct", "min_pct", "max_pct"}


def nhom_chi_so(metric):
    """false-pass and false-reject are opposite errors; merging them hides the trade-off."""
    if metric.startswith("fp"):
        return "false_pass"
    if metric.startswith("ff"):
        return "false_reject_clean"
    return "other:" + metric


def doc(ten):
    p = os.path.join(TBL, ten)
    if not os.path.exists(p):
        sys.exit("BLOCK: thieu %s. Dem tren mot phan cac ma tran la MOT CON SO KHAC." % ten)
    with io.open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    dem = collections.Counter()
    thieu_goc = 0
    for ten in NGUON:
        hang = doc(ten)
        khoa = lambda x: tuple(x[k] for k in x if k not in KHONG_PHAI_O)
        goc = {khoa(x): x for x in hang if x["config"] == GOC}
        if not goc:
            sys.exit("BLOCK: %s khong co cau hinh goc %r, khong so duoc voi gi." % (ten, GOC))
        for x in hang:
            if x["config"] not in PHE:
                continue
            g = goc.get(khoa(x))
            if g is None:
                thieu_goc += 1
                continue
            a, b = float(x["mean"]), float(g["mean"])
            n = nhom_chi_so(x["metric"])
            dem[(x["config"], n, "worse")] += a > b
            dem[(x["config"], n, "equal")] += a == b
            dem[(x["config"], n, "better")] += a < b

    if thieu_goc:
        # Silent truncation is a bug: say how many cells had no baseline to compare against.
        print("CANH BAO: %d o cua phe khong tim duoc o goc tuong ung, da bo qua." % thieu_goc)

    nhom = sorted({(c, n) for (c, n, _) in dem})
    if not nhom:
        sys.exit("BLOCK: 0 o duoc so sanh. Kiem 0 don vi khong phai la sach.")

    ra = os.path.join(TBL, "ablation-nulls.csv")
    with io.open(ra, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ablation", "error_direction", "n_cells", "n_worse", "n_equal", "n_better",
                    "worse_pct", "equal_pct"])
        for c, n in nhom:
            te, bg, tt = dem[(c, n, "worse")], dem[(c, n, "equal")], dem[(c, n, "better")]
            tong = te + bg + tt
            w.writerow([c, n, tong, te, bg, tt,
                        round(100.0 * te / tong, 1), round(100.0 * bg / tong, 1)])
            print("  %-24s %-20s %2d o: te hon %d, bang %d, tot hon %d"
                  % (c, n, tong, te, bg, tt))
    print("\nwrote paper/tables/ablation-nulls.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
