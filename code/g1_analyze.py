"""
G1 make-or-break analysis. Given the 3 checker verdicts (collected in-session via
sub-agents), compute: seed detect-rate (positive-control), held-out false-pass,
and the make-or-break: does a positive-control gate (block checkers failing seed
liveness) reduce held-out false-pass vs trusting all checkers?
"""
from g1_artifacts import ARTIFACTS, ground_truth, SEED, HELDOUT, CLEAN

# verdicts collected from the 3 checker sub-agents (PASS/FAIL per artifact id)
VERDICTS = {
    "strict":  {"A1":"PASS","A2":"PASS","A3":"PASS","A4":"PASS","S1":"FAIL","S2":"FAIL","S3":"FAIL","H1":"FAIL","H2":"FAIL","H3":"FAIL","H4":"FAIL"},
    "moderate":{"A1":"PASS","A2":"PASS","A3":"PASS","A4":"PASS","S1":"FAIL","S2":"FAIL","S3":"FAIL","H1":"FAIL","H2":"FAIL","H3":"FAIL","H4":"FAIL"},
    "lenient": {"A1":"PASS","A2":"PASS","A3":"PASS","A4":"PASS","S1":"PASS","S2":"FAIL","S3":"FAIL","H1":"FAIL","H2":"FAIL","H3":"FAIL","H4":"FAIL"},
}
TAU = 1.0   # liveness threshold: checker must catch ALL seed defects to be 'live'

def detect_rate(checker, subset):
    # fraction of DEFECTS in subset that the checker flags FAIL (catches)
    defs = [a for a in subset if a["label"] != "clean"]
    caught = sum(1 for a in defs if VERDICTS[checker][a["id"]] == "FAIL")
    return caught / len(defs) if defs else 1.0

def held_out_false_pass(checker):
    # held-out defects the checker WRONGLY passes
    fp = sum(1 for a in HELDOUT if VERDICTS[checker][a["id"]] == "PASS")
    return fp, len(HELDOUT)

print("=== per-checker ===")
for c in VERDICTS:
    sd = detect_rate(c, SEED)
    ho = detect_rate(c, HELDOUT)
    fp, n = held_out_false_pass(c)
    live = sd >= TAU
    print(f"  {c:9} seed-detect(pos-control)={sd:.2f}  held-out-detect={ho:.2f}  "
          f"held-out-false-pass={fp}/{n}  Live(τ={TAU})={live}")

# ----- make-or-break: gate false-pass WITH vs WITHOUT positive-control -----
# gate PASS on an artifact iff >=1 LIVE checker passes it (lenient aggregation to
# expose false-pass); WITH pos-control only live checkers count; WITHOUT, all count.
def gate_false_pass(use_positive_control):
    live_checkers = [c for c in VERDICTS if (detect_rate(c, SEED) >= TAU) or (not use_positive_control)]
    fp = 0
    for a in HELDOUT:  # all are defects; false-pass if gate says PASS
        # gate trusts a PASS from any contributing checker
        passed = any(VERDICTS[c][a["id"]] == "PASS" for c in live_checkers)
        fp += 1 if passed else 0
    return fp, len(HELDOUT), live_checkers

print("\n=== MAKE-OR-BREAK: held-out false-pass, gate WITH vs WITHOUT positive-control ===")
for use in [False, True]:
    fp, n, lc = gate_false_pass(use)
    print(f"  positive-control={use}:  held-out false-pass={fp}/{n}   contributing checkers={lc}")

# ----- G-gen check: does seed-detect predict held-out-detect? -----
print("\n=== G-gen (does positive-control on seeds predict held-out catching?) ===")
for c in VERDICTS:
    print(f"  {c:9} seed={detect_rate(c,SEED):.2f}  held-out={detect_rate(c,HELDOUT):.2f}")
print("\n=== VERDICT ===")
fp_off = gate_false_pass(False)[0]; fp_on = gate_false_pass(True)[0]
if fp_off == 0:
    print("  NO SIGNAL: held-out false-pass is already 0 WITHOUT positive-control ->")
    print("  the held-out defects are too EASY (all checkers catch them) -> positive-control")
    print("  has nothing to screen. DEGENERATE benchmark (G1 caught it cheaply, as intended).")
elif fp_on < fp_off:
    print(f"  SIGNAL: positive-control cuts held-out false-pass {fp_off} -> {fp_on}. Proceed to G2.")
else:
    print(f"  NO SIGNAL: positive-control did not reduce false-pass ({fp_off} -> {fp_on}).")
