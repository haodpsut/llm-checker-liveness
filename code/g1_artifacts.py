"""
G1 smoke-test artifacts for ATTEST. Each artifact is a short research-claim +
evidence pair with a KNOWN ground-truth label. Defects span 3 classes and are
split into a SEED set (for positive-control / checker-liveness) and a HELD-OUT
set (for false-pass measurement, per HD-2: never evaluate false-pass on seeds).

label: 'clean' or the defect class. is_seed marks the positive-control set.
Ground truth is unambiguous by construction so the make-or-break is measurable.
"""

ARTIFACTS = [
    # ---- CLEAN (4) ----
    dict(id="A1", label="clean", is_seed=False, text=(
        "Claim: our method reduces latency by 12%. Evidence: Table 2 reports "
        "mean latency 88ms (ours) vs 100ms (baseline) over 20 runs, 88/100 = 0.88, a 12% reduction.")),
    dict(id="A2", label="clean", is_seed=False, text=(
        "Claim: the scheduler is feasible. Evidence: the constraint checker reports "
        "all 5 hard constraints satisfied at 100%, and the solution serves every request within its window.")),
    dict(id="A3", label="clean", is_seed=False, text=(
        "Claim: KAN and MLP perform comparably. Evidence: macro-F1 is 0.853 (KAN) vs 0.852 (MLP); "
        "we state they are indistinguishable and do NOT claim superiority.")),
    dict(id="A4", label="clean", is_seed=False, text=(
        "Claim: we cite Vaswani et al. 2017 for the transformer architecture. Evidence: "
        "'Attention Is All You Need', NeurIPS 2017, which introduces the transformer. Citation supports the claim.")),

    # ---- SEED defects (3, one per class) : positive-control ----
    dict(id="S1", label="fabricated-citation", is_seed=True, text=(
        "Claim: prior work shows quantum-inspired search beats CMA-ES on this task. Evidence: "
        "we cite 'Nguyen & Kwon, Quantum-Inspired Superiority, IEEE TQE 2023, DOI 10.1109/TQE.2023.9981234'.")),  # fabricated DOI
    dict(id="S2", label="infeasible-number", is_seed=True, text=(
        "Claim: the scheduler serves 100% of demand. Evidence: Fig 8 reports data-completion of 0.19, "
        "and the problem requires serving 100% of demand.")),  # 0.19 contradicts 100%
    dict(id="S3", label="unsupported-superiority", is_seed=True, text=(
        "Claim: our method outperforms all baselines. Evidence: Table 4 shows our score 89 vs "
        "the strongest baseline (CMA-ES) 158; higher is better.")),  # 89 < 158, so it LOSES

    # ---- HELD-OUT defects (4, different instances, same classes) : false-pass eval ----
    dict(id="H1", label="fabricated-citation", is_seed=False, text=(
        "Claim: federated KAN was first applied to satellite traffic by us. Evidence: we cite "
        "'Smith et al., FedKAN-Sat, arXiv:2499.00001, 2025' as the only prior work, which we surpass.")),  # fake arxiv id 2499
    dict(id="H2", label="infeasible-number", is_seed=False, text=(
        "Claim: every satellite link stays within the energy budget. Evidence: Table 3 shows satellite 7 "
        "consumes 420 J while its stated budget is 300 J.")),  # 420 > 300 violates
    dict(id="H3", label="unsupported-superiority", is_seed=False, text=(
        "Claim: our policy is state-of-the-art and Pareto-optimal. Evidence: it reaches gap +4.4% while "
        "the learned baseline reaches +1.0%; lower gap is better.")),  # +4.4 worse than +1.0
    dict(id="H4", label="unsupported-superiority", is_seed=False, text=(
        "Claim: the quantum component is the key novelty and drives the gains. Evidence: the ablation "
        "table shows removing the quantum component changes the score by +0.06% (within noise).")),  # ablation shows no effect
]

SEED = [a for a in ARTIFACTS if a["is_seed"]]
HELDOUT = [a for a in ARTIFACTS if (not a["is_seed"]) and a["label"] != "clean"]
CLEAN = [a for a in ARTIFACTS if a["label"] == "clean"]

def ground_truth(aid):
    for a in ARTIFACTS:
        if a["id"] == aid:
            return "FAIL" if a["label"] != "clean" else "PASS"
    return None

if __name__ == "__main__":
    print(f"artifacts: {len(ARTIFACTS)} (clean {len(CLEAN)}, seed-defect {len(SEED)}, held-out-defect {len(HELDOUT)})")
    for a in ARTIFACTS:
        print(f"  {a['id']}: {a['label']:24} seed={a['is_seed']}  truth={ground_truth(a['id'])}")
