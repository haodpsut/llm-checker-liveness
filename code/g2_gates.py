"""
G2 gate logic: ATTEST-full + 7 baselines/ablations (formulation v2 section 9).
Pure decision logic over per-checker verdicts -- NO LLM calls here. The harness
(g2_dryrun.py for now, g2_run.py later with real checkers) supplies verdicts.

A gate config is a dict of flags:
  multichecker      : use the full checker set + q-of-n; else a single checker
  positive_control  : drop checkers whose seed detect_rate < tau (Primitive 1)
  honest_neg_block  : fail-closed on unsupported superiority/novelty claims (Primitive 2)
  dec_tools         : resolve decidable predicates (citation) with a tool, not judgment
  fail_closed       : missing/insufficient evidence -> FAIL (never skip)
  producer_checks   : self-review (checker == producer, biased-lenient)
  verify            : if False, gate always PASS (no-verification upper bound)
  q_frac            : pass-quorum as a FRACTION of LIVE checkers -- gate affirms PASS only
                      if #PASS >= ceil(q_frac * |live|). Relative (not absolute) so that
                      positive-control screening cannot make the quorum unreachable.
                      ATTEST uses majority-of-live (0.5); superiority claims get unanimity
                      via honest_neg_block regardless.
"""
import math

SUPERIORITY_CLASSES = {"overlapping-ci-superiority", "antithetical-ablation"}  # for METRIC grouping only

# The gate must decide whether an artifact CARRIES a superiority/novelty claim from its TEXT
# (a real gate has no ground-truth class label). Keyword detector, deliberately broad; it only
# triggers a block when a checker ALSO dissents, so flagging a legitimate claim is harmless.
_SUP_KEYWORDS = ("significantly better", "significantly outperform", "outperform", "state-of-the-art",
                 "pareto", "key novelty", "drives the gains", "novelty", "surpass", "superior",
                 "best baseline", "first applied", "first to")
def has_superiority_claim(text):
    t = text.lower()
    return any(k in t for k in _SUP_KEYWORDS)

# ---- the 8 configurations --------------------------------------------------
# q_frac = majority-of-live for realistic fail-closed voting (controls false-fail + cost);
# superiority claims are lifted to unanimity by honest_neg_block.
CONFIGS = lambda n=None: {
    "ATTEST":                 dict(name="ATTEST", multichecker=True, positive_control=True, honest_neg_block=True,
                                   dec_tools=True, fail_closed=True, producer_checks=False, verify=True, q_frac=0.5),
    "b_i_self_review":        dict(name="soft self-review", multichecker=False, positive_control=False,
                                   honest_neg_block=False, dec_tools=False, fail_closed=False,
                                   producer_checks=True, verify=True, q_frac=1.0),
    "b_ii_single_judge":      dict(name="single LLM-judge", multichecker=False, positive_control=False,
                                   honest_neg_block=False, dec_tools=False, fail_closed=True,
                                   producer_checks=False, verify=True, q_frac=1.0),
    "b_iii_no_poscontrol":    dict(name="-positive-control", multichecker=True, positive_control=False,
                                   honest_neg_block=True, dec_tools=True, fail_closed=True,
                                   producer_checks=False, verify=True, q_frac=0.5),
    "b_iv_autochain":         dict(name="-human-transition (auto-chain)", multichecker=True, positive_control=True,
                                   honest_neg_block=True, dec_tools=True, fail_closed=True,
                                   producer_checks=False, verify=True, q_frac=0.5),   # single-phase == ATTEST; differs across phases
    "b_v_no_honestneg":       dict(name="-honest-neg-block", multichecker=True, positive_control=True,
                                   honest_neg_block=False, dec_tools=True, fail_closed=True,
                                   producer_checks=False, verify=True, q_frac=0.5),
    "b_vi_no_agreement":      dict(name="-multichecker (single)", multichecker=False, positive_control=True,
                                   honest_neg_block=True, dec_tools=True, fail_closed=True,
                                   producer_checks=False, verify=True, q_frac=1.0),
    "b_vii_no_verify":        dict(name="no-verification", multichecker=False, positive_control=False,
                                   honest_neg_block=False, dec_tools=False, fail_closed=False,
                                   producer_checks=False, verify=False, q_frac=0.0),
}

def live_checkers(seed_detect, cfg, tau):
    """Return the contributing checker names after positive-control screening."""
    names = list(seed_detect.keys())
    if not cfg["multichecker"]:
        # single checker: pick the designated 'moderate' if present else first
        names = [next((c for c in names if "moderate" in c), names[0])]
    if cfg["positive_control"]:
        live = [c for c in names if seed_detect[c] >= tau]
        return live
    return names

def gate_decision(artifact, verdicts, seed_detect, cfg, tau, producer_verdict=None):
    """
    verdicts: {checker_name: 'PASS'/'FAIL'} for THIS artifact (judgment vote).
    seed_detect: {checker_name: detect_rate on the seed judge pool} (for liveness).
    producer_verdict: 'PASS'/'FAIL' from the producer's self-review (biased).
    Returns 'PASS' or 'FAIL' (the gate's release decision).
    """
    if not cfg["verify"]:
        return "PASS"                                   # no-verification upper bound

    if cfg["producer_checks"]:
        v = producer_verdict if producer_verdict is not None else "PASS"
        return v                                        # self-review, not fail-closed

    C = live_checkers(seed_detect, cfg, tau)
    if not C:                                           # no live checker
        return "FAIL" if cfg["fail_closed"] else "PASS" # fail-closed: block

    # --- decidable predicate (citation) : tool or checker ---
    if artifact["predicate_kind"] == "dec":
        if cfg["dec_tools"]:
            # tool resolves fabricated citation deterministically
            return "FAIL" if artifact["ground_truth"] == "FAIL" else "PASS"
        # else falls through to checker judgment below (checkers usually miss fabricated cites)

    votes = [verdicts[c] for c in C]
    n_pass = sum(1 for v in votes if v == "PASS")
    n_fail = len(votes) - n_pass

    # --- honest-negative block : fail-closed on unsupported superiority/novelty ---
    # detected from the artifact TEXT, not the ground-truth class label (a real gate has no label)
    if cfg["honest_neg_block"] and has_superiority_claim(artifact.get("text", "")):
        # any live checker dissent blocks release (forces reframe) -- fail-closed on these claims
        if n_fail >= 1:
            return "FAIL"

    # --- q-of-n agreement (fail-closed): PASS iff a STRICT MAJORITY of live checkers
    #     affirm PASS. Strict majority = floor(|live|/2)+1, so 2 live checkers require
    #     BOTH (avoids the |live|=2 -> need=1 "union" corner). Single checker -> need 1.
    #     Configs with q_frac==1.0 (single-judge/self-review already routed) keep need=1. ---
    need = (len(C)//2 + 1) if cfg["q_frac"] < 1.0 else max(1, len(C))
    if n_pass >= need:
        return "PASS"
    return "FAIL"

if __name__ == "__main__":
    cfgs = CONFIGS(3)
    print("configs:")
    for k, c in cfgs.items():
        print(f"  {k:22} {c['name']}")
