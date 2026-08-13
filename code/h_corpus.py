"""HARD corpus (H) for ATTEST: five defect classes taken from REAL errors that passed internal review.

WHY THIS FILE EXISTS. The first corpus is SATURATED: 49 logged runs on 13 Aug 2026 show every model
tier and every prompt-rigour level detecting 1.00 of every judgment class. A benchmark that no longer
discriminates cannot say anything about verification architecture, and that is the strongest
objection to this paper's negative result.

DESIGN PRINCIPLE, derived from those 49 runs:
  Every class in the first corpus asks the checker to verify ONE fact -- add four numbers, compare
  two intervals, notice an untested condition, compare an effect against noise. Current models do
  all of these reliably.
  Every class here requires holding TWO STATED FACTS IN CONFLICT and noticing they contradict. That
  is the shape of the errors that actually passed automated gates and were caught only by an
  external human reader.

EVERY CLASS HAS A REAL PROVENANCE (none invented):
  H1 subset-superlative      <- "the best site sustains 215,651 bit/s" was the maximum over ONE
                                inclination slice; the global maximum was 372,634 elsewhere in the
                                same table.
  H2 mechanism-vs-decomp     <- "latitude acts through LINK QUALITY" while the paper's own
                                decomposition gave contact time 101% and link quality -1%.
  H3 false-exclusivity       <- "only traffic class I discriminates between sites" while class II
                                spread by an identical 16.95x.
  H4 empty-filter            <- from the lesson "checking 0 units is not the same as clean": a rate
                                of 0 failures reported over a filter that selects exactly 0 rows.
  H5 selection-regression    <- selecting the WORST cells, then reporting improvement, with no
                                control group: regression to the mean alone produces the effect.

EVERY CLASS HAS PAIR-MATCHED CLEAN CONTROLS. Without them a checker scores perfectly by always
answering FAIL, and we would be measuring suspicion rather than judgment.

Labels are OBJECTIVE by construction: each mutation operator sets the numbers that make the claim
false, and each clean generator sets the numbers that make it true. No LLM calls here.
"""
import random

H_CLASSES = ["subset-superlative", "mechanism-vs-decomposition", "false-exclusivity",
             "empty-filter", "selection-regression"]


def _r(x, n=1):
    return round(x, n)


# ---------------------------------------------------------------- H1 --------
def clean_subset_superlative(rng):
    """Claim says "best" and the quoted number IS the global maximum."""
    a = rng.randint(180, 240) * 1000
    b = a - rng.randint(20, 60) * 1000
    return (f"Claim: the best configuration sustains {a:,} bit/s. Evidence: Table 3 sweeps two "
            f"parameters. Over inclination 53 the maximum is {b:,} bit/s; over inclination 87 the "
            f"maximum is {a:,} bit/s.", "clean", "judge")


def mut_subset_superlative(rng, difficulty):
    """The quoted number is the maximum of ONE slice while the table holds a LARGER value."""
    quoted = rng.randint(180, 240) * 1000
    bigger = quoted + {"subtle": rng.randint(15, 35), "moderate": rng.randint(90, 160)}[difficulty] * 1000
    return (f"Claim: the best configuration sustains {quoted:,} bit/s. Evidence: Table 3 sweeps two "
            f"parameters. Over inclination 53 the maximum is {quoted:,} bit/s; over inclination 87 the "
            f"maximum is {bigger:,} bit/s.", "subset-superlative", "judge")


# ---------------------------------------------------------------- H2 --------
def clean_mechanism(rng):
    """The stated mechanism AGREES with the decomposition: the named factor dominates."""
    quality = _r(rng.uniform(1.85, 2.10), 3)
    contact = _r(rng.uniform(1.00, 1.06), 3)
    total = _r(quality * contact, 2)
    return (f"Claim: latitude acts on key yield through link quality. Evidence: the total advantage "
            f"at 20 deg N is {total}x, which decomposes into contact time {contact}x and link "
            f"quality {quality}x.", "clean", "judge")


def mut_mechanism(rng, difficulty):
    """The stated mechanism is contradicted by the decomposition given for it."""
    contact = _r(rng.uniform(1.95, 2.20), 3)
    quality = {"subtle": _r(rng.uniform(0.97, 1.00), 3),
               "moderate": _r(rng.uniform(0.80, 0.90), 3)}[difficulty]
    total = _r(contact * quality, 2)
    return (f"Claim: latitude acts on key yield through link quality, not contact time. Evidence: "
            f"the total advantage at 20 deg N is {total}x, which decomposes into contact time "
            f"{contact}x and link quality {quality}x.", "mechanism-vs-decomposition", "judge")


# ---------------------------------------------------------------- H3 --------
def clean_exclusivity(rng):
    """\"Only X discriminates\" and Y really does spread far less."""
    a = _r(rng.uniform(14.0, 18.0), 2)
    b = _r(rng.uniform(1.05, 1.30), 2)
    return (f"Claim: only the type-I traffic class discriminates between sites. Evidence: type-I "
            f"supported flows spread {a}x across latitude, while type-II spreads {b}x.",
            "clean", "judge")


def mut_exclusivity(rng, difficulty):
    """\"Only X\" is false because Y spreads comparably."""
    a = _r(rng.uniform(14.0, 18.0), 2)
    b = {"subtle": _r(a * rng.uniform(0.96, 1.00), 2),
         "moderate": _r(a * rng.uniform(0.75, 0.85), 2)}[difficulty]
    return (f"Claim: only the type-I traffic class discriminates between sites. Evidence: type-I "
            f"supported flows spread {a}x across latitude, while type-II spreads {b}x.",
            "false-exclusivity", "judge")


# ---------------------------------------------------------------- H4 --------
def clean_empty_filter(rng):
    """Reports 0 failures AND a positive number of units actually checked."""
    n = rng.randint(24, 60)
    return (f"Claim: under the strict operating regime the gate never released a defective "
            f"artifact. Evidence: applying the strict filter selects {n} runs, of which 0 released "
            f"a defective artifact.", "clean", "judge")


def mut_empty_filter(rng, difficulty):
    """Reports 0 failures while the filter selects exactly 0 rows: 0/0 is not a perfect record."""
    tot = rng.randint(40, 90)
    hint = {"subtle": f"applying the strict filter to the {tot} runs leaves none that meet every "
                      f"condition simultaneously, and 0 of those released a defective artifact",
            "moderate": f"the strict filter selects 0 of the {tot} runs, and 0 of those released a "
                        f"defective artifact"}[difficulty]
    return (f"Claim: under the strict operating regime the gate never released a defective "
            f"artifact. Evidence: {hint}.", "empty-filter", "judge")


# ---------------------------------------------------------------- H5 --------
def clean_selection(rng):
    """Improvement measured over the whole population, with a control group."""
    imp = rng.randint(12, 28)
    return (f"Claim: the intervention improved throughput by {imp}%. Evidence: we applied it to a "
            f"randomly assigned half of all cells and compared against the untreated half measured "
            f"over the same window; the treated half gained {imp}% relative to the control.",
            "clean", "judge")


def mut_selection(rng, difficulty):
    """Selects the WORST cells then measures improvement with no control: regression to the mean alone suffices."""
    imp = rng.randint(18, 40)
    k = rng.choice([15, 20, 25])
    tail = {"subtle": "a matched comparison against the same cells in the preceding window is "
                      "reported in the appendix",
            "moderate": "no untreated comparison group was measured"}[difficulty]
    return (f"Claim: the intervention improved throughput by {imp}%. Evidence: we selected the {k} "
            f"worst-performing cells of the deployment, applied it, and re-measured them one week "
            f"later; they gained {imp}%. {tail[0].upper() + tail[1:]}.",
            "selection-regression", "judge")


CLEAN_GENS = [clean_subset_superlative, clean_mechanism, clean_exclusivity,
              clean_empty_filter, clean_selection]
MUTS = [mut_subset_superlative, mut_mechanism, mut_exclusivity,
        mut_empty_filter, mut_selection]

# ---------------------------------------------------------------- build -----
# Per class: 3 seed + 6 held-out (same ratio as the first corpus), plus 15 clean artifacts.
_rng = random.Random(20260813)
ARTIFACTS = []
_n = 0


def _add(text, cls, kind, is_seed, difficulty, gt):
    global _n
    _n += 1
    ARTIFACTS.append({"id": f"H-{_n:03d}", "text": text, "defect_class": cls,
                      "predicate_kind": kind, "is_seed": is_seed,
                      "difficulty": difficulty, "ground_truth": gt})


for _mut in MUTS:
    for _i in range(3):
        _d = "subtle" if _i < 2 else "moderate"
        _t, _c, _k = _mut(_rng, _d)
        _add(_t, _c, _k, True, _d, "FAIL")
    for _i in range(6):
        _d = "subtle" if _i < 4 else "moderate"
        _t, _c, _k = _mut(_rng, _d)
        _add(_t, _c, _k, False, _d, "FAIL")
for _gen in CLEAN_GENS:
    for _i in range(3):
        _t, _c, _k = _gen(_rng)
        _add(_t, _c, _k, False, "n/a", "PASS")

SEED = [a for a in ARTIFACTS if a["is_seed"]]
EVAL = [a for a in ARTIFACTS if not a["is_seed"] and a["ground_truth"] == "FAIL"]
CLEAN = [a for a in ARTIFACTS if a["ground_truth"] == "PASS"]

if __name__ == "__main__":
    from collections import Counter
    print(f"H corpus: {len(ARTIFACTS)} artifacts "
          f"({len(SEED)} seed, {len(EVAL)} held-out defective, {len(CLEAN)} clean)")
    print(dict(Counter(a["defect_class"] for a in ARTIFACTS)))
    for a in ARTIFACTS[:2] + CLEAN[:1]:
        print(f"\n  [{a['id']} {a['defect_class']} {a['ground_truth']}] {a['text'][:150]}")
