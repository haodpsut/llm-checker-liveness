#!/usr/bin/env python3
"""Emit the two corpus-composition CSVs that the paper still cites: compose.csv and corpus.csv.

Why this is a separate file. These two tables describe the CORPUS ITSELF, so they depend only on
`g2_corpus.py` and on no measurement. They used to be produced by `g2_tables.py`, which also
formatted several result tables that have since been retired to `paper/tables/legacy-28jul/`. When
those CSVs were moved, `g2_tables.py` began failing at import time on its first `open()` while the
two tables the paper needs were left stale, and the failure was invisible because the freshness gate
only reports that a CSV is older than its producer, not why.

The lesson recorded with it: a clean-clone check must run EVERY script the repository ships, not
only the ones listed in the README. The README commands all passed while this one was broken.

No measurement input, so this is deterministic and safe to re-run at any time.
"""
import csv
import os

from g2_corpus import CORPUS, JUDGE_CLASSES

TBL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "paper", "tables")


def wcsv(name, header, rows):
    with open(os.path.join(TBL, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  wrote {name}: {len(rows)} rows")


def count(cls, **kw):
    return sum(1 for a in CORPUS
               if a["defect_class"] == cls and all(a.get(k) == v for k, v in kw.items()))


def main():
    rows = []
    for cls in JUDGE_CLASSES + ["fabricated-citation"]:
        kind = "judgment" if cls in JUDGE_CLASSES else "decidable"
        seed = count(cls, is_seed=True)
        held = sum(1 for a in CORPUS if a["defect_class"] == cls and not a["is_seed"])
        rows.append([cls, kind, seed, held,
                     count(cls, difficulty="subtle"), count(cls, difficulty="moderate")])
    wcsv("compose.csv", ["class", "kind", "n_seed", "n_heldout", "n_subtle", "n_moderate"], rows)

    wcsv("corpus.csv", ["quantity", "n"], [
        ["total", len(CORPUS)],
        ["clean", sum(1 for a in CORPUS if a["defect_class"] == "clean")],
        ["defective", sum(1 for a in CORPUS if a["defect_class"] != "clean")],
        ["defective_seed", sum(1 for a in CORPUS
                               if a["defect_class"] != "clean" and a["is_seed"])],
        ["defective_heldout", sum(1 for a in CORPUS
                                  if a["defect_class"] != "clean" and not a["is_seed"])],
    ])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
