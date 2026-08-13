"""
G1 round-2 make-or-break analysis (non-degenerate benchmark: subtle defects).
Reports: per-checker seed detect-rate (positive-control) vs held-out false-pass;
a tau-sweep of positive-control screening; the make-or-break (false-pass WITH vs
WITHOUT positive-control); and the G-gen check (does seed detect-rate predict
held-out detect-rate?).
"""
from g1r2_artifacts import ARTIFACTS, ground_truth, SEED, HELDOUT, CLEAN

VERDICTS = {
    # strict: computes arithmetic, checks CI overlap, distrusts unverifiable citations, checks scope
    "strict":  {"CA":"PASS","CB":"PASS","CC":"PASS","SA":"FAIL","SB":"FAIL","SC":"FAIL","HA":"FAIL","HB":"FAIL","HC":"FAIL","HD":"FAIL"},
    # moderate: catches arithmetic + CI, but trusts plausible citations (misses SA, HA)
    "moderate":{"CA":"PASS","CB":"PASS","CC":"PASS","SA":"PASS","SB":"FAIL","SC":"FAIL","HA":"PASS","HB":"FAIL","HC":"FAIL","HD":"FAIL"},
    # lenient: trusts author, no arithmetic / no CI check, only catches blatant scope gap (HD)
    "lenient": {"CA":"PASS","CB":"PASS","CC":"PASS","SA":"PASS","SB":"PASS","SC":"PASS","HA":"PASS","HB":"PASS","HC":"PASS","HD":"FAIL"},
}

def detect_rate(checker, subset):
    defs = [a for a in subset if a["label"] != "clean"]
    caught = sum(1 for a in defs if VERDICTS[checker][a["id"]] == "FAIL")
    return caught / len(defs) if defs else 1.0

def clean_false_fail(checker):
    return sum(1 for a in CLEAN if VERDICTS[checker][a["id"]] == "FAIL"), len(CLEAN)

print("=== per-checker ===")
for c in VERDICTS:
    sd, ho = detect_rate(c, SEED), detect_rate(c, HELDOUT)
    fp = sum(1 for a in HELDOUT if VERDICTS[c][a["id"]] == "PASS")
    ff, nff = clean_false_fail(c)
    print(f"  {c:9} seed-detect={sd:.2f}  held-out-detect={ho:.2f}  held-out-false-pass={fp}/{len(HELDOUT)}  clean-false-fail={ff}/{nff}")

# ---- positive-control screening: keep only checkers with seed detect_rate >= tau ----
def gate_false_pass(tau):
    # a checker contributes only if Live (seed detect >= tau); tau=0 => trust all (no PC)
    contrib = [c for c in VERDICTS if detect_rate(c, SEED) >= tau]
    if not contrib:  # fail-closed: no live checker -> gate blocks everything -> 0 false-pass
        return 0, len(HELDOUT), []
    # gate is permissive-worst-case: a held-out defect false-passes if ANY contributing checker passes it
    fp = sum(1 for a in HELDOUT if any(VERDICTS[c][a["id"]] == "PASS" for c in contrib))
    return fp, len(HELDOUT), contrib

print("\n=== MAKE-OR-BREAK: positive-control tau-sweep (held-out false-pass) ===")
for tau in [0.0, 0.34, 0.67, 1.0]:
    fp, n, contrib = gate_false_pass(tau)
    tag = "  <-- no positive-control (trust all)" if tau == 0.0 else ""
    print(f"  tau={tau:.2f}: false-pass={fp}/{n}  live-checkers={contrib}{tag}")

print("\n=== G-gen: does seed detect-rate predict held-out detect-rate? ===")
for c in VERDICTS:
    print(f"  {c:9} seed={detect_rate(c,SEED):.2f}  held-out={detect_rate(c,HELDOUT):.2f}")

fp_off = gate_false_pass(0.0)[0]
fp_on  = gate_false_pass(1.0)[0]
print("\n=== VERDICT ===")
if fp_off > fp_on:
    print(f"  SIGNAL: positive-control cuts held-out false-pass {fp_off}/{len(HELDOUT)} -> {fp_on}/{len(HELDOUT)}.")
    print("  Non-degenerate: degraded checkers that miss seeds ALSO false-pass held-out,")
    print("  and seed liveness screens them out. Make-or-break has signal -> G2 viable.")
    print("  CAVEAT: the residual leak at tau=0.67 is the fabricated-citation class (HA),")
    print("  a DECIDABLE predicate needing a tool (citation-resolve), NOT judgment -> matches")
    print("  the formulation's Pi^dec vs Pi^judge split: positive-control governs judgment defects;")
    print("  tools govern citation/compile. Coherent division of labor.")
else:
    print(f"  NO SIGNAL: {fp_off} -> {fp_on}.")
