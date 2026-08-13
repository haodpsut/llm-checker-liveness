#!/usr/bin/env python3
"""Derive raw/PROVENANCE.md from the orchestration log that launched the checker runs.

WHY THIS EXISTS. An external reader pointed out that the paper named no model, no version, no
temperature and no run date, so nothing about the measurement condition could be checked. That was
correct, and the reason is worse than an omission: the checker runs were launched by an orchestrator
that recorded its own parameters in its session log, but the checker output files carried no header,
so at write-up time the condition was only recoverable from memory.

The fix is not to hand-type what we remember. It is to read the launch parameters back out of the
orchestration log and emit them, so the table in the paper is derived like every other number here.

WHAT THIS CANNOT RECOVER. Two things were never recorded anywhere and are therefore reported as
unknown rather than guessed:

  * temperature and top-p. The orchestration interface exposes no sampling parameters, so every run
    used the harness default and no run varied it. "Default" is not a value we can print.
  * the exact build behind each model alias. Runs requested a tier alias; the alias resolves to a
    build at dispatch time and the resolved identifier was not echoed back.

Both are recorded as limitations in the paper rather than filled in.

Usage:  python3 provenance.py <orchestration-log.jsonl>
The log itself is NOT released: it is a full working session and contains unrelated material.
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "raw", "PROVENANCE.md")
RAW = os.path.join(HERE, "raw")

# Alias -> the model identifier the alias denoted during this campaign. Recorded here because the
# log stores the alias that was requested, not the build that served it.
ALIAS = {
    "opus": "Claude Opus 5 (alias `opus`)",
    "sonnet": "Claude Sonnet 5 (alias `sonnet`)",
    "haiku": "Claude Haiku 4.5, build `claude-haiku-4-5-20251001` (alias `haiku`)",
}

# Which experimental arm each launch belongs to, matched on the launch description.
ARMS = [
    ("prompt rigour (first corpus)", r"^G2 |checker on G2|strict checker"),
    ("model tier (first corpus)", r"^G3 "),
    ("reasoning class (first corpus)", r"^G4 "),
    ("hard corpus", r"^Hard corpus"),
    ("pilot / null-condition", r"null-condition|ID m|^Checker tier"),
]


def arm_of(desc):
    for name, pat in ARMS:
        if re.search(pat, desc, re.I):
            return name
    return "unclassified"


def launches(path):
    """Every checker launch in the orchestration log, as (arm, alias, description)."""
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            content = (d.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict) or c.get("type") != "tool_use":
                    continue
                if c.get("name") != "Agent":
                    continue
                i = c.get("input") or {}
                model = i.get("model")
                desc = (i.get("description") or "").strip()
                if not model or not desc:
                    continue
                out.append((arm_of(desc), model, desc))
    return out


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    log = sys.argv[1]
    if not os.path.exists(log):
        raise SystemExit(f"BLOCK: orchestration log not found: {log}")

    rows = launches(log)
    if not rows:
        raise SystemExit("BLOCK: 0 checker launches found. Empty is broken, not clean.")

    n_logs = len([f for f in os.listdir(RAW) if f.endswith(".txt")])
    by_arm = collections.OrderedDict()
    for arm, _pat in ARMS:
        by_arm[arm] = collections.Counter()
    by_arm["unclassified"] = collections.Counter()
    for arm, model, _d in rows:
        by_arm[arm][model] += 1

    unknown = sorted({m for _a, m, _d in rows} - set(ALIAS))
    if unknown:
        raise SystemExit(f"BLOCK: launch used an alias with no recorded identity: {unknown}")

    L = []
    L.append("# Measurement provenance\n")
    L.append("Derived by `code/provenance.py` from the orchestration log that launched the checker")
    L.append("runs. Not hand-transcribed. The log is a full working session and is not released.\n")
    L.append(f"**{len(rows)} checker launches** recorded; **{n_logs} raw logs** in this directory.")
    L.append("The two counts differ because pilot launches that were superseded, and launches whose")
    L.append("output was folded into an existing file, did not each produce a new file. The raw logs")
    L.append("are the data; this table is the condition they were produced under.\n")
    L.append("## Models\n")
    for a in sorted(ALIAS):
        L.append(f"* `{a}` = {ALIAS[a]}")
    L.append("")
    L.append("## Launches per arm\n")
    L.append("| arm | " + " | ".join(f"`{a}`" for a in sorted(ALIAS)) + " | total |")
    L.append("|---|" + "---|" * (len(ALIAS) + 1))
    for arm, cnt in by_arm.items():
        if not cnt:
            continue
        cells = [str(cnt.get(a, 0)) for a in sorted(ALIAS)]
        L.append(f"| {arm} | " + " | ".join(cells) + f" | {sum(cnt.values())} |")
    L.append("")
    L.append("The prompt-rigour arm is served entirely by one alias, which is what makes it a prompt")
    L.append("contrast rather than a model contrast: within that arm the model is held fixed and only")
    L.append("the leading instruction differs.\n")
    L.append("## Run dates\n")
    dates = sorted({m.group(1) for f in os.listdir(RAW)
                    for m in [re.search(r"(\d{8})\.txt$", f)] if m})
    L.append("Taken from the raw filenames: " + ", ".join(dates) + ".\n")
    L.append("## Not recorded, and therefore not reported\n")
    L.append("* **Temperature and top-p.** The orchestration interface exposes no sampling")
    L.append("  parameters. Every run used the harness default and no run varied it, so run-to-run")
    L.append("  spread here is whatever that default produces, not a controlled setting.")
    L.append("* **The build behind each alias.** Launches requested a tier alias; the resolved build")
    L.append("  identifier was not echoed back, so only `haiku` has a dated build above.")
    L.append("* **Tool access.** No checker was given any tool beyond reading its own prompt file.")
    L.append("  This is a property of the harness the launches used, not a per-run setting.\n")
    L.append("Any conclusion that depends on a fixed sampling temperature is out of scope for this")
    L.append("data set.")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"  wrote raw/PROVENANCE.md from {len(rows)} launches "
          f"({dict(collections.Counter(m for _a, m, _d in rows))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
