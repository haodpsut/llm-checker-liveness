#!/usr/bin/env python3
"""Numbers stated in the ARTIFACT's own prose must match what the artifact actually contains.

WHY THIS EXISTS. Ca 15/08/2026. The paper was updated from 58 to 76 logged runs when a second model
family was added. `main.tex` was updated, `claims.json` was updated, every CSV was regenerated, and
the number-tracing gate passed. But `ARTIFACT-README.md` and `raw/RUN-LOG.md` still said 58, and a
reader comparing the paper against the released artifact saw two different headline numbers.

No gate caught it, because every gate we had compares the PAPER against the CSVs. Nobody was
comparing the ARTIFACT'S OWN PROSE against the artifact's own contents. The README is a claim
surface like any other: it is the first thing a reviewer or a reproducer reads, and when it
disagrees with the paper the reader has no way to tell which one is stale.

The rule is narrow on purpose: it checks counts that can be resolved against the filesystem, so it
cannot produce opinions, only arithmetic. Anything it cannot resolve, it says so rather than
passing silently.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(HERE, "raw")

# The README travels under two names: `ARTIFACT-README.md` inside the authors' paper tree, and
# `README.md` at the root of the released repository, because that is the name a reader sees first.
# Either satisfies the rule; a rule whose file is absent under BOTH names is a real miss.
README_NAMES = ("README.md", "ARTIFACT-README.md")

# `paper/main.tex` is deliberately NOT part of the released artifact: the manuscript is a separate
# claim surface and is not redistributed here. The two rules that read it can therefore only run in
# the authors' tree. They are marked `in_paper_tree_only` so that, in the released repository, they
# are reported as NOT DISTRIBUTED and counted in their own denominator, rather than reported as a
# prose mismatch -- which would tell a reproducer the artifact is broken when it is not.
# Ca 23/10/2026: before this split, `python3 code/check_artifact_claims.py` exited 2 in the public
# repository and printed "khong ton tai" for a file that is absent by design.

# (file, regex with one capture group, what the number must equal, human label, paper-tree-only)
def rules():
    n_logs = len([f for f in os.listdir(RAW) if f.endswith(".txt")])
    n_csv = len([f for f in os.listdir(os.path.join(ROOT, "paper", "tables"))
                 if f.endswith(".csv")])
    return [
        (README_NAMES, r"(\d+)\s+raw checker logs", n_logs, "so log tho", False),
        ("code/raw/RUN-LOG.md", r"\*\*(\d+)\s+logged runs", n_logs, "so luot da ghi log", False),
        ("paper/main.tex", r"all\s+\$(\d+)\$\s+raw checker logs", n_logs, "so log tho neu trong bai", True),
        ("paper/main.tex", r"Raw logs for all\s+\$(\d+)\$\s+runs", n_logs, "so luot trong caption", True),
    ], n_logs, n_csv


def main():
    checks, n_logs, n_csv = rules()
    print(f"check_artifact_claims -- thuc te tren dia: {n_logs} log tho, {n_csv} CSV\n")
    bad, seen, khong_phat_hanh = [], 0, []
    for rel, pat, want, label, chi_trong_cay_bai in checks:
        ten = (rel,) if isinstance(rel, str) else rel
        path = next((os.path.join(ROOT, r) for r in ten
                     if os.path.exists(os.path.join(ROOT, r))), None)
        if path is None:
            if chi_trong_cay_bai:
                khong_phat_hanh.append(f"{ten[0]}: {label}")
            else:
                bad.append(f"{ten[0]}: khong ton tai")
            continue
        rel = os.path.relpath(path, ROOT)
        txt = open(path, encoding="utf-8", errors="replace").read()
        hits = re.findall(pat, txt)
        if not hits:
            print(f"  BO QUA  {rel:26s} {label} -- khong tim thay mau, KHONG phai da kiem")
            continue
        for h in hits:
            seen += 1
            ok = int(h) == want
            print(f"  {'OK   ' if ok else 'LECH '}  {rel:26s} {label}: ghi {h}, thuc te {want}")
            if not ok:
                bad.append(f"{rel}: {label} ghi {h} nhung thuc te la {want}")

    # Hai don vi khac nhau, nen dem rieng: SO CON SO da doi chieu, va SO LUAT khong chay duoc.
    # Gop chung vao mot mau so la sai, vi mot luat co the khop nhieu con so trong cung mot tep.
    n_luat = len(checks)
    print(f"\n  da doi chieu {seen} con so, tu {n_luat - len(khong_phat_hanh)}/{n_luat} luat chay duoc o day")
    if khong_phat_hanh:
        print(f"  KHONG PHAT HANH -- {len(khong_phat_hanh)}/{n_luat} luat doc `paper/main.tex`, la")
        print("  ban thao, KHONG nam trong artifact nay. Chung chi chay duoc trong cay cua tac gia;")
        print("  o day chung KHONG duoc coi la da kiem:")
        for k in khong_phat_hanh:
            print(f"    - {k}")
    if seen == 0:
        print("BLOCK: khong doi chieu duoc con so nao. Kiem 0 don vi khong phai la sach.")
        return 2
    if bad:
        print(f"\nBLOCK -- {len(bad)} con so trong van xuoi cua ARTIFACT khong khop thuc te:")
        for b in bad:
            print(f"  - {b}")
        print("  README la mot BE MAT TUYEN BO. Doc gia doi chieu bai voi artifact se thay hai so")
        print("  khac nhau va khong biet cai nao cu.")
        return 2
    con_lai = (f" {len(khong_phat_hanh)} luat doc ban thao khong kiem duoc o ban phat hanh."
               if khong_phat_hanh else "")
    print(f"\nPASS -- van xuoi cua artifact khop voi noi dung artifact: {seen} con so dung.{con_lai}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
