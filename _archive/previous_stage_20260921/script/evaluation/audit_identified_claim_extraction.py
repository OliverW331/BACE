"""Export source-aligned extraction comparisons; semantic review remains explicit.

This command makes no model calls and does not treat quote matches or claim
counts as semantic-fidelity measurements.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def rows(path):
    with path.open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(2**20):
            result.update(block)
    return result.hexdigest()


def calls_by_case(path):
    result = {}
    for row in rows(path):
        result[row["job_summary"]["generation_case_id"]] = row
    return result


def extraction_view(record):
    if record.get("output_processing_mode") == "schema_only_context_rendered":
        from contextual_claims import canonicalize
        rendered = canonicalize(record["task"], record["parsed_output"])
        if record.get("canonical_output") != rendered:
            raise ValueError("Recorded canonical output differs from native group rendering")
        return rendered
    if record.get("output_processing_mode") == "schema_only_identified_patch":
        from identified_claim_patches import canonicalize, make_claim_index
        draft = record["dynamic_input"]["draft_extraction"]
        if record["dynamic_input"].get("draft_claim_index") != make_claim_index(record["task"], draft):
            raise ValueError("Draft claim index differs from its recorded source draft")
        rendered = canonicalize(record["task"], record["parsed_output"], draft, record.get("source_attributions"))
        if record.get("canonical_output") != rendered:
            raise ValueError("Recorded canonical output differs from identified edits")
        return rendered
    if record.get("output_processing_mode") == "schema_only_patched":
        from claim_extraction_patches import canonicalize
        rendered = canonicalize(record["task"], record["parsed_output"],
                                record["dynamic_input"]["draft_extraction"], record.get("source_attributions"))
        if record.get("canonical_output") != rendered:
            raise ValueError("Recorded canonical output differs from sparse patch application")
        return rendered
    return record["parsed_output"]


def quote_status(claim, source):
    quotes = claim.get("source_quotes", [])
    return bool(quotes) and all(isinstance(q, str) and q and q in source for q in quotes)


def compare(plan_path, split, run_override=None):
    plan = json.loads(plan_path.read_text())
    for name, expected in plan["baseline_files"].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f"Frozen baseline changed: {name}")
    if split == "validation":
        freeze = plan.get("validation_freeze")
        if not freeze or freeze.get("validation_contents_reviewed_before_freeze") is not False:
            raise ValueError("Validation requires a candidate frozen before source review")
        for name, expected in freeze["candidate_files"].items():
            if digest(ROOT / name) != expected:
                raise ValueError(f"Frozen validation candidate changed: {name}")
    selected = [c["generation_case_id"] for c in plan["cases"] if c["split"] == split]
    cases_path = next(ROOT / p for p in plan["baseline_files"] if p.endswith("/generation_cases.jsonl"))
    output_path = next(ROOT / p for p in plan["baseline_files"] if p.endswith("/generated_disclosures.jsonl"))
    cases = {r["generation_case_id"]: r for r in rows(cases_path)}
    disclosures = {r["generation_case_id"]: r for r in rows(output_path)}
    original_dir = ROOT / plan["baseline_dir"]
    run_directory = plan.get("run_directories", {}).get(split, split)
    if run_override is not None:
        extra_run = plan["additional_runs"][run_override]
        if extra_run["split"] != split:
            raise ValueError("Requested run belongs to a different sample split")
        run_directory = run_override
        selected = extra_run["case_ids"]
    revised_dir = plan_path.parent / run_directory
    manifest = json.loads((revised_dir / "claim_extraction_run_manifest.json").read_text())
    if manifest["run_status"] != "complete":
        raise ValueError(f"Revised run is not complete: {manifest['run_status']}")
    for name, expected in manifest.get("code_hashes", {}).items():
        if digest(ROOT / name) != expected:
            raise ValueError(f"Output adapter or runner changed: {name}")
    rendering = manifest.get("rendering_lineage")
    if rendering:
        if digest(Path(rendering["native_manifest"])) != rendering["native_manifest_sha256"]:
            raise ValueError("Native rendering manifest changed")
        for name, expected in rendering["native_call_files"].items():
            if digest(Path(name)) != expected:
                raise ValueError(f"Native rendering input changed: {name}")
        native_rows = {r["call_id"]: r for name in rendering["native_call_files"] for r in rows(Path(name))}
        for task in ("ec", "dc"):
            for r in rows(revised_dir / f"{task}_extraction_calls.jsonl"):
                native_row = native_rows[r["call_id"]]
                for field in ("parsed_output", "raw_output", "api_response", "dynamic_input", "messages_sha256"):
                    if r[field] != native_row[field]:
                        raise ValueError(f"Rendering changed a native field: {field}")
    draft_dir = None
    if manifest.get("draft_run"):
        draft_dir = Path(manifest["draft_run"]["directory"])
        draft_manifest = Path(manifest["draft_run"]["manifest"])
        for name, path in [("draft_manifest", draft_manifest)] + [
            (f"draft_{task}_calls", draft_dir / f"{task}_extraction_calls.jsonl")
            for task in ("ec", "dc")
        ]:
            if name == "draft_manifest" and manifest["draft_run"].get("identity_fields"):
                from generation_claims import sha256_json
                current_draft = json.loads(path.read_text())
                identity = {key: current_draft.get(key) for key in manifest["draft_run"]["identity_fields"]}
                if (identity != manifest["draft_run"]["identity"]
                        or sha256_json(identity) != manifest["source_hashes"][name]
                        or current_draft.get("run_status") != "complete"):
                    raise ValueError(f"Refinement draft identity changed: {path}")
            elif digest(path) != manifest["source_hashes"][name]:
                raise ValueError(f"Refinement draft changed: {path}")
    comparisons, statistics = [], []
    for task in ("ec", "dc"):
        original = calls_by_case(original_dir / f"{task}_extraction_calls.jsonl")
        revised = calls_by_case(revised_dir / f"{task}_extraction_calls.jsonl")
        drafts = calls_by_case(draft_dir / f"{task}_extraction_calls.jsonl") if draft_dir else {}
        if set(revised) != set(selected):
            raise ValueError("Run cases differ from the frozen sample")
        for cid in selected:
            left, right = original[cid], revised[cid]
            if any(r["call_status"] != "success" for r in (left, right)):
                raise ValueError(f"Unsuccessful extraction: {task}, {cid}")
            source_input = dict(right["dynamic_input"])
            draft_payload = source_input.pop("draft_extraction", None)
            source_input.pop("draft_claim_index", None)
            if draft_dir:
                draft = drafts[cid]
                if (draft["call_id"] != right.get("draft_call_id")
                        or draft_payload != draft["parsed_output"]
                        or source_input != draft["dynamic_input"]
                        or draft["call_status"] != "success"
                        or draft.get("api_response", {}).get("status") != "completed"):
                    raise ValueError(f"Refinement lineage mismatch: {cid}")
            elif draft_payload is not None:
                raise ValueError("Unexpected draft without a refinement manifest")
            if source_input != left["dynamic_input"]:
                raise ValueError(f"Uncontrolled source input change: {cid}")
            for field in ("deployment_name", "request_parameters"):
                if left[field] != right[field]:
                    raise ValueError(f"Uncontrolled comparison change: {field}, {cid}")
            if right.get("api_response", {}).get("status") != "completed":
                raise ValueError(f"Incomplete provider response: {cid}")
            left_output, right_output = extraction_view(left), extraction_view(right)
            if task == "ec":
                visible = [c for c in cases[cid]["prompt_evidence"] if c["shown_in_prompt"]]
                expected = [c["prompt_label"] for c in visible]
                if right.get("output_processing_mode") in ("schema_only_patched", "schema_only_identified_patch"):
                    from claim_extraction_patches import report_attribution
                    expected_attribution = ({} if manifest.get("report_attribution_mode") == "draft_preserved" else {c["prompt_label"]: report_attribution(c["source_label"]) for c in visible})
                    if right.get("source_attributions") != expected_attribution:
                        raise ValueError("Report attribution differs from visible source labels")
                for r in (left, right):
                    if [c["prompt_label"] for c in extraction_view(r)["evidence_results"]] != expected:
                        raise ValueError(f"Missing or reordered evidence labels: {cid}")
                groups = [
                    (card["prompt_label"], card["retrieval_text"], card["source_label"],
                     left_output["evidence_results"][i]["claims"],
                     right_output["evidence_results"][i]["claims"],
                     left_output["evidence_results"][i].get("unextracted_spans", []),
                     right_output["evidence_results"][i].get("unextracted_spans", []))
                    for i, card in enumerate(visible)
                ]
            else:
                groups = [("disclosure", disclosures[cid]["generated_text"], "generated disclosure",
                           left_output["claims"], right_output["claims"],
                           left_output.get("unextracted_spans", []),
                           right_output.get("unextracted_spans", []))]
            counts = {"generation_case_id": cid, "split": split, "task": task,
                      "baseline_claims": 0, "revised_claims": 0,
                      "baseline_claims_with_exact_quotes": 0, "revised_claims_with_exact_quotes": 0,
                      "revised_claims_with_unresolved_context": 0,
                      "revised_unextracted_spans": 0,
                      "revised_unextracted_spans_with_exact_quotes": 0}
            for label, source, source_label, old_claims, new_claims, old_spans, new_spans in groups:
                for claim in new_claims:
                    if not isinstance(claim.get("unresolved_context"), list):
                        raise ValueError(f"Missing v2 uncertainty field: {cid}, {label}")
                    if not all(isinstance(v, str) for v in claim["unresolved_context"]):
                        raise ValueError("Invalid uncertainty descriptions")
                for name, claims in (("baseline", old_claims), ("revised", new_claims)):
                    counts[name + "_claims"] += len(claims)
                    counts[name + "_claims_with_exact_quotes"] += sum(quote_status(c, source) for c in claims)
                counts["revised_claims_with_unresolved_context"] += sum(bool(c["unresolved_context"]) for c in new_claims)
                counts["revised_unextracted_spans"] += len(new_spans)
                counts["revised_unextracted_spans_with_exact_quotes"] += sum(quote_status(s, source) for s in new_spans)
                comparisons.append({
                    "generation_case_id": cid, "split": split, "task": task,
                    "source_unit": label, "source_label": source_label, "source_text": source,
                    "baseline_call_id": left["call_id"], "revised_call_id": right["call_id"],
                    "baseline_claims": old_claims, "revised_claims": new_claims,
                    "baseline_unextracted_spans": old_spans, "revised_unextracted_spans": new_spans,
                    **({"draft_call_id": right["draft_call_id"],
                        "draft_claims": (next(g["claims"] for g in draft_payload["evidence_results"]
                                              if g["prompt_label"] == label)
                                         if task == "ec" else draft_payload["claims"])}
                       if draft_payload is not None else {}),
                })
            statistics.append(counts)
    target = plan_path.parent / f"{run_directory}_comparison.jsonl"
    target.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in comparisons))
    with (plan_path.parent / f"{run_directory}_structural_checks.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(statistics[0]))
        writer.writeheader()
        writer.writerows(statistics)
    print(json.dumps({"split": split, "compared_cases": len(selected), "source_units": len(comparisons),
                      "controlled_inputs": "source and model settings matched",
                      "refinement_draft_added": bool(draft_dir), "output": str(target),
                      "semantic_fidelity": "requires source-grounded review; not inferred from these counts"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=ROOT / "evidence_pilot/evaluation/extraction_repair/pilot_v2/plan.json")
    parser.add_argument("--split", required=True, choices=("development", "validation"))
    parser.add_argument("--run-directory", help="Named additional run registered in the plan")
    args = parser.parse_args()
    compare(args.plan.resolve(), args.split, args.run_directory)
