"""
Corpus label audit (benchmark integrity, per G1 constraint 'audit the labels').
Re-derives ground truth OBJECTIVELY from the artifact text for every machine-checkable
class, and asserts it matches the stored label. Catches rounding accidents that could
make a 'subtle infeasible' artifact actually feasible, or an 'overlapping-CI' pair
actually disjoint. Fabricated-citation and scope-gap are not arithmetic, so they are
audited structurally (cite is in the fake list / claimed condition absent from evidence).
"""
import re
from g2_corpus import CORPUS, FAKE_CITES

def nums(t):
    return [float(x) for x in re.findall(r"\d+\.\d+|\d+", t)]

def audit_infeasible(a):
    t = a["text"]
    if "latency budget" in t:
        budget = float(re.search(r"(\d+) ms latency budget", t).group(1))
        stages = [float(x) for x in re.findall(r"(\d+) ms", t) if float(x) != budget]
        # the budget also matches ' ms' pattern once; strip it
        stages = [float(x) for x in re.findall(r"(\d+) ms", t)]
        stages = stages[1:] if stages and stages[0] == budget else stages
        return sum(stages) > budget, f"sum(stages)={sum(stages)} vs budget={budget}"
    cap = float(re.search(r"capacity (\d+\.\d+)", t).group(1))
    allocs = [float(x) for x in re.findall(r"allocated ([\d., ]+) of", t)[0].replace(" ", "").split(",")]
    return sum(allocs) > cap, f"sum(alloc)={round(sum(allocs),3)} vs cap={cap}"

def audit_overlap(a):
    t = a["text"]
    m = re.findall(r"([\d.]+) \+/- ([\d.]+)", t)
    (o, oc), (b, bc) = (float(m[0][0]), float(m[0][1])), (float(m[1][0]), float(m[1][1]))
    overlap = (o - oc) <= (b + bc)          # intervals overlap => 'significant' is false
    return overlap, f"ours[{o-oc:.3f},{o+oc:.3f}] base[{b-bc:.3f},{b+bc:.3f}] overlap={overlap}"

def audit_antithetical(a):
    eff = float(re.search(r"changes the score by ([\d.]+)%", a["text"]).group(1))
    noise = float(re.search(r"noise is \+/-([\d.]+)%", a["text"]).group(1))
    return eff <= noise, f"effect={eff}% vs noise={noise}% -> within-noise={eff<=noise}"

def audit_scope(a):
    t = a["text"]
    claimed = re.search(r"robust to ([\w\- ]+)\.", t).group(1).strip()
    return (f"no {claimed} condition is tested" in t), f"claimed='{claimed}' untested-in-evidence"

def audit_citation(a):
    cite = re.search(r"we cite '(.+)'", a["text"]).group(1)
    return (cite in FAKE_CITES), "cite is in the fabricated set"

AUDITORS = {
    "infeasible": audit_infeasible,
    "overlapping-ci-superiority": audit_overlap,
    "antithetical-ablation": audit_antithetical,
    "scope-gap": audit_scope,
    "fabricated-citation": audit_citation,
}

def main():
    bad = []
    for a in CORPUS:
        cls = a["defect_class"]
        if cls == "clean":
            continue
        holds, why = AUDITORS[cls](a)
        # 'holds' means the defect really is present -> ground truth must be FAIL
        expect_fail = a["ground_truth"] == "FAIL"
        ok = holds == expect_fail
        if not ok:
            bad.append((a["id"], cls, a["difficulty"], why))
    print(f"audited {sum(1 for a in CORPUS if a['defect_class']!='clean')} defect artifacts")
    if bad:
        print(f"  !! {len(bad)} MISLABELED (defect not actually present):")
        for b in bad:
            print("   ", b)
    else:
        print("  OK: every labeled defect is objectively present in its text (no rounding accidents).")
    # also spot-check a few witnesses for the paper's 'objective ground truth' claim
    print("\n  witness spot-check (subtle infeasible + overlapping-CI):")
    shown = 0
    for a in CORPUS:
        if a["defect_class"] in ("infeasible", "overlapping-ci-superiority") and a["difficulty"] == "subtle":
            _, why = AUDITORS[a["defect_class"]](a)
            print(f"   {a['id']} [{a['defect_class']}] {why}")
            shown += 1
            if shown >= 4:
                break

if __name__ == "__main__":
    main()
