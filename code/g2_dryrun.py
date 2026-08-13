"""
G2 DRY-RUN harness -- SIMULATED checker verdicts, NO LLM calls, NO cost.

Purpose (user chose: build the benchmark, do NOT run the real matrix yet):
  1. validate plumbing end-to-end (corpus -> verdicts -> 8 gates -> metrics);
  2. power-analysis-lite: with a checker model calibrated to G1 observations, does the
     experiment DESIGN separate ATTEST from its ablations -- and in WHICH regime?

KEY REGIME (discovered in the first dry-run): under fail-closed UNANIMITY one competent
checker suffices, so positive-control / honest-neg-block are redundant. They become
load-bearing under MAJORITY voting WHEN degraded checkers can form a bloc. So the real
experiment sweeps the DEGRADED-CHECKER FRACTION. This dry-run reproduces that sweep to
confirm the design has power before spending on the real matrix.

*** All numbers are SIMULATED, not measured. ***
"""
import random, math
from g2_corpus import SEED_JUDGE, EVAL_JUDGE, EVAL_DEC, CLEAN_POOL
from g2_gates import CONFIGS, gate_decision, SUPERIORITY_CLASSES

TAU = 0.6
N_SIM = 300

# P(vote FAIL on a defect) by (type, predicate_kind, difficulty); P(false-FAIL on clean).
# 'sup_subtle' = catch rate on SUBTLE superiority overclaims (overlapping-CI / within-noise
# ablation) -- a distinct statistical-literacy skill. Base values match G1 (moderate DID
# catch CI-overlap there), so honest-neg-block looks redundant; sweep (block 4) lowers it.
CATCH = {
    "strict":   {("judge","subtle"):0.95, ("judge","moderate"):0.98, ("dec","subtle"):0.85, "sup_subtle":0.92, "clean_ff":0.02},
    "moderate": {("judge","subtle"):0.80, ("judge","moderate"):0.92, ("dec","subtle"):0.15, "sup_subtle":0.80, "clean_ff":0.03},
    "lenient":  {("judge","subtle"):0.15, ("judge","moderate"):0.45, ("dec","subtle"):0.05, "sup_subtle":0.10, "clean_ff":0.01},
}
PRODUCER_CATCH = 0.10

def verdict(ctype, art, rng, sup_override=None):
    if art["defect_class"] == "clean":
        return "FAIL" if rng.random() < CATCH[ctype]["clean_ff"] else "PASS"
    diff = art["difficulty"] if art["difficulty"] in ("subtle","moderate") else "subtle"
    if art["defect_class"] in SUPERIORITY_CLASSES and diff == "subtle":
        p = sup_override[ctype] if (sup_override and ctype in sup_override) else CATCH[ctype]["sup_subtle"]
    else:
        p = CATCH[ctype][(art["predicate_kind"], diff)]
    return "FAIL" if rng.random() < p else "PASS"

def producer_verdict(art, rng):
    return "PASS" if art["defect_class"] == "clean" else ("FAIL" if rng.random() < PRODUCER_CATCH else "PASS")

def seed_detect_for(pool, rng, sup_override=None):
    # {checker_name: detect_rate on SEED_JUDGE}
    out = {}
    for name, ctype in pool:
        caught = sum(1 for a in SEED_JUDGE if verdict(ctype, a, rng, sup_override) == "FAIL")
        out[name] = caught / len(SEED_JUDGE)
    return out

def run_config(cfg, pool, rng, sup_override=None):
    seed_detect = seed_detect_for(pool, rng, sup_override)
    typ = dict(pool)
    m = dict(fp_judge=0, fp_dec=0, ff_clean=0, hn_catch=0, hn_total=0)
    def decide(a):
        vs = {name: verdict(typ[name], a, rng, sup_override) for name, _ in pool}
        return gate_decision(a, vs, seed_detect, cfg, TAU, producer_verdict(a, rng))
    for a in EVAL_JUDGE:
        if decide(a) == "PASS": m["fp_judge"] += 1
        if a["defect_class"] in SUPERIORITY_CLASSES:
            m["hn_total"] += 1
            if decide(a) == "FAIL": m["hn_catch"] += 1
    for a in EVAL_DEC:
        if decide(a) == "PASS": m["fp_dec"] += 1
    for a in CLEAN_POOL:
        if decide(a) == "FAIL": m["ff_clean"] += 1
    return m

def make_pool(n_lenient):
    pool = [("strict1","strict"), ("moderate1","moderate")]
    pool += [(f"lenient{i+1}","lenient") for i in range(n_lenient)]
    return pool

def make_pool_homog(n_moderate):
    # 1 strict + several moderate, all pass liveness -> isolates honest-neg-block:
    # majority (need > half) can be carried by correlated moderate misses on overclaims,
    # while honest-neg-block trusts the single strict dissent. |live|>=3 so majority != unanimity.
    return [("strict1","strict")] + [(f"moderate{i+1}","moderate") for i in range(n_moderate)]

def avg_over_sims(cfg, pool, rng, sup_override=None):
    acc = dict(fp_judge=0.0, fp_dec=0.0, ff_clean=0.0, hn_catch=0.0, hn_total=0.0)
    for _ in range(N_SIM):
        m = run_config(cfg, pool, rng, sup_override)
        for k in acc: acc[k] += m[k]
    for k in acc: acc[k] /= N_SIM
    return acc

def main():
    rng = random.Random(20260728)
    nj, nd, nc = len(EVAL_JUDGE), len(EVAL_DEC), len(CLEAN_POOL)
    cfgs = CONFIGS()
    print("*** SIMULATED (dry-run, no LLM). Estimates the real G2 matrix to size spend. ***")
    print(f"pools: eval-judge={nj}  eval-dec(citation)={nd}  clean={nc} | tau={TAU} sims={N_SIM}\n")

    # ---- (1) full matrix at a representative pool (1 strict, 1 moderate, 2 lenient) ----
    pool = make_pool(2)
    print(f"[MATRIX] pool = {[t for _,t in pool]}")
    hdr = f"{'config':30} {'fp_judge':>9} {'fp_dec':>7} {'ff_clean':>9} {'hn-catch':>9}"
    print(hdr); print("-"*len(hdr))
    for k, cfg in cfgs.items():
        m = avg_over_sims(cfg, pool, rng)
        hn = m["hn_catch"]/m["hn_total"] if m["hn_total"] else 0
        print(f"{cfg['name']:30} {m['fp_judge']/nj:>8.1%} {m['fp_dec']/nd:>7.0%} {m['ff_clean']/nc:>8.1%} {hn:>8.0%}")

    # ---- (2) make-or-break #1: degraded-fraction sweep, ATTEST vs -positive-control ----
    print("\n[SWEEP] make-or-break #1 -- held-out judge false-pass vs #degraded checkers")
    print(f"{'#lenient':>9} {'degraded-frac':>14} {'-PC fp_judge':>14} {'ATTEST fp_judge':>16}")
    for nl in range(0, 5):
        pool = make_pool(nl)
        frac = nl / len(pool)
        a = avg_over_sims(cfgs["ATTEST"], pool, rng)["fp_judge"]/nj
        b = avg_over_sims(cfgs["b_iii_no_poscontrol"], pool, rng)["fp_judge"]/nj
        print(f"{nl:>9} {frac:>13.0%} {b:>13.1%} {a:>15.1%}")

    # ---- (3) make-or-break #2: honest-neg-block vs checker STATISTICAL competence ----
    # honest-neg-block blocks superiority claims on ANY dissent (bar of 1), so it earns its
    # keep only when strict-majority misses overclaims -- i.e. when the surviving checkers
    # are weak on subtle statistical claims. Sweep the moderate checker's sup-competence.
    pool = make_pool_homog(3)   # 1 strict + 3 moderate (|live|=4, majority need=3 != unanimity)
    print("\n[SWEEP] make-or-break #2 -- honest-neg catch vs moderate stat-competence (pool: 1 strict + 3 moderate)")
    print(f"{'moderate sup-catch':>20} {'-HNB hn-catch':>14} {'ATTEST hn-catch':>16}")
    sep2_any = False
    for sup in [0.9, 0.7, 0.5, 0.3, 0.15]:
        ov = {"moderate": sup}
        on  = avg_over_sims(cfgs["ATTEST"], pool, rng, ov)
        off = avg_over_sims(cfgs["b_v_no_honestneg"], pool, rng, ov)
        d_on  = on["hn_catch"]/max(on["hn_total"],1)
        d_off = off["hn_catch"]/max(off["hn_total"],1)
        if d_on - d_off > 0.1: sep2_any = True
        print(f"{sup:>20.2f} {d_off:>13.0%} {d_on:>15.0%}")

    print("\n=== DESIGN POWER (simulated) ===")
    pool = make_pool(3)
    a3 = avg_over_sims(cfgs["ATTEST"], pool, rng)["fp_judge"]/nj
    b3 = avg_over_sims(cfgs["b_iii_no_poscontrol"], pool, rng)["fp_judge"]/nj
    sep1 = b3 - a3 > 0.05
    print(f"  MOB#1 positive-control: separates at high degraded-frac  {'YES' if sep1 else 'NO'} ( -PC={b3:.0%} vs ATTEST={a3:.0%} )")
    print(f"  MOB#2 honest-neg-block: separates when checkers weak on stats  {'YES' if sep2_any else 'NO'}")
    print("  HONEST NOTE: MOB#2 is CONDITIONAL -- with stat-competent checkers, strict-majority")
    print("  already catches overclaims and honest-neg-block is redundant for DETECTION. Its")
    print("  robust value is producer-side ENFORCEMENT (forces honest reframe), a separate")
    print("  multi-round experiment. Report Primitive 2 honestly on both axes; do NOT overclaim.")
    print(f"  -> {'MOB#1 alone justifies the matrix; scope MOB#2 as conditional + add reframe study' if sep1 else 'redesign before spending'}")

if __name__ == "__main__":
    main()
