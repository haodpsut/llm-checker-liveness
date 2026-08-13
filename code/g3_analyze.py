"""
Path-A analysis: checkers are three REAL model tiers (opus/sonnet/haiku), one neutral
prompt, so heterogeneity comes from model CAPABILITY, not prompt personas.

Reports, all from g3_verdicts.json:
  (1) per-model detect-rate by class + seed vs held-out (is there a real capability gradient?);
  (2) inter-model ERROR CORRELATION on held-out defects (the Byzantine-independence question:
      do same-family models miss the SAME defects? high correlation is a HONEST negative to report);
  (3) positive-control make-or-break with real tiers: screen models by seed liveness, does
      held-out false-pass drop? (tau chosen between the tiers' seed-detect rates).
"""
import os, json, itertools
from g2_corpus import SEED_JUDGE, EVAL_JUDGE, EVAL_DEC, CLEAN_POOL, JUDGE_CLASSES
from g2_gates import CONFIGS, gate_decision, SUPERIORITY_CLASSES

HERE = os.path.dirname(__file__)
V = json.load(open(os.path.join(HERE, "g3_verdicts.json")))   # {"opus":{id:PASS/FAIL},...}
MODELS = ["opus", "sonnet", "haiku"]

def detect(model, arts):
    d = [a for a in arts if a["defect_class"] != "clean"]
    return sum(1 for a in d if V[model].get(a["id"]) == "FAIL") / len(d) if d else 0.0

def miss_set(model, arts):
    # defects this model WRONGLY passed (missed)
    return {a["id"] for a in arts if a["defect_class"] != "clean" and V[model].get(a["id"]) == "PASS"}

print("=== (1) per-model detect-rate (real capability gradient?) ===")
print(f"{'model':8} {'seed(judge)':>12} {'held(judge)':>12} {'held(cite)':>11} " +
      "  ".join(f"{c[:10]:>11}" for c in JUDGE_CLASSES))
for m in MODELS:
    per = "  ".join(f"{detect(m,[a for a in EVAL_JUDGE if a['defect_class']==c]):>11.2f}" for c in JUDGE_CLASSES)
    print(f"{m:8} {detect(m,SEED_JUDGE):>12.2f} {detect(m,EVAL_JUDGE):>12.2f} {detect(m,EVAL_DEC):>11.2f} {per}")

print("\n=== (2) inter-model error correlation on held-out defects ===")
allheld = EVAL_JUDGE + EVAL_DEC
misses = {m: miss_set(m, allheld) for m in MODELS}
ndef = len([a for a in allheld if a["defect_class"] != "clean"])
for a_, b_ in itertools.combinations(MODELS, 2):
    A, B = misses[a_], misses[b_]
    inter, uni = len(A & B), len(A | B)
    jac = inter / uni if uni else 0.0
    # phi-like: co-miss vs expected under independence
    pa, pb = len(A)/ndef, len(B)/ndef
    exp_comiss = pa * pb * ndef
    print(f"  {a_:6} vs {b_:6}: |missA|={len(A)} |missB|={len(B)} co-miss={inter} "
          f"(indep-expected {exp_comiss:.1f})  Jaccard={jac:.2f}")
print("  -> co-miss >> independent-expected means correlated blind spots (same-family limitation).")

print("\n=== (3) make-or-break: BALANCED pool (1 of each tier) -- positive-control NOT needed ===")
seed_detect_all = {m: detect(m, SEED_JUDGE) for m in MODELS}
print("  seed detect:", {m: round(v,2) for m,v in seed_detect_all.items()})
nj = len(EVAL_JUDGE)
def run_pool(pool_models, tau):
    # pool_models: list of model names (repeats allowed = correlated bloc, same verdicts)
    names = [f"{m}{i}" for i,m in enumerate(pool_models)]
    n2r = dict(zip(names, pool_models))
    sd = {n: detect(n2r[n], SEED_JUDGE) for n in names}
    out = {}
    for cfgkey in ["ATTEST", "b_iii_no_poscontrol"]:
        cfg = CONFIGS()[cfgkey]
        fp = sum(1 for a in EVAL_JUDGE
                 if gate_decision(a, {n: V[n2r[n]].get(a["id"],"PASS") for n in names},
                                  sd, cfg, tau, V["haiku"].get(a["id"],"PASS")) == "PASS")
        out[cfgkey] = fp/nj
    live = [n for n in names if sd[n] >= tau]
    return out, live
for tau in [0.0, 0.9]:
    o,live = run_pool(["opus","sonnet","haiku"], tau)
    print(f"  tau={tau:.1f}: -PC={o['b_iii_no_poscontrol']:.1%}  ATTEST={o['ATTEST']:.1%}  ({len(live)} live)")

print("\n=== (4) make-or-break: WEAK-MAJORITY pool (1 strong + correlated cheap bloc) ===")
print("  realistic 'cheap models at scale': the competent checker is a MINORITY.")
print(f"  {'pool':22} {'tau':>4} {'-PC fp':>8} {'ATTEST fp':>10} {'live':>5}")
for pool_models in [["opus","haiku","haiku"], ["opus","haiku","haiku","haiku"], ["sonnet","haiku","haiku","haiku"]]:
    for tau in [0.0, 0.85]:
        o, live = run_pool(pool_models, tau)
        tag = "+".join('O' if 'opus' in m else 'S' if 'sonnet' in m else 'H' for m in pool_models)
        print(f"  {tag:22} {tau:>4.2f} {o['b_iii_no_poscontrol']:>8.1%} {o['ATTEST']:>10.1%} {len(live):>5}")

print("\n=== (5) G-gen honesty: seed vs held-out per model (does seed OVER-estimate?) ===")
for m in MODELS:
    s,h = detect(m,SEED_JUDGE), detect(m,EVAL_JUDGE)
    print(f"  {m:8} seed={s:.2f}  held={h:.2f}  gap={s-h:+.2f}  {'(seed over-estimates)' if s-h>0.05 else '(ok)'}")
