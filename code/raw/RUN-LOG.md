# Raw checker logs: full re-measurement

This directory holds the **verbatim output of every checker run**. It did not exist before this
campaign: verdicts had been **hand-transcribed** into `g2_build_verdicts.py`, `g3_build_verdicts.py`
and `g4_analyze.py`, largely as **range rules**:

```python
for i in range(19, 64):  strict[f"G2-{i:03d}"] = "FAIL"   # comment: "verbatim from agent"
def perfect(): ...                                        # "both perfect, verbatim"
runs = {"sonnet_s1": {**perfect(), "J-001": "PASS"}}      # perfect + hand-noted deviations
```

That encoding turns the claim *"all 45 items FAIL"* into something **unverifiable from the
artifact**: had the real run deviated on one item, the rule would have erased it silently.

From now on **the raw log is the data** and the verdict JSON is **derived**. No line in a log means
no verdict: nothing inferred, filled in, or rounded.

## Scale

**58 logged runs.** First corpus: 24 prompt-rigour runs, 9 model-tier runs, 16 reasoning-class runs.
Second (hard) corpus: 9 runs.

| | |
|---|---|
| Models | prompt-rigour arm: one mid-tier model held fixed (the variable is the prompt) · tier arms: strong / mid / cheap |
| Tools available to the checker | **none**, beyond a single `Read` of its own prompt file |
| Prompts | used verbatim. The three rigour prompts share a **byte-identical** artifact body; only the leading instruction differs |
| Coverage | first corpus **69/72** (`G2-064..066` are absent from the original prompt file) · reasoning corpus 28/28 · hard corpus 60/60 |

## Result: the earlier capability gradient is gone

### Prompt rigour (range over runs)

| rig | seed-detect | held-detect | citation | false-reject |
|---|---|---|---|---|
| strict | 1.00 | 1.00 | **1.00** | **0.00 – 0.22** |
| moderate | 1.00 | 1.00 | 0.00 | 0.00 |
| lenient | **0.20 – 1.00** | **0.20 – 1.00** | 0.00 | 0.00 |

### Model tier (three runs each, identical in every run)

| tier | seed-detect | held-detect | citation | false-reject |
|---|---|---|---|---|
| strong | 1.00 | 1.00 | **1.00** | 0.00 |
| mid | 1.00 | 1.00 | 0.00 | 0.00 |
| cheap | 1.00 | 1.00 | 0.00 | 0.00 |

An earlier measurement of this same benchmark, months before and on an earlier model generation,
recorded the cheap tier at 0.80 seeded and 0.60 held-out, and 0.25 on arithmetic. That gradient has
closed.

## Three conclusions from the first corpus

### 1. Judgment classes are **saturated**

On all three axes every configuration detects nearly every judgment defect. The ladders
*strict > moderate > lenient* and *strong > mid > cheap* **no longer exist**. This is a model
generation change, not a measurement error: same benchmark, same prompts, different date.

### 2. The only clean, stable separation is the **decidable** class

Fabricated citations: **only** the strict prompt and the strong tier detect them, at **1.00**.
Moderate, lenient, mid and cheap return **0.00 in every run**, without exception.

> This is the decidable/judgment predicate split, and the evidence for it is now cleaner than
> before: catching a fabricated citation needs a **tool**, not a stricter checker or a larger model.

### 3. Weak configurations are **not stable across runs**

| case | spread over identical runs |
|---|---|
| lenient, held-detect | **0.20 → 1.00** |
| strict, false-reject | **0.00 → 0.22** |
| cheap tier, reasoning corpus | over-rejects the same valid reduction in some runs, not others |

The strong tier, by contrast, is invariant across every run of both experiments.

## What earlier hand-transcription got right

Worth recording, because it shows the earlier numbers were **not fabricated**, only single draws:

1. The cheap tier over-rejects the **same** valid NP-hardness reduction (`J-007`) that the earlier
   transcription noted, at a similar rate.
2. Fabricated citations at 0.00 for the moderate and lenient rigs reproduced exactly.

## An ambiguity that cannot be resolved

**The model used for the earlier measurement was never recorded.** So the difference between the two
campaigns **cannot be attributed** to a model change rather than run-to-run variance. That is the
price of not logging the first campaign: *you cannot reproduce what you did not record.*

---

# Second campaign: bimodality, and a second corpus

## Output-format change, from run 42 onward

From run 42 the checker was asked to return **the list of failed IDs** (`FAIL: G2-019, ...`) instead
of 69 `ID: PASS|FAIL` lines. `_from_faillist.py` expands it back.

**The cost, recorded so it is not forgotten:** both forms carry the same information, because the ID
set is fixed and read from the prompt file. But if a checker **omits** an ID, the full form exposes
it immediately as a missing line, whereas the compact form silently treats it as PASS. The expander
blocks on unknown or repeated IDs and prints how many IDs were inferred to be PASS, but it cannot
detect an omission. Runs 1 through 41 keep the full form.

## Finding 1: the varying conditions are **BIMODAL**, not noisy

| condition | bad mode | 95% interval | **values ever observed** |
|---|---|---|---|
| lenient detects 9 of 45 | 4/12 | [0.10, 0.65] | **9 or 45** |
| strict rejects genuine citations | 6/9 | [0.30, 0.93] | **0 or 4** |
| cheap tier over-rejects `J-007` | 2/10 | [0.03, 0.56] | 0 or 1 |

After twelve lenient runs and nine strict runs, **no intermediate value has ever appeared**.
Reporting `mean ± std` for the lenient checker gives `0.73 ± 0.38`, a value **no run produced**.
That is why the paper reports **mode proportions with exact Clopper-Pearson intervals** instead; the
interval function is verified against two textbook cases (0/10 → [0, 0.3085], 10/10 → [0.6915, 1]).

The strict checker's four false-rejects are **always the same four items**, so the checker switches
to a different reading **consistently** rather than making scattered errors.

## Finding 2: a harder corpus does separate the tiers

`h_corpus.py`, 60 artifacts, five classes drawn from **errors that passed automated verification on
real submitted papers** and were caught only by an external reader. Fifteen pair-matched clean
controls. `h_audit.py` re-derives every label from the artifact text: **60/60 agree**. Artifact
order is **shuffled** before the prompt is built, so position cannot leak the label.

| tier | held-out detection | false-reject |
|---|---|---|
| strong | **1.00** (3/3 runs) | 0.00 |
| mid | **1.00** (3/3 runs) | 0.00 |
| cheap | **0.80 – 0.87** | 0.00 – 0.20 |

The capability gradient **reappears**. So saturation on the first corpus is a property of **defect
difficulty**, not of the instrument.

## Finding 3 (the important one): the blind spot **MOVES**

```
h-cheap-r1:  missed 9 -> the entire empty-filter class      | 0 false-rejects
h-cheap-r2:  missed 6 -> the selection-regression class     | 3 false-rejects
h-cheap-r3:  missed 6 -> the selection-regression class     | 0 false-rejects
```

The cheap tier is **not uniformly weaker**. It is **blind to one class at a time**, and which class
changes between runs with nothing else changed.

> This is exactly the regime positive-control liveness was built for, a **systematic** rather than
> random failure, **and it still cannot exploit it**: a seeded pool drawn from the class the checker
> happens to handle this run will **certify** it, and it will then fail on the class it is blind to.
> Seeding every class does not repair this either, because the gate must set a **single threshold τ**
> over a pooled detection rate, and a checker blind to one class in five still clears any τ ≤ 0.8.

## Regenerating

```
python3 g2_parse_raw.py     # raw/ -> g2_verdicts.json, fail-closed
python3 rerun_report.py     # raw/ -> tables/rerun-*.csv (ranges + mode intervals)
python3 h_audit.py          # re-derive every hard-corpus label from its text
python3 h_score.py          # raw/ -> tables/hard-corpus.csv, hard-blindspot-shift.csv
```

The earlier hand-transcribed verdicts are kept at `g2_verdicts.json.28jul-transcribed` for
comparison and are **not used for any number in the paper**.
