"""
G2 REAL matrix runner (turnkey; the LLM-cost step the user DEFERRED).

Architecture: checker verdicts come from real agents, but a Python script cannot spawn
sub-agents itself. So this splits into two tool-friendly modes:

  export  : write one checker-prompt file per rigor level (strict/moderate/lenient),
            each listing the artifacts to judge with a fixed PASS/FAIL output contract.
            The operator (assistant) feeds each file to a Claude Max sub-agent -> free.

  analyze : given a verdicts JSON {rigor: {artifact_id: "PASS"/"FAIL"}} collected from the
            agents, run the SAME g2_gates logic + metrics as the dry-run, now on REAL data.

This keeps zero LLM cost until the operator chooses to run the export->judge->analyze loop.
Reuses g2_corpus (artifacts) and g2_gates (decision logic) verbatim, so the real matrix and
the dry-run share one code path (no drift).
"""
import sys, json
from g2_corpus import CORPUS, SEED_JUDGE, EVAL_JUDGE, EVAL_DEC, CLEAN_POOL
from g2_gates import CONFIGS, gate_decision, SUPERIORITY_CLASSES

TAU = 0.6
RIGORS = ["strict", "moderate", "lenient"]

RIGOR_PROMPT = {
    "strict":   "You are a MAXIMALLY RIGOROUS checker. You MUST: add up numbers to test constraints "
                "(allocations vs capacity, stage times vs budget); check confidence intervals for OVERLAP "
                "(overlap => 'significant' is false); treat any citation you cannot verify as unsupported; "
                "check the evidence actually TESTS the claimed condition.",
    "moderate": "You are an ordinary reviewer. Skim the numbers; flag something only if it looks off. "
                "You do not always recompute sums or intervals.",
    "lenient":  "You are a friendly, trusting reviewer. You do not recompute numbers, intervals, or verify "
                "citations. You PASS unless a contradiction is blatant.",
}

def artifacts_to_judge():
    # everything the gates evaluate: seeds (for liveness) + eval defects + clean
    ids = {a["id"]: a for a in SEED_JUDGE + EVAL_JUDGE + EVAL_DEC + CLEAN_POOL}
    return list(ids.values())

def export():
    arts = artifacts_to_judge()
    for rigor in RIGORS:
        lines = [RIGOR_PROMPT[rigor],
                 "",
                 "For EACH artifact output exactly one line `ID: PASS` or `ID: FAIL`.",
                 "PASS = claim supported by evidence, no defect. FAIL = a defect is present.",
                 ""]
        for a in arts:
            lines.append(f"{a['id']}: {a['text']}")
        path = f"g2_checker_prompt_{rigor}.txt"
        with open(path, "w") as f:
            f.write("\n".join(lines))
        print(f"wrote {path}  ({len(arts)} artifacts)")
    print("\nNext: feed each g2_checker_prompt_<rigor>.txt to a Claude Max sub-agent (free),")
    print("collect verdicts into g2_verdicts.json = {rigor: {id: PASS/FAIL}}, then: python3 g2_run.py analyze g2_verdicts.json")

def seed_detect_from(verd, rigor_pool):
    out = {}
    for name, rigor in rigor_pool:
        caught = sum(1 for a in SEED_JUDGE if verd[rigor].get(a["id"]) == "FAIL")
        out[name] = caught / len(SEED_JUDGE)
    return out

def analyze(path, rigor_pool=None):
    verd = json.load(open(path))
    for r in RIGORS:
        assert r in verd, f"verdicts missing rigor '{r}'"
    rigor_pool = rigor_pool or [("strict1","strict"), ("moderate1","moderate"),
                                ("lenient1","lenient"), ("lenient2","lenient")]
    # map pool checker-name -> rigor for verdict lookup (reuse a lenient's verdicts for both lenient slots)
    name2rigor = dict(rigor_pool)
    seed_detect = seed_detect_from(verd, rigor_pool)
    nj, nd, nc = len(EVAL_JUDGE), len(EVAL_DEC), len(CLEAN_POOL)
    print(f"REAL verdicts from {path} | pool={[r for _,r in rigor_pool]} | tau={TAU}")
    print("seed detect-rate:", {n: round(v,2) for n,v in seed_detect.items()})
    hdr = f"{'config':30} {'fp_judge':>9} {'fp_dec':>7} {'ff_clean':>9} {'hn-catch':>9}"
    print(hdr); print("-"*len(hdr))
    for k, cfg in CONFIGS().items():
        fpj = fpd = ffc = hnc = hnt = 0
        def decide(a):
            vs = {name: verd[name2rigor[name]].get(a["id"], "PASS") for name,_ in rigor_pool}
            # producer self-review verdict: reuse lenient as optimistic proxy if present
            prod = verd.get("lenient", {}).get(a["id"], "PASS")
            return gate_decision(a, vs, seed_detect, cfg, TAU, prod)
        for a in EVAL_JUDGE:
            if decide(a) == "PASS": fpj += 1
            if a["defect_class"] in SUPERIORITY_CLASSES:
                hnt += 1
                if decide(a) == "FAIL": hnc += 1
        for a in EVAL_DEC:
            if decide(a) == "PASS": fpd += 1
        for a in CLEAN_POOL:
            if decide(a) == "FAIL": ffc += 1
        print(f"{cfg['name']:30} {fpj/nj:>8.1%} {fpd/nd:>7.0%} {ffc/nc:>8.1%} {(hnc/hnt if hnt else 0):>8.0%}")
    print("\nNOTE: single-pool real numbers. Full make-or-break needs the degraded-fraction sweep")
    print("(collect extra lenient verdict sets) + the multi-round reframe study for Primitive 2.")

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "export":
        export()
    elif len(sys.argv) >= 3 and sys.argv[1] == "analyze":
        analyze(sys.argv[2])
    else:
        print("usage: python3 g2_run.py export | analyze <verdicts.json>")
