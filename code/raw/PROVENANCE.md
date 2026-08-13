# Measurement provenance

Derived by `code/provenance.py` from the orchestration log that launched the checker
runs. Not hand-transcribed. The log is a full working session and is not released.

**65 checker launches** recorded; **58 raw logs** in this directory.
The two counts differ because pilot launches that were superseded, and launches whose
output was folded into an existing file, did not each produce a new file. The raw logs
are the data; this table is the condition they were produced under.

## Models

* `haiku` = Claude Haiku 4.5, build `claude-haiku-4-5-20251001` (alias `haiku`)
* `opus` = Claude Opus 5 (alias `opus`)
* `sonnet` = Claude Sonnet 5 (alias `sonnet`)

## Launches per arm

| arm | `haiku` | `opus` | `sonnet` | total |
|---|---|---|---|---|
| prompt rigour (first corpus) | 0 | 0 | 24 | 24 |
| model tier (first corpus) | 3 | 3 | 3 | 9 |
| reasoning class (first corpus) | 10 | 3 | 3 | 16 |
| hard corpus | 3 | 3 | 3 | 9 |
| pilot / null-condition | 3 | 2 | 2 | 7 |

The prompt-rigour arm is served entirely by one alias, which is what makes it a prompt
contrast rather than a model contrast: within that arm the model is held fixed and only
the leading instruction differs.

## Run dates

Taken from the raw filenames: 20260813.

## Not recorded, and therefore not reported

* **Temperature and top-p.** The orchestration interface exposes no sampling
  parameters. Every run used the harness default and no run varied it, so run-to-run
  spread here is whatever that default produces, not a controlled setting.
* **The build behind each alias.** Launches requested a tier alias; the resolved build
  identifier was not echoed back, so only `haiku` has a dated build above.
* **Tool access.** No checker was given any tool beyond reading its own prompt file.
  This is a property of the harness the launches used, not a per-run setting.

Any conclusion that depends on a fixed sampling temperature is out of scope for this
data set.
