"""Emit LaTeX table bodies from the real CSVs (numbers-from-CSV, no hand typing)."""
import os, csv
TBL = os.path.join(os.path.dirname(__file__), "..", "paper", "tables")

def rd(name):
    return list(csv.DictReader(open(os.path.join(TBL, name))))

def pct(x): return f"{float(x)*100:.1f}"
def pct0(x): return f"{float(x)*100:.0f}"

# ---- Table 1: 8-config matrix ----
order = ["ATTEST","-positive-control","-honest-neg-block","-human-transition (auto-chain)",
         "-multichecker (single)","single LLM-judge","soft self-review","no-verification"]
m = {r["config"]: r for r in rd("matrix.csv")}
lines = []
for name in order:
    r = m[name]
    disp = name.replace("&","\\&")
    bold = r"\bfseries " if name == "ATTEST" else ""
    lines.append(f"{bold}{disp} & {bold}{pct(r['fp_judge'])} & {bold}{pct0(r['fp_dec'])} & "
                 f"{bold}{pct(r['ff_clean'])} & {bold}{pct0(r['hn_catch'])} \\\\")
open(os.path.join(TBL,"tab-matrix.tex"),"w").write("\n".join(lines)+"\n")

# ---- Table 2: G-gen ----
g = rd("ggen.csv")
lines = [f"{r['checker']} & {float(r['seed_judge']):.2f} & {float(r['heldout_judge']):.2f} & {float(r['heldout_citation']):.2f} \\\\" for r in g]
open(os.path.join(TBL,"tab-ggen.tex"),"w").write("\n".join(lines)+"\n")

# ---- Table 3: per-class held-out false-pass ----
p = rd("perclass.csv")
nice = {"infeasible":"infeasible (arithmetic)","overlapping-ci-superiority":"overlapping-CI superiority",
        "scope-gap":"scope gap","antithetical-ablation":"antithetical ablation","fabricated-citation":"fabricated citation"}
lines = [f"{nice.get(r['class'],r['class'])} & {r['n']} & {r['ATTEST_fp']} & {r['noPC_fp']} \\\\" for r in p]
open(os.path.join(TBL,"tab-perclass.tex"),"w").write("\n".join(lines)+"\n")

# ---- Table 4: benchmark composition (from the corpus) ----
import json
from g2_corpus import CORPUS, JUDGE_CLASSES
nice = {"infeasible":"infeasible (arithmetic)","overlapping-ci-superiority":"overlapping-CI superiority",
        "scope-gap":"scope gap","antithetical-ablation":"antithetical ablation","fabricated-citation":"fabricated citation"}
def count(cls, **kw):
    return sum(1 for a in CORPUS if a["defect_class"]==cls and all(a.get(k)==v for k,v in kw.items()))
lines=[]; compose_rows=[]
for cls in JUDGE_CLASSES+["fabricated-citation"]:
    kind = "judgment" if cls in JUDGE_CLASSES else "decidable"
    seed = count(cls, is_seed=True); ev = sum(1 for a in CORPUS if a["defect_class"]==cls and not a["is_seed"])
    sub = count(cls, difficulty="subtle"); mod = count(cls, difficulty="moderate")
    lines.append(f"{nice[cls]} & {kind} & {seed} & {ev} & {sub} & {mod} \\\\")
    compose_rows.append([cls, kind, seed, ev, sub, mod])
# clean-control count is reported in prose; keep this table a uniform 3-rule table
open(os.path.join(TBL,"tab-compose.tex"),"w").write("\n".join(lines)+"\n")

# The numbers in these two tables never passed through a CSV, so the claim manifest had nothing to
# anchor them to and the number-verification gate could not check them. Writing them out gives every
# number in the paper a data cell to be checked against. The values are unchanged; only the path is new.
def _wcsv(name, header, rows):
    with open(os.path.join(TBL, name), "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)

_wcsv("compose.csv", ["class","kind","n_seed","n_heldout","n_subtle","n_moderate"], compose_rows)
# corpus totals, so the counts quoted in prose have something to anchor to
_wcsv("corpus.csv", ["quantity","n"], [
    ["total",   len(CORPUS)],
    ["clean",   sum(1 for a in CORPUS if a["defect_class"] == "clean")],
    ["defective", sum(1 for a in CORPUS if a["defect_class"] != "clean")],
    ["defective_seed",    sum(1 for a in CORPUS if a["defect_class"] != "clean" and a["is_seed"])],
    ["defective_heldout", sum(1 for a in CORPUS if a["defect_class"] != "clean" and not a["is_seed"])],
])

# ---- Table 5: per-class detect-rate by checker (held-out), from verdicts ----
V = json.load(open(os.path.join(os.path.dirname(__file__),"g2_verdicts.json")))
def detect(rig, cls):
    arts=[a for a in CORPUS if a["defect_class"]==cls and not a["is_seed"]]
    return sum(1 for a in arts if V[rig].get(a["id"])=="FAIL")/len(arts)
lines=[]; detect_rows=[]
for cls in JUDGE_CLASSES+["fabricated-citation"]:
    s_, m_, l_ = detect('strict',cls), detect('moderate',cls), detect('lenient',cls)
    lines.append(f"{nice[cls]} & {s_:.2f} & {m_:.2f} & {l_:.2f} \\\\")
    detect_rows.append([cls, f"{s_:.4f}", f"{m_:.4f}", f"{l_:.4f}"])
open(os.path.join(TBL,"tab-detect.tex"),"w").write("\n".join(lines)+"\n")
_wcsv("detect.csv", ["class","strict","moderate","lenient"], detect_rows)

print("wrote tab-matrix.tex, tab-ggen.tex, tab-perclass.tex, tab-compose.tex, tab-detect.tex")
print("wrote detect.csv, compose.csv, corpus.csv")
for f in ["tab-matrix.tex","tab-ggen.tex","tab-perclass.tex"]:
    print("---",f); print(open(os.path.join(TBL,f)).read())
