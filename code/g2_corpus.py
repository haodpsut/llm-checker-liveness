"""
G2 benchmark corpus + mutation operators for ATTEST.

Design constraints carried over from G1 (see G1-findings.md), enforced here:
  (1) defects must be SUBTLE (violation margin small) -- no blatant contradictions,
      which G1 round-1 showed every checker catches (degenerate).
  (2) seed and held-out(eval) instances are matched in class AND difficulty but are
      DIFFERENT draws (HD-2: never measure false-pass on the seed pool).
  (3) each artifact is tagged predicate_kind: 'judge' (needs checker reasoning:
      infeasible-after-arithmetic / overlapping-CI / scope-gap / antithetical-ablation)
      vs 'dec' (decidable, needs a tool: fabricated-citation). Positive-control is
      evaluated on the 'judge' classes; 'dec' classes are the tool's job.
  (4) difficulty is an explicit knob so we can stratify results.

Ground truth is objective by construction (we compute the arithmetic / CI overlap),
even though the CHECKER is asked to judge without a calculator. So labels are cheap
and exact while the checker task stays genuine judgment.

No LLM calls here: this only GENERATES the labeled corpus. Deterministic via a fixed
seed so the corpus is reproducible.
"""
import random

# ---- defect taxonomy -------------------------------------------------------
JUDGE_CLASSES = ["infeasible", "overlapping-ci-superiority", "scope-gap", "antithetical-ablation"]
DEC_CLASSES   = ["fabricated-citation"]
DEFECT_CLASSES = JUDGE_CLASSES + DEC_CLASSES

# plausible-but-FABRICATED citations (valid DOI shape, no impossible-id tell)
FAKE_CITES = [
    "Zhang & Lee, Neural Beam Prediction for LEO, IEEE TWC 2021, DOI 10.1109/TWC.2021.3098123",
    "Park, Choi & Ryu, Doppler-Aware Handover for NGSO, IEEE TVT 2022, DOI 10.1109/TVT.2022.3156789",
    "Ivanov & Sato, Federated Beam Scheduling, IEEE JSAC 2023, DOI 10.1109/JSAC.2023.3271044",
    "Mehta, Oh & Fernandez, Adaptive Link Control for Mega-Constellations, IEEE TCOM 2022, DOI 10.1109/TCOM.2022.3188902",
]
# REAL citations (checker that can look up should accept these)
REAL_CITES = [
    "Vaswani et al., Attention Is All You Need, NeurIPS 2017, DOI 10.48550/arXiv.1706.03762",
    "Kingma & Ba, Adam: A Method for Stochastic Optimization, ICLR 2015, DOI 10.48550/arXiv.1412.6980",
    "He et al., Deep Residual Learning, CVPR 2016, DOI 10.1109/CVPR.2016.90",
]

def _round(xs, d=2):
    return [round(x, d) for x in xs]

# ---- CLEAN templates (each returns text + is objectively PASS) --------------
def clean_alloc(rng):
    n = rng.choice([3, 4]); cap = 1.0
    xs = _round([rng.uniform(0.15, 0.30) for _ in range(n)])
    while sum(xs) > cap - 0.05:            # keep a clear feasible margin
        xs = _round([rng.uniform(0.12, 0.25) for _ in range(n)])
    return f"Claim: the {n} flows fit within the shared link. Evidence: they are allocated {', '.join(map(str,xs))} of a link with normalized capacity {cap}."

def clean_latency(rng):
    budget = rng.choice([50, 60, 80]); k = 3
    stages = [rng.randint(8, budget//k - 2) for _ in range(k)]
    while sum(stages) > budget - 6:
        stages = [rng.randint(6, budget//k - 3) for _ in range(k)]
    return f"Claim: the request meets its {budget} ms latency budget. Evidence: the pipeline stages take {', '.join(f'{s} ms' for s in stages)}."

def clean_compare_sig(rng):     # honest significant win: disjoint intervals
    ci = round(rng.uniform(0.01, 0.02), 2)
    base = round(rng.uniform(0.68, 0.74), 3)
    ours = round(base + rng.uniform(0.10, 0.15), 3)     # big gap >> 2*ci
    return f"Claim: our method significantly outperforms the baseline. Evidence: score {ours} +/- {ci} (ours) vs {base} +/- {ci} (baseline) over 10 seeds; the intervals do not overlap."

def clean_compare_comparable(rng):   # honest 'comparable', no superiority claim
    ci = round(rng.uniform(0.02, 0.03), 3)
    base = round(rng.uniform(0.80, 0.85), 3)
    ours = round(base + rng.uniform(-0.005, 0.005), 3)
    return f"Claim: our method performs comparably to the baseline (we do NOT claim superiority). Evidence: score {ours} +/- {ci} (ours) vs {base} +/- {ci} (baseline) over 10 seeds; intervals overlap."

def clean_citation(rng):
    return f"Claim: this technique is established prior art we build on. Evidence: we cite '{rng.choice(REAL_CITES)}'."

def clean_ablation_keydriver(rng):
    drop = round(rng.uniform(6.0, 15.0), 1)
    return f"Claim: the attention module is a key driver of performance. Evidence: the ablation table shows removing it drops the score by {drop}% (well beyond the +/-0.3% seed noise)."

def clean_robust(rng):
    return "Claim: our policy is robust to jamming. Evidence: Table 5 reports performance under three jamming intensities (light, moderate, severe), with graceful degradation at each."

CLEAN_GENS = [clean_alloc, clean_latency, clean_compare_sig, clean_compare_comparable,
              clean_citation, clean_ablation_keydriver, clean_robust]

# ---- MUTATION operators (inject a defect; ground truth becomes FAIL) --------
# each takes rng + difficulty in {'subtle','moderate'} and returns (text, class, predicate_kind)
def mut_infeasible(rng, difficulty):
    margin = {"subtle": 0.05, "moderate": 0.20}[difficulty]   # how far over the line
    n = rng.choice([3, 4]); cap = 1.0
    xs = _round([rng.uniform(0.20, 0.34) for _ in range(n)])
    # scale so the sum sits just above capacity by ~margin
    s = sum(xs); xs = _round([x * (cap + margin) / s for x in xs])
    return (f"Claim: the {n} flows fit within the shared link. Evidence: they are allocated {', '.join(map(str,xs))} of a link with normalized capacity {cap}.",
            "infeasible", "judge")

def mut_infeasible_latency(rng, difficulty):
    over = {"subtle": 3, "moderate": 15}[difficulty]
    budget = rng.choice([50, 60]); k = 3
    total = budget + over
    a = rng.randint(total//3 - 4, total//3 + 4); b = rng.randint(total//3 - 4, total//3 + 4); c = total - a - b
    return (f"Claim: the request meets its {budget} ms latency budget. Evidence: the pipeline stages take {a} ms, {b} ms, and {c} ms.",
            "infeasible", "judge")

def mut_overlap_super(rng, difficulty):
    ci = round(rng.uniform(0.03, 0.05), 3)
    gap = {"subtle": ci * 0.4, "moderate": ci * 0.9}[difficulty]   # gap < 2*ci => overlap
    base = round(rng.uniform(0.75, 0.82), 3)
    ours = round(base + gap, 3)
    return (f"Claim: our method is statistically significantly better. Evidence: F1 {ours} +/- {ci} (ours) vs {base} +/- {ci} (baseline) over 10 seeds.",
            "overlapping-ci-superiority", "judge")

def mut_scope_gap(rng, difficulty):
    tested, claimed = rng.choice([("the interference-free channel", "jamming"),
                                  ("clear-sky conditions", "heavy rain fade"),
                                  ("a single-user setting", "dense multi-user contention")])
    hedge = {"subtle": "Table 5 reports strong results on " + tested + " only",
             "moderate": "we evaluate exclusively on " + tested}[difficulty]
    return (f"Claim: our policy is robust to {claimed}. Evidence: {hedge}; no {claimed} condition is tested.",
            "scope-gap", "judge")

def mut_antithetical(rng, difficulty):
    # defect = ablation effect is WITHIN noise (0.3%) yet claim says 'key driver'.
    # subtle = effect just under noise (hard to call); moderate = clearly negligible.
    eff = {"subtle": round(rng.uniform(0.15, 0.29), 2), "moderate": round(rng.uniform(0.0, 0.10), 2)}[difficulty]
    return (f"Claim: the quantum component is the key novelty and drives the gains. Evidence: the ablation shows removing it changes the score by {eff}% (the reported seed noise is +/-0.3%).",
            "antithetical-ablation", "judge")

def mut_fabricated_citation(rng, difficulty):
    # difficulty has little effect: fabrication requires external lookup regardless
    return (f"Claim: this technique is established prior art we build on. Evidence: we cite '{rng.choice(FAKE_CITES)}'.",
            "fabricated-citation", "dec")

JUDGE_MUTS = [mut_infeasible, mut_infeasible_latency, mut_overlap_super, mut_scope_gap, mut_antithetical]
DEC_MUTS   = [mut_fabricated_citation]

# ---- corpus generation -----------------------------------------------------
def build_corpus(seed=20260728, n_clean=18, per_class_seed=3, per_class_eval=6):
    rng = random.Random(seed)
    arts = []; k = 0
    def add(text, cls, kind, is_seed, difficulty):
        nonlocal k
        k += 1
        arts.append(dict(
            id=f"G2-{k:03d}", text=text, defect_class=cls, predicate_kind=kind,
            is_seed=is_seed, difficulty=difficulty,
            ground_truth=("PASS" if cls == "clean" else "FAIL")))
    # clean pool
    for _ in range(n_clean):
        g = rng.choice(CLEAN_GENS)
        add(g(rng), "clean", "judge", False, "n/a")
    # judgment-class defects: seed + eval, subtle-dominant (enforce constraint 1)
    for mut in JUDGE_MUTS:
        for _ in range(per_class_seed):
            diff = rng.choice(["subtle", "subtle", "moderate"])
            t, cls, kind = mut(rng, diff); add(t, cls, kind, True, diff)
        for _ in range(per_class_eval):
            diff = rng.choice(["subtle", "subtle", "moderate"])
            t, cls, kind = mut(rng, diff); add(t, cls, kind, False, diff)
    # decidable-class defects (fabricated-citation): also seed+eval but tagged 'dec'
    for mut in DEC_MUTS:
        for _ in range(per_class_seed):
            t, cls, kind = mut(rng, "subtle"); add(t, cls, kind, True, "subtle")
        for _ in range(per_class_eval):
            t, cls, kind = mut(rng, "subtle"); add(t, cls, kind, False, "subtle")
    return arts

CORPUS = build_corpus()
SEED_JUDGE   = [a for a in CORPUS if a["is_seed"] and a["predicate_kind"] == "judge"]
EVAL_JUDGE   = [a for a in CORPUS if (not a["is_seed"]) and a["defect_class"] in JUDGE_CLASSES]
EVAL_DEC     = [a for a in CORPUS if (not a["is_seed"]) and a["defect_class"] in DEC_CLASSES]
CLEAN_POOL   = [a for a in CORPUS if a["defect_class"] == "clean"]

if __name__ == "__main__":
    from collections import Counter
    print(f"corpus size: {len(CORPUS)}")
    print(f"  clean            : {len(CLEAN_POOL)}")
    print(f"  seed (judge)     : {len(SEED_JUDGE)}")
    print(f"  eval judge-class : {len(EVAL_JUDGE)}")
    print(f"  eval dec-class   : {len(EVAL_DEC)}")
    print("  by class:", dict(Counter(a["defect_class"] for a in CORPUS)))
    print("  by difficulty (defects):", dict(Counter(a["difficulty"] for a in CORPUS if a["defect_class"] != "clean")))
    print("\n  sample subtle defects:")
    shown = set()
    for a in CORPUS:
        if a["defect_class"] != "clean" and a["difficulty"] == "subtle" and a["defect_class"] not in shown:
            shown.add(a["defect_class"]); print(f"   [{a['defect_class']}] {a['text']}")
