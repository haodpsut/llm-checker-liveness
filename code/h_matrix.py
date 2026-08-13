#!/usr/bin/env python3
"""The 8-configuration ablation matrix on the HARD corpus, at thresholds that actually fire.

WHY THIS EXISTS. An external reviewer made three connected points about the earlier results, and
checking them against the data confirmed all three:

  (a) The liveness threshold was INERT. On the first corpus every tier detects 1.00 of the seeded
      pool, and tau was 0.85, so positive-control screening never excluded anyone. "ATTEST equals
      -positive-control" was therefore not evidence that liveness fails to help; it was the
      arithmetic consequence of a filter that never fired.
  (b) The ablation matrix had only ever been run on the SATURATED corpus. The architectural claim
      was tested exactly where nothing can separate.
  (c) The per-class threshold variant was argued for in prose and never actually run.

This file addresses all three. On the hard corpus the cheap tier detects 0.80-0.87 of the seeded
pool while both stronger tiers detect 1.00, so a threshold can be placed where it discriminates:

    tau = 0.90   pooled : excludes the cheap tier in every run
    tau = 0.85   pooled : excludes it in some runs and not others (0.80 vs 0.87)
    per-class    : requires every defect class to clear the threshold separately, which is the
                   variant the prose claimed would not help; here it is measured rather than argued

No new model calls: the gate decision is deterministic given the verdicts already logged in raw/.
"""
import csv
import glob
import os
import re
import sys
from collections import defaultdict
from math import comb

import h_corpus as H
from g2_gates import CONFIGS, gate_decision

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
TBL = os.path.join(HERE, "..", "paper", "tables")

GT = {a["id"]: a["ground_truth"] for a in H.ARTIFACTS}
CLS = {a["id"]: a["defect_class"] for a in H.ARTIFACTS}
SEED_IDS = [a["id"] for a in H.SEED]
EVAL = H.EVAL
CLEAN = H.CLEAN
ORDER = ["ATTEST", "b_iii_no_poscontrol", "b_v_no_honestneg", "b_vi_no_agreement",
         "b_ii_single_judge", "b_i_self_review", "b_vii_no_verify"]


def read(path):
    v = {m.group(1): m.group(2)
         for m in re.finditer(r"^(H-\d{3}):\s*(PASS|FAIL)", open(path).read(), re.M)}
    missing = set(GT) - set(v)
    if missing:
        raise SystemExit(f"BLOCK {os.path.basename(path)}: missing {sorted(missing)[:5]}")
    return v


def runs_by_tier():
    out = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(RAW, "h-*.txt"))):
        out[os.path.basename(f).split("-")[1]].append(f)
    if not out:
        raise SystemExit("BLOCK: 0 hard-corpus logs. Empty is broken, not clean.")
    return out


def seed_detect_pooled(v):
    d = [i for i in SEED_IDS if GT[i] == "FAIL"]
    return sum(1 for i in d if v[i] == "FAIL") / len(d)


def seed_detect_per_class(v):
    """Worst class rate. A checker blind to one class in five scores 0 here, not 0.8."""
    per = defaultdict(lambda: [0, 0])
    for i in SEED_IDS:
        if GT[i] != "FAIL":
            continue
        per[CLS[i]][1] += 1
        per[CLS[i]][0] += v[i] == "FAIL"
    return min(k / n for k, n in per.values())


def run_matrix(pool, tau, mode, by_tier):
    """One row set. mode='pooled' or 'per-class' decides how seed detection is scored."""
    names = [f"{m}{i}" for i, m in enumerate(pool)]
    n2t = dict(zip(names, pool))
    n_pool = min(len(by_tier[t]) for t in set(pool))
    rows, live_counts = [], []
    acc = {k: {"fp_judge": [], "ff_clean": []} for k in ORDER}
    for r in range(n_pool):
        V = {t: read(by_tier[t][r]) for t in set(pool)}
        score = seed_detect_pooled if mode == "pooled" else seed_detect_per_class
        sd = {n: score(V[n2t[n]]) for n in names}
        live_counts.append(sum(1 for n in names if sd[n] >= tau))
        for k in ORDER:
            cfg = CONFIGS()[k]

            def dec(a):
                return gate_decision(a, {n: V[n2t[n]][a["id"]] for n in names},
                                     sd, cfg, tau, V[pool[-1]][a["id"]])
            acc[k]["fp_judge"].append(sum(1 for a in EVAL if dec(a) == "PASS") / len(EVAL))
            acc[k]["ff_clean"].append(sum(1 for a in CLEAN if dec(a) == "FAIL") / len(CLEAN))
    for k in ORDER:
        nm = CONFIGS()[k]["name"]
        for metric in ("fp_judge", "ff_clean"):
            xs = acc[k][metric]
            # Percentages are emitted next to the fractions because the TABLE prints percentages.
            # Storing only the fraction means every cell a reader sees is one mental conversion
            # away from the artifact, and the number-tracing gate cannot match it at all.
            rows.append([mode, f"{tau:.2f}", nm, metric,
                         f"{sum(xs)/len(xs):.4f}", f"{min(xs):.4f}", f"{max(xs):.4f}", len(xs),
                         f"{100*min(xs):.0f}", f"{100*max(xs):.0f}"])
    return rows, live_counts


def paired_test(pool, tau, mode, by_tier, a="ATTEST", b="b_iii_no_poscontrol"):
    """Paired comparison of two configurations on the SAME artifacts, run by run.

    The marginal Clopper-Pearson intervals for 0/30 and 6/30 overlap, so a reader comparing only
    those two intervals would rightly withhold judgement. But the two configurations see identical
    artifacts under identical checker verdicts with one mechanism toggled, so the pairing carries
    the information and an unpaired interval throws it away. Reported alongside the intervals, not
    instead of them.
    """
    names = [f"{m}{i}" for i, m in enumerate(pool)]
    n2t = dict(zip(names, pool))
    score = seed_detect_pooled if mode == "pooled" else seed_detect_per_class
    a_blocks = b_blocks = 0
    for r in range(min(len(by_tier[t]) for t in set(pool))):
        V = {t: read(by_tier[t][r]) for t in set(pool)}
        sd = {n: score(V[n2t[n]]) for n in names}
        for art in EVAL:
            v = {n: V[n2t[n]][art["id"]] for n in names}
            da = gate_decision(art, v, sd, CONFIGS()[a], tau, V[pool[-1]][art["id"]])
            db = gate_decision(art, v, sd, CONFIGS()[b], tau, V[pool[-1]][art["id"]])
            if da == db:
                continue
            if da == "FAIL":
                a_blocks += 1
            else:
                b_blocks += 1
    n = a_blocks + b_blocks
    k = min(a_blocks, b_blocks)
    p = 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)
    return a_blocks, b_blocks, n, p


def clopper_pearson(k, n, alpha=0.05):
    """Exact binomial interval. Self-checked below against two hand-verifiable endpoints."""
    def tail_ge(pr):
        return sum(comb(n, i) * pr ** i * (1 - pr) ** (n - i) for i in range(k, n + 1))

    def tail_le(pr):
        return sum(comb(n, i) * pr ** i * (1 - pr) ** (n - i) for i in range(0, k + 1))
    lo = 0.0
    if k > 0:
        x, y = 0.0, 1.0
        for _ in range(200):
            m = (x + y) / 2
            x, y = (m, y) if tail_ge(m) < alpha / 2 else (x, m)
        lo = x
    hi = 1.0
    if k < n:
        x, y = 0.0, 1.0
        for _ in range(200):
            m = (x + y) / 2
            x, y = (x, m) if tail_le(m) < alpha / 2 else (m, y)
        hi = y
    return lo, hi


def main():
    by_tier = runs_by_tier()
    # Two orderings of the SAME pool. The single-judge and single-checker ablations pick names[0],
    # so the ordering silently decides WHICH checker becomes the lone judge. Reporting only the
    # strong-first ordering would make "a single LLM judge also reaches 0%" an artefact of having
    # quietly handed that baseline the best checker in the pool. The realistic deployment the paper
    # motivates is the opposite: one cheap judge at scale.
    pools = {"strong-first": ["opus", "haiku", "haiku", "haiku"],
             "cheap-first":  ["haiku", "haiku", "haiku", "opus"]}
    all_rows = []
    print("h_matrix -- 8-configuration matrix on the hard corpus\n")
    print(f"{'pool':13s} {'mode':10s} {'tau':>5s}  live checkers per run (of 4)")
    for pname, pool in pools.items():
      for mode, tau in (("pooled", 0.85), ("pooled", 0.90), ("per-class", 0.90)):
        rows, live = run_matrix(pool, tau, mode, by_tier)
        rows = [[pname] + r for r in rows]
        all_rows += rows
        print(f"{pname:13s} {mode:10s} {tau:5.2f}  {live}"
              + ("   <-- never fires" if all(x == 4 for x in live) else "   <-- FIRES"))
    with open(os.path.join(TBL, "hard-matrix.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pool", "mode", "tau", "config", "metric", "mean", "min", "max", "n_runs",
                    "min_pct", "max_pct"])
        w.writerows(all_rows)
    print(f"\n  wrote hard-matrix.csv: {len(all_rows)} rows")

    # --- paired test + exact intervals, emitted so the prose can cite a CSV cell -------------
    lo0, hi0 = clopper_pearson(0, len(EVAL))
    assert abs(hi0 - 0.1157) < 1e-3, f"clopper_pearson self-check failed: 0/30 -> {hi0}"
    ab, bb, nd, pv = paired_test(pools["strong-first"], 0.90, "per-class", by_tier)
    rows = [["ATTEST_vs_no_poscontrol", "discordant_attest_blocks", ab],
            ["ATTEST_vs_no_poscontrol", "discordant_other_blocks", bb],
            ["ATTEST_vs_no_poscontrol", "discordant_total", nd],
            ["ATTEST_vs_no_poscontrol", "p_two_sided", f"{pv:.6f}"]]
    for k in (0, 4, 6):
        lo, hi = clopper_pearson(k, len(EVAL))
        rows.append([f"fp_judge_{k}_of_{len(EVAL)}", "ci_lo", f"{lo:.4f}"])
        rows.append([f"fp_judge_{k}_of_{len(EVAL)}", "ci_hi", f"{hi:.4f}"])
    with open(os.path.join(TBL, "hard-paired.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["comparison", "quantity", "value"])
        w.writerows(rows)
    print(f"\n  wrote hard-paired.csv: {nd} discordant artifacts, "
          f"{ab} one way and {bb} the other, two-sided p = {pv:.2e}")

    print(f"\n{'pool':13s} {'config':24s} {'fp_judge':>14s} {'ff_clean':>14s}   (per-class tau=0.90)")
    for pname in pools:
        for k in ORDER:
            nm = CONFIGS()[k]["name"]
            got = {r[4]: r for r in all_rows
                   if r[0] == pname and r[1] == "per-class" and r[2] == "0.90" and r[3] == nm}
            def band(m):
                r = got[m]
                return f"{float(r[5]):.2f}" if r[6] == r[7] else f"{float(r[6]):.2f}-{float(r[7]):.2f}"
            print(f"{pname:13s} {nm:24s} {band('fp_judge'):>14s} {band('ff_clean'):>14s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
