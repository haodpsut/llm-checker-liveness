"""Assemble g2_verdicts.json from the 3 real checker sub-agent outputs (28/07/2026)."""
import json, re

# strict: clean ranges (001-018 PASS, 019-063 FAIL, 067-072 FAIL) -- verbatim from agent
strict = {}
for i in range(1, 19):   strict[f"G2-{i:03d}"] = "PASS"
for i in range(19, 64):  strict[f"G2-{i:03d}"] = "FAIL"
for i in range(67, 73):  strict[f"G2-{i:03d}"] = "FAIL"

MODERATE = """
G2-019: PASS
G2-020: PASS
G2-021: PASS
G2-022: PASS
G2-023: PASS
G2-024: PASS
G2-025: PASS
G2-026: FAIL
G2-027: PASS
G2-028: PASS
G2-029: PASS
G2-030: PASS
G2-031: PASS
G2-032: FAIL
G2-033: PASS
G2-034: PASS
G2-035: PASS
G2-036: PASS
G2-037: FAIL
G2-038: FAIL
G2-039: FAIL
G2-040: PASS
G2-041: PASS
G2-042: FAIL
G2-043: PASS
G2-044: FAIL
G2-045: FAIL
G2-046: FAIL
G2-047: FAIL
G2-048: FAIL
G2-049: FAIL
G2-050: FAIL
G2-051: FAIL
G2-052: FAIL
G2-053: FAIL
G2-054: FAIL
G2-055: FAIL
G2-056: FAIL
G2-057: FAIL
G2-058: FAIL
G2-059: FAIL
G2-060: FAIL
G2-061: FAIL
G2-062: PASS
G2-063: FAIL
G2-067: PASS
G2-068: PASS
G2-069: PASS
G2-070: PASS
G2-071: PASS
G2-072: PASS
G2-001: PASS
G2-002: PASS
G2-003: PASS
G2-004: PASS
G2-005: PASS
G2-006: PASS
G2-007: PASS
G2-008: PASS
G2-009: PASS
G2-010: PASS
G2-011: PASS
G2-012: PASS
G2-013: PASS
G2-014: PASS
G2-015: PASS
G2-016: PASS
G2-017: PASS
G2-018: PASS
"""

LENIENT = """
G2-019: PASS
G2-020: PASS
G2-021: PASS
G2-028: PASS
G2-029: PASS
G2-030: PASS
G2-037: PASS
G2-038: PASS
G2-039: PASS
G2-046: FAIL
G2-047: FAIL
G2-048: FAIL
G2-055: FAIL
G2-056: FAIL
G2-057: FAIL
G2-022: PASS
G2-023: PASS
G2-024: PASS
G2-025: PASS
G2-026: FAIL
G2-027: PASS
G2-031: PASS
G2-032: PASS
G2-033: PASS
G2-034: PASS
G2-035: PASS
G2-036: PASS
G2-040: PASS
G2-041: PASS
G2-042: PASS
G2-043: PASS
G2-044: PASS
G2-045: PASS
G2-049: FAIL
G2-050: FAIL
G2-051: FAIL
G2-052: FAIL
G2-053: FAIL
G2-054: FAIL
G2-058: FAIL
G2-059: FAIL
G2-060: FAIL
G2-061: FAIL
G2-062: FAIL
G2-063: FAIL
G2-067: PASS
G2-068: PASS
G2-069: PASS
G2-070: PASS
G2-071: PASS
G2-072: PASS
G2-001: PASS
G2-002: PASS
G2-003: PASS
G2-004: PASS
G2-005: PASS
G2-006: PASS
G2-007: PASS
G2-008: PASS
G2-009: PASS
G2-010: PASS
G2-011: PASS
G2-012: PASS
G2-013: PASS
G2-014: PASS
G2-015: PASS
G2-016: PASS
G2-017: PASS
G2-018: PASS
"""

def parse(block):
    d = {}
    for m in re.finditer(r"(G2-\d{3}):\s*(PASS|FAIL)", block):
        d[m.group(1)] = m.group(2)
    return d

moderate = parse(MODERATE)
lenient = parse(LENIENT)

# integrity: all three cover the same id set
ids = set(strict) & set(moderate) & set(lenient)
for name, d in [("strict", strict), ("moderate", moderate), ("lenient", lenient)]:
    missing = set(strict) - set(d)
    assert not missing, f"{name} missing {sorted(missing)}"
    assert len(d) == len(strict), f"{name} has {len(d)} != {len(strict)}"

out = {"strict": strict, "moderate": moderate, "lenient": lenient}
json.dump(out, open("g2_verdicts.json", "w"), indent=0)
print(f"wrote g2_verdicts.json | {len(strict)} artifacts x 3 checkers")
print("per-checker #FAIL:", {k: sum(1 for v in d.values() if v=='FAIL') for k,d in out.items()})
