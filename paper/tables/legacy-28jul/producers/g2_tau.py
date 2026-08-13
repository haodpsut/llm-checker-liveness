"""tau-sensitivity of the liveness threshold, from REAL verdicts.
On the representative pool (strict 1.0, moderate 0.6, 2x lenient 0.4), sweep tau and
record ATTEST held-out false-pass and false-reject. Writes ../paper/tables/tau.csv."""
import os, json, csv
from g2_corpus import SEED_JUDGE, EVAL_JUDGE, CLEAN_POOL
from g2_gates import CONFIGS, gate_decision, SUPERIORITY_CLASSES

V = json.load(open(os.path.join(os.path.dirname(__file__), "g2_verdicts.json")))
POOL = [("strict1","strict"), ("moderate1","moderate"), ("lenient1","lenient"), ("lenient2","lenient")]
name2rig = dict(POOL)

def detect(rig, arts):
    d = [a for a in arts if a["defect_class"] != "clean"]
    return sum(1 for a in d if V[rig].get(a["id"]) == "FAIL") / len(d)

seed_detect = {n: detect(r, SEED_JUDGE) for n, r in POOL}
cfg = CONFIGS()["ATTEST"]
nj, nc = len(EVAL_JUDGE), len(CLEAN_POOL)

rows = []
for i in range(0, 21):
    tau = i / 20
    fp = sum(1 for a in EVAL_JUDGE
             if gate_decision(a, {n: V[name2rig[n]].get(a["id"],"PASS") for n,_ in POOL},
                              seed_detect, cfg, tau, V["lenient"].get(a["id"],"PASS")) == "PASS")
    ff = sum(1 for a in CLEAN_POOL
             if gate_decision(a, {n: V[name2rig[n]].get(a["id"],"PASS") for n,_ in POOL},
                              seed_detect, cfg, tau, V["lenient"].get(a["id"],"PASS")) == "FAIL")
    n_live = sum(1 for n,_ in POOL if seed_detect[n] >= tau)
    rows.append([f"{tau:.2f}", f"{fp/nj:.4f}", f"{ff/nc:.4f}", n_live])

TBL = os.path.join(os.path.dirname(__file__), "..", "paper", "tables")
with open(os.path.join(TBL, "tau.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["tau","fp_judge","ff_clean","n_live"]); w.writerows(rows)
print("wrote tau.csv; seed_detect=", {n: round(v,2) for n,v in seed_detect.items()})
for r in rows[::4]:
    print("  tau", r[0], "fp", r[1], "ff", r[2], "live", r[3])
