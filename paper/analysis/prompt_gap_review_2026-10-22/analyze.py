"""Verify saved prompt runs and compare gaps on the same complete disclosures."""
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
OLD = ROOT / "paper/analysis/residual_gap_review_2026-10-20"
SAVED = ROOT / "BACE/analysis/outputs/evaluator_gap/prompt_sensitivity"
INPUTS = {}
VARIANTS = ("ragas_style", "ragchecker_style")


def read(path, expected=None):
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    INPUTS[str(path.relative_to(ROOT))] = sha
    if expected:
        assert sha == expected, path
    return data


def rows(path, expected=None):
    return csv.DictReader(io.StringIO(read(path, expected).decode()))


def close(a, b):
    assert abs(float(a) - float(b)) < 1e-12, (a, b)


def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_csv(name, entries):
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(entries[0]))
        w.writeheader()
        w.writerows(entries)


# Exact descriptive estimands; no new inferential tests or model calls.
write_json("analysis_plan.json", {
    "status": "Post-experiment descriptive analysis of saved outputs",
    "primary": "Native score minus each BACE-condition support rate, paired by disclosure; positive means the native score is higher.",
    "aggregation": "Equal weight per complete disclosure; report claim-pooled BACE rates separately.",
    "sample": "Whole-disclosure complete cases in the saved three-condition prompt experiment; retain zero-candidate claims.",
    "secondary": "Remove original-BACE factual_boundary_distortion claims from each BACE condition's numerator and denominator. Native inventories remain unchanged.",
    "selection": "Reuse the existing R01-R18 examples for longitudinal comparison, without reselecting on new outcomes.",
    "inference": "No new intervals or tests; saved company-cluster intervals for prompt effects are separately attributed. These are descriptive score gaps, not accuracy gaps or causal allocations.",
})
prov = json.loads(read(SAVED / "provenance.json"))
freeze = json.loads(read(ROOT / "BACE/experiments/prompt_sensitivity_v1/freeze.json", prov["freeze_sha256"]))
plan = json.loads(read(ROOT / "BACE/experiments/prompt_sensitivity_v1/plan.json", prov["plan_sha256"]))
status = json.loads(read(ROOT / "BACE/results/prompt_sensitivity_v1/status.json"))
assert status["status"] == "COMPLETED"
old_prov = json.loads(read(OLD / "selection_provenance.json"))
packets = {}
key_to_rid = {}
for i in range(1, 19):
    rid = f"R{i:02d}"
    p = json.loads(read(OLD / f"packets/{rid}.json", old_prov["output_sha256"][f"packets/{rid}.json"]))
    packets[rid] = p
    key_to_rid[p["selection"]["generation_case_id"], p["target_dc"]["dc_id"]] = rid
metrics = {r["generation_case_id"]: r for r in rows(ROOT / "BACE/analysis/outputs/snapshot/metrics.csv", freeze["files"]["BACE/analysis/outputs/snapshot/metrics.csv"])}
labels = {(r["generation_case_id"], r["dc_id"]): r["label"] for r in rows(ROOT / "BACE/analysis/outputs/snapshot/claims.csv", freeze["files"]["BACE/analysis/outputs/snapshot/claims.csv"])}
paired_cases = list(rows(SAVED / "tables/paired_cases.csv", prov["tables"]["paired_cases.csv"]))
scores = list(rows(SAVED / "tables/scores.csv", prov["tables"]["scores.csv"]))
effects = list(rows(SAVED / "tables/effects.csv", prov["tables"]["effects.csv"]))
claim_index = {}
selected = {}
counts = defaultdict(Counter)
kept = defaultdict(Counter)
composition = defaultdict(Counter)
for r in rows(SAVED / "tables/paired_claims.csv", prov["tables"]["paired_claims.csv"]):
    key = (r["generation_case_id"], r["dc_id"])
    assert key not in claim_index
    values = {c: r[c] == "True" for c in ("original", *VARIANTS)}
    assert all(r[c] in ("True", "False") for c in values)
    assert all(r[c + "_status"] == "success" and r[c + "_input_hash"] == r["input_hash"] for c in VARIANTS)
    claim_index[key] = values
    cid = key[0]
    counts[cid]["claims"] += 1
    for c, v in values.items():
        counts[cid][c] += v
    if labels[key] != "factual_boundary_distortion":
        kept[cid]["claims"] += 1
        for c, v in values.items():
            kept[cid][c] += v
    for c in VARIANTS:
        if not values[c]:
            composition[c][labels[key]] += 1
    if key in key_to_rid:
        selected[key_to_rid[key]] = {"paired_claim": r, "prompt_variants": {}}
assert len(selected) == 18
assert len(paired_cases) == len(counts) == 1796
assert len(claim_index) == 94854
for r in paired_cases:
    cid = r["generation_case_id"]
    assert counts[cid]["claims"] == int(r["claims"]) == int(float(metrics[cid]["bace_dc_count"]))
    for c in ("original", *VARIANTS):
        close(counts[cid][c] / counts[cid]["claims"], r[c])
    close(r["original"], metrics[cid]["bace_support_rate_all_dc"])

# Read the original frozen jobs for all 18 targets.
jobs = {}
for case in plan["cases"]:
    cid = case["generation_case_id"]
    if cid not in {k[0] for k in key_to_rid}:
        continue
    for line in read(ROOT / case["cache_path"], case["cache_sha256"]).decode().splitlines():
        saved = json.loads(line)
        job = saved["job"]
        key = (cid, job["dc_id"])
        if key not in key_to_rid:
            continue
        rid = key_to_rid[key]
        packet = packets[rid]
        assert saved["original_support_sets"] == packet["support"]["support_sets"]
        assert job["dynamic_input"]["dc_claim"]["dc_text"] == packet["target_dc"]["dc_text"]
        by_id = {e["ec_id"]: e for e in packet["candidate_ecs"]}
        input_ecs = job["dynamic_input"]["ec_claims"]
        assert {job["ec_original_by_alias"][e["ec_claim_id"]]: e["ec_text"] for e in input_ecs} == {k: e["ec_text"] for k, e in by_id.items()}
        jobs[rid] = job
assert len(jobs) == 18

# Verify raw files against their frozen output hashes and reconcile every paired verdict.
for condition in VARIANTS:
    path = ROOT / f"BACE/results/prompt_sensitivity_v1/runs/{condition}/calls.jsonl"
    h = hashlib.sha256()
    seen = set()
    failed = 0
    with path.open("rb") as f:
        for line_no, line in enumerate(f, 1):
            h.update(line)
            if not line.strip():
                continue
            record = json.loads(line)
            key = (record["generation_case_id"], record["dc_id"])
            assert key not in seen
            seen.add(key)
            valid = record["call_status"] == "success" and record["output_valid"]
            if not valid:
                failed += 1
            if key in claim_index:
                assert valid
                assert bool(record["restored_output"]["support_sets"]) == claim_index[key][condition]
            if key in key_to_rid:
                rid = key_to_rid[key]
                job = jobs[rid]
                assert record["dynamic_input"] == job["dynamic_input"]
                assert record["call_identity"]["job_input_hash"] == selected[rid]["paired_claim"]["input_hash"]
                assert record["restored_output"]["support_sets"] == json.loads(selected[rid]["paired_claim"][condition + "_sets"])
                assert set(record["candidate_ec_ids"]) == set(packets[rid]["aliases"] if "aliases" in packets[rid] else (e["ec_id"] for e in packets[rid]["candidate_ecs"]))
                selected[rid]["prompt_variants"][condition] = {
                    "supported": bool(record["restored_output"]["support_sets"]),
                    "support_sets": record["restored_output"]["support_sets"],
                    "model_called": record["model_called"], "call_status": record["call_status"],
                    "call_id": record["call_id"], "input_hash": record["call_identity"]["job_input_hash"],
                    "source_path": str(path.relative_to(ROOT)), "source_line": line_no,
                    "raw_record_sha256": hashlib.sha256(line).hexdigest(),
                    "rationale": None, "diagnosis": None,
                }
    sha = h.hexdigest()
    assert sha == prov["source_calls"][str(path.relative_to(ROOT))]
    INPUTS[str(path.relative_to(ROOT))] = sha
    assert len(seen) == status["conditions"][condition]["planned"]
    assert failed == status["conditions"][condition]["failed"]
    print(condition, "raw file and all paired verdicts verified; failures:", failed, flush=True)

case_rows = []
for r in paired_cases:
    cid = r["generation_case_id"]
    m = metrics[cid]
    row = {"generation_case_id": cid, "company_id": r["company_id"], "company_name": r["company_name"],
           "claims": counts[cid]["claims"], "claims_excluding_original_boundary": kept[cid]["claims"],
           "ragas_native": float(m["ragas_faithfulness"]), "ragchecker_native": float(m["ragchecker_faithfulness"])}
    assert kept[cid]["claims"] > 0
    for c in ("original", *VARIANTS):
        row[c] = counts[cid][c] / counts[cid]["claims"]
        row[c + "_excluding_original_boundary"] = kept[cid][c] / kept[cid]["claims"]
    case_rows.append(row)

def summarize(exclude=False):
    suffix = "_excluding_original_boundary" if exclude else ""
    means = {c: mean(r[c + suffix] for r in case_rows) * 100 for c in ("original", *VARIANTS)}
    means.update({f + "_native": mean(r[f + "_native"] for r in case_rows) * 100 for f in ("ragas", "ragchecker")})
    return {"mean_support_percent": means,
            "native_minus_bace_gap_pp": {c: {f: mean((r[f + "_native"] - r[c + suffix]) * 100 for r in case_rows) for f in ("ragas", "ragchecker")} for c in ("original", *VARIANTS)},
            "claim_pooled_support_percent": {c: sum(v[c] for v in (kept if exclude else counts).values()) / sum(v["claims"] for v in (kept if exclude else counts).values()) * 100 for c in ("original", *VARIANTS)}}

all_claims = summarize()
for s in scores:
    close(all_claims["mean_support_percent"][s["condition"]] / 100, s["estimate"])
for e in effects:
    close((all_claims["mean_support_percent"][e["condition"]] - all_claims["mean_support_percent"]["original"]) / 100, e["estimate"])
flips = {c: [rid for rid, x in sorted(selected.items()) if x["prompt_variants"][c]["supported"] != (x["paired_claim"]["original"] == "True")] for c in VARIANTS}
result = {
    "computed_at_utc": datetime.now(timezone.utc).isoformat(), "status": "COMPUTED_VERIFIED",
    "disclosures": len(case_rows), "companies": len({r["company_id"] for r in case_rows}), "claims": len(claim_index),
    "excluded_disclosures": sorted(set(c["generation_case_id"] for c in plan["cases"]) - set(counts)),
    "failed_condition_records": sum(status["conditions"][c]["failed"] for c in VARIANTS),
    "all_claims": all_claims, "excluding_original_boundary": summarize(True),
    "remaining_claim_count_excluding_original_boundary": sum(c["claims"] for c in kept.values()),
    "original_boundary_claim_count": len(claim_index) - sum(c["claims"] for c in kept.values()),
    "saved_prompt_effects": effects, "saved_prompt_scores": scores,
    "selected_case_count": len(selected), "changed_selected_cases": flips,
    "notes": ["All means use the same 1,796 complete disclosures and equal disclosure weights.",
              "Native scores retain each framework's own claims and evidence interface.",
              "The adapted prompts judge the same BACE DCs against the same candidate ECs; no diagnosis was rerun and no textual rationale was saved.",
              "Boundary exclusion removes the original BACE boundary-labelled DCs from all BACE conditions, including newly supported ones. It does not remove corresponding native claims.",
              "The 18 cases are reused examples, not a representative sample or human validation."]}
write_json("results.json", result)
write_json("selected_prompt_results.json", selected)
write_csv("paired_gap_cases.csv", case_rows)
write_csv("case_changes.csv", [{"review_id": rid, "original": x["paired_claim"]["original"], **{c: x["prompt_variants"][c]["supported"] for c in VARIANTS}} for rid, x in sorted(selected.items())])
write_csv("remaining_unsupported_by_original_label.csv", [{"condition": c, "original_bace_label": label, "claims": n, "denominator": sum(composition[c].values()), "share": n / sum(composition[c].values())} for c in VARIANTS for label, n in sorted(composition[c].items())])
write_json("provenance.json", {"input_sha256": INPUTS, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                             "output_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.suffix in (".json", ".csv") and p.name != "provenance.json"},
                             "command": "python paper/analysis/prompt_gap_review_2026-10-22/analyze.py", "model_calls": 0, "new_human_adjudications": 0})
print(json.dumps(result, ensure_ascii=False, indent=2))
