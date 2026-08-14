#!/usr/bin/env python3
"""Every script this repository ships must either run, refuse with a usage line, or be declared dead.

WHY THIS EXISTS. Twice now a shipped script was broken and nothing noticed. The first time,
`g2_tables.py` began failing at import when several CSVs were retired to `legacy-28jul/`, and the
clean-clone check missed it because that check ran only the five commands the README lists. The
second time, five retired producers under `legacy-28jul/producers/` turned out to be unrunnable from
a fresh clone at all: they resolve their inputs relative to `code/`, so moving them broke every path
they use. They were kept "for comparison", but a producer that cannot run documents nothing a reader
can check; it is a claim about provenance with no evidence behind it.

The rule this enforces is the one the README already states and could not previously back up: a
clean-clone check must exercise EVERY script the repository ships, not the subset that is convenient
to document. Each script must fall into exactly one of three states, and an unclassified script is a
failure rather than a default pass:

  RUNS    exits 0 with no arguments. The default expectation.
  USAGE   exits non-zero AND prints a usage line, because it genuinely needs an argument.
          Refusing clearly is a pass; failing silently is not.
  FROZEN  declared below with a reason. A frozen script is never executed, and the declaration is
          what makes it honest: the reader is told it is inert instead of discovering it.

Run from anywhere: `python3 code/check_scripts_run.py`. Exit 0 = every script accounted for.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Scripts that are kept for provenance and are NOT expected to run. Each needs a reason a reader can
# evaluate, not just a name on a list.
FROZEN = {
    "paper/tables/legacy-28jul/producers/g2_tables.py":
        "retired producer of the 28 July measurement set. It resolves its inputs relative to code/ "
        "and reads CSVs that were retired with it, so it cannot run from its current location. Kept "
        "to show how the earlier tables were built, not to rebuild them.",
    "paper/tables/legacy-28jul/producers/g2_realreport.py":
        "as above; imports g2_corpus from code/, which is not on the path from this directory.",
    "paper/tables/legacy-28jul/producers/g2_tau.py":
        "as above; imports g2_corpus from code/.",
    "paper/tables/legacy-28jul/producers/g3_paper_artifacts.py":
        "as above; imports g2_corpus from code/.",
    # The paper draws all three of its figures inline in TikZ, so the matplotlib producers below
    # have no consumer. They also read CSVs (sweep.csv, tau.csv, g3-regime.csv) that were retired
    # with the 28 July measurement set, so they cannot run even if something wanted them to.
    "paper/figs/make_fig2.py":
        "dead matplotlib producer: reads the retired tables/sweep.csv, and its figure is now drawn "
        "inline in TikZ.",
    "paper/figs/make_fig3.py":
        "dead matplotlib producer: reads the retired tables/tau.csv.",
    "paper/figs/make_fig_regime.py":
        "dead matplotlib producer: reads the retired figs/g3-regime.csv.",
    "paper/tables/legacy-28jul/producers/g4_analyze.py":
        "as above; imports g4_corpus from code/. Its output g4_verdicts.json is superseded by the "
        "raw logs, which are now the source of truth.",
}

# Scripts that legitimately require an argument. They must REFUSE clearly rather than fail silently.
NEEDS_ARGS = {
    "code/provenance.py":
        "takes the orchestration log path; that log is a full working session and is not released.",
    "code/raw/_from_faillist.py": "takes an output file and a fail list.",
    "code/raw/_write_raw.py": "takes an output file and the IDs to write.",
    "paper/style/measure_plot.py": "takes the PDF to measure.",
}

TIMEOUT = 180


def shipped():
    """Every .py the repository ships, as repo-relative paths, in a stable order."""
    try:
        out = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True,
                             text=True, timeout=30)
        files = [l for l in out.stdout.split("\n") if l.strip()]
    except (OSError, subprocess.SubprocessError):
        files = []
    if not files:                       # not a git checkout: fall back to a walk
        for dirpath, dirs, names in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
            for n in names:
                if n.endswith(".py"):
                    files.append(os.path.relpath(os.path.join(dirpath, n), ROOT))
    return sorted(files)


def main():
    # Exclude THIS file. Without it the checker executes itself, and each copy executes itself
    # again: the first run spawned a tree of processes and only stopped at the 180s timeout, which
    # it then reported as an ordinary failing script. A completeness checker that enumerates
    # everything will enumerate itself, and "run every script" has to mean every OTHER script.
    me = os.path.relpath(os.path.abspath(__file__), ROOT)
    files = [f for f in shipped() if f != me]
    if not files:
        print("BLOCK: found 0 python scripts. Empty is broken, not clean.")
        return 2

    # A declaration for a file this checkout does not contain is INERT, not a fault, and must not
    # block. The published repository ships a subset of the working tree (no paper/figs, no
    # paper/style), so the same declaration list is partly active in the authoring tree and partly
    # dormant in a clone. Two earlier versions of this check got that wrong in opposite directions:
    # first it blocked on "declared but not shipped", then on "declared but absent", and each time
    # every clone of the artifact reported faults that were neither stale nor exemptions. A gate
    # that cries wolf on a correct checkout is the one people learn to skip.
    #
    # What this gate is actually for is unchanged and unweakened: a script that IS present must run,
    # refuse with a usage line, or be declared dead. Nothing below can be silenced by a declaration.
    inert = sorted((set(FROZEN) | set(NEEDS_ARGS)) - set(files))
    problems = []

    ran = usage = frozen = 0
    print(f"check_scripts_run -- {len(files)} shipped script(s)\n")
    for rel in files:
        if rel in FROZEN:
            frozen += 1
            print(f"  FROZEN {rel}")
            continue
        path = os.path.join(ROOT, rel)
        try:
            p = subprocess.run([sys.executable, path], cwd=os.path.dirname(path),
                               capture_output=True, text=True, timeout=TIMEOUT)
            rc, out = p.returncode, (p.stdout + p.stderr)
        except subprocess.TimeoutExpired:
            rc, out = -1, f"timed out after {TIMEOUT}s"
        if rel in NEEDS_ARGS:
            if rc != 0 and "usage" in out.lower():
                usage += 1
                print(f"  USAGE  {rel}")
            else:
                problems.append(f"{rel}: declared as needing arguments but "
                                f"{'exited 0' if rc == 0 else 'printed no usage line'}")
                print(f"  BAD    {rel}")
        elif rc == 0:
            ran += 1
            print(f"  RUNS   {rel}")
        else:
            problems.append(f"{rel}: exit {rc}. Either fix it, declare it in NEEDS_ARGS with the "
                            f"argument it wants, or declare it FROZEN with a reason. "
                            f"Last line: {out.strip().splitlines()[-1] if out.strip() else '(no output)'}")
            print(f"  FAIL   {rel}")

    print(f"\n  ran clean: {ran}   refused with usage: {usage}   declared frozen: {frozen}   "
          f"unaccounted: {len(problems)}")
    if inert:
        print(f"  declarations inert in this checkout (not part of it): {len(inert)}")
        for i in inert:
            print(f"      {i}")
    if problems:
        print("\nBLOCK -- every shipped script must run, refuse clearly, or be declared dead:")
        for p in problems:
            print(f"  - {p}")
        return 2
    print("\nPASS -- every shipped script is accounted for.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
