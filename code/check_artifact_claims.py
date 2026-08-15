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

# (file, regex with one capture group, what the number must equal, human label)
def rules():
    n_logs = len([f for f in os.listdir(RAW) if f.endswith(".txt")])
    n_csv = len([f for f in os.listdir(os.path.join(ROOT, "paper", "tables"))
                 if f.endswith(".csv")])
    return [
        ("ARTIFACT-README.md", r"(\d+)\s+raw checker logs", n_logs, "so log tho"),
        ("code/raw/RUN-LOG.md", r"\*\*(\d+)\s+logged runs", n_logs, "so luot da ghi log"),
        ("paper/main.tex", r"all\s+\$(\d+)\$\s+raw checker logs", n_logs, "so log tho neu trong bai"),
        ("paper/main.tex", r"Raw logs for all\s+\$(\d+)\$\s+runs", n_logs, "so luot trong caption"),
    ], n_logs, n_csv


def main():
    checks, n_logs, n_csv = rules()
    print(f"check_artifact_claims -- thuc te tren dia: {n_logs} log tho, {n_csv} CSV\n")
    bad, seen = [], 0
    for rel, pat, want, label in checks:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            bad.append(f"{rel}: khong ton tai")
            continue
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

    print(f"\n  da doi chieu {seen} con so")
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
    print("\nPASS -- van xuoi cua artifact khop voi noi dung artifact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
