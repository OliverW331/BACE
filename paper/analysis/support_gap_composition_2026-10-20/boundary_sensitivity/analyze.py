"""Post-experiment arithmetic sensitivity; no new judgments or model calls.

Primary estimand: exclude BACE factual_boundary_distortion claims from the
denominator, retaining the supported numerator. Average within-disclosure
rates over the same jointly completed disclosures. Comparator native scores
are unchanged; this is not removal of a common aligned claim inventory.
Secondary scenario: hypothetically relabel this category as supported without
changing the denominator. Neither scenario is an accuracy correction.
"""
import csv
import hashlib
import io
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
SNAPSHOT = ROOT / "BACE/analysis/outputs/snapshot"
inputs = {}


def read(path):
    content = path.read_bytes()
    inputs[str(path.relative_to(ROOT))] = hashlib.sha256(content).hexdigest()
    return content


manifest = json.loads(read(SNAPSHOT / "manifest.json"))
tables = {n: list(csv.DictReader(io.StringIO(read(SNAPSHOT / f"{n}.csv").decode())))
          for n in ("metrics", "claims")}
for n in tables:
    assert inputs[str((SNAPSHOT / f"{n}.csv").relative_to(ROOT))] == manifest["tables"][n]
metrics = {r["generation_case_id"]: r for r in tables["metrics"]
           if all(r[f"{f}_complete"] == "True" for f in ("bace", "ragas", "ragchecker"))}
counts = defaultdict(Counter)
for r in tables["claims"]:
    if r["generation_case_id"] in metrics:
        counts[r["generation_case_id"]][r["label"]] += 1
rows = []
for cid, m in sorted(metrics.items()):
    c = counts[cid]
    n, s, b = sum(c.values()), c["direct"] + c["inferred"], c["factual_boundary_distortion"]
    assert n == int(float(m["bace_dc_count"]))
    assert s == int(float(m["bace_supported_direct"])) + int(float(m["bace_supported_inferred"]))
    assert b == int(float(m["bace_factual_boundary_distortion"]))
    assert n - b > 0, (cid, "Zero adjusted denominator; review the analysis cohort")
    assert math.isclose(s / n, float(m["bace_support_rate_all_dc"]), abs_tol=1e-12)
    rows.append({"generation_case_id": cid, "company_id": m["company_id"],
                 "bace_claims": n, "supported": s, "boundary_distortion": b,
                 "remaining_claims": n - b, "bace_native": s / n,
                 "bace_excluding_boundary": s / (n - b),
                 "bace_hypothetical_boundary_supported": (s + b) / n,
                 "ragas_native": float(m["ragas_faithfulness"]),
                 "ragchecker_native": float(m["ragchecker_faithfulness"])})
with (OUT / "disclosure_sensitivity.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
macro = {k: 100 * mean(r[k] for r in rows) for k in
         ("bace_native", "bace_excluding_boundary", "bace_hypothetical_boundary_supported",
          "ragas_native", "ragchecker_native")}
totals = {k: sum(r[k] for r in rows) for k in
          ("bace_claims", "supported", "boundary_distortion", "remaining_claims")}
result = {
    "computed_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "COMPUTED_VERIFIED", "analysis_status": "Post-experiment descriptive sensitivity",
    "planned_disclosures": len(tables["metrics"]), "complete_disclosures": len(rows),
    "companies": len({r["company_id"] for r in rows}),
    "excluded_incomplete_cases": sorted(set(r["generation_case_id"] for r in tables["metrics"]) - set(metrics)),
    "zero_adjusted_denominators": 0, "pooled_claim_counts": totals,
    "disclosure_macro_support_percent": macro,
    "comparator_minus_bace_gap_pp": {
        scenario: {f: macro[f + "_native"] - macro[scenario] for f in ("ragas", "ragchecker")}
        for scenario in ("bace_native", "bace_excluding_boundary", "bace_hypothetical_boundary_supported")},
    "bace_pooled_excluding_boundary_percent": 100 * totals["supported"] / totals["remaining_claims"],
    "primary_formula": "mean_disclosures[supported / (all_BACE_claims - factual_boundary_distortion)]",
    "secondary_formula": "mean_disclosures[(supported + factual_boundary_distortion) / all_BACE_claims]",
    "interpretation": "Comparator native scores retain their full native inventories. These sensitivities change the BACE estimand only and do not establish evaluator accuracy or a causal contribution of the category to the native gap.",
    "inference": {"tests": "None", "intervals": "None; exact description of saved outputs", "seed": None},
    "provenance": {"input_sha256": inputs, "python": sys.version, "executable": sys.executable,
                   "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   "command": "python paper/analysis/support_gap_composition_2026-10-20/boundary_sensitivity/analyze.py",
                   "output_csv_sha256": hashlib.sha256((OUT / "disclosure_sensitivity.csv").read_bytes()).hexdigest(),
                   "model_calls": 0, "experiment_changes": []}}
(OUT / "results.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "provenance"}, indent=2))
