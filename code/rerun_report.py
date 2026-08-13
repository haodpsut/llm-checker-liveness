#!/usr/bin/env python3
"""Report for the re-run: read DIRECTLY from raw/, emit CSVs as RANGES.

Why this is a NEW script rather than a patch to the three older report scripts: each of those
computes over ONE run and returns ONE number. This measurement campaign has three to twelve runs
per condition, and its central finding is that weak configurations are NOT stable across runs (the
lenient checker's held-out detection spans 0.20 to 1.00). Collapsing several runs into one number
destroys exactly that finding. The older scripts are kept untouched for the earlier dataset so the
two can still be compared.

Every emitted cell carries mean / min / max / n_runs. No cell is allowed to carry mean alone.

Run:  python3 rerun_report.py
"""
import csv
import os
import re
import statistics as st

import g2_corpus as C2
import g4_corpus as C4
from g2_gates import CONFIGS, gate_decision

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
TBL = os.path.join(HERE, "..", "paper", "tables")

GT2 = {a["id"]: a["ground_truth"] for a in C2.CORPUS}
CLS2 = {a["id"]: a["defect_class"] for a in C2.CORPUS}
SEED2 = {a["id"]: a["is_seed"] for a in C2.CORPUS}
GT4 = {a["id"]: a["ground_truth"] for a in C4.ARTIFACTS}

def _runs(prefix):
    """Every raw/<prefix>-*.txt is one run. Discovered DYNAMICALLY: adding a run means adding a file,
    not editing code. Hard-coding the run list is the easiest way for a new run to be silently
    dropped from the statistics."""
    import glob
    fs = sorted(os.path.basename(f) for f in glob.glob(os.path.join(RAW, prefix + "-*.txt")))
    if not fs:
        raise SystemExit("BROKEN: 0 runs for %s -- empty is broken, not clean" % prefix)
    return fs

G2_RUNS = {k: _runs("g2-" + k) for k in ("strict", "moderate", "lenient")}
G3_RUNS = {t: _runs("g3-" + t) for t in ("opus", "sonnet", "haiku")}
G4_RUNS = {t: _runs("g4-" + t) for t in ("opus", "sonnet", "haiku")}


def read(fn, pat):
    path = os.path.join(RAW, fn)
    v = {m.group(1): m.group(2) for m in re.finditer(pat, open(path).read(), re.M)}
    if not v:
        raise SystemExit(f"BROKEN: {fn} has no verdict lines -- an empty log is BROKEN, not clean")
    return v


r2 = lambda fn: read(fn, r"^(G2-\d{3}):\s*(PASS|FAIL)")
r4 = lambda fn: read(fn, r"^(J-\d{3}):\s*(PASS|FAIL)")


def rate(v, keep):
    xs = [i for i in v if keep(i)]
    if not xs:
        raise SystemExit("BROKEN: filter selected 0 units -- an empty sweep is BROKEN, not 0%")
    return sum(1 for i in xs if v[i] == "FAIL") / len(xs)


def band(vals):
    """mean/min/max at 4 decimals. Never returns mean alone."""
    # Percent columns are emitted alongside the fractions because every TABLE in the paper prints
    # percentages. Without them the printed cell cannot be matched against the artifact at all, and
    # a number-tracing gate reports the whole table as untraceable, which is indistinguishable from
    # a stale number left behind from an earlier run.
    return [f"{st.mean(vals):.4f}", f"{min(vals):.4f}", f"{max(vals):.4f}", str(len(vals)),
            f"{100*st.mean(vals):.1f}", f"{100*min(vals):.0f}", f"{100*max(vals):.0f}"]


HDR = ["mean", "min", "max", "n_runs", "mean_pct", "min_pct", "max_pct"]


def wcsv(name, header, rows):
    with open(os.path.join(TBL, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {name:24s} {len(rows)} dong")


def per_checker(runs, reader, label):
    """seed-detect / held-detect / citation / false-reject per rig or per tier."""
    rows = []
    for key, files in runs.items():
        vs = [reader(f) for f in files]
        m = {
            "seed_detect":  lambda v: rate(v, lambda i: GT2[i] == "FAIL" and SEED2[i] and CLS2[i] != "fabricated-citation"),
            "held_detect":  lambda v: rate(v, lambda i: GT2[i] == "FAIL" and not SEED2[i] and CLS2[i] != "fabricated-citation"),
            "citation":     lambda v: rate(v, lambda i: CLS2[i] == "fabricated-citation" and not SEED2[i]),
            "false_reject": lambda v: rate(v, lambda i: GT2[i] == "PASS"),
        }
        for metric, fn in m.items():
            rows.append([key, metric] + band([fn(v) for v in vs]))
    wcsv(f"rerun-{label}.csv", [label.replace("g2", "rig").replace("g3", "tier"), "metric"] + HDR, rows)
    return rows


def gate_matrix(runs, pool, tau, label, dec_source):
    """The 8-configuration matrix, RECOMPUTED per run, then reported as a range."""
    names = [f"{m}{i}" for i, m in enumerate(pool)]
    n2r = dict(zip(names, pool))
    order = ["ATTEST", "b_iii_no_poscontrol", "b_v_no_honestneg", "b_vi_no_agreement",
             "b_ii_single_judge", "b_i_self_review", "b_vii_no_verify"]
    per_run = {k: {"fp_judge": [], "fp_dec": [], "ff_clean": []} for k in order}
    # Conditions have DIFFERENT run counts (strict 9, moderate 3, lenient 12). Run r of each
    # condition is paired into one "pool", so the number of pools is bounded by the condition with
    # the FEWEST runs. This was hard-coded as range(3) and SILENTLY discarded every run past the
    # third: exactly the silent truncation this project forbids. It now prints the pool count and
    # what was dropped.
    n_pool = min(len(f) for f in runs.values())
    dropped = {t: len(f) - n_pool for t, f in runs.items() if len(f) > n_pool}
    print(f"    [{label}] paired {n_pool} pools from {len(runs)} conditions"
          + (f"; DROPPED {dropped} surplus runs (bounded by the condition with fewest runs)" if dropped else ""))
    for r in range(n_pool):
        V = {t: r2(files[r]) for t, files in runs.items()}
        sd = {n: rate(V[n2r[n]], lambda i: GT2[i] == "FAIL" and SEED2[i] and CLS2[i] != "fabricated-citation")
              for n in names}
        EJ = [a for a in C2.EVAL_JUDGE]
        ED = [a for a in C2.EVAL_DEC]
        CL = [a for a in C2.CLEAN_POOL]
        for k in order:
            cfg = CONFIGS()[k]
            def dec(a):
                return gate_decision(a, {n: V[n2r[n]].get(a["id"], "PASS") for n in names},
                                     sd, cfg, tau, V[dec_source].get(a["id"], "PASS"))
            per_run[k]["fp_judge"].append(sum(1 for a in EJ if dec(a) == "PASS") / len(EJ))
            per_run[k]["fp_dec"].append(sum(1 for a in ED if dec(a) == "PASS") / len(ED))
            per_run[k]["ff_clean"].append(sum(1 for a in CL if dec(a) == "FAIL") / len(CL))
    rows = []
    for k in order:
        nm = CONFIGS()[k]["name"]
        for metric in ("fp_judge", "fp_dec", "ff_clean"):
            rows.append([nm, metric] + band(per_run[k][metric]))
    wcsv(f"rerun-{label}-matrix.csv", ["config", "metric"] + HDR, rows)


def g4_table():
    rows = []
    SEED = {a["id"] for a in C4.SEED}
    EVAL = {a["id"] for a in C4.EVAL}
    CLEAN = {a["id"] for a in C4.CLEAN}
    for t, files in G4_RUNS.items():
        vs = [r4(f) for f in files]
        def det(v, pool):
            d = [i for i in pool if GT4[i] == "FAIL"]
            return sum(1 for i in d if v[i] == "FAIL") / len(d)
        for metric, fn in (("seed_detect", lambda v: det(v, SEED)),
                           ("held_detect", lambda v: det(v, EVAL)),
                           ("held_fp",     lambda v: 1 - det(v, EVAL)),
                           ("false_reject", lambda v: sum(1 for i in CLEAN if v[i] == "FAIL") / len(CLEAN))):
            rows.append([t, metric] + band([fn(v) for v in vs]))
    wcsv("rerun-g4.csv", ["tier", "metric"] + HDR, rows)



# ---------------------------------------------------------------------------------------------
# MODE analysis. Reporting `mean +/- std` for the lenient checker gives 0.467 +/- 0.38, a value NO
# run ever produced. The distribution is BIMODAL: across twelve runs only 9 or 45 was ever observed,
# with nothing in between, so a mean hides precisely the thing worth reporting. The correct summary
# is the MODE proportion with an EXACT binomial (Clopper-Pearson) interval.
from math import comb


def _binom_cdf(k, n, p):
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson(k, n, alpha=0.05):
    """Exact interval for a binomial proportion. Verified against two textbook cases:
    0/10 -> [0, 0.3085] and 10/10 -> [0.6915, 1]."""
    lo, hi = 0.0, 1.0
    if k > 0:
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a + b) / 2
            if 1 - _binom_cdf(k - 1, n, m) > alpha / 2:
                b = m
            else:
                a = m
        lo = a
    if k < n:
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a + b) / 2
            if _binom_cdf(k, n, m) < alpha / 2:
                b = m
            else:
                a = m
        hi = b
    return lo, hi


assert abs(clopper_pearson(0, 10)[1] - 0.3085) < 1e-3, "clopper_pearson is broken"
assert abs(clopper_pearson(10, 10)[0] - 0.6915) < 1e-3, "clopper_pearson is broken"

CLEAN_IDS = {"G2-%03d" % i for i in range(1, 19)}


def modes():
    """Proportion falling into the BAD mode per varying condition, with interval and observed values."""
    rows = []

    def fails(fn):
        return {k for k, v in r2(fn).items() if v == "FAIL"}

    # lenient: bad mode = detects < 20 defects (only 9 or 45 was ever observed)
    fs = G2_RUNS["lenient"]
    vals = sorted({len(fails(f)) for f in fs})
    k = sum(1 for f in fs if len(fails(f)) < 20)
    lo, hi = clopper_pearson(k, len(fs))
    rows.append(["lenient_weak_mode", k, len(fs), f"{k/len(fs):.4f}",
                 f"{lo:.4f}", f"{hi:.4f}", "|".join(map(str, vals))])

    # strict: bad mode = any false-reject on a clean artifact
    fs = G2_RUNS["strict"]
    vals = sorted({len(fails(f) & CLEAN_IDS) for f in fs})
    k = sum(1 for f in fs if fails(f) & CLEAN_IDS)
    lo, hi = clopper_pearson(k, len(fs))
    rows.append(["strict_falsereject_mode", k, len(fs), f"{k/len(fs):.4f}",
                 f"{lo:.4f}", f"{hi:.4f}", "|".join(map(str, vals))])

    # haiku on the reasoning corpus: bad mode = over-rejects J-007
    fs = G4_RUNS["haiku"]
    k = sum(1 for f in fs if r4(f).get("J-007") == "FAIL")
    lo, hi = clopper_pearson(k, len(fs))
    rows.append(["g4_haiku_overreject", k, len(fs), f"{k/len(fs):.4f}",
                 f"{lo:.4f}", f"{hi:.4f}", "0|1"])

    # `observed_values` is a pipe-joined STRING, so the two attractors it names are invisible to
    # any tool that reads CSV cells as numbers: the paper prints "9 or 45 of 45" and no cell held
    # 9, 45 or the denominator. Split them into numeric columns as well, so the printed table can
    # be traced back cell by cell rather than by reading a string with the eye.
    out = []
    for r in rows:
        vs = [v for v in r[6].split("|") if v.strip().lstrip("-").isdigit()]
        lo_v = min(map(int, vs)) if vs else ""
        hi_v = max(map(int, vs)) if vs else ""
        out.append(list(r) + [lo_v, hi_v, len(vs)])
    wcsv("rerun-modes.csv",
         ["condition", "k_bad", "n_runs", "p_bad", "ci_lo", "ci_hi", "observed_values",
          "mode_low", "mode_high", "n_distinct_values"], out)
    return rows

def main():
    print("rerun_report -- reading from raw/, emitting CSVs as ranges\n")
    per_checker(G2_RUNS, r2, "g2")
    per_checker(G3_RUNS, r2, "g3")
    g4_table()
    gate_matrix(G2_RUNS, ["strict", "moderate", "lenient", "lenient"], 0.6, "g2", "lenient")
    gate_matrix(G3_RUNS, ["opus", "haiku", "haiku", "haiku"], 0.85, "g3", "haiku")
    modes()
    print("\ndone. Every cell carries mean/min/max/n_runs; no cell carries mean alone.")


if __name__ == "__main__":
    main()
