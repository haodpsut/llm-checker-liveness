"""Generate LaTeX table bodies + figure CSVs for the real-model (Path A) paper rewrite.
All numbers from g3_verdicts.json (3 real model tiers). Emits inline-ready .tex row bodies
(no \\input -- acmart+booktabs breaks on \\input) and CSVs under paper/tables & paper/figs."""
import os, json, csv
from g2_corpus import SEED_JUDGE, EVAL_JUDGE, EVAL_DEC, CLEAN_POOL, JUDGE_CLASSES
from g2_gates import CONFIGS, gate_decision, SUPERIORITY_CLASSES

HERE = os.path.dirname(__file__)
TBL = os.path.join(HERE, "..", "paper", "tables")
FIG = os.path.join(HERE, "..", "paper", "figs")
V = json.load(open(os.path.join(HERE, "g3_verdicts.json")))
MODELS = ["opus", "sonnet", "haiku"]
nice = {"infeasible":"infeasible","overlapping-ci-superiority":"overlap-CI","scope-gap":"scope-gap",
        "antithetical-ablation":"ablation","fabricated-citation":"citation"}

def detect(model, arts):
    d=[a for a in arts if a["defect_class"]!="clean"]
    return sum(1 for a in d if V[model].get(a["id"])=="FAIL")/len(d) if d else 0.0

# ---- Table A: real-model capability gradient (model x seed/held/per-class) ----
rows=[]; grad_rows=[]
for m in MODELS:
    percls=[detect(m,[a for a in EVAL_JUDGE if a['defect_class']==c]) for c in JUDGE_CLASSES]
    per=" & ".join(f"{v:.2f}" for v in percls)
    cite=detect(m, EVAL_DEC)
    rows.append(f"{m} & {detect(m,SEED_JUDGE):.2f} & {detect(m,EVAL_JUDGE):.2f} & {per} & {cite:.2f} \\\\")
    grad_rows.append([m, f"{detect(m,SEED_JUDGE):.4f}", f"{detect(m,EVAL_JUDGE):.4f}"]
                     + [f"{v:.4f}" for v in percls] + [f"{cite:.4f}"])
open(os.path.join(TBL,"g3-gradient.tex"),"w").write("\n".join(rows)+"\n")

# These per-tier numbers are quoted DIRECTLY in the prose but never passed through a CSV, so the
# claim manifest had nothing to anchor them to. Writing them out changes no value; it only adds a
# path along which they can be checked.
def _wcsv(name, header, rws, d=TBL):
    with open(os.path.join(d, name), "w", newline="") as f:
        w=csv.writer(f); w.writerow(header); w.writerows(rws)

_wcsv("g3-gradient.csv", ["model","seed_judge","heldout_judge"]+list(JUDGE_CLASSES)+["citation"], grad_rows)

# ---- Table B: G-gen honesty (seed vs held per model) ----
rows=[f"{m} & {detect(m,SEED_JUDGE):.2f} & {detect(m,EVAL_JUDGE):.2f} & {detect(m,SEED_JUDGE)-detect(m,EVAL_JUDGE):+.2f} \\\\" for m in MODELS]
open(os.path.join(TBL,"g3-ggen.tex"),"w").write("\n".join(rows)+"\n")
_wcsv("g3-ggen.csv", ["model","seed_judge","heldout_judge","gap"],
      [[m, f"{detect(m,SEED_JUDGE):.4f}", f"{detect(m,EVAL_JUDGE):.4f}",
        f"{detect(m,SEED_JUDGE)-detect(m,EVAL_JUDGE):+.4f}"] for m in MODELS])

# ---- helper: run a pool (repeats = correlated bloc) ----
def run_pool(pool_models, tau, cfgkey):
    names=[f"{m}{i}" for i,m in enumerate(pool_models)]; n2r=dict(zip(names,pool_models))
    sd={n:detect(n2r[n],SEED_JUDGE) for n in names}
    cfg=CONFIGS()[cfgkey]
    fpj=sum(1 for a in EVAL_JUDGE if gate_decision(a,{n:V[n2r[n]].get(a["id"],"PASS") for n in names},sd,cfg,tau,V["haiku"].get(a["id"],"PASS"))=="PASS")
    fpd=sum(1 for a in EVAL_DEC if gate_decision(a,{n:V[n2r[n]].get(a["id"],"PASS") for n in names},sd,cfg,tau,V["haiku"].get(a["id"],"PASS"))=="PASS")
    ffc=sum(1 for a in CLEAN_POOL if gate_decision(a,{n:V[n2r[n]].get(a["id"],"PASS") for n in names},sd,cfg,tau,V["haiku"].get(a["id"],"PASS"))=="FAIL")
    return fpj/len(EVAL_JUDGE), fpd/len(EVAL_DEC), ffc/len(CLEAN_POOL)

# ---- Table C: 8-config matrix on the WEAK-MAJORITY pool (opus + 3 haiku), tau=0.85 ----
POOL=["opus","haiku","haiku","haiku"]; TAU=0.85
order=["ATTEST","b_iii_no_poscontrol","b_v_no_honestneg","b_vi_no_agreement","b_ii_single_judge","b_i_self_review","b_vii_no_verify"]
rows=[]; mat_rows=[]
for k in order:
    fpj,fpd,ffc=run_pool(POOL,TAU,k)
    name=CONFIGS()[k]["name"]; bold=r"\bfseries " if k=="ATTEST" else ""
    rows.append(f"{bold}{name} & {bold}{fpj*100:.1f} & {bold}{fpd*100:.0f} & {bold}{ffc*100:.1f} \\\\")
    mat_rows.append([name, f"{fpj:.4f}", f"{fpd:.4f}", f"{ffc:.4f}"])
open(os.path.join(TBL,"g3-matrix.tex"),"w").write("\n".join(rows)+"\n")
_wcsv("g3-matrix.csv", ["config","fp_judge","fp_dec","ff_clean"], mat_rows)

# ---- Figure CSV: make-or-break across pool compositions (balanced -> weak-majority) ----
comps=[("O+S+H",["opus","sonnet","haiku"]),("O+H+H",["opus","haiku","haiku"]),
       ("O+3H",["opus","haiku","haiku","haiku"]),("S+3H",["sonnet","haiku","haiku","haiku"]),
       ("O+4H",["opus"]+["haiku"]*4)]
with open(os.path.join(FIG,"g3-regime.csv"),"w",newline="") as f:
    w=csv.writer(f); w.writerow(["pool","weak_frac","noPC_fp","ATTEST_fp"])
    for tag,pm in comps:
        wk=sum(1 for m in pm if m=="haiku")/len(pm)
        npc,_,_=run_pool(pm,0.0,"b_iii_no_poscontrol")   # tau=0 -> trust all
        att,_,_=run_pool(pm,0.85,"ATTEST")               # tau=0.85 -> screen haiku
        w.writerow([tag,f"{wk:.3f}",f"{npc:.4f}",f"{att:.4f}"])

print("wrote g3-gradient.tex, g3-ggen.tex, g3-matrix.tex, figs/g3-regime.csv")
for fn in ["g3-gradient.tex","g3-matrix.tex","g3-ggen.tex"]:
    print(f"--- {fn} ---"); print(open(os.path.join(TBL,fn)).read())
print("--- g3-regime.csv ---"); print(open(os.path.join(FIG,"g3-regime.csv")).read())
