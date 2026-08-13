"""
G1 round-2 artifacts. Round-1 was degenerate: held-out defects were blatant
internal contradictions that EVERY checker caught, so positive-control had
nothing to screen. Round-2 uses SUBTLE defects matched in difficulty between
seed and held-out, in classes where a degraded checker plausibly false-passes:
  A fabricated-citation  : plausible DOI, NO impossible-id tell (needs external lookup)
  B subtle-infeasible    : violation only visible after ARITHMETIC (sum > capacity/budget)
  C overlapping-CI-super  : 'significant' claim but confidence intervals OVERLAP
  D scope-gap (held-out) : claim scope exceeds what evidence tests
Seeds and held-out are matched per class so a degraded checker that misses the
seed should also miss the held-out -> positive-control can screen it -> signal.
"""

ARTIFACTS = [
    # ---- CLEAN (3) ----
    dict(id="CA", label="clean", is_seed=False, text=(
        "Claim: our method significantly outperforms the baseline. Evidence: accuracy 0.85 +/- 0.01 (ours) "
        "vs 0.70 +/- 0.01 (baseline) over 10 seeds; the intervals do not overlap.")),
    dict(id="CB", label="clean", is_seed=False, text=(
        "Claim: the allocation is within link capacity. Evidence: three flows are allocated 0.4, 0.3, and 0.2 "
        "of the shared link; total 0.9 <= capacity 1.0.")),
    dict(id="CC", label="clean", is_seed=False, text=(
        "Claim: we cite Vaswani et al. 2017 for the transformer. Evidence: 'Attention Is All You Need', "
        "NeurIPS 2017, DOI 10.48550/arXiv.1706.03762. Real and supports the claim.")),

    # ---- SEED defects (3, one per class A/B/C) : positive-control ----
    dict(id="SA", label="fabricated-citation", is_seed=True, text=(
        "Claim: neural beam prediction is established prior art. Evidence: we cite "
        "'Zhang & Lee, Neural Beam Prediction for LEO, IEEE TWC 2021, DOI 10.1109/TWC.2021.3098123'.")),  # plausible but fabricated DOI
    dict(id="SB", label="subtle-infeasible", is_seed=True, text=(
        "Claim: the three flows fit within the shared link. Evidence: they are allocated 0.40, 0.35, and 0.30 "
        "of a link with normalized capacity 1.0.")),  # 0.40+0.35+0.30 = 1.05 > 1.0
    dict(id="SC", label="overlapping-ci-superiority", is_seed=True, text=(
        "Claim: our method is statistically significantly better. Evidence: F1 0.812 +/- 0.03 (ours) vs "
        "0.795 +/- 0.03 (baseline) over 10 seeds.")),  # CIs overlap heavily -> not significant

    # ---- HELD-OUT defects (4: A/B/C matched + D new class) : false-pass eval ----
    dict(id="HA", label="fabricated-citation", is_seed=False, text=(
        "Claim: Doppler-aware handover is prior art we build on. Evidence: we cite "
        "'Park, Choi & Ryu, Doppler-Aware Handover for NGSO, IEEE TVT 2022, DOI 10.1109/TVT.2022.3156789'.")),  # plausible but fabricated
    dict(id="HB", label="subtle-infeasible", is_seed=False, text=(
        "Claim: the request meets its 50 ms end-to-end latency budget. Evidence: the pipeline stages take "
        "22 ms, 18 ms, and 13 ms respectively.")),  # 22+18+13 = 53 > 50
    dict(id="HC", label="overlapping-ci-superiority", is_seed=False, text=(
        "Claim: our scheduler is significantly faster. Evidence: makespan 12.1 +/- 0.6 ms (ours) vs "
        "12.6 +/- 0.7 ms (baseline) over 8 seeds.")),  # intervals overlap -> not significant
    dict(id="HD", label="scope-gap", is_seed=False, text=(
        "Claim: our policy is robust to jamming. Evidence: Table 5 reports performance only on the "
        "interference-free channel; no jamming condition is tested.")),  # evidence does not test the claim
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
        print(f"  {a['id']}: {a['label']:28} seed={a['is_seed']}  truth={ground_truth(a['id'])}")
