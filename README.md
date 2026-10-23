# Checker liveness: two defect benchmarks, a fail-closed gate, and 76 raw checker logs

This is the artifact for a measurement study of **positive-control liveness**: the idea that a
verification gate should emit PASS only while its checkers keep catching a pool of seeded defects.
We built such a gate, measured it, reported a null, and then had to retract that null. An external
reader pointed out that the liveness threshold we evaluated sat below every checker's seeded
detection rate, so the screen never excluded anybody: the mechanism was switched off for the whole
comparison. Re-measured on a harder benchmark with the threshold placed where it discriminates, the
mechanism separates by 13 to 20 points. Both the original null and the correction are in here.

Everything quoted in the paper is derived here, and every derivation starts from a **raw checker
log** in `code/raw/`.

## The three findings the artifact is for

**The blind spot moves.** On the harder benchmark the cheap checker fails *systematically*, missing
an entire defect class rather than scattered instances, which is the regime liveness screening
exists for. But *which* class it is blind to changes between identical runs. See
`paper/tables/hard-blindspot-shift.csv` and the three `code/raw/h-haiku-r1..r3-20260813.txt` logs, the cheap tier on that benchmark.

**A mechanism that never fires cannot be measured, and looks exactly like a mechanism that does not
work.** Every internal gate passed the original null, because a filter that excludes nobody is
perfectly consistent with itself. `code/h_matrix.py` re-runs the whole ablation matrix at thresholds
that do fire, and reports, as its top line, *how many checkers the screen actually excluded in each
run*. That count is the cheapest evidence that a verification mechanism is switched on at all, and
it was missing. See `paper/tables/hard-matrix.csv`.

The same file also shows a second artefact we found while checking the first: the single-judge and
single-checker ablations reduce the pool to one member and took the first, so writing the pool
strong-first silently handed the single-judge baseline the best checker. Both pool orderings are
reported; two rows exchange values under a change that alters no data.

**Checker competence is bimodal, not noisy.** Across twelve identical runs the lenient checker
detected either 9 or 45 of 45 defects and never any value between; the strict checker rejected
either zero or exactly the same four genuine citations. See `paper/tables/rerun-modes.csv`, whose
`observed_values` column records every value that was ever seen.

## Layout

```
code/
  g2_corpus.py            first benchmark: 72 artifacts, 5 classes, one-fact defects
  h_corpus.py             second benchmark: 60 artifacts, 5 classes, two-facts-in-conflict defects
  h_audit.py              re-derives every label of the second benchmark from its own text
  g2_gates.py             the gate and its ablations
  g2_parse_raw.py         raw logs -> verdicts, fail-closed
  rerun_report.py         raw logs -> range CSVs + mode proportions with exact intervals
  h_score.py              raw logs -> hard-corpus CSVs, per defect class
  h_matrix.py             the ablation matrix at thresholds that fire, both pool orderings,
                          plus the paired test and its exact intervals
  provenance.py           derives raw/PROVENANCE.md from the orchestration log
  ablation_nulls.py       per ablation, the count of cells in which it differs from ATTEST,
                          reported SEPARATELY for false-pass and for false-reject on clean work
  check_freshness.py      every CSV must be newer than its producer and its raw data, and the two
                          producer registries must agree with each other
  csv-producer.map        which script produces which CSV
  raw/                    76 raw checker logs + RUN-LOG.md + PROVENANCE.md
paper/
  tables/                 every CSV the paper cites
  tables/legacy-28jul/    an earlier, retired measurement set, kept for comparison
  claim-scope.json        superlative and exclusivity claims, with their full source lists
  REF-VERIFICATION-*.md   what was opened to verify each reference, and what disagreed
claims.json               every number in the paper -> the CSV cell it comes from
```

## Reproducing the numbers

The checker runs themselves call a language model and cannot be replayed deterministically; that is
why the raw logs are the data. Everything downstream of them is deterministic:

```
python3 code/g2_parse_raw.py     # raw logs -> verdicts, blocks on a missing or unknown ID
python3 code/h_audit.py          # 60/60 labels must agree with the text they were derived from
python3 code/rerun_report.py     # -> paper/tables/rerun-*.csv
python3 code/h_score.py          # -> paper/tables/hard-corpus.csv, hard-blindspot-shift.csv
python3 code/corpus_tables.py    # -> paper/tables/compose.csv, corpus.csv
python3 code/h_matrix.py         # -> paper/tables/hard-matrix.csv, hard-paired.csv
python3 code/ablation_nulls.py   # -> paper/tables/ablation-nulls.csv; READS the three matrices
                                 #    above, so it must run after them
python3 code/check_freshness.py  # no table may be older than the data behind it
python3 code/check_artifact_claims.py  # the artifact's own prose must match its contents
```

## Conventions this artifact tries to hold to

**The raw log is the data.** Verdicts are derived from logs, never hand-written. An earlier version
of this work encoded results as range rules (`for i in range(19, 64): FAIL`), which makes a claim
about 45 items unverifiable from the artifact. Every such file has been replaced.

**No cell carries a mean alone.** Every emitted number has `mean`, `min`, `max` and `n_runs`,
because the central finding is that some conditions are not stable across runs.

**Empty is broken, not clean.** Every gate here blocks when it has checked zero units, rather than
reporting a pass.

**Silent truncation is a bug.** When the pooling step has to drop surplus runs, it prints how many
and from which condition.

**Percentages are stored, not left to the reader.** Every table in the paper prints percentages
while the CSVs held fractions, so no printed cell could be matched against the artifact. Each
producer now emits the percentage columns alongside the fractions.

**What was not recorded cannot be reconstructed honestly.** Sampling temperature was never settable
through the launch interface, and the build behind two of the three model aliases was never echoed
back. `raw/PROVENANCE.md` states both as unknown rather than filling them in, and the per-arm launch
table is derived from the orchestration log rather than typed from memory.

## What is deliberately not in here

**The manuscript itself.** The paper is a separate claim surface and is under review, so its source
is not redistributed here. Two of the four rules in `code/check_artifact_claims.py` read
`paper/main.tex`; run in this repository they report themselves as NOT DISTRIBUTED and are excluded
from the count of what was verified, rather than reported as a failure. Everything that backs a
number in the paper is here.

**`code/g2_verdicts.json.28jul-transcribed`** is kept on purpose and is read by nothing. It is the
transcription of an earlier result set that encoded outcomes as range rules, which is the practice
the Conventions section above says was removed. It is retained so that the change is inspectable
rather than merely asserted.

## Known limits

Three tiers of a single model family, so cross-family checker independence is untested. The
proportion estimates rest on 9 to 12 runs, so their exact-binomial intervals are wide and support
the claim that both modes occur often rather than any precise rate. The first benchmark is
saturated on judgment predicates and can no longer discriminate among verification architectures;
the second separates the cheap tier by roughly 0.15, so where the transition actually sits is open.
The 13 to 20 point liveness separation rests on a paired comparison: the marginal Clopper-Pearson
intervals for 0/30 against 4/30 and 6/30 overlap, and only the pairing (14 discordant artifacts,
all in the same direction, two-sided p = 1.22e-4) makes the difference decisive. Both are reported
in `paper/tables/hard-paired.csv`; neither should be quoted without the other.
