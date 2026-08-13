"""
Full REAL-data G2 report from g2_verdicts.json (3 real checker sub-agents, 28/07/2026).
Produces the three paper artifacts with MEASURED (not simulated) numbers:
  (1) the 8-config matrix at the representative pool,
  (2) G-gen check: per-checker seed detect-rate vs held-out detect-rate (validates T2),
  (3) make-or-break #1: degraded-fraction sweep, ATTEST vs -positive-control.
Reuses g2_gates verbatim (same decision logic as dry-run -> no drift).
"""
import json, os, csv
from g2_corpus import SEED_JUDGE, EVAL_JUDGE, EVAL_DEC, CLEAN_POOL, JUDGE_CLASSES
from g2_gates import CONFIGS, gate_decision, SUPERIORITY_CLASSES

TBL = os.path.join(os.path.dirname(__file__), "..", "paper", "tables")
def _wcsv(name, header, rows):
    os.makedirs(TBL, exist_ok=True)
    with open(os.path.join(TBL, name), "w", newline="") as f:
        w = csv.writer(f); w.writerow(header)
        for r in rows: w.writerow(r)

TAU = 0.6
V = json.load(open("g2_verdicts.json"))
nj, nd, nc = len(EVAL_JUDGE), len(EVAL_DEC), len(CLEAN_POOL)

def detect(rigor, pool_arts):
    defs = [a for a in pool_arts if a["defect_class"] != "clean"]
    return sum(1 for a in defs if V[rigor].get(a["id"]) == "FAIL") / len(defs)

def seed_detect_for(pool):
    return {name: detect(rigor, SEED_JUDGE) for name, rigor in pool}

def run_matrix(pool):
    sd = seed_detect_for(pool); name2rig = dict(pool)
    rows = {}
    for k, cfg in CONFIGS().items():
        fpj = fpd = ffc = hnc = hnt = 0
        def decide(a):
            vs = {name: V[name2rig[name]].get(a["id"], "PASS") for name, _ in pool}
            prod = V["lenient"].get(a["id"], "PASS")
            return gate_decision(a, vs, sd, cfg, TAU, prod)
        for a in EVAL_JUDGE:
            if decide(a) == "PASS": fpj += 1
            if a["defect_class"] in SUPERIORITY_CLASSES:
                hnt += 1
                if decide(a) == "FAIL": hnc += 1
        for a in EVAL_DEC:
            if decide(a) == "PASS": fpd += 1
        for a in CLEAN_POOL:
            if decide(a) == "FAIL": ffc += 1
        rows[k] = dict(name=cfg["name"], fpj=fpj/nj, fpd=fpd/nd, ffc=ffc/nc, hn=(hnc/hnt if hnt else 0))
    return rows, sd

def pool(nl):
    return [("strict1","strict"), ("moderate1","moderate")] + [(f"lenient{i}","lenient") for i in range(nl)]

print("=== REAL G2 report (measured, 3 checker sub-agents) ===\n")

# (1) matrix at representative pool (1 strict, 1 moderate, 2 lenient)
rows, sd = run_matrix(pool(2))
print(f"[1] MATRIX  pool=strict+moderate+2*lenient  tau={TAU}")
print(f"    seed detect-rate: " + "  ".join(f"{n.split('1')[0] if n.endswith('1') else n}={v:.2f}" for n,v in sd.items()))
hdr = f"    {'config':30} {'fp_judge':>9} {'fp_dec':>7} {'ff_clean':>9} {'hn-catch':>9}"
print(hdr); print("    " + "-"*(len(hdr)-4))
for k in rows:
    r = rows[k]
    print(f"    {r['name']:30} {r['fpj']:>8.1%} {r['fpd']:>7.0%} {r['ffc']:>8.1%} {r['hn']:>8.0%}")

# (2) G-gen: seed vs held-out detect-rate per checker (does positive-control predict held-out?)
print("\n[2] G-gen check (validates soundness T2): seed detect-rate vs held-out detect-rate")
print(f"    {'checker':10} {'seed(judge)':>12} {'held-out(judge)':>16} {'held-out(dec/cite)':>19}")
for rigor in ["strict", "moderate", "lenient"]:
    print(f"    {rigor:10} {detect(rigor,SEED_JUDGE):>12.2f} {detect(rigor,EVAL_JUDGE):>16.2f} {detect(rigor,EVAL_DEC):>19.2f}")

# (3) make-or-break #1: degraded-fraction sweep, ATTEST vs -positive-control (REAL)
print("\n[3] MAKE-OR-BREAK #1 (real): held-out judge false-pass vs #degraded(lenient) checkers")
print(f"    {'#lenient':>9} {'degraded-frac':>14} {'-PC fp_judge':>14} {'ATTEST fp_judge':>16}")
for nl in range(0, 5):
    p = pool(nl); frac = nl/len(p)
    r, _ = run_matrix(p)
    print(f"    {nl:>9} {frac:>13.0%} {r['b_iii_no_poscontrol']['fpj']:>13.1%} {r['ATTEST']['fpj']:>15.1%}")

# per-class held-out false-pass for ATTEST vs -PC at the representative pool (for the paper table)
print("\n[4] per-class held-out false-pass @ pool(2)  (ATTEST vs -positive-control)")
r2, sd2 = run_matrix(pool(2)); name2rig = dict(pool(2))
for cls in JUDGE_CLASSES + ["fabricated-citation"]:
    arts = [a for a in (EVAL_JUDGE+EVAL_DEC) if a["defect_class"] == cls]
    if not arts: continue
    def fp_for(cfgkey):
        cfg = CONFIGS()[cfgkey]; c = 0
        for a in arts:
            vs = {name: V[name2rig[name]].get(a["id"],"PASS") for name,_ in pool(2)}
            if gate_decision(a, vs, sd2, cfg, TAU, V["lenient"].get(a["id"],"PASS")) == "PASS": c += 1
        return c, len(arts)
    a_fp = fp_for("ATTEST"); b_fp = fp_for("b_iii_no_poscontrol")
    print(f"    {cls:28} ATTEST {a_fp[0]}/{a_fp[1]}   -PC {b_fp[0]}/{b_fp[1]}")

# ---------------- CSV export (numbers-from-CSV rule) ----------------
rows_m, sd_m = run_matrix(pool(2))
_wcsv("matrix.csv", ["config","fp_judge","fp_dec","ff_clean","hn_catch"],
      [[rows_m[k]["name"], f"{rows_m[k]['fpj']:.4f}", f"{rows_m[k]['fpd']:.4f}",
        f"{rows_m[k]['ffc']:.4f}", f"{rows_m[k]['hn']:.4f}"] for k in rows_m])
_wcsv("ggen.csv", ["checker","seed_judge","heldout_judge","heldout_citation"],
      [[r, f"{detect(r,SEED_JUDGE):.4f}", f"{detect(r,EVAL_JUDGE):.4f}", f"{detect(r,EVAL_DEC):.4f}"]
       for r in ["strict","moderate","lenient"]])
sweep_rows = []
for nl in range(0, 5):
    p = pool(nl); r, _ = run_matrix(p)
    sweep_rows.append([nl, f"{nl/len(p):.4f}", f"{r['b_iii_no_poscontrol']['fpj']:.4f}", f"{r['ATTEST']['fpj']:.4f}"])
_wcsv("sweep.csv", ["n_lenient","degraded_frac","noPC_fp_judge","ATTEST_fp_judge"], sweep_rows)
pc_rows = []
r2b, sd2b = run_matrix(pool(2)); n2r = dict(pool(2))
for cls in JUDGE_CLASSES + ["fabricated-citation"]:
    arts = [a for a in (EVAL_JUDGE+EVAL_DEC) if a["defect_class"] == cls]
    if not arts: continue
    def _fp(cfgkey):
        cfg = CONFIGS()[cfgkey]; c = 0
        for a in arts:
            vs = {name: V[n2r[name]].get(a["id"],"PASS") for name,_ in pool(2)}
            if gate_decision(a, vs, sd2b, cfg, TAU, V["lenient"].get(a["id"],"PASS")) == "PASS": c += 1
        return c
    pc_rows.append([cls, _fp("ATTEST"), _fp("b_iii_no_poscontrol"), len(arts)])
_wcsv("perclass.csv", ["class","ATTEST_fp","noPC_fp","n"], pc_rows)
print(f"\nCSVs written to {os.path.normpath(TBL)}: matrix.csv, ggen.csv, sweep.csv, perclass.csv")
