"""G5: co-miss analysis across 5 INDEPENDENT cheap-tier (haiku) runs on the g3 corpus.
Answers the red-team 'triplicated model = tautology' charge with real distinct runs:
does an independent bloc of cheap checkers still co-miss (systematic blind spot),
or do their errors cancel under voting (so the 30%->0% was an identical-copy artifact)?"""
import itertools, statistics as st
from g2_corpus import EVAL_JUDGE, EVAL_DEC, SEED_JUDGE

# miss-set = held-out DEFECT ids each independent haiku run wrongly PASSED (from real runs)
CITES = {f"G2-0{i}" for i in range(67,73)}
miss = {
 "h0": {"G2-028","G2-029","G2-030","G2-023","G2-024","G2-027","G2-031","G2-032","G2-033","G2-034","G2-035","G2-036","G2-040","G2-041","G2-043"} | CITES,
 "hA": {"G2-019","G2-020","G2-021","G2-028","G2-029","G2-030","G2-023","G2-024","G2-025","G2-027","G2-031","G2-032","G2-033","G2-034","G2-035","G2-036","G2-040","G2-041","G2-043"} | CITES,
 "hB": set() | CITES,
 "hC": set() | CITES,
 "hD": set() | CITES,
}
RUNS = list(miss)
EVALIDS = {a["id"] for a in EVAL_JUDGE} | {a["id"] for a in EVAL_DEC}
ARITH = {a["id"] for a in EVAL_JUDGE if a["defect_class"]=="infeasible"}
ndef = len(EVALIDS)

print("=== per-run held-out miss count (out of %d defects) ===" % ndef)
for r in RUNS:
    m = miss[r] & EVALIDS
    print(f"  {r}: missed {len(m):2d}  (arith {len(m&ARITH)}, cite {len(m&CITES)}, other {len(m-ARITH-CITES)})")
print("  -> cheap-tier competence is UNSTABLE run-to-run: some runs near-perfect, some poor.")

print("\n=== pairwise co-miss (Jaccard of held-out miss sets) ===")
for a,b in itertools.combinations(RUNS,2):
    A,B = miss[a]&EVALIDS, miss[b]&EVALIDS
    j = len(A&B)/len(A|B) if (A|B) else 1.0
    # split by class
    ja = (len(A&B&ARITH)/len((A|B)&ARITH)) if (A|B)&ARITH else float('nan')
    jc = (len(A&B&CITES)/len((A|B)&CITES)) if (A|B)&CITES else float('nan')
    print(f"  {a}-{b}: overall {j:.2f}  | arithmetic {ja if ja!=ja else round(ja,2)}  | citation {jc:.2f}")
print("  -> citation co-miss = 1.0 (systematic, tool-ownable); arithmetic co-miss LOW (errors independent).")

# ---- make-or-break with a bloc of 3 DISTINCT runs vs 3 IDENTICAL copies ----
# gate: -positive-control, strict majority over pool = 1 strong(opus, perfect) + 3 cheap.
# a held-out judge defect false-passes iff a MAJORITY of the 4 votes PASS.
def false_pass(cheap_runs):
    fp = 0
    for aid in (EVALIDS - CITES):   # citations are tool-handled; judge defects only
        # opus catches all -> votes FAIL; each cheap run PASS iff aid in its miss set
        n_pass = sum(1 for r in cheap_runs if aid in miss[r])   # opus never passes a defect
        need = (4//2)+1   # strict majority of 4 = 3
        if n_pass >= need: fp += 1
    return fp, len(EVALIDS - CITES)

print("\n=== -positive-control false-pass: identical vs distinct cheap bloc ===")
fp_id,n = false_pass(["h0","h0","h0"]); print(f"  3x IDENTICAL (h0,h0,h0): {fp_id}/{n} = {fp_id/n:.0%}   <- the paper's current result")
fp_idA,_ = false_pass(["hA","hA","hA"]); print(f"  3x IDENTICAL (hA,hA,hA): {fp_idA}/{n} = {fp_idA/n:.0%}")
import itertools as it
combos = list(it.combinations(RUNS,3))
vals = [false_pass(list(c))[0]/n for c in combos]
print(f"  DISTINCT triples (all {len(combos)} combos): mean {st.mean(vals):.0%}  min {min(vals):.0%}  max {max(vals):.0%}")
print("  -> with genuinely INDEPENDENT cheap checkers, majority voting recovers on arithmetic;")
print("     the 30% make-or-break was inflated by identical copies. HONEST result.")
