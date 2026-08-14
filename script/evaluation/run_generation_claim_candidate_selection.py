#!/usr/bin/env python3
"""Select candidate ECs for each deduplicated DC using the complete case EC set.

The LLM receives one target claim and all deduplicated evidence claims from the
same generation case. It may return only temporary EC identifiers. All input
validation, ID mapping, output validation, original-ID restoration, manifests,
and resume behavior are deterministic.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from generation_claims import (
    InputValidationError,
    OutputValidationError,
    append_jsonl,
    extract_usage,
    make_structured_text_config,
    normalize_azure_base_url,
    read_json,
    read_jsonl,
    require_file,
    serialize_sdk_response,
    sha256_file,
    sha256_json,
    utc_now,
    validate_file_hash,
    write_json,
    write_jsonl,
)
from run_generation_claim_support_assessment import (
    call_model_with_retries,
    format_duration,
    load_call_records,
    make_temporary_ids,
    prepare_output_directory,
    render_messages,
    select_case_ids,
    split_values,
    start_progress_heartbeat,
    stop_progress_heartbeat,
    usage_sum,
    validate_claim_rows,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env", override=False)

SCRIPT_VERSION = "run_generation_claim_candidate_selection_v1"
CONFIG_SCHEMA_VERSION = "generation_claim_candidate_selection_config_v1"
CALL_SCHEMA_VERSION = "generation_claim_candidate_selection_call_v1"
FAILURE_SCHEMA_VERSION = "generation_claim_candidate_selection_failure_v1"
RUN_MANIFEST_SCHEMA_VERSION = "generation_claim_candidate_selection_run_manifest_v1"
QUALITY_SUMMARY_SCHEMA_VERSION = "generation_claim_candidate_selection_quality_summary_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Select candidate evidence claims for each deduplicated disclosure "
            "claim using the complete case evidence-claim set."
        )
    )
    parser.add_argument("--ec-claims", type=Path, required=True)
    parser.add_argument("--dc-claims", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "config/evaluation/generation_claim_candidate_selection_config.json"
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="generation_claim_candidate_selection_run")
    parser.add_argument("--model-key", default=None)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--dc-id", action="append", default=[])
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--max-dcs", type=int, default=None)
    parser.add_argument("--request-delay-seconds", type=float, default=0.0)
    parser.add_argument(
        "--progress-interval-seconds",
        type=float,
        default=15.0,
        help="Print a heartbeat while waiting for an API call; use 0 to disable.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def load_and_validate_configuration(
    config_path: Path,
) -> tuple[dict[str, Any], str, Path, dict[str, Any], Path]:
    require_file(config_path, "candidate-selection config")
    config = read_json(config_path)
    if config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise InputValidationError(
            "Unsupported candidate-selection config schema: "
            f"{config.get('schema_version')!r}"
        )

    config_dir = config_path.parent
    prompt_spec = config.get("prompt")
    if not isinstance(prompt_spec, dict):
        raise InputValidationError("Missing candidate-selection prompt configuration")
    prompt_path = config_dir / str(prompt_spec.get("file") or "")
    require_file(prompt_path, "candidate-selection prompt")
    validate_file_hash(
        prompt_path,
        prompt_spec.get("sha256"),
        "candidate-selection prompt",
    )
    prompt_text = prompt_path.read_text(encoding="utf-8")

    schema_spec = config.get("response_schema")
    if not isinstance(schema_spec, dict):
        raise InputValidationError(
            "Missing candidate-selection response_schema configuration"
        )
    schema_path = config_dir / str(schema_spec.get("file") or "")
    require_file(schema_path, "candidate-selection response schema")
    validate_file_hash(
        schema_path,
        schema_spec.get("sha256"),
        "candidate-selection response schema",
    )
    schema = read_json(schema_path)
    if schema.get("$id") != schema_spec.get("version"):
        raise InputValidationError(
            "Candidate-selection response schema $id does not match configured version"
        )
    return config, prompt_text, prompt_path, schema, schema_path


def resolve_model(
    config: dict[str, Any], *, model_key_override: str | None, dry_run: bool
) -> tuple[str, dict[str, Any], str, str | None]:
    model_key_env = str(config.get("current_primary_model_env") or "")
    model_key = (
        model_key_override
        or os.environ.get(model_key_env)
        or config.get("current_primary_model")
    )
    models = config.get("models") or {}
    if model_key not in models:
        raise InputValidationError(
            f"Unknown candidate-selection model key: {model_key!r}"
        )
    model = models[model_key]
    if model.get("provider") != "azure_openai" or model.get("api_style") != "responses":
        raise InputValidationError(
            "Candidate selection requires an Azure OpenAI Responses API model"
        )

    deployment_env = str(model.get("deployment_name_env") or "")
    endpoint_env = str(model.get("endpoint_env") or "")
    key_env = str(model.get("api_key_env") or "")
    deployment = os.environ.get(deployment_env) or model.get("deployment_name")
    endpoint = os.environ.get(endpoint_env, "")

    if dry_run:
        deployment = deployment or f"<dry-run:{deployment_env}>"
        base_url = normalize_azure_base_url(endpoint) if endpoint else None
    else:
        if not deployment:
            raise InputValidationError(
                f"Missing Azure deployment environment variable: {deployment_env}"
            )
        if not endpoint:
            raise InputValidationError(
                f"Missing Azure endpoint environment variable: {endpoint_env}"
            )
        if not os.environ.get(key_env):
            raise InputValidationError(
                f"Missing Azure API key environment variable: {key_env}"
            )
        base_url = normalize_azure_base_url(endpoint)
    return str(model_key), model, str(deployment), base_url


def make_client(*, config: dict[str, Any], model: dict[str, Any], base_url: str) -> Any:
    key_env = str(model.get("api_key_env") or "")
    api_key = os.environ.get(key_env)
    if not api_key:
        raise InputValidationError(f"Missing Azure API key environment variable: {key_env}")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise InputValidationError(
            "The openai package is required for live candidate-selection calls"
        ) from exc
    runtime = config.get("runtime") or {}
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=float(runtime.get("request_timeout_seconds", 600)),
        max_retries=0,
    )


def build_jobs(
    *,
    ec_rows: list[dict[str, Any]],
    dc_rows: list[dict[str, Any]],
    case_ids: list[str],
    requested_dc_ids: set[str] | None,
    max_dcs: int | None,
    config: dict[str, Any],
    prompt_spec: dict[str, Any],
    schema_spec: dict[str, Any],
    model_key: str,
    model: dict[str, Any],
    deployment: str,
) -> list[dict[str, Any]]:
    selection = config.get("selection") or {}
    minimum_width = int(selection.get("temporary_id_min_width", 3))
    max_ecs = int(selection.get("max_evidence_claims_per_case", 500))
    if minimum_width < 1:
        raise InputValidationError("temporary_id_min_width must be at least 1")
    if max_ecs < 1:
        raise InputValidationError("max_evidence_claims_per_case must be at least 1")

    selected_case_set = set(case_ids)
    available_dc_ids = {
        str(row["dc_id"])
        for row in dc_rows
        if row["generation_case_id"] in selected_case_set
    }
    if requested_dc_ids:
        unknown = sorted(requested_dc_ids - available_dc_ids)
        if unknown:
            raise InputValidationError(f"Requested DC IDs not found: {unknown}")

    request_parameters = dict(model.get("request_parameters") or {})
    jobs: list[dict[str, Any]] = []
    for generation_case_id in case_ids:
        case_ecs = sorted(
            (row for row in ec_rows if row["generation_case_id"] == generation_case_id),
            key=lambda row: str(row["ec_id"]),
        )
        case_dcs = sorted(
            (row for row in dc_rows if row["generation_case_id"] == generation_case_id),
            key=lambda row: str(row["dc_id"]),
        )
        if len(case_ecs) > max_ecs:
            raise InputValidationError(
                f"{generation_case_id} has {len(case_ecs)} ECs; configured maximum is "
                f"{max_ecs}. Refusing to split the set because candidates could be missed."
            )

        ec_alias_by_original, ec_original_by_alias = make_temporary_ids(
            (str(row["ec_id"]) for row in case_ecs),
            prefix="ec",
            minimum_width=minimum_width,
        )
        dc_alias_by_original, _ = make_temporary_ids(
            (str(row["dc_id"]) for row in case_dcs),
            prefix="dc",
            minimum_width=minimum_width,
        )
        ec_input = [
            {
                "ec_claim_id": ec_alias_by_original[str(row["ec_id"])],
                "ec_text": row["ec_text"],
            }
            for row in case_ecs
        ]
        for dc_row in case_dcs:
            original_dc_id = str(dc_row["dc_id"])
            if requested_dc_ids and original_dc_id not in requested_dc_ids:
                continue
            dc_alias = dc_alias_by_original[original_dc_id]
            dynamic_input = {
                "ec_claims": ec_input,
                "dc_claim": {
                    "dc_claim_id": dc_alias,
                    "dc_text": dc_row["dc_text"],
                },
            }
            job_input_hash = sha256_json(dynamic_input)
            call_identity = {
                "generation_case_id": generation_case_id,
                "dc_id": original_dc_id,
                "job_input_hash": job_input_hash,
                "prompt_version": prompt_spec["version"],
                "prompt_sha256": prompt_spec["sha256"],
                "schema_version": schema_spec["version"],
                "schema_sha256": schema_spec["sha256"],
                "model_key": model_key,
                "model_id": model.get("model_id"),
                "model_version": model.get("model_version"),
                "deployment_name": deployment,
                "request_parameters": request_parameters,
            }
            jobs.append(
                {
                    "generation_case_id": generation_case_id,
                    "case_id": dc_row["case_id"],
                    "generated_disclosure_id": dc_row["generated_disclosure_id"],
                    "dc_id": original_dc_id,
                    "dc_alias": dc_alias,
                    "ec_original_by_alias": ec_original_by_alias,
                    "dynamic_input": dynamic_input,
                    "job_input_hash": job_input_hash,
                    "call_identity": call_identity,
                    "call_id": f"candidate_{sha256_json(call_identity)[:32]}",
                    "request_parameters": request_parameters,
                }
            )
    jobs.sort(key=lambda job: (job["generation_case_id"], job["dc_alias"]))
    if max_dcs is not None:
        if max_dcs < 1:
            raise InputValidationError("--max-dcs must be at least 1")
        jobs = jobs[:max_dcs]
    if not jobs:
        raise InputValidationError("No DCs match the requested filters")
    return jobs


def validate_candidate_response(
    payload: Any,
    *,
    expected_dc_id: str,
    expected_ec_ids: list[str],
) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {
        "dc_claim_id",
        "candidate_ec_ids",
    }:
        raise OutputValidationError(
            "Response root must contain exactly dc_claim_id and candidate_ec_ids"
        )
    if payload["dc_claim_id"] != expected_dc_id:
        raise OutputValidationError(
            f"dc_claim_id must equal {expected_dc_id!r}, got {payload['dc_claim_id']!r}"
        )
    candidate_ids = payload["candidate_ec_ids"]
    if not isinstance(candidate_ids, list):
        raise OutputValidationError("candidate_ec_ids must be an array")
    if any(not isinstance(claim_id, str) or not claim_id for claim_id in candidate_ids):
        raise OutputValidationError("candidate_ec_ids contains an invalid EC ID")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise OutputValidationError("candidate_ec_ids contains a duplicate EC ID")
    expected_order = {claim_id: index for index, claim_id in enumerate(expected_ec_ids)}
    unknown = sorted(set(candidate_ids) - set(expected_order))
    if unknown:
        raise OutputValidationError(f"candidate_ec_ids contains unknown EC IDs: {unknown}")
    return {
        "dc_claim_id": expected_dc_id,
        "candidate_ec_ids": sorted(candidate_ids, key=expected_order.__getitem__),
    }


def restore_original_ids(
    validated_output: dict[str, Any],
    *,
    original_dc_id: str,
    ec_original_by_alias: dict[str, str],
) -> dict[str, Any]:
    return {
        "dc_claim_id": original_dc_id,
        "candidate_ec_ids": [
            ec_original_by_alias[alias]
            for alias in validated_output["candidate_ec_ids"]
        ],
    }


def execute_job(
    *,
    job: dict[str, Any],
    client: Any,
    deployment: str,
    prompt_text: str,
    schema: dict[str, Any],
    schema_spec: dict[str, Any],
    model_key: str,
    model: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    expected_ec_ids = list(job["ec_original_by_alias"])
    common = {
        "schema_version": CALL_SCHEMA_VERSION,
        "call_id": job["call_id"],
        "generation_case_id": job["generation_case_id"],
        "case_id": job["case_id"],
        "generated_disclosure_id": job["generated_disclosure_id"],
        "dc_id": job["dc_id"],
        "dc_temporary_id": job["dc_alias"],
        "ec_temporary_id_map": job["ec_original_by_alias"],
        "call_identity": job["call_identity"],
        "dynamic_input": job["dynamic_input"],
        "model_key": model_key,
        "model_id": model.get("model_id"),
        "model_version": model.get("model_version"),
        "deployment_name": deployment,
        "request_parameters": job["request_parameters"],
        "started_at_utc": utc_now(),
    }
    messages = render_messages(prompt_text, job["dynamic_input"])
    text_config = make_structured_text_config(
        schema,
        name=schema_spec["structured_output_name"],
        strict=bool(schema_spec.get("strict", True)),
    )
    runtime = config.get("runtime") or {}
    max_invalid_retries = int(runtime.get("max_invalid_output_retries", 2))
    attempts: list[dict[str, Any]] = []
    last_raw = ""
    last_parsed: Any = None
    last_validation_error: str | None = None

    for output_attempt in range(max_invalid_retries + 1):
        response, error, network_retries = call_model_with_retries(
            client=client,
            deployment=deployment,
            messages=messages,
            text_config=text_config,
            request_parameters=job["request_parameters"],
            runtime=runtime,
        )
        if error is not None:
            attempts.append(
                {
                    "output_attempt": output_attempt,
                    "messages_sha256": sha256_json(messages),
                    "network_retries": network_retries,
                    "status": "api_error",
                    "error_type": type(error).__name__,
                    "error_message": str(error)[:4000],
                    "http_status": getattr(error, "status_code", None),
                    "usage": {
                        "input_tokens": None,
                        "output_tokens": None,
                        "total_tokens": None,
                    },
                    "api_response": None,
                }
            )
            return {
                **common,
                "finished_at_utc": utc_now(),
                "call_status": "api_error",
                "model_called": True,
                "attempts": attempts,
                "raw_output": last_raw,
                "parsed_output": last_parsed,
                "validated_output": None,
                "restored_output": None,
                "output_valid": False,
                "validation_error": last_validation_error,
                "error_type": type(error).__name__,
                "error_message": str(error)[:4000],
                "http_status": getattr(error, "status_code", None),
                "usage": usage_sum(attempt["usage"] for attempt in attempts),
            }

        api_response = serialize_sdk_response(response)
        usage = extract_usage(api_response)
        last_raw = getattr(response, "output_text", None) or ""
        last_parsed = None
        validated: dict[str, Any] | None = None
        restored: dict[str, Any] | None = None
        try:
            last_parsed = json.loads(last_raw)
            validated = validate_candidate_response(
                last_parsed,
                expected_dc_id=job["dc_alias"],
                expected_ec_ids=expected_ec_ids,
            )
            restored = restore_original_ids(
                validated,
                original_dc_id=job["dc_id"],
                ec_original_by_alias=job["ec_original_by_alias"],
            )
            last_validation_error = None
        except (json.JSONDecodeError, OutputValidationError) as exc:
            last_validation_error = str(exc)
        attempts.append(
            {
                "output_attempt": output_attempt,
                "messages_sha256": sha256_json(messages),
                "network_retries": network_retries,
                "status": "success" if validated is not None else "invalid_output",
                "raw_output": last_raw,
                "parsed_output": last_parsed,
                "validation_error": last_validation_error,
                "usage": usage,
                "api_response": api_response,
            }
        )
        if validated is not None and restored is not None:
            return {
                **common,
                "finished_at_utc": utc_now(),
                "call_status": "success",
                "model_called": True,
                "attempts": attempts,
                "raw_output": last_raw,
                "parsed_output": last_parsed,
                "validated_output": validated,
                "restored_output": restored,
                "output_valid": True,
                "validation_error": None,
                "error_type": None,
                "error_message": None,
                "http_status": None,
                "usage": usage_sum(attempt["usage"] for attempt in attempts),
            }

    return {
        **common,
        "finished_at_utc": utc_now(),
        "call_status": "invalid_output",
        "model_called": True,
        "attempts": attempts,
        "raw_output": last_raw,
        "parsed_output": last_parsed,
        "validated_output": None,
        "restored_output": None,
        "output_valid": False,
        "validation_error": last_validation_error,
        "error_type": None,
        "error_message": None,
        "http_status": None,
        "usage": usage_sum(attempt["usage"] for attempt in attempts),
    }


def output_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "calls": output_dir / "claim_candidate_calls.jsonl",
        "failures": output_dir / "claim_candidate_failures.jsonl",
        "results": output_dir / "dc_candidate_ecs.jsonl",
        "quality": output_dir / "quality_summary.json",
        "manifest": output_dir / "claim_candidate_run_manifest.json",
    }


def make_quality_summary(
    *,
    jobs: list[dict[str, Any]],
    latest_calls: dict[str, dict[str, Any]],
    all_call_records: list[dict[str, Any]],
    results: list[dict[str, Any]],
    dry_run: bool,
) -> dict[str, Any]:
    records = [latest_calls[job["call_id"]] for job in jobs if job["call_id"] in latest_calls]
    candidate_counts = [len(result["candidate_ec_ids"]) for result in results]
    usage_totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for record in all_call_records:
        for key in usage_totals:
            value = (record.get("usage") or {}).get(key)
            if isinstance(value, int):
                usage_totals[key] += value
    return {
        "schema_version": QUALITY_SUMMARY_SCHEMA_VERSION,
        "created_at_utc": utc_now(),
        "dry_run": dry_run,
        "generation_case_count": len({job["generation_case_id"] for job in jobs}),
        "dc_count": len(jobs),
        "ec_counts_by_case": {
            case_id: len(
                next(
                    job["dynamic_input"]["ec_claims"]
                    for job in jobs
                    if job["generation_case_id"] == case_id
                )
            )
            for case_id in sorted({job["generation_case_id"] for job in jobs})
        },
        "calls_planned": len(jobs),
        "calls_recorded": len(records),
        "calls_success": sum(record.get("call_status") == "success" for record in records),
        "calls_invalid_output": sum(
            record.get("call_status") == "invalid_output" for record in records
        ),
        "calls_api_error": sum(
            record.get("call_status") == "api_error" for record in records
        ),
        "candidate_count_total": None if dry_run else sum(candidate_counts),
        "candidate_count_min": None if dry_run or not candidate_counts else min(candidate_counts),
        "candidate_count_max": None if dry_run or not candidate_counts else max(candidate_counts),
        "candidate_count_mean": (
            None
            if dry_run or not candidate_counts
            else sum(candidate_counts) / len(candidate_counts)
        ),
        "empty_candidate_dc_count": (
            None if dry_run else sum(count == 0 for count in candidate_counts)
        ),
        "usage_totals": usage_totals,
    }


def main() -> None:
    args = parse_args()
    if args.dry_run and args.resume:
        raise InputValidationError("--dry-run and --resume cannot be combined")
    if args.request_delay_seconds < 0:
        raise InputValidationError("--request-delay-seconds cannot be negative")
    if args.progress_interval_seconds < 0:
        raise InputValidationError("--progress-interval-seconds cannot be negative")
    require_file(args.ec_claims, "deduplicated EC claims")
    require_file(args.dc_claims, "deduplicated DC claims")

    config, prompt_text, prompt_path, schema, schema_path = (
        load_and_validate_configuration(args.config)
    )
    model_key, model, deployment, base_url = resolve_model(
        config,
        model_key_override=args.model_key,
        dry_run=args.dry_run,
    )
    ec_rows = read_jsonl(args.ec_claims)
    dc_rows = read_jsonl(args.dc_claims)
    validate_claim_rows(
        ec_rows,
        dc_rows,
        ec_path=args.ec_claims,
        dc_path=args.dc_claims,
    )
    case_ids = select_case_ids(
        ec_rows,
        requested=split_values(args.case_id),
        max_cases=args.max_cases,
    )
    jobs = build_jobs(
        ec_rows=ec_rows,
        dc_rows=dc_rows,
        case_ids=case_ids,
        requested_dc_ids=split_values(args.dc_id),
        max_dcs=args.max_dcs,
        config=config,
        prompt_spec=config["prompt"],
        schema_spec=config["response_schema"],
        model_key=model_key,
        model=model,
        deployment=deployment,
    )

    paths = output_paths(args.output_dir)
    previous_manifest = prepare_output_directory(
        output_dir=args.output_dir,
        paths=paths,
        resume=args.resume,
    )
    run_identity = {
        "script_version": SCRIPT_VERSION,
        "inputs": {
            "ec_claims": {"path": str(args.ec_claims), "sha256": sha256_file(args.ec_claims)},
            "dc_claims": {"path": str(args.dc_claims), "sha256": sha256_file(args.dc_claims)},
        },
        "config_path": str(args.config),
        "config_sha256": sha256_file(args.config),
        "prompt_sha256": sha256_file(prompt_path),
        "schema_sha256": sha256_file(schema_path),
        "selected_generation_case_ids": case_ids,
        "selected_dc_ids": [job["dc_id"] for job in jobs],
        "model_key": model_key,
        "model_id": model.get("model_id"),
        "model_version": model.get("model_version"),
        "deployment_name": deployment,
        "request_parameters": model.get("request_parameters") or {},
    }
    run_identity_sha256 = sha256_json(run_identity)
    if previous_manifest is not None:
        if previous_manifest.get("run_identity_sha256") != run_identity_sha256:
            raise InputValidationError(
                "Cannot resume because inputs, filters, prompt, schema, model, or "
                "request parameters differ from the existing run manifest"
            )

    manifest = {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "script_version": SCRIPT_VERSION,
        "run_id": args.run_id,
        "status": "dry_run" if args.dry_run else "running",
        "dry_run": args.dry_run,
        "started_at_utc": (
            previous_manifest.get("started_at_utc") if previous_manifest else utc_now()
        ),
        "completed_at_utc": None,
        "run_identity": run_identity,
        "run_identity_sha256": run_identity_sha256,
        "planned_model_calls": len(jobs),
        "outputs": {key: str(path) for key, path in paths.items()},
    }
    write_json(paths["manifest"], manifest)

    latest_calls, all_call_records = load_call_records(paths["calls"])
    if args.dry_run:
        write_jsonl(paths["calls"], [])
        write_jsonl(paths["failures"], [])
        write_jsonl(paths["results"], [])
        summary = make_quality_summary(
            jobs=jobs,
            latest_calls={},
            all_call_records=[],
            results=[],
            dry_run=True,
        )
        write_json(paths["quality"], summary)
        manifest["completed_at_utc"] = utc_now()
        write_json(paths["manifest"], manifest)
        print("Dry run complete.")
        print(f"Selected generation cases: {summary['generation_case_count']}")
        print(f"Selected DCs / planned model calls: {len(jobs)}")
        print(f"EC counts by case: {summary['ec_counts_by_case']}")
        print(f"Run manifest: {paths['manifest']}")
        return

    client = make_client(config=config, model=model, base_url=str(base_url))
    pending_jobs = [
        job
        for job in jobs
        if latest_calls.get(job["call_id"], {}).get("call_status") != "success"
    ]
    print(
        f"Run plan: {len(jobs)} calls total | {len(jobs) - len(pending_jobs)} "
        f"resume-skipped | {len(pending_jobs)} calls this run",
        flush=True,
    )
    run_started = time.monotonic()
    for index, job in enumerate(pending_jobs, start=1):
        label = (
            f"[{index}/{len(pending_jobs)}] {job['generation_case_id']} "
            f"{job['dc_alias']} ({len(job['dynamic_input']['ec_claims'])} ECs)"
        )
        call_started = time.monotonic()
        print(f"{label} started", flush=True)
        heartbeat = start_progress_heartbeat(
            label=label,
            interval_seconds=args.progress_interval_seconds,
            call_started=call_started,
            run_started=run_started,
        )
        try:
            record = execute_job(
                job=job,
                client=client,
                deployment=deployment,
                prompt_text=prompt_text,
                schema=schema,
                schema_spec=config["response_schema"],
                model_key=model_key,
                model=model,
                config=config,
            )
        finally:
            stop_progress_heartbeat(heartbeat)
        append_jsonl(paths["calls"], record)
        latest_calls[job["call_id"]] = record
        all_call_records.append(record)
        candidate_count = len(
            (record.get("validated_output") or {}).get("candidate_ec_ids") or []
        )
        usage = record.get("usage") or {}
        print(
            f"{label} finished: {record['call_status']} | candidates "
            f"{candidate_count} | tokens {usage.get('input_tokens')}/"
            f"{usage.get('output_tokens')} | elapsed "
            f"{format_duration(time.monotonic() - call_started)}",
            flush=True,
        )
        if args.request_delay_seconds and index < len(pending_jobs):
            time.sleep(args.request_delay_seconds)

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for job in jobs:
        record = latest_calls.get(job["call_id"])
        if not record or record.get("call_status") != "success":
            failures.append(
                {
                    "schema_version": FAILURE_SCHEMA_VERSION,
                    "call_id": job["call_id"],
                    "generation_case_id": job["generation_case_id"],
                    "dc_id": job["dc_id"],
                    "call_status": (record or {}).get("call_status", "missing"),
                    "validation_error": (record or {}).get("validation_error"),
                    "error_type": (record or {}).get("error_type"),
                    "error_message": (record or {}).get("error_message"),
                }
            )
            continue
        results.append(record["restored_output"])
    results.sort(key=lambda result: result["dc_claim_id"])
    failures.sort(key=lambda failure: failure["dc_id"])
    write_jsonl(paths["results"], results)
    write_jsonl(paths["failures"], failures)

    summary = make_quality_summary(
        jobs=jobs,
        latest_calls=latest_calls,
        all_call_records=all_call_records,
        results=results,
        dry_run=False,
    )
    write_json(paths["quality"], summary)
    manifest["status"] = "complete" if not failures else "complete_with_failures"
    manifest["completed_at_utc"] = utc_now()
    manifest["result_counts"] = {
        "dc_candidate_results": len(results),
        "failures": len(failures),
    }
    write_json(paths["manifest"], manifest)

    print(f"Run status: {manifest['status']}")
    print(f"Candidate ECs selected: {summary['candidate_count_total']}")
    print(f"Empty candidate DCs: {summary['empty_candidate_dc_count']}")
    print(f"Quality summary: {paths['quality']}")
    print(f"Run manifest: {paths['manifest']}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
