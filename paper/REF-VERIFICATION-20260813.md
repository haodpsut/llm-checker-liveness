# Reference verification record

23 entries in `refs.bib`. For each, this records **the source that was opened** and **the result of
the comparison**, not "skimmed and looked plausible".

Tools: `verify_refs_layer2.py` (Crossref, field by field) and the arXiv API. Raw evidence:
`l2-report.txt`, `arxiv-verify.json`, `xref-direct.json`.

## Summary

| | |
|---|---|
| Entries verified against Crossref, **0 field mismatches** | **9** |
| Entries verified at source on arXiv (title, first author, author count, year) | **13** |
| Entries whose source **could not be opened** | **1** (a book) |
| Individual fields compared | **117** |

## A. Nine entries with DOIs, Crossref-verified, no mismatches

`lamport1982byzantine` · `jia2011mutation` · `kamoi2024selfcorrect` · `madaan2023selfrefine` ·
`schick2023toolformer` · `shinn2023reflexion` · `zheng2023judging` · `panickssery2024selfpref` ·
`dhuliawala2023cove`

### Three REAL errors, found by opening the source rather than trusting Crossref alone

1. **`schick2023toolformer` was missing an author.** The proceedings page lists **9** authors; the
   entry had **8**, omitting the sixth. Added.
2. **`shinn2023reflexion` had an author too many.** The **proceedings** version has **5** authors;
   the entry carried the **arXiv** author list (6) on a proceedings citation. Removed.
3. **Four entries cited arXiv preprints that already had published versions.**
   `dhuliawala2023cove` is in Findings of ACL 2024; `panickssery2024selfpref` is in NeurIPS 2024
   with page numbers. Entry type and venue corrected in both.

All three errors sat in the **middle or tail** of the author list, never in the first author or the
title. That is where they survive review.

## B. Thirteen entries without DOIs, verified on arXiv

ICLR, ICML, pre-2023 NeurIPS and preprint-only work **do not register Crossref DOIs**. For these,
arXiv is the source of record. Title, first-author surname, author count and year were compared via
the arXiv API; all thirteen agree.

Three entries differ in author **count** only because the entry uses `and others`, which is standard
BibTeX. Not an error.

## C. One entry whose source could not be opened

A monograph published by a university press. Both publisher URLs return **HTTP 403** from this
environment. Crossref holds the **online edition** with a year one later than the print edition
recorded in the entry.

**Decision: the DOI was removed and the print year kept.** Pairing a print year with an online
edition's DOI would be wrong, and the print year could not be confirmed at source, so it was not
changed either. The entry is left **UNRESOLVED**, which is an honest statement that it has not been
proven at source, not a statement that it is clean.

## D. Two cases where the GATE was wrong, and the gate was fixed rather than the bibliography

Both were recorded as rules in the verification pipeline:

1. **A publisher deposited a title containing HTML markup.** `html.unescape` converts entities but
   does not strip tags, so the leftover tag was compared as text and the gate reported a title
   mismatch on a perfectly correct entry.
2. **LaTeX-command diacritics.** Unicode normalisation removes accents from **characters** but not
   from LaTeX commands, so an accented surname written as a command never matched its plain form.

The **first fix was itself wrong**: it used an optional-brace pattern that consumed the closing
brace without the opening one, leaving an unbalanced string, so the gate still failed, only with a
different message. It was rewritten with three explicit balanced forms, given **four negative test
cases** so that loosening normalisation cannot blind the gate, and re-run against a separate,
already-clean bibliography to confirm no regression.
