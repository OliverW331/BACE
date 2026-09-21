#!/usr/bin/env python3
"""Validate and summarize the completed BACE comparison pilot without model calls."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from statistics import mean

from audit_staged_claim_extraction import extraction_view
from claim_refinement_lineage import original_source_input
from external_evaluation import load_cases
from generation_claims import build_dc_jobs, build_ec_jobs, make_dc_occurrences, make_ec_occurrences, sha256_json
from run_bace_comparison_pilot import ROOT, check_frozen, read

LABELS = ("non_disclosure_statement", "contradiction", "evidence_conflation",
          "factual_boundary_distortion", "inferential_inflation", "unsupported_novelty")
STAGES = {
    "dedup": ("generation_claim_semantic_dedup", "semantic_dedup_run_manifest.json", "semantic_dedup_calls.jsonl", None),
    "candidates": ("generation_claim_candidate_selection", "claim_candidate_run_manifest.json", "claim_candidate_calls.jsonl", "dc_candidate_ecs.jsonl"),
    "support": ("generation_claim_support", "claim_support_run_manifest.json", "claim_support_calls.jsonl", "dc_support_sets.jsonl"),
    "diagnosis": ("generation_claim_unsupported_diagnosis", "claim_unsupported_diagnosis_run_manifest.json", "claim_unsupported_diagnosis_calls.jsonl", "dc_unsupported_diagnoses.jsonl"),
}


@lru_cache(maxsize=None)
def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def index(records, key):
    result = {r[key]: r for r in records}
    if len(result) != len(records):
        raise ValueError(f"Duplicate {key}")
    return result


def file_info(path):
    path = Path(path).resolve()
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def bace_metrics(ec_rows, dc_rows, support_rows, diagnosis_rows, candidate_rows=None):
    ecs, dcs = index(ec_rows, "ec_id"), index(dc_rows, "dc_id")
    support = index(support_rows, "dc_claim_id")
    diagnosis = index(diagnosis_rows, "dc_claim_id")
    if not dcs or not ecs or set(support) != set(dcs):
        raise ValueError("Empty claims or incomplete/foreign support judgments")
    candidates = index(candidate_rows, "dc_claim_id") if candidate_rows is not None else None
    if candidates is not None and set(candidates) != set(dcs):
        raise ValueError("Incomplete/foreign candidate selections")
    used, unsupported = set(), set()
    direct = inferred = multi_required = 0
    for dc_id, record in support.items():
        sets = record["support_sets"]
        if not sets:
            unsupported.add(dc_id)
        elif any(s["support_type"] == "direct" for s in sets):
            direct += 1
        else:
            inferred += 1
        multi_required += bool(sets) and all(len(s["ec_claim_ids"]) > 1 for s in sets)
        if candidates is not None:
            candidate_ids = candidates[dc_id]["candidate_ec_ids"]
            if len(set(candidate_ids)) != len(candidate_ids) or not set(candidate_ids) <= set(ecs):
                raise ValueError("Duplicate or foreign candidate EC")
        for support_set in sets:
            ids = support_set["ec_claim_ids"]
            if not ids or len(ids) != len(set(ids)) or not set(ids) <= set(ecs):
                raise ValueError("Empty, duplicate or foreign support EC")
            if support_set["support_type"] not in ("direct", "inferred"):
                raise ValueError("Unknown support type")
            if any(ecs[e]["generation_case_id"] != dcs[dc_id]["generation_case_id"] for e in ids):
                raise ValueError("Cross-case support edge")
            if candidates is not None and not set(ids) <= set(candidate_ids):
                raise ValueError("Support EC absent from candidates")
            used.update(ids)
    if set(diagnosis) != unsupported:
        raise ValueError("Diagnoses must partition exactly the unsupported DCs")
    labels = Counter(r["unsupported_label"] for r in diagnosis.values())
    if set(labels) - set(LABELS):
        raise ValueError("Unknown diagnosis label")
    supported = direct + inferred
    return {"bace_dc_count": len(dcs), "bace_supported_direct": direct,
            "bace_supported_inferred": inferred, "bace_unsupported": len(unsupported),
            "bace_non_disclosure_statement": labels["non_disclosure_statement"],
            "bace_support_rate_all_dc": supported / len(dcs),
            "bace_support_rate_excluding_non_disclosure_sensitivity": ratio(supported, len(dcs) - labels["non_disclosure_statement"]),
            "bace_multi_ec_required_dc_count": multi_required,
            **{f"bace_{label}": labels[label] for label in LABELS[1:]},
            "bace_ec_count": len(ecs), "bace_used_ec_count": len(used),
            "bace_eccr": len(used) / len(ecs), "bace_inference_rate": ratio(inferred, supported)}


def external_metrics(record, framework, adapted):
    if record["status"] != "success" or record["metric"] != "faithfulness":
        raise ValueError("External result is not a successful faithfulness evaluation")
    for key in ("generation_case_id", "prompt_hash", "response_hash", "context_hash", "evidence_ids", "prompt_labels"):
        if record[key] != adapted[key]:
            raise ValueError(f"External input differs: {key}")
    claims = record["claims"]
    if not claims or len(claims) != record["claim_count"] or any(type(c["supported"]) is not bool for c in claims):
        raise ValueError("Invalid external claim denominator or verdict")
    supported = sum(c["supported"] for c in claims)
    if abs(supported / len(claims) - record["score"]) > 1e-12:
        raise ValueError("External native score does not match verdicts")
    return {f"{framework}_claim_count": len(claims), f"{framework}_supported": supported,
            f"{framework}_faithfulness": record["score"]}


def audit_downstream(base, cid):
    usage = {}
    for stage, (old_folder, manifest_name, calls_name, result_name) in STAGES.items():
        manifest = read(base / stage / manifest_name)
        identity = manifest["run_identity"]
        if manifest["status"] != "complete" or manifest["dry_run"]:
            raise ValueError("Downstream stage is not complete")
        if sha256_json(identity) != manifest["run_identity_sha256"] or identity["selected_generation_case_ids"] != [cid]:
            raise ValueError("Downstream run identity mismatch")
        old = read(ROOT / "evidence_pilot/evaluation" / old_folder / "text_embedding_3_large_gpt_5_6_sol_schema_only_full" / manifest_name)["run_identity"]
        controlled = ("config_sha256", "prompt_sha256", "schema_sha256", "model_key", "model_id", "model_version", "deployment_name", "request_parameters")
        if any(identity[key] != old[key] for key in controlled):
            raise ValueError(f"Downstream setting differs from baseline: {stage}")
        for info in identity["inputs"].values():
            if file_info(info["path"])["sha256"] != info["sha256"]:
                raise ValueError("Downstream input hash differs")
        records = rows(base / stage / calls_name)
        latest = {r["call_id"]: r for r in records}
        for record in latest.values():
            if record["call_status"] != "success" or record["generation_case_id"] != cid:
                raise ValueError("Unsuccessful or foreign downstream call")
            if any(record[key] != identity[key] for key in controlled[3:]):
                raise ValueError("Native downstream model differs from manifest")
        if result_name:
            expected = index([r["restored_output"] for r in latest.values()], "dc_claim_id")
            if index(rows(base / stage / result_name), "dc_claim_id") != expected:
                raise ValueError("Downstream results differ from native restored outputs")
            if set(expected) != set(identity["selected_dc_ids"]):
                raise ValueError("Native call coverage differs from selected DCs")
        elif len(latest) != 2:
            raise ValueError("Expected one full EC dedup and one full DC dedup call")
        usage[stage] = {"logical_calls": len(latest), "recorded_invocations": len(records),
                        "unsuccessful_records": sum(r["call_status"] != "success" for r in records),
                        "input_tokens": sum((r.get("usage") or {}).get("input_tokens") or 0 for r in records),
                        "output_tokens": sum((r.get("usage") or {}).get("output_tokens") or 0 for r in records)}
    return usage


def audit_extraction(directory, cid, task, source_job, source_files, chain=None):
    """Replay every accepted stage and verify source/model lineage to direct v8."""
    chain = [] if chain is None else chain
    manifest_path = directory / "claim_extraction_run_manifest.json"
    manifest = read(manifest_path)
    if manifest["run_status"] != "complete":
        raise ValueError("Incomplete extraction source")
    call_path = directory / f"{task}_extraction_calls.jsonl"
    selected = [r for r in rows(call_path) if r["job_summary"]["generation_case_id"] == cid]
    record = selected[-1]
    if record["call_status"] != "success" or record["api_response"]["status"] != "completed":
        raise ValueError("Incomplete native extraction")
    if original_source_input(record) != source_job["dynamic_input"]:
        raise ValueError("Extraction source changed")
    for path, expected in manifest["code_hashes"].items():
        if file_info(ROOT / path)["sha256"] != expected:
            raise ValueError(f"Extraction code changed: {path}")
    canonical = extraction_view(record)
    if record.get("canonical_output") != canonical:
        raise ValueError("Canonical extraction differs from native replay")
    source_files[str(call_path.relative_to(ROOT))] = file_info(call_path)
    source_files[str(manifest_path.relative_to(ROOT))] = file_info(manifest_path)
    chain.append({"directory": str(directory.relative_to(ROOT)), "call_id": record["call_id"],
                  "prompt_version": manifest["prompts"][task]["version"]})
    if manifest.get("draft_run"):
        draft_dir = Path(manifest["draft_run"]["directory"])
        draft_manifest = read(draft_dir / "claim_extraction_run_manifest.json")
        identity = {key: draft_manifest.get(key) for key in manifest["draft_run"]["identity_fields"]}
        if identity != manifest["draft_run"]["identity"] or sha256_json(identity) != manifest["source_hashes"]["draft_manifest"]:
            raise ValueError("Draft manifest identity changed")
        if file_info(draft_dir / f"{task}_extraction_calls.jsonl")["sha256"] != manifest["source_hashes"][f"draft_{task}_calls"]:
            raise ValueError("Draft native calls changed")
        draft, draft_canonical, _ = audit_extraction(draft_dir, cid, task, source_job, source_files, chain)
        if record["draft_call_id"] != draft["call_id"] or record["dynamic_input"]["draft_extraction"] != draft_canonical:
            raise ValueError("Draft-to-review linkage differs")
        for key in ("deployment_name", "request_parameters"):
            if record[key] != draft[key]:
                raise ValueError("Extraction model settings differ across stages")
    return record, canonical, chain


def write_csv(path, records):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    args = parser.parse_args()
    output = args.plan.resolve().parent
    plan = read(args.plan)
    check_frozen(plan)
    if read(output / "execution_status.json")["status"] != "complete":
        raise ValueError("All ten cases must finish before publishing a comparison")
    external_config = read(ROOT / "config/evaluation/configs/external_evaluation_config.json")
    adapted = index(load_cases(external_config), "generation_case_id")
    originals = index(rows(ROOT / plan["generation_cases"]), "generation_case_id")
    disclosures = index(rows(ROOT / plan["generated_disclosures"]), "generation_case_id")
    external = {f: index(rows(ROOT / external_config["frameworks"][f]["output_dir"] / "results.jsonl"), "generation_case_id")
                for f in ("ragchecker", "ragas")}
    with (output.parent / "pilot_v1/comparison.csv").open() as stream:
        old = index(list(csv.DictReader(stream)), "generation_case_id")
    source_files = {name: {"path": name, "sha256": digest} for name, digest in plan["frozen_files"].items()}
    comparison, changes, extraction_lineage, downstream_usage = [], [], [], {}
    for case in plan["cases"]:
        cid = case["generation_case_id"]
        short = cid.split("stratified_by_evidence_type_n10__", 1)[1]
        base = output / "bace" / short
        downstream_usage[cid] = audit_downstream(base, cid)
        inputs = {"ec": base / "dedup/ec_claims.jsonl", "dc": base / "dedup/dc_claims.jsonl",
                  "support": base / "support/dc_support_sets.jsonl", "diagnosis": base / "diagnosis/dc_unsupported_diagnoses.jsonl",
                  "candidates": base / "candidates/dc_candidate_ecs.jsonl"}
        for path in base.rglob("*.json*"):
            source_files[str(path.relative_to(ROOT))] = file_info(path)
        ec, dc = rows(inputs["ec"]), rows(inputs["dc"])
        if {r["generation_case_id"] for r in ec + dc} != {cid}:
            raise ValueError("BACE outputs belong to another case")
        for task, claims in (("ec", ec), ("dc", dc)):
            directory = ROOT / case["extraction_directory"]
            job = (build_ec_jobs([originals[cid]]) if task == "ec" else build_dc_jobs([originals[cid]], disclosures))[0]
            record, canonical, chain = audit_extraction(directory, cid, task, job, source_files)
            expected_versions = [f"generation_{task}_claim_atomicity_review_prompt_v2", f"generation_{task}_claim_patch_review_prompt_v4", f"generation_{task}_claim_extraction_prompt_v8"]
            if [c["prompt_version"] for c in chain] != expected_versions:
                raise ValueError(f"Extraction is not the accepted three-stage pipeline: {cid}")
            job["call_id"] = record["call_id"]
            adapter = {record["call_id"]: {**record, "parsed_output": canonical}}
            maker = make_ec_occurrences if task == "ec" else make_dc_occurrences
            regenerated = maker([job], adapter, use_parsed_output=True)
            occurrence_path = directory / f"{task}_claim_occurrences.jsonl"
            actual = [r for r in rows(occurrence_path) if r["generation_case_id"] == cid]
            if actual != regenerated:
                raise ValueError("Occurrence file differs from replayed native extraction")
            source_files[str(occurrence_path.relative_to(ROOT))] = file_info(occurrence_path)
            members = [oid for r in claims for oid in r[f"{task}_occurrence_ids"]]
            if Counter(members) != Counter(r[f"{task}_occurrence_id"] for r in actual):
                raise ValueError("Dedup does not partition all source occurrences exactly once")
            extraction_lineage.append({"generation_case_id": cid, "task": task, "reuse_extraction": case["reuse_extraction"], "occurrence_count": len(actual), "deduplicated_count": len(claims), "stages_latest_first": chain})
        row = {key: old[cid][key] for key in ("generation_case_id", "company", "reporting_year", "task")}
        row.update(bace_metrics(ec, dc, rows(inputs["support"]), rows(inputs["diagnosis"]), rows(inputs["candidates"])))
        for framework in external:
            row.update(external_metrics(external[framework][cid], framework, adapted[cid]))
        comparison.append(row)
        change = {key: row[key] for key in ("generation_case_id", "company", "reporting_year", "task")}
        for key in ("bace_dc_count", "bace_supported_direct", "bace_supported_inferred", "bace_unsupported", "bace_non_disclosure_statement", "bace_support_rate_all_dc", "bace_support_rate_excluding_non_disclosure_sensitivity", "bace_multi_ec_required_dc_count"):
            prior = float(old[cid][key]) if "rate" in key else int(old[cid][key])
            change.update({f"old_{key}": prior, f"new_{key}": row[key], f"delta_{key}": row[key] - prior if row[key] is not None else None})
        changes.append(change)
    totals = {key: sum(r[key] for r in comparison) for key in comparison[0] if key.startswith("bace_") and "rate" not in key and key != "bace_eccr"}
    n, supported = totals["bace_dc_count"], totals["bace_supported_direct"] + totals["bace_supported_inferred"]
    aggregates = {"bace": {**totals, "macro_dcsr": mean(r["bace_support_rate_all_dc"] for r in comparison), "micro_dcsr": supported / n,
                          "macro_non_disclosure_sensitivity": mean(r["bace_support_rate_excluding_non_disclosure_sensitivity"] for r in comparison if r["bace_support_rate_excluding_non_disclosure_sensitivity"] is not None),
                          "macro_eccr": mean(r["bace_eccr"] for r in comparison), "micro_eccr": totals["bace_used_ec_count"] / totals["bace_ec_count"],
                          "macro_inference_rate": mean(r["bace_inference_rate"] for r in comparison if r["bace_inference_rate"] is not None)}}
    for framework in external:
        count = sum(r[f"{framework}_claim_count"] for r in comparison)
        supported_count = sum(r[f"{framework}_supported"] for r in comparison)
        aggregates[framework] = {"claim_count": count, "supported_count": supported_count,
                                 "macro_faithfulness": mean(r[f"{framework}_faithfulness"] for r in comparison), "micro_faithfulness": supported_count / count, "reused_results": True}
    summary = {"schema_version": "bace_comparison_summary_v2", "created_at_utc": datetime.now(timezone.utc).isoformat(),
               "case_count": len(comparison), "reference_answer_required": False,
               "extraction_pipeline": plan["extraction_pipeline"],
               "reused_extraction_cases": sum(c["reuse_extraction"] for c in plan["cases"]),
               "new_extraction_cases": sum(not c["reuse_extraction"] for c in plan["cases"]),
               "selection_purpose": plan["case_selection"], "aggregates": aggregates,
               "old_bace_macro_dcsr": mean(float(r["bace_support_rate_all_dc"]) for r in old.values()),
               "method": {"primary_rate": "DCSR = (direct + inferred) / all deduplicated DCs. A DC with any direct support alternative is classified as direct; otherwise nonempty support sets imply inferred.",
                          "sensitivity": "Exclude only unsupported DCs diagnosed as non_disclosure_statement from the denominator; numerator unchanged. Not a comprehensive absence-claim filter.",
                          "multi_ec_required": "Supported DCs whose every returned minimal sufficient support set has more than one EC. A singleton alternative means multi-EC support is not required by the returned assessment. Cardinality is independent of direct/inferred type.",
                          "eccr": "Unique ECs in the union of accepted support sets / all supplied deduplicated ECs. Utilization diagnostic, not a monotonic quality score; no task-relevance filter.",
                          "aggregation": "Macro weights cases equally. Micro pools each framework's own claims. Claim denominators differ across frameworks.",
                          "external": "Native version-pinned faithfulness only, with Azure Responses transport. RAGChecker checks individual evidence cards; RAGAS judges joined contexts. Other metrics from these frameworks were not run.",
                          "comparison": "Same raw evidence and generated disclosures as pilot_v1. Only BACE extraction treatment changed; downstream prompts/models unchanged but rejudged without repeated-run control."},
               "limitations": ["No independent human correctness labels; support-score gaps do not establish evaluator accuracy or BACE superiority.", "Ten previously examined engineering cases, not a held-out or prevalence benchmark.", "Unsupported means not entailed within the evaluated evidence, not false in the world.", "Unresolved extraction context remains in provenance but is not a separate support-model input.", "Before/after changes combine extraction representation changes and possible downstream LLM variation."],
               "validation": {"frozen_files": "verified", "native_extraction_replay_and_source_lineage": "verified for all ten cases and all three stages", "dedup_occurrence_partition": "verified", "support_candidate_and_diagnosis_coverage": "verified", "external_input_hashes_and_native_score_denominators": "verified", "independent_human_annotations": 0},
               "downstream_usage_by_case": downstream_usage,
               "source_files": source_files}
    summary["column_definitions"] = {
        "bace_dc_count": "Number of deduplicated disclosure claims; denominator of primary DCSR.",
        "bace_supported_direct": "DCs with at least one direct minimal sufficient support set.",
        "bace_supported_inferred": "DCs with sufficient inferred support and no direct alternative.",
        "bace_unsupported": "DCs with no returned sufficient support set; not a real-world falsity label.",
        "bace_non_disclosure_statement": "Unsupported DCs asserting that an item was not disclosed/provided; included in primary DCSR.",
        "bace_support_rate_all_dc": "Primary DCSR: (direct + inferred) / all DCs.",
        "bace_support_rate_excluding_non_disclosure_sensitivity": "Sensitivity only: (direct + inferred) / (all DCs - unsupported non-disclosure DCs).",
        "bace_multi_ec_required_dc_count": "Supported DCs with no returned singleton support alternative.",
        "bace_contradiction": "Unsupported DCs whose proposition conflicts with evidence under matching factual boundaries.",
        "bace_evidence_conflation": "Unsupported DCs constructing an unentailed relationship from multiple evidence elements.",
        "bace_factual_boundary_distortion": "Unsupported DCs transferring an anchored fact across entity, time, scope, metric or other material boundaries.",
        "bace_inferential_inflation": "Unsupported DCs drawing a stronger conclusion than the matched evidence entails.",
        "bace_unsupported_novelty": "Unsupported DCs without a recognizable evidence anchor for the core proposition.",
        "bace_ec_count": "All supplied deduplicated evidence claims, without a relevance/usability filter.",
        "bace_used_ec_count": "Unique ECs appearing in at least one accepted support set.",
        "bace_eccr": "Used ECs / all ECs; supplied-evidence utilization, not monotonic generation quality.",
        "bace_inference_rate": "Inferred-only supported DCs / all supported DCs; support type is independent of EC count.",
        "ragchecker_claim_count": "Claims extracted by the native RAGChecker pipeline; its own denominator.",
        "ragchecker_supported": "RAGChecker claims entailed by at least one individually checked evidence card.",
        "ragchecker_faithfulness": "Native RAGChecker supported / extracted claims.",
        "ragas_claim_count": "Statements extracted by the native RAGAS pipeline; its own denominator.",
        "ragas_supported": "RAGAS statements judged supported using the joined supplied contexts.",
        "ragas_faithfulness": "Native RAGAS supported / extracted statements.",
    }
    source_files["summary_script"] = file_info(Path(__file__))
    source_files["comparison_metric_tests"] = file_info(ROOT / "tests/evaluation/test_bace_comparison.py")
    adjustment = output / "runtime_adjustment.json"
    if adjustment.exists():
        summary["runtime_adjustment"] = read(adjustment)
        summary["usage_caveat"] = "Recorded usage is a lower bound because seven candidate processes were interrupted during rate-limit recovery; an in-flight provider response may not have returned before interruption."
        source_files["runtime_adjustment"] = file_info(adjustment)
    source_files["execution_plan"] = file_info(args.plan)
    source_files["execution_status"] = file_info(output / "execution_status.json")
    review_path = output / "review_cases.jsonl"
    if review_path.exists():
        source_files["illustrative_case_reviews"] = file_info(review_path)
        summary["illustrative_review_count"] = len(rows(review_path))
    write_csv(output / "comparison.csv", comparison)
    write_csv(output / "bace_changes.csv", changes)
    (output / "extraction_lineage.json").write_text(json.dumps(extraction_lineage, indent=2) + "\n")
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(aggregates, indent=2))


if __name__ == "__main__":
    main()
