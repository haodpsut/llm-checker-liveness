"""Assemble g3_verdicts.json from 3 REAL model-tier checkers (opus/sonnet/haiku),
one neutral prompt, 28/07/2026. opus & sonnet both caught all defects; haiku transcribed."""
import json, re

# opus and sonnet: 001-018 PASS, 019-063 FAIL, 067-072 FAIL (both perfect, verbatim)
def perfect():
    d = {}
    for i in range(1,19):  d[f"G2-{i:03d}"]="PASS"
    for i in range(19,64): d[f"G2-{i:03d}"]="FAIL"
    for i in range(67,73): d[f"G2-{i:03d}"]="FAIL"
    return d
opus, sonnet = perfect(), perfect()

HAIKU = """
G2-019: FAIL G2-020: FAIL G2-021: FAIL G2-028: PASS G2-029: PASS G2-030: PASS
G2-037: FAIL G2-038: FAIL G2-039: FAIL G2-046: FAIL G2-047: FAIL G2-048: FAIL
G2-055: FAIL G2-056: FAIL G2-057: FAIL G2-022: FAIL G2-023: PASS G2-024: PASS
G2-025: FAIL G2-026: FAIL G2-027: PASS G2-031: PASS G2-032: PASS G2-033: PASS
G2-034: PASS G2-035: PASS G2-036: PASS G2-040: PASS G2-041: PASS G2-042: FAIL
G2-043: PASS G2-044: FAIL G2-045: FAIL G2-049: FAIL G2-050: FAIL G2-051: FAIL
G2-052: FAIL G2-053: FAIL G2-054: FAIL G2-058: FAIL G2-059: FAIL G2-060: FAIL
G2-061: FAIL G2-062: FAIL G2-063: FAIL G2-067: PASS G2-068: PASS G2-069: PASS
G2-070: PASS G2-071: PASS G2-072: PASS
G2-001: PASS G2-002: PASS G2-003: PASS G2-004: PASS G2-005: PASS G2-006: PASS
G2-007: PASS G2-008: PASS G2-009: PASS G2-010: PASS G2-011: PASS G2-012: PASS
G2-013: PASS G2-014: PASS G2-015: PASS G2-016: PASS G2-017: PASS G2-018: PASS
"""
haiku = {m.group(1): m.group(2) for m in re.finditer(r"(G2-\d{3}):\s*(PASS|FAIL)", HAIKU)}

for name,d in [("opus",opus),("sonnet",sonnet),("haiku",haiku)]:
    assert len(d)==69, f"{name} has {len(d)}"
json.dump({"opus":opus,"sonnet":sonnet,"haiku":haiku}, open("g3_verdicts.json","w"), indent=0)
print("wrote g3_verdicts.json | #FAIL:", {k:sum(1 for v in d.values() if v=='FAIL') for k,d in [('opus',opus),('sonnet',sonnet),('haiku',haiku)]})
