"""
G4 GENUINE-JUDGMENT defect classes: ground truth requires REASONING, not computation,
so a checker cannot be trivially perfect by being told to 'add up the numbers'. This
directly answers the G6 red-team point that the whole make-or-break lived in a computable
(arithmetic) class. Four classes, all with an unambiguous correct answer that an expert
verifies but a calculator cannot:
  invalid-reduction     : a complexity reduction argued in the WRONG direction
  circular-justification: the justification assumes its own conclusion
  correlation-causation : a causal/intervention claim from purely observational correlation
  confounded-attribution: an ablation that changes two things at once, so it isolates nothing
Each defective artifact has a matched CLEAN control (the valid version of the same argument).
Hand-authored; ground truth is by construction and stated in the comment on each item.
"""

ARTIFACTS = [
    # ================= invalid-reduction =================
    # FAIL: reducing OUR problem TO a hard problem shows ours is no harder, not that it is hard.
    dict(id="J-001", defect_class="invalid-reduction", is_seed=True, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: our scheduling problem is NP-hard. Evidence: we give a polynomial-time reduction from our problem to 3-SAT, and 3-SAT is NP-hard."),
    dict(id="J-002", defect_class="invalid-reduction", is_seed=True, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: problem P is at least as hard as vertex cover. Evidence: we reduce P to vertex cover in polynomial time."),
    dict(id="J-003", defect_class="invalid-reduction", is_seed=False, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: our routing problem is NP-hard. Evidence: we reduce it in polynomial time to the travelling salesman problem, which is NP-hard."),
    dict(id="J-004", defect_class="invalid-reduction", is_seed=False, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: allocation problem A is intractable. Evidence: A can be reduced to integer programming, which is NP-hard, so A is NP-hard."),
    dict(id="J-005", defect_class="invalid-reduction", is_seed=False, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: our matching variant is NP-complete. Evidence: it is in NP, and it reduces in polynomial time to max-flow."),
    # CLEAN: correct direction (reduce FROM a known-hard problem TO ours).
    dict(id="J-006", defect_class="clean", is_seed=False, ground_truth="PASS", predicate_kind="judge",
         text="Claim: our scheduling variant is NP-hard. Evidence: we give a polynomial-time reduction from Hamiltonian cycle (NP-hard) to our variant."),
    dict(id="J-007", defect_class="clean", is_seed=False, ground_truth="PASS", predicate_kind="judge",
         text="Claim: our problem is NP-hard. Evidence: we reduce set cover, which is NP-hard, to our problem in polynomial time."),

    # ================= circular-justification =================
    dict(id="J-011", defect_class="circular-justification", is_seed=True, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: the selected features are the most informative. Evidence: they are exactly the features our selector returns, and our selector is designed to return the most informative features."),
    dict(id="J-012", defect_class="circular-justification", is_seed=True, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: our clustering is the correct one. Evidence: the points are grouped by our algorithm, which by construction produces the correct grouping."),
    dict(id="J-013", defect_class="circular-justification", is_seed=False, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: model M is the best calibrated. Evidence: it minimizes our calibration score, which we define as the quantity that M minimizes."),
    dict(id="J-014", defect_class="circular-justification", is_seed=False, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: our policy is optimal. Evidence: it achieves the highest reward under our reward model, and our reward model is defined so that this policy scores highest."),
    dict(id="J-015", defect_class="circular-justification", is_seed=False, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: these are the ground-truth labels. Evidence: they are the labels our annotation tool outputs, and the tool is defined to output ground truth."),
    # CLEAN: justified against an INDEPENDENT external criterion.
    dict(id="J-016", defect_class="clean", is_seed=False, ground_truth="PASS", predicate_kind="judge",
         text="Claim: our selected features are informative. Evidence: replacing a random feature set with them raises held-out downstream accuracy from 0.71 to 0.86."),
    dict(id="J-017", defect_class="clean", is_seed=False, ground_truth="PASS", predicate_kind="judge",
         text="Claim: model M is well calibrated. Evidence: its expected calibration error on a held-out set, computed independently of M, is 0.02."),

    # ================= correlation-causation =================
    dict(id="J-021", defect_class="correlation-causation", is_seed=True, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: increasing buffer size causes lower loss, so we enlarge buffers. Evidence: across our logs, larger buffers coincide with lower loss."),
    dict(id="J-022", defect_class="correlation-causation", is_seed=True, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: teams using our tool ship faster because the tool causes the speed-up. Evidence: in a survey, teams that adopted the tool report shorter cycle times."),
    dict(id="J-023", defect_class="correlation-causation", is_seed=False, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: users who see feature X convert more because X drives conversion. Evidence: observational logs show X-exposed users convert at twice the rate."),
    dict(id="J-024", defect_class="correlation-causation", is_seed=False, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: deeper networks generalize better, and depth is the cause. Evidence: in a scan of published models, deeper ones report higher accuracy."),
    dict(id="J-025", defect_class="correlation-causation", is_seed=False, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: our regularizer causes the flatter minima we observe. Evidence: runs with the regularizer end at flatter minima than runs without it, which also used a different batch size and seed."),
    # CLEAN: correlation acknowledged, no causal/intervention claim.
    dict(id="J-026", defect_class="clean", is_seed=False, ground_truth="PASS", predicate_kind="judge",
         text="Claim: buffer size correlates with lower loss; we use it only as a predictive feature and make no causal claim."),
    dict(id="J-027", defect_class="clean", is_seed=False, ground_truth="PASS", predicate_kind="judge",
         text="Claim: our regularizer improves flatness. Evidence: a controlled A/B with only the regularizer toggled, all else fixed across 5 seeds, yields flatter minima."),

    # ================= confounded-attribution =================
    dict(id="J-031", defect_class="confounded-attribution", is_seed=True, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: the attention module contributes +4% accuracy. Evidence: removing attention and simultaneously switching the optimizer from Adam to SGD dropped accuracy by 4%."),
    dict(id="J-032", defect_class="confounded-attribution", is_seed=True, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: our auxiliary loss adds 3 points. Evidence: the run without the loss also used a smaller model and less data, and scored 3 points lower."),
    dict(id="J-033", defect_class="confounded-attribution", is_seed=False, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: pretraining gives +6 BLEU. Evidence: the no-pretraining baseline was also trained for fewer steps with a different tokenizer, scoring 6 BLEU lower."),
    dict(id="J-034", defect_class="confounded-attribution", is_seed=False, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: the graph encoder is responsible for the gain. Evidence: the variant without it also removed skip connections and halved the hidden size, and performed worse."),
    dict(id="J-035", defect_class="confounded-attribution", is_seed=False, ground_truth="FAIL", predicate_kind="judge",
         text="Claim: our sampler improves quality by 2 points. Evidence: the comparison run used the old sampler together with a shorter context window and fewer decoding steps."),
    # CLEAN: single factor isolated.
    dict(id="J-036", defect_class="clean", is_seed=False, ground_truth="PASS", predicate_kind="judge",
         text="Claim: attention contributes +4% accuracy. Evidence: ablating only attention, with every other setting held identical, drops accuracy by 4%."),
    dict(id="J-037", defect_class="clean", is_seed=False, ground_truth="PASS", predicate_kind="judge",
         text="Claim: pretraining gives +6 BLEU. Evidence: the sole difference from the baseline is the pretraining stage; steps, tokenizer, and data are identical."),
]

JUDGE_CLASSES = ["invalid-reduction","circular-justification","correlation-causation","confounded-attribution"]
SEED = [a for a in ARTIFACTS if a["is_seed"]]
EVAL = [a for a in ARTIFACTS if (not a["is_seed"]) and a["defect_class"]!="clean"]
CLEAN = [a for a in ARTIFACTS if a["defect_class"]=="clean"]

if __name__ == "__main__":
    from collections import Counter
    print(f"total {len(ARTIFACTS)} | seed {len(SEED)} | eval-defect {len(EVAL)} | clean {len(CLEAN)}")
    print("by class:", dict(Counter(a['defect_class'] for a in ARTIFACTS)))
