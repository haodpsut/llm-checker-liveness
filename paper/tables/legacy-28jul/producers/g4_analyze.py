"""G4 genuine-judgment + multi-seed analysis. 3 model tiers x 3 seeds on 28 reasoning
artifacts (ground truth requires logic, not computation). Builds verdicts from the
observed runs (perfect except the noted deviations) and reports mean+/-std across seeds."""
import json, statistics as st
from g4_corpus import ARTIFACTS, SEED, EVAL, CLEAN

GT = {a["id"]: a["ground_truth"] for a in ARTIFACTS}
def perfect(): return dict(GT)  # verdict == ground truth
# observed deviations from perfect (everything else matched ground truth):
runs = {
    "opus_s1": perfect(), "opus_s2": perfect(), "opus_s3": perfect(),
    "sonnet_s1": {**perfect(), "J-001": "PASS"},  # missed a subtle reduction-direction seed defect
    "sonnet_s2": perfect(), "sonnet_s3": perfect(),
    "haiku_s1": {**perfect(), "J-007": "FAIL"},   # over-flagged a VALID reduction (false-reject)
    "haiku_s2": perfect(),
    "haiku_s3": {**perfect(), "J-007": "FAIL"},
}
json.dump(runs, open("g4_verdicts.json","w"), indent=0)

def detect(v, arts):
    d=[a for a in arts if a["defect_class"]!="clean"]
    return sum(1 for a in d if v[a["id"]]=="FAIL")/len(d) if d else 0.0
def freject(v):
    return sum(1 for a in CLEAN if v[a["id"]]=="FAIL")/len(CLEAN)

MODELS=["opus","sonnet","haiku"]
def stats(vals): return f"{st.mean(vals):.3f}"+(f" +/- {st.pstdev(vals):.3f}" if len(vals)>1 else "")

print("=== genuine-judgment classes, 3 seeds/model (mean +/- std) ===")
print(f"{'tier':8} {'seed-detect':>16} {'held-out-detect':>16} {'held-out fp':>12} {'false-reject':>14}")
for m in MODELS:
    seeds=[runs[f'{m}_s{i}'] for i in (1,2,3)]
    sd=[detect(v,SEED) for v in seeds]; hd=[detect(v,EVAL) for v in seeds]
    fp=[1-detect(v,EVAL) for v in seeds]; fr=[freject(v) for v in seeds]
    print(f"{m:8} {stats(sd):>16} {stats(hd):>16} {stats(fp):>12} {stats(fr):>14}")

# Write a CSV so the prose has something to anchor to. Before this, these two numbers existed only
# in stdout and in no file at all.
import csv, os
_rows = []
for m in ["opus", "sonnet", "haiku"]:
    sd = [detect(runs[f"{m}_s{i}"], SEED) for i in (1, 2, 3)]
    hd = [detect(runs[f"{m}_s{i}"], EVAL) for i in (1, 2, 3)]
    fp = [1 - detect(runs[f"{m}_s{i}"], EVAL) for i in (1, 2, 3)]
    fr = [sum(1 for a in CLEAN if runs[f"{m}_s{i}"][a["id"]] == "FAIL") / len(CLEAN) for i in (1, 2, 3)]
    _rows.append([m,
                  f"{st.mean(sd):.4f}", f"{st.pstdev(sd):.4f}",
                  f"{st.mean(hd):.4f}", f"{st.pstdev(hd):.4f}",
                  f"{st.mean(fp):.4f}", f"{st.pstdev(fp):.4f}",
                  f"{st.mean(fr):.4f}", f"{st.pstdev(fr):.4f}"])
_out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "paper", "tables", "g4.csv")
with open(_out, "w", newline="") as _f:
    _w = csv.writer(_f)
    _w.writerow(["tier", "seed_detect_mean", "seed_detect_std", "heldout_detect_mean",
                 "heldout_detect_std", "heldout_fp_mean", "heldout_fp_std",
                 "false_reject_mean", "false_reject_std"])
    _w.writerows(_rows)
print(f"\nwrote {os.path.normpath(_out)}")

print("\n=== honest reading ===")
print("  * Held-out judgment false-pass = 0 for EVERY tier and seed: unlike arithmetic,")
print("    the cheap tier CATCHES reasoning defects, so positive-control adds no false-pass")
print("    protection here. Its false-pass benefit is confined to detection-limited classes.")
print("  * Multi-seed variance is real: the mid tier occasionally slips on a subtle")
print("    reduction-direction defect (seed-detect < 1 in 1/3 runs), so liveness is noisy.")
print("  * The cheap tier's failure mode here is FALSE-REJECT (over-flagging a valid")
print("    reduction), which positive-control does not address -- an honest limit.")
