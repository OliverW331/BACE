#!/usr/bin/env python3
"""Extract atomic EC/DC claim occurrences from frozen generation artifacts.

The CLI is experiment-folder agnostic. Pilot and formal runs use the same
implementation and differ only in their explicit input and output paths.

No Azure credentials are required for input validation or ``--dry-run``.
Live calls read endpoint, deployment, and API key only from configured
environment variables.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Sequence

from dotenv import load_dotenv

from generation_claims import (
    InputValidationError,
    OutputValidationError,
    add_call_identity,
    append_jsonl,
    build_dc_jobs,
    build_ec_jobs,
    canonical_json,
    extract_usage,
    make_dc_occurrences,
    make_ec_occurrences,
    make_structured_text_config,
    normalize_azure_base_url,
    read_json,
    read_jsonl,
    render_messages,
    require_file,
    select_cases,
    serialize_sdk_response,
    sha256_file,
    sha256_json,
    sha256_text,
    utc_now,
    validate_ec_extraction_response,
    validate_extraction_response,
    validate_file_hash,
    write_json,
    write_jsonl,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env", override=False)

SCRIPT_VERSION = "run_generation_claim_extraction_v1.5"
RUN_MANIFEST_SCHEMA_VERSION = "generation_claim_extraction_run_manifest_v1"
QUALITY_SUMMARY_SCHEMA_VERSION = "generation_claim_extraction_quality_summary_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract atomic EC/DC claim occurrences from generation artifacts."
    )
    parser.add_argument("--generation-cases", type=Path, required=True)
    parser.add_argument("--generation-input-manifest", type=Path, required=True)
    parser.add_argument("--generated-disclosures", type=Path, required=True)
    parser.add_argument("--generation-run-manifest", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "config/evaluation/configs/generation_claim_extraction_config.json"
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="claim_extraction_run")
    parser.add_argument("--model-key", default=None)
    parser.add_argument("--only", choices=["both", "ec", "dc"], default="both")
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--company-id", action="append", default=[])
    parser.add_argument("--task-id", action="append", default=[])
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--request-delay-seconds", type=float, default=0.0)
    parser.add_argument(
        "--progress-interval-seconds",
        type=float,
        default=10.0,
        help="Print a heartbeat while waiting for each API call; use 0 to disable.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def split_values(values: Sequence[str]) -> set[str] | None:
    parsed: set[str] = set()
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                parsed.add(part)
    return parsed or None


def merge_dicts(*values: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for value in values:
        merged.update(value)
    return merged


def format_duration(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {remaining_seconds:02d}s"
    if minutes:
        return f"{minutes}m {remaining_seconds:02d}s"
    return f"{remaining_seconds}s"


def should_skip_on_resume(record: dict[str, Any] | None) -> bool:
    return bool(record) and record.get("call_status") == "success"


def start_progress_heartbeat(
    *,
    label: str,
    interval_seconds: float,
    call_started: float,
    run_started: float,
) -> tuple[threading.Event, threading.Thread] | None:
    if interval_seconds <= 0:
        return None
    stop_event = threading.Event()

    def report_waiting() -> None:
        while not stop_event.wait(interval_seconds):
            now = time.monotonic()
            print(
                f"{label} waiting | call elapsed {format_duration(now - call_started)} "
                f"| run elapsed {format_duration(now - run_started)}",
                flush=True,
            )

    thread = threading.Thread(target=report_waiting, daemon=True)
    thread.start()
    return stop_event, thread


def stop_progress_heartbeat(
    heartbeat: tuple[threading.Event, threading.Thread] | None,
) -> None:
    if heartbeat is None:
        return
    stop_event, thread = heartbeat
    stop_event.set()
    thread.join(timeout=1.0)


def load_and_validate_configuration(
    config_path: Path,
) -> tuple[
    dict[str, Any],
    dict[str, str],
    dict[str, Path],
    dict[str, dict[str, Any]],
    dict[str, Path],
]:
    require_file(config_path, "claim extraction config")
    config = read_json(config_path)
    if config.get("schema_version") != "generation_claim_extraction_config_v1":
        raise InputValidationError(
            f"Unsupported claim extraction config schema: {config.get('schema_version')!r}"
        )

    config_dir = config_path.parent
    prompt_texts: dict[str, str] = {}
    prompt_paths: dict[str, Path] = {}
    for task in ("ec", "dc"):
        spec = config.get("prompts", {}).get(task)
        if not isinstance(spec, dict):
            raise InputValidationError(f"Missing {task} prompt configuration")
        prompt_path = config_dir / spec["file"]
        require_file(prompt_path, f"{task} prompt")
        validate_file_hash(prompt_path, spec.get("sha256"), f"{task} prompt")
        prompt_paths[task] = prompt_path
        prompt_texts[task] = prompt_path.read_text(encoding="utf-8")

    schemas: dict[str, dict[str, Any]] = {}
    schema_paths: dict[str, Path] = {}
    for task in ("ec", "dc"):
        schema_spec = config.get("response_schemas", {}).get(task)
        if not isinstance(schema_spec, dict):
            raise InputValidationError(
                f"Missing {task} response schema configuration"
            )
        schema_path = config_dir / schema_spec["file"]
        require_file(schema_path, f"{task} claim extraction response schema")
        validate_file_hash(
            schema_path, schema_spec.get("sha256"), f"{task} response schema"
        )
        schema = read_json(schema_path)
        if schema.get("$id") != schema_spec.get("version"):
            raise InputValidationError(
                f"{task} response schema $id does not match configured version"
            )
        schemas[task] = schema
        schema_paths[task] = schema_path
    return config, prompt_texts, prompt_paths, schemas, schema_paths


def validate_source_manifests(
    *,
    generation_cases_path: Path,
    generation_input_manifest_path: Path,
    generated_disclosures_path: Path,
    generation_run_manifest_path: Path,
    case_count: int,
    disclosure_count: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    input_manifest = read_json(generation_input_manifest_path)
    run_manifest = read_json(generation_run_manifest_path)

    if input_manifest.get("generation_case_count") != case_count:
        raise InputValidationError(
            "Generation input manifest case count does not match generation_cases.jsonl"
        )
    validate_file_hash(
        generation_cases_path,
        run_manifest.get("generation_cases_sha256"),
        "generation cases referenced by generation run manifest",
    )
    validate_file_hash(
        generation_input_manifest_path,
        run_manifest.get("generation_input_manifest_sha256"),
        "generation input manifest referenced by generation run manifest",
    )
    if run_manifest.get("case_count_success") != disclosure_count:
        raise InputValidationError(
            "Generation run manifest success count does not match "
            "generated_disclosures.jsonl"
        )
    output_recorded = (run_manifest.get("outputs") or {}).get(
        "generated_disclosures_jsonl"
    )
    if output_recorded:
        recorded_path = Path(output_recorded)
        if recorded_path.name != generated_disclosures_path.name:
            raise InputValidationError(
                "Generation run manifest references a different disclosure output filename"
            )
    return input_manifest, run_manifest


def resolve_model(
    config: dict[str, Any], *, model_key_override: str | None, dry_run: bool
) -> tuple[str, dict[str, Any], str, str | None, str | None]:
    model_key_env = config.get("current_primary_model_env")
    model_key = (
        model_key_override
        or os.environ.get(str(model_key_env or ""))
        or config.get("current_primary_model")
    )
    models = config.get("models") or {}
    if model_key not in models:
        raise InputValidationError(f"Unknown model key: {model_key!r}")
    model = models[model_key]
    if model.get("provider") != "azure_openai" or model.get("api_style") != "responses":
        raise InputValidationError(
            "This implementation currently requires Azure OpenAI Responses API configuration"
        )

    deployment_env = model.get("deployment_name_env")
    deployment = os.environ.get(deployment_env or "") or model.get("deployment_name")
    endpoint_env = model.get("endpoint_env")
    endpoint = os.environ.get(endpoint_env or "")
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
        key_env = model.get("api_key_env")
        if not os.environ.get(key_env or ""):
            raise InputValidationError(
                f"Missing Azure API key environment variable: {key_env}"
            )
        base_url = normalize_azure_base_url(endpoint)
    return str(model_key), model, str(deployment), base_url, endpoint_env


def make_client(
    *, config: dict[str, Any], model: dict[str, Any], base_url: str
) -> Any:
    key_env = model.get("api_key_env")
    api_key = os.environ.get(key_env or "")
    if not api_key:
        raise InputValidationError(f"Missing Azure API key environment variable: {key_env}")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise InputValidationError(
            "The openai package is required for live extraction calls"
        ) from exc

    runtime = config.get("runtime") or {}
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=float(runtime.get("request_timeout_seconds", 180)),
        max_retries=0,
    )


def output_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "ec_calls": output_dir / "ec_extraction_calls.jsonl",
        "dc_calls": output_dir / "dc_extraction_calls.jsonl",
        "ec_occurrences": output_dir / "ec_claim_occurrences.jsonl",
        "dc_occurrences": output_dir / "dc_claim_occurrences.jsonl",
        "failures": output_dir / "extraction_failures.jsonl",
        "quality": output_dir / "quality_summary.json",
        "manifest": output_dir / "claim_extraction_run_manifest.json",
    }


def prepare_output_directory(
    *, output_dir: Path, paths: dict[str, Path], resume: bool
) -> dict[str, Any] | None:
    existing_files = list(output_dir.iterdir()) if output_dir.is_dir() else []
    if existing_files and not resume:
        raise InputValidationError(
            f"Output directory is not empty: {output_dir}. Use --resume only for "
            "the same run, or choose a new output directory."
        )
    if resume:
        if not paths["manifest"].is_file():
            raise InputValidationError(
                f"Cannot resume without run manifest: {paths['manifest']}"
            )
        previous = read_json(paths["manifest"])
    else:
        previous = None
    output_dir.mkdir(parents=True, exist_ok=True)
    return previous


def load_latest_call_records(paths: dict[str, Path]) -> tuple[
    dict[str, dict[str, Any]], list[dict[str, Any]]
]:
    latest: dict[str, dict[str, Any]] = {}
    all_records: list[dict[str, Any]] = []
    for key in ("ec_calls", "dc_calls"):
        path = paths[key]
        if not path.is_file():
            continue
        for record in read_jsonl(path):
            call_id = record.get("call_id")
            if not call_id:
                raise InputValidationError(f"Call record without call_id in {path}")
            latest[str(call_id)] = record
            all_records.append(record)
    return latest, all_records


def get_status_code(error: Exception) -> int | None:
    status = getattr(error, "status_code", None)
    if isinstance(status, int):
        return status
    response = getattr(error, "response", None)
    response_status = getattr(response, "status_code", None)
    return response_status if isinstance(response_status, int) else None


def is_retryable_error(error: Exception) -> bool:
    status = get_status_code(error)
    if status in {408, 409, 429} or (isinstance(status, int) and status >= 500):
        return True
    error_name = type(error).__name__.lower()
    return any(token in error_name for token in ("timeout", "connection", "ratelimit"))


def call_model_with_retries(
    *,
    client: Any,
    deployment: str,
    messages: list[dict[str, str]],
    text_config: dict[str, Any],
    request_parameters: dict[str, Any],
    runtime: dict[str, Any],
) -> tuple[Any | None, Exception | None, int]:
    max_retries = int(runtime.get("max_network_retries", 4))
    initial = float(runtime.get("retry_initial_seconds", 2))
    maximum = float(runtime.get("retry_max_seconds", 60))
    for attempt in range(max_retries + 1):
        try:
            response = client.responses.create(
                model=deployment,
                input=messages,
                text=text_config,
                **request_parameters,
            )
            return response, None, attempt
        except Exception as exc:  # provider exceptions vary by SDK version
            if attempt >= max_retries or not is_retryable_error(exc):
                return None, exc, attempt
            delay = min(maximum, initial * (2**attempt))
            print(
                f"  retryable API error ({type(exc).__name__}); retrying in {delay:g}s",
                flush=True,
            )
            time.sleep(delay)
    raise AssertionError("unreachable retry loop")


def job_summary(job: dict[str, Any]) -> dict[str, Any]:
    if job["task"] == "ec":
        return {
            "generation_case_id": job["generation_case_id"],
            "evidence_count": len(job["evidence_records"]),
            "evidence_section_sha256": job["evidence_section_sha256"],
        }
    return {
        "generation_case_id": job["generation_case_id"],
        "generation_output_id": job["generation_output_id"],
        "generated_text_hash": job["generated_text_hash"],
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
    messages = render_messages(prompt_text, job["dynamic_input"])
    text_config = make_structured_text_config(
        schema,
        name=schema_spec["structured_output_name"],
        strict=bool(schema_spec.get("strict", True)),
    )
    request_parameters = merge_dicts(
        model.get("request_parameters") or {},
        (model.get("task_request_parameters") or {}).get(job["task"], {}),
    )
    started_at = utc_now()
    response, error, retries = call_model_with_retries(
        client=client,
        deployment=deployment,
        messages=messages,
        text_config=text_config,
        request_parameters=request_parameters,
        runtime=config.get("runtime") or {},
    )
    common = {
        "schema_version": "generation_claim_extraction_call_v1",
        "call_id": job["call_id"],
        "task": job["task"],
        "call_identity": job["call_identity"],
        "job_summary": job_summary(job),
        "dynamic_input": job["dynamic_input"],
        "messages_sha256": sha256_json(messages),
        "model_key": model_key,
        "model_id": model.get("model_id"),
        "model_version": model.get("model_version"),
        "deployment_name": deployment,
        "request_parameters": request_parameters,
        "started_at_utc": started_at,
        "finished_at_utc": utc_now(),
        "retry_attempts": retries,
    }
    if error is not None:
        return {
            **common,
            "call_status": "api_error",
            "raw_output": "",
            "parsed_output": None,
            "validated_output": None,
            "output_valid": False,
            "validation_error": None,
            "error_type": type(error).__name__,
            "error_message": str(error)[:4000],
            "http_status": get_status_code(error),
            "usage": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
            "api_response": None,
        }

    api_response = serialize_sdk_response(response)
    raw_output = getattr(response, "output_text", None) or ""
    parsed: Any = None
    validation_error: str | None = None
    validated: dict[str, Any] | None = None
    processing_mode = str(
        (config.get("output_validation") or {}).get("mode", "strict")
    )
    try:
        parsed = json.loads(raw_output)
        if processing_mode == "schema_only":
            validated = parsed
        elif processing_mode == "strict":
            require_unique_quotes = bool(
                (config.get("output_validation") or {}).get(
                    "require_unique_source_quotes", True
                )
            )
            if job["task"] == "ec":
                validated = validate_ec_extraction_response(
                    parsed,
                    evidence_records=job["evidence_records"],
                    require_unique_quotes=require_unique_quotes,
                )
            else:
                validated = validate_extraction_response(
                    parsed,
                    source_text=job["source_text"],
                    context_metadata=job["context_metadata"],
                    require_unique_quotes=require_unique_quotes,
                )
        else:
            raise InputValidationError(
                f"Unsupported output validation mode: {processing_mode!r}"
            )
    except (json.JSONDecodeError, OutputValidationError) as exc:
        validation_error = str(exc)

    return {
        **common,
        "call_status": "success" if validated is not None else "invalid_output",
        "raw_output": raw_output,
        "parsed_output": parsed,
        "validated_output": validated,
        "output_valid": validated is not None,
        "output_processing_mode": processing_mode,
        "validation_error": validation_error,
        "error_type": None,
        "error_message": None,
        "http_status": None,
        "usage": extract_usage(api_response),
        "api_response": api_response,
    }


def make_quality_summary(
    *,
    selection_counts: dict[str, int],
    ec_jobs: list[dict[str, Any]],
    dc_jobs: list[dict[str, Any]],
    latest_calls: dict[str, dict[str, Any]],
    all_call_records: list[dict[str, Any]],
    ec_occurrences: list[dict[str, Any]],
    dc_occurrences: list[dict[str, Any]],
    dry_run: bool,
) -> dict[str, Any]:
    def claim_count(record: dict[str, Any]) -> int:
        validated = record.get("validated_output") or {}
        if record.get("task") == "ec":
            return sum(
                len(result.get("claims") or [])
                for result in validated.get("evidence_results") or []
            )
        return len(validated.get("claims") or [])

    task_counts: dict[str, dict[str, int]] = {}
    for task, jobs in (("ec", ec_jobs), ("dc", dc_jobs)):
        records = [latest_calls[job["call_id"]] for job in jobs if job["call_id"] in latest_calls]
        task_counts[task] = {
            "jobs_planned": len(jobs),
            "calls_recorded": len(records),
            "calls_success": sum(record.get("call_status") == "success" for record in records),
            "calls_invalid_output": sum(
                record.get("call_status") == "invalid_output" for record in records
            ),
            "calls_api_error": sum(
                record.get("call_status") == "api_error" for record in records
            ),
            "successful_calls_with_no_claim": sum(
                record.get("call_status") == "success"
                and claim_count(record) == 0
                for record in records
            ),
        }

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
        "selection_counts": selection_counts,
        "task_counts": task_counts,
        "occurrence_counts": {
            "ec_claim_occurrences": len(ec_occurrences),
            "dc_claim_occurrences": len(dc_occurrences),
        },
        "usage_totals": usage_totals,
    }


def main() -> None:
    args = parse_args()
    if args.request_delay_seconds < 0:
        raise InputValidationError("--request-delay-seconds cannot be negative")
    if args.progress_interval_seconds < 0:
        raise InputValidationError("--progress-interval-seconds cannot be negative")
    if args.dry_run and args.resume:
        raise InputValidationError("--dry-run and --resume cannot be combined")

    for path, label in (
        (args.generation_cases, "generation cases"),
        (args.generation_input_manifest, "generation input manifest"),
        (args.generated_disclosures, "generated disclosures"),
        (args.generation_run_manifest, "generation run manifest"),
    ):
        require_file(path, label)

    config, prompt_texts, prompt_paths, schemas, schema_paths = (
        load_and_validate_configuration(args.config)
    )
    output_processing_mode = str(
        (config.get("output_validation") or {}).get("mode", "strict")
    )
    if output_processing_mode not in {"strict", "schema_only"}:
        raise InputValidationError(
            f"Unsupported output validation mode: {output_processing_mode!r}"
        )
    cases = read_jsonl(args.generation_cases)
    disclosures = read_jsonl(args.generated_disclosures)
    input_manifest, source_run_manifest = validate_source_manifests(
        generation_cases_path=args.generation_cases,
        generation_input_manifest_path=args.generation_input_manifest,
        generated_disclosures_path=args.generated_disclosures,
        generation_run_manifest_path=args.generation_run_manifest,
        case_count=len(cases),
        disclosure_count=len(disclosures),
    )
    selected_cases, disclosures_by_case, selection_counts = select_cases(
        cases,
        disclosures,
        case_ids=split_values(args.case_id),
        company_ids=split_values(args.company_id),
        task_ids=split_values(args.task_id),
        max_cases=args.max_cases,
    )

    model_key, model, deployment, base_url, _endpoint_env = resolve_model(
        config, model_key_override=args.model_key, dry_run=args.dry_run
    )
    configured_tasks = ["ec", "dc"] if args.only == "both" else [args.only]
    ec_jobs = build_ec_jobs(selected_cases) if "ec" in configured_tasks else []
    dc_jobs = (
        build_dc_jobs(selected_cases, disclosures_by_case)
        if "dc" in configured_tasks
        else []
    )

    for jobs, task in ((ec_jobs, "ec"), (dc_jobs, "dc")):
        prompt_spec = config["prompts"][task]
        schema_spec = config["response_schemas"][task]
        effective_request_parameters = merge_dicts(
            model.get("request_parameters") or {},
            (model.get("task_request_parameters") or {}).get(task, {}),
        )
        for index, job in enumerate(jobs):
            jobs[index] = add_call_identity(
                job,
                prompt_version=prompt_spec["version"],
                prompt_sha256=prompt_spec["sha256"],
                schema_version=schema_spec["version"],
                schema_sha256=schema_spec["sha256"],
                model_key=model_key,
                model_id=model["model_id"],
                model_version=model.get("model_version"),
                deployment_name=deployment,
                request_parameters=effective_request_parameters,
            )

    call_ids = [job["call_id"] for job in ec_jobs + dc_jobs]
    if len(call_ids) != len(set(call_ids)):
        raise InputValidationError(
            "Deterministic call ID collision detected across extraction jobs"
        )

    paths = output_paths(args.output_dir)
    previous_manifest = prepare_output_directory(
        output_dir=args.output_dir,
        paths=paths,
        resume=args.resume,
    )
    source_hashes = {
        "generation_cases": sha256_file(args.generation_cases),
        "generation_input_manifest": sha256_file(args.generation_input_manifest),
        "generated_disclosures": sha256_file(args.generated_disclosures),
        "generation_run_manifest": sha256_file(args.generation_run_manifest),
        "config": sha256_file(args.config),
        "ec_response_schema": sha256_file(schema_paths["ec"]),
        "dc_response_schema": sha256_file(schema_paths["dc"]),
        "ec_prompt": sha256_file(prompt_paths["ec"]),
        "dc_prompt": sha256_file(prompt_paths["dc"]),
    }
    filters = {
        "case_ids": sorted(split_values(args.case_id) or []),
        "company_ids": sorted(split_values(args.company_id) or []),
        "task_ids": sorted(split_values(args.task_id) or []),
        "max_cases": args.max_cases,
        "only": args.only,
    }
    run_fingerprint = sha256_json(
        {
            "source_hashes": source_hashes,
            "filters": filters,
            "selected_generation_case_ids": [
                case["generation_case_id"] for case in selected_cases
            ],
            "model_key": model_key,
            "deployment": deployment,
            "run_id": args.run_id,
        }
    )
    if previous_manifest:
        if previous_manifest.get("run_fingerprint") != run_fingerprint:
            raise InputValidationError(
                "Cannot resume because inputs, filters, prompts, schema, model, or "
                "deployment differ from the existing run manifest"
            )
        if previous_manifest.get("dry_run"):
            raise InputValidationError("A dry run cannot be resumed as a live run")

    started_at = (
        previous_manifest.get("started_at_utc") if previous_manifest else utc_now()
    )
    manifest: dict[str, Any] = {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "script_version": SCRIPT_VERSION,
        "run_id": args.run_id,
        "run_status": "dry_run" if args.dry_run else "running",
        "run_fingerprint": run_fingerprint,
        "dry_run": args.dry_run,
        "resumed": args.resume,
        "started_at_utc": started_at,
        "updated_at_utc": utc_now(),
        "completed_at_utc": None,
        "inputs": {
            "generation_cases": str(args.generation_cases),
            "generation_input_manifest": str(args.generation_input_manifest),
            "generated_disclosures": str(args.generated_disclosures),
            "generation_run_manifest": str(args.generation_run_manifest),
            "source_generation_input_schema": input_manifest.get("schema_version"),
            "source_generation_run_schema": source_run_manifest.get("schema_version"),
        },
        "source_hashes": source_hashes,
        "filters": filters,
        "selection_counts": selection_counts,
        "model": {
            "model_key": model_key,
            "model_id": model.get("model_id"),
            "model_version": model.get("model_version"),
            "deployment_name": deployment,
            "provider": model.get("provider"),
            "api_style": model.get("api_style"),
            "base_url": base_url,
            "request_parameters": model.get("request_parameters"),
            "task_request_parameters": model.get("task_request_parameters"),
        },
        "prompts": {
            task: {
                "path": str(prompt_paths[task]),
                "version": config["prompts"][task]["version"],
                "sha256": config["prompts"][task]["sha256"],
            }
            for task in ("ec", "dc")
        },
        "response_schemas": {
            task: {
                "path": str(schema_paths[task]),
                "version": config["response_schemas"][task]["version"],
                "sha256": config["response_schemas"][task]["sha256"],
                "strict": config["response_schemas"][task].get("strict"),
            }
            for task in ("ec", "dc")
        },
        "planned_jobs": {"ec": len(ec_jobs), "dc": len(dc_jobs)},
        "runtime_controls": {
            "request_delay_seconds": args.request_delay_seconds,
            "progress_interval_seconds": args.progress_interval_seconds,
        },
        "output_processing_mode": output_processing_mode,
        "outputs": {key: str(path) for key, path in paths.items()},
    }
    write_json(paths["manifest"], manifest)

    if args.dry_run:
        for key in ("ec_calls", "dc_calls", "ec_occurrences", "dc_occurrences", "failures"):
            write_jsonl(paths[key], [])
        quality = make_quality_summary(
            selection_counts=selection_counts,
            ec_jobs=ec_jobs,
            dc_jobs=dc_jobs,
            latest_calls={},
            all_call_records=[],
            ec_occurrences=[],
            dc_occurrences=[],
            dry_run=True,
        )
        write_json(paths["quality"], quality)
        manifest["run_status"] = "dry_run_complete"
        manifest["updated_at_utc"] = utc_now()
        manifest["completed_at_utc"] = manifest["updated_at_utc"]
        manifest["quality_summary"] = quality
        write_json(paths["manifest"], manifest)
        print("Dry run complete.")
        print(f"Selected cases: {len(selected_cases)}")
        print(f"Planned EC calls: {len(ec_jobs)}")
        print(f"Planned DC calls: {len(dc_jobs)}")
        print(f"Manifest: {paths['manifest']}")
        return

    if base_url is None:
        raise InputValidationError("Live run requires a normalized Azure base URL")
    client = make_client(config=config, model=model, base_url=base_url)
    latest_calls, all_call_records = load_latest_call_records(paths)
    jobs = ec_jobs + dc_jobs
    total_jobs = len(jobs)
    skipped_jobs = sum(
        should_skip_on_resume(latest_calls.get(job["call_id"]))
        for job in jobs
    )
    live_jobs_total = total_jobs - skipped_jobs
    live_jobs_completed = 0
    completed_durations: list[float] = []
    run_started_monotonic = time.monotonic()
    print("")
    print(
        f"Run plan: {total_jobs} jobs total | {skipped_jobs} resume-skipped | "
        f"{live_jobs_total} API calls this run",
        flush=True,
    )
    if args.progress_interval_seconds:
        print(
            f"Progress heartbeat: every {args.progress_interval_seconds:g}s while waiting",
            flush=True,
        )
    try:
        for index, job in enumerate(jobs, start=1):
            previous = latest_calls.get(job["call_id"])
            if should_skip_on_resume(previous):
                print(
                    f"[{index}/{total_jobs}] {job['task']} {job['call_id']} (resume skip)",
                    flush=True,
                )
                continue
            call_number = live_jobs_completed + 1
            average_duration = (
                sum(completed_durations) / len(completed_durations)
                if completed_durations
                else None
            )
            estimated_remaining = (
                average_duration * (live_jobs_total - live_jobs_completed)
                + args.request_delay_seconds
                * max(0, live_jobs_total - live_jobs_completed - 1)
                if average_duration is not None
                else None
            )
            eta_text = (
                f" | estimated remaining {format_duration(estimated_remaining)}"
                if estimated_remaining is not None
                else " | estimated remaining available after first call"
            )
            progress_label = (
                f"[{index}/{total_jobs} | call {call_number}/{live_jobs_total}] "
                f"{job['task']} {job['call_id']}"
            )
            print(
                f"{progress_label} started | run elapsed "
                f"{format_duration(time.monotonic() - run_started_monotonic)}{eta_text}",
                flush=True,
            )
            call_started_monotonic = time.monotonic()
            heartbeat = start_progress_heartbeat(
                label=progress_label,
                interval_seconds=args.progress_interval_seconds,
                call_started=call_started_monotonic,
                run_started=run_started_monotonic,
            )
            try:
                record = execute_job(
                    job=job,
                    client=client,
                    deployment=deployment,
                    prompt_text=prompt_texts[job["task"]],
                    schema=schemas[job["task"]],
                    schema_spec=config["response_schemas"][job["task"]],
                    model_key=model_key,
                    model=model,
                    config=config,
                )
            finally:
                stop_progress_heartbeat(heartbeat)
            call_duration = time.monotonic() - call_started_monotonic
            completed_durations.append(call_duration)
            live_jobs_completed += 1
            call_path = paths["ec_calls"] if job["task"] == "ec" else paths["dc_calls"]
            append_jsonl(call_path, record)
            latest_calls[job["call_id"]] = record
            all_call_records.append(record)
            if record["call_status"] != "success":
                append_jsonl(
                    paths["failures"],
                    {
                        "schema_version": "generation_claim_extraction_failure_v1",
                        "timestamp_utc": utc_now(),
                        "call_id": job["call_id"],
                        "task": job["task"],
                        "call_status": record["call_status"],
                        "job_summary": record["job_summary"],
                        "validation_error": record.get("validation_error"),
                        "error_type": record.get("error_type"),
                        "error_message": record.get("error_message"),
                        "http_status": record.get("http_status"),
                    },
                )
            validated_output = record.get("validated_output") or {}
            if job["task"] == "ec":
                claims_extracted = sum(
                    len(result.get("claims") or [])
                    for result in validated_output.get("evidence_results") or []
                )
            else:
                claims_extracted = len(validated_output.get("claims") or [])
            usage = record.get("usage") or {}
            average_duration = sum(completed_durations) / len(completed_durations)
            remaining_jobs = live_jobs_total - live_jobs_completed
            estimated_remaining = (
                average_duration * remaining_jobs
                + args.request_delay_seconds * remaining_jobs
            )
            print(
                f"{progress_label} finished: {record['call_status']} "
                f"| call {format_duration(call_duration)} "
                f"| claims {claims_extracted} "
                f"| tokens in/out {usage.get('input_tokens')}/{usage.get('output_tokens')} "
                f"| run elapsed {format_duration(time.monotonic() - run_started_monotonic)} "
                f"| estimated remaining {format_duration(estimated_remaining)}",
                flush=True,
            )
            if args.request_delay_seconds and remaining_jobs > 0:
                print(
                    f"Rate-limit delay: {args.request_delay_seconds:g}s",
                    flush=True,
                )
                time.sleep(args.request_delay_seconds)
    except KeyboardInterrupt:
        manifest["run_status"] = "interrupted"
        manifest["updated_at_utc"] = utc_now()
        write_json(paths["manifest"], manifest)
        raise

    successful_calls = {
        call_id: record
        for call_id, record in latest_calls.items()
        if record.get("call_status") == "success"
    }
    use_parsed_output = output_processing_mode == "schema_only"
    ec_occurrences = make_ec_occurrences(
        ec_jobs, successful_calls, use_parsed_output=use_parsed_output
    )
    dc_occurrences = make_dc_occurrences(
        dc_jobs, successful_calls, use_parsed_output=use_parsed_output
    )
    write_jsonl(paths["ec_occurrences"], ec_occurrences)
    write_jsonl(paths["dc_occurrences"], dc_occurrences)
    unresolved_failures = []
    for job in jobs:
        record = latest_calls.get(job["call_id"])
        if not record or record.get("call_status") == "success":
            continue
        unresolved_failures.append(
            {
                "schema_version": "generation_claim_extraction_failure_v1",
                "timestamp_utc": utc_now(),
                "call_id": job["call_id"],
                "task": job["task"],
                "call_status": record.get("call_status"),
                "job_summary": record.get("job_summary"),
                "validation_error": record.get("validation_error"),
                "error_type": record.get("error_type"),
                "error_message": record.get("error_message"),
                "http_status": record.get("http_status"),
            }
        )
    write_jsonl(paths["failures"], unresolved_failures)
    if not paths["ec_calls"].exists():
        write_jsonl(paths["ec_calls"], [])
    if not paths["dc_calls"].exists():
        write_jsonl(paths["dc_calls"], [])

    quality = make_quality_summary(
        selection_counts=selection_counts,
        ec_jobs=ec_jobs,
        dc_jobs=dc_jobs,
        latest_calls=latest_calls,
        all_call_records=all_call_records,
        ec_occurrences=ec_occurrences,
        dc_occurrences=dc_occurrences,
        dry_run=False,
    )
    write_json(paths["quality"], quality)
    incomplete = any(
        quality["task_counts"][task]["calls_success"]
        != quality["task_counts"][task]["jobs_planned"]
        for task in ("ec", "dc")
    )
    manifest["run_status"] = "complete_with_failures" if incomplete else "complete"
    manifest["updated_at_utc"] = utc_now()
    manifest["completed_at_utc"] = manifest["updated_at_utc"]
    manifest["quality_summary"] = quality
    write_json(paths["manifest"], manifest)

    print("")
    print(f"Run status: {manifest['run_status']}")
    print(f"EC occurrences: {len(ec_occurrences)}")
    print(f"DC occurrences: {len(dc_occurrences)}")
    print(f"Quality summary: {paths['quality']}")
    print(f"Run manifest: {paths['manifest']}")


if __name__ == "__main__":
    main()
