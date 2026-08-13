# Checker liveness: two defect benchmarks, a fail-closed gate, and 58 raw checker logs

This is the artifact for a measurement study of **positive-control liveness**: the idea that a
verification gate should emit PASS only while its checkers keep catching a pool of seeded defects.
We built such a gate, measured it, and report what the measurements say. They are mostly negative
about it.

Everything quoted in the paper is derived here, and every derivation starts from a **raw checker
log** in `code/raw/`.

## The two findings the artifact is for

**The blind spot moves.** On the harder benchmark the cheap checker fails *systematically*, missing
an entire defect class rather than scattered instances, which is the regime liveness screening
exists for. But *which* class it is blind to changes between identical runs. See
`paper/tables/hard-blindspot-shift.csv` and the three `code/raw/h-cheap-r*.txt` logs.

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
  check_freshness.py      every CSV must be newer than its producer and its raw data
  csv-producer.map        which script produces which CSV
  raw/                    58 raw checker logs + RUN-LOG.md
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
python3 code/check_freshness.py  # no table may be older than the data behind it
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

## Known limits

Three tiers of a single model family, so cross-family checker independence is untested. The
proportion estimates rest on 9 to 12 runs, so their exact-binomial intervals are wide and support
the claim that both modes occur often rather than any precise rate. The first benchmark is
saturated on judgment predicates and can no longer discriminate among verification architectures;
the second separates the cheap tier by roughly 0.15, so where the transition actually sits is open.
