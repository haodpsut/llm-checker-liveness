#!/usr/bin/env python3
"""Label audit for corpus H: RE-DERIVE ground truth from the artifact TEXT, never trust the stored label.

Why this is mandatory. Labels are set by the generator; if the generator is wrong the labels are
wrong and EVERY downstream measurement is wrong with them, invisibly. The first corpus had exactly
such a case: a "moderate ablation" whose real effect EXCEEDED the declared noise threshold, so it
was labelled FAIL while its own text said the opposite.

This file parses the numbers out of each artifact, recomputes, and compares against the label. A
disagreement of one unit BLOCKS.
"""
import re
import sys

import h_corpus as H


def num(s):
    return float(s.replace(",", ""))


def derive(a):
    """Return (PASS|FAIL, reason) derived from the text. None if this class is not numerically derivable."""
    t, c = a["text"], a["defect_class"]

    if c in ("subset-superlative",) or (c == "clean" and "sustains" in t):
        quoted = num(re.search(r"sustains ([\d,]+) bit/s", t).group(1))
        maxima = [num(x) for x in re.findall(r"maximum is ([\d,]+) bit/s", t)]
        return ("PASS" if quoted >= max(maxima) else "FAIL",
                f"quoted {quoted:,.0f} vs table maximum {max(maxima):,.0f}")

    if c in ("mechanism-vs-decomposition",) or (c == "clean" and "decomposes" in t):
        contact = float(re.search(r"contact time ([\d.]+)x", t).group(1))
        quality = float(re.search(r"link quality ([\d.]+)x", t).group(1))
        says_quality_only = "not contact time" in t
        # the stated mechanism is "quality", so quality must be the dominant factor
        ok = quality >= contact
        return ("FAIL" if (says_quality_only and not ok) else "PASS",
                f"contact {contact}x vs quality {quality}x; claim excludes contact = {says_quality_only}")

    if c in ("false-exclusivity",) or (c == "clean" and "spread" in t):
        a1 = float(re.search(r"type-I supported flows spread ([\d.]+)x", t).group(1))
        b1 = float(re.search(r"type-II spreads ([\d.]+)x", t).group(1))
        return ("PASS" if b1 < a1 / 2 else "FAIL", f"type-I {a1}x vs type-II {b1}x")

    if c in ("empty-filter",) or (c == "clean" and "strict filter" in t):
        m = re.search(r"selects ([\d]+) runs", t) or re.search(r"selects ([\d]+) of the", t)
        if m:
            n = int(m.group(1))
        else:
            n = 0 if "leaves none" in t else None
        if n is None:
            return None
        return ("PASS" if n > 0 else "FAIL", f"filter selects {n} units")

    if c in ("selection-regression",) or (c == "clean" and "throughput" in t):
        selected_extreme = "worst-performing" in t
        has_control = "randomly assigned" in t or "untreated half" in t
        return ("FAIL" if (selected_extreme and not has_control) else "PASS",
                f"selected on extremes = {selected_extreme}, has control = {has_control}")

    return None


def main():
    bad, checked, skipped = [], 0, 0
    for a in H.ARTIFACTS:
        d = derive(a)
        if d is None:
            skipped += 1
            continue
        checked += 1
        got, why = d
        if got != a["ground_truth"]:
            bad.append((a["id"], a["defect_class"], a["ground_truth"], got, why, a["text"][:90]))
    print(f"h_audit -- {len(H.ARTIFACTS)} artifacts | re-derived {checked} | not derivable {skipped}")
    if checked == 0:
        print("BLOCK: 0 units checked. Empty is BROKEN, not clean.")
        return 2
    if bad:
        print(f"\nBLOCK -- {len(bad)} labels DISAGREE:")
        for i, c, stored, got, why, txt in bad[:10]:
            print(f"  {i} [{c}] stored={stored} derived={got}  ({why})\n      {txt}...")
        return 2
    print(f"PASS -- {checked}/{len(H.ARTIFACTS)} labels agree with the value re-derived from the text.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
