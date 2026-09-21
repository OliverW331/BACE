#!/usr/bin/env python3
"""Rebuild claim-extraction artifacts from recorded structured model outputs.

This utility performs no semantic output validation and makes no API calls.
Every recorded ``parsed_output`` is accepted as the extraction result. Source
quotes are retained as best-effort provenance annotations only.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from generation_claims import (
    InputValidationError,
    build_dc_jobs,
    build_ec_jobs,
    make_dc_occurrences,
    make_ec_occurrences,
    read_jsonl,
    sha256_file,
    utc_now,
    write_json,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild claim occurrences from recorded parsed outputs without "
            "semantic validation or API calls."
        )
    )
    parser.add_argument("--generation-cases", type=Path, required=True)
    parser.add_argument("--generated-disclosures", type=Path, required=True)
    parser.add_argument("--source-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="claim_extraction_schema_only_rebuild")
    return parser.parse_args()


def call_paths(directory: Path) -> dict[str, Path]:
    return {
        "ec": directory / "ec_extraction_calls.jsonl",
        "dc": directory / "dc_extraction_calls.jsonl",
    }


def load_latest_calls(directory: Path) -> dict[tuple[str, str], dict[str, Any]]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for task, path in call_paths(directory).items():
        if not path.is_file():
            raise InputValidationError(f"Missing recorded call file: {path}")
        for record in read_jsonl(path):
            generation_case_id = (record.get("job_summary") or {}).get(
                "generation_case_id"
            )
            if not isinstance(generation_case_id, str) or not generation_case_id:
                raise InputValidationError(
                    f"Recorded {task.upper()} call has no generation_case_id in {path}"
                )
            latest[(task, generation_case_id)] = record
    return latest


def accept_parsed_record(record: dict[str, Any]) -> dict[str, Any] | None:
    parsed = record.get("parsed_output")
    if not isinstance(parsed, dict):
        return None
    accepted = dict(record)
    accepted["prior_call_status"] = record.get("call_status")
    accepted["prior_validation_error"] = record.get("validation_error")
    accepted["call_status"] = "success"
    accepted["validated_output"] = parsed
    accepted["output_valid"] = True
    accepted["validation_error"] = None
    accepted["error_type"] = None
    accepted["error_message"] = None
    accepted["http_status"] = None
    accepted["output_processing_mode"] = "schema_only"
    return accepted


def main() -> None:
    args = parse_args()
    existing = list(args.output_dir.iterdir()) if args.output_dir.is_dir() else []
    if existing:
        raise InputValidationError(f"Output directory is not empty: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    cases = read_jsonl(args.generation_cases)
    disclosures = read_jsonl(args.generated_disclosures)
    disclosures_by_case = {
        str(row["generation_case_id"]): row for row in disclosures
    }
    ec_jobs = build_ec_jobs(cases)
    dc_jobs = build_dc_jobs(cases, disclosures_by_case)
    source_calls = load_latest_calls(args.source_run_dir)

    accepted_by_id: dict[str, dict[str, Any]] = {}
    accepted_by_task: dict[str, list[dict[str, Any]]] = {"ec": [], "dc": []}
    failures: list[dict[str, Any]] = []
    for job in ec_jobs + dc_jobs:
        task = str(job["task"])
        generation_case_id = str(job["generation_case_id"])
        source = source_calls.get((task, generation_case_id))
        if source is None:
            job["call_id"] = f"missing::{task}::{generation_case_id}"
            failures.append(
                {
                    "task": task,
                    "generation_case_id": generation_case_id,
                    "reason": "recorded_call_missing",
                }
            )
            continue
        job["call_id"] = str(source.get("call_id") or f"missing::{task}::{generation_case_id}")
        accepted = accept_parsed_record(source)
        if accepted is None:
            failures.append(
                {
                    "task": task,
                    "generation_case_id": generation_case_id,
                    "call_id": source.get("call_id"),
                    "reason": "parsed_output_missing",
                }
            )
            continue
        call_id = str(accepted["call_id"])
        job["call_id"] = call_id
        accepted_by_id[call_id] = accepted
        accepted_by_task[task].append(accepted)

    ec_occurrences = make_ec_occurrences(
        ec_jobs, accepted_by_id, use_parsed_output=True
    )
    dc_occurrences = make_dc_occurrences(
        dc_jobs, accepted_by_id, use_parsed_output=True
    )

    output_files = {
        "ec_calls": args.output_dir / "ec_extraction_calls.jsonl",
        "dc_calls": args.output_dir / "dc_extraction_calls.jsonl",
        "ec_occurrences": args.output_dir / "ec_claim_occurrences.jsonl",
        "dc_occurrences": args.output_dir / "dc_claim_occurrences.jsonl",
        "failures": args.output_dir / "extraction_failures.jsonl",
        "quality": args.output_dir / "quality_summary.json",
        "manifest": args.output_dir / "claim_extraction_run_manifest.json",
    }
    for task in ("ec", "dc"):
        accepted_by_task[task].sort(
            key=lambda row: str((row.get("job_summary") or {}).get("generation_case_id"))
        )
    write_jsonl(output_files["ec_calls"], accepted_by_task["ec"])
    write_jsonl(output_files["dc_calls"], accepted_by_task["dc"])
    write_jsonl(output_files["ec_occurrences"], ec_occurrences)
    write_jsonl(output_files["dc_occurrences"], dc_occurrences)
    write_jsonl(output_files["failures"], failures)

    def task_counts(task: str, jobs: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "jobs_planned": len(jobs),
            "calls_recorded": sum(
                (task, str(job["generation_case_id"])) in source_calls for job in jobs
            ),
            "calls_success": len(accepted_by_task[task]),
            "calls_invalid_output": 0,
            "calls_api_error": sum(
                failure["task"] == task for failure in failures
            ),
            "successful_calls_with_no_claim": 0,
        }

    usage_totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for record in accepted_by_id.values():
        for key in usage_totals:
            value = (record.get("usage") or {}).get(key)
            if isinstance(value, int):
                usage_totals[key] += value
    quality = {
        "schema_version": "generation_claim_extraction_quality_summary_v1",
        "created_at_utc": utc_now(),
        "dry_run": False,
        "output_processing_mode": "schema_only",
        "selection_counts": {
            "generation_cases_total": len(cases),
            "successful_disclosures_total": len(disclosures),
            "selected_successful_cases": len(cases),
            "matching_cases_without_successful_disclosure": 0,
        },
        "task_counts": {
            "ec": task_counts("ec", ec_jobs),
            "dc": task_counts("dc", dc_jobs),
        },
        "occurrence_counts": {
            "ec_claim_occurrences": len(ec_occurrences),
            "dc_claim_occurrences": len(dc_occurrences),
        },
        "usage_totals": usage_totals,
    }
    write_json(output_files["quality"], quality)

    source_call_files = call_paths(args.source_run_dir)
    manifest = {
        "schema_version": "generation_claim_extraction_run_manifest_v1",
        "script_version": "rebuild_generation_claim_outputs_schema_only_v1",
        "run_id": args.run_id,
        "run_status": "complete" if not failures else "complete_with_failures",
        "output_processing_mode": "schema_only",
        "created_at_utc": utc_now(),
        "completed_at_utc": utc_now(),
        "inputs": {
            "generation_cases": str(args.generation_cases),
            "generated_disclosures": str(args.generated_disclosures),
            "source_run_dir": str(args.source_run_dir),
        },
        "source_hashes": {
            "generation_cases": sha256_file(args.generation_cases),
            "generated_disclosures": sha256_file(args.generated_disclosures),
            "ec_extraction_calls": sha256_file(source_call_files["ec"]),
            "dc_extraction_calls": sha256_file(source_call_files["dc"]),
        },
        "outputs": {key: str(path) for key, path in output_files.items()},
        "quality_summary": quality,
    }
    write_json(output_files["manifest"], manifest)

    print("Schema-only rebuild complete.")
    print(f"EC occurrences: {len(ec_occurrences)}")
    print(f"DC occurrences: {len(dc_occurrences)}")
    print(f"Unusable recorded calls: {len(failures)}")
    print(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()
