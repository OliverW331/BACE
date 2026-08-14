#!/usr/bin/env python3
"""Semantically deduplicate EC/DC claim occurrences within generation cases.

The script performs conservative exact-normalized grouping first, then asks one
LLM call per case and claim kind to partition the remaining claim units by
semantic equivalence. The LLM may only select existing unit IDs; canonical claim
text and all provenance are materialized deterministically from the inputs.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from dotenv import load_dotenv

from generation_claims import (
    InputValidationError,
    OutputValidationError,
    append_jsonl,
    canonical_json,
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


REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env", override=False)

SCRIPT_VERSION = "run_generation_claim_semantic_dedup_v1"
CONFIG_SCHEMA_VERSION = "generation_claim_semantic_dedup_config_v1"
RUN_MANIFEST_SCHEMA_VERSION = "generation_claim_semantic_dedup_run_manifest_v1"
QUALITY_SUMMARY_SCHEMA_VERSION = "generation_claim_semantic_dedup_quality_summary_v1"
CALL_SCHEMA_VERSION = "generation_claim_semantic_dedup_call_v1"
EC_OUTPUT_SCHEMA_VERSION = "deduplicated_ec_claim_v1"
DC_OUTPUT_SCHEMA_VERSION = "deduplicated_dc_claim_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Semantically deduplicate EC/DC claim occurrences within each generation case."
    )
    parser.add_argument("--ec-occurrences", type=Path, default=None)
    parser.add_argument("--dc-occurrences", type=Path, default=None)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "config/evaluation/configs/generation_claim_semantic_dedup_config.json"
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="claim_semantic_dedup_run")
    parser.add_argument("--model-key", default=None)
    parser.add_argument("--only", choices=["both", "ec", "dc"], default="both")
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--max-cases", type=int, default=None)
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


def start_progress_heartbeat(
    *, label: str, interval_seconds: float, call_started: float, run_started: float
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


def normalize_claim_text(text: str) -> str:
    """Conservative deterministic normalization before semantic deduplication."""
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def load_and_validate_configuration(
    config_path: Path,
) -> tuple[dict[str, Any], str, Path, dict[str, Any], Path]:
    require_file(config_path, "semantic dedup config")
    config = read_json(config_path)
    if config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise InputValidationError(
            f"Unsupported semantic dedup config schema: {config.get('schema_version')!r}"
        )

    config_dir = config_path.parent
    prompt_spec = config.get("prompt")
    if not isinstance(prompt_spec, dict):
        raise InputValidationError("Missing semantic dedup prompt configuration")
    prompt_path = config_dir / str(prompt_spec.get("file") or "")
    require_file(prompt_path, "semantic dedup prompt")
    validate_file_hash(prompt_path, prompt_spec.get("sha256"), "semantic dedup prompt")
    prompt_text = prompt_path.read_text(encoding="utf-8")

    schema_spec = config.get("response_schema")
    if not isinstance(schema_spec, dict):
        raise InputValidationError("Missing semantic dedup response_schema configuration")
    schema_path = config_dir / str(schema_spec.get("file") or "")
    require_file(schema_path, "semantic dedup response schema")
    validate_file_hash(
        schema_path,
        schema_spec.get("sha256"),
        "semantic dedup response schema",
    )
    schema = read_json(schema_path)
    if schema.get("$id") != schema_spec.get("version"):
        raise InputValidationError(
            "Semantic dedup response schema $id does not match configured version"
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
        raise InputValidationError(f"Unknown semantic dedup model key: {model_key!r}")
    model = models[model_key]
    if model.get("provider") != "azure_openai" or model.get("api_style") != "responses":
        raise InputValidationError(
            "Semantic dedup currently requires an Azure OpenAI Responses API model"
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
        raise InputValidationError("The openai package is required for live dedup calls") from exc
    runtime = config.get("runtime") or {}
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=float(runtime.get("request_timeout_seconds", 600)),
        max_retries=0,
    )


def validate_occurrences(rows: list[dict[str, Any]], kind: str, path: Path) -> None:
    expected_schema = "ec_claim_occurrence_v1" if kind == "ec" else "dc_claim_occurrence_v1"
    occurrence_key = "ec_occurrence_id" if kind == "ec" else "dc_occurrence_id"
    seen_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=1):
        label = f"{kind.upper()} occurrence {path}:{row_number}"
        if row.get("schema_version") != expected_schema:
            raise InputValidationError(
                f"{label} has unsupported schema {row.get('schema_version')!r}"
            )
        required = {
            "generation_case_id",
            "case_id",
            occurrence_key,
            "claim_text",
            "source_spans",
            "context_resolutions",
        }
        if kind == "ec":
            required.update({"evidence_id", "evidence_provenance"})
        else:
            required.update({"generation_output_id", "generated_text_hash"})
        missing = sorted(required - set(row))
        if missing:
            raise InputValidationError(f"{label} is missing required fields: {missing}")
        occurrence_id = row.get(occurrence_key)
        if not isinstance(occurrence_id, str) or not occurrence_id:
            raise InputValidationError(f"{label}.{occurrence_key} must be non-empty")
        if occurrence_id in seen_ids:
            raise InputValidationError(f"Duplicate {occurrence_key}: {occurrence_id}")
        seen_ids.add(occurrence_id)
        if not isinstance(row.get("claim_text"), str) or not row["claim_text"].strip():
            raise InputValidationError(f"{label}.claim_text must be non-empty")
        if not isinstance(row.get("source_spans"), list) or not row["source_spans"]:
            raise InputValidationError(f"{label}.source_spans must be a non-empty array")
        if not isinstance(row.get("context_resolutions"), list):
            raise InputValidationError(f"{label}.context_resolutions must be an array")


def selected_case_ids(
    rows_by_kind: dict[str, list[dict[str, Any]]],
    *,
    requested: set[str] | None,
    max_cases: int | None,
    only: str,
) -> list[str]:
    case_sets = {
        kind: {str(row["generation_case_id"]) for row in rows}
        for kind, rows in rows_by_kind.items()
    }
    if only == "both" and case_sets.get("ec") != case_sets.get("dc"):
        ec_only = sorted(case_sets.get("ec", set()) - case_sets.get("dc", set()))
        dc_only = sorted(case_sets.get("dc", set()) - case_sets.get("ec", set()))
        raise InputValidationError(
            "EC and DC occurrence files must contain the same generation cases for "
            f"--only both; EC-only={ec_only[:5]}, DC-only={dc_only[:5]}"
        )
    available: set[str] = set()
    for values in case_sets.values():
        available.update(values)
    if requested:
        unknown = sorted(requested - available)
        if unknown:
            raise InputValidationError(f"Requested generation case IDs not found: {unknown}")
        available.intersection_update(requested)
    selected = sorted(available)
    if max_cases is not None:
        if max_cases < 1:
            raise InputValidationError("--max-cases must be at least 1")
        selected = selected[:max_cases]
    if not selected:
        raise InputValidationError("No claim occurrences match the selected generation cases")
    return selected


def representative_sort_key(row: dict[str, Any], occurrence_key: str) -> tuple[Any, ...]:
    text = str(row["claim_text"])
    return (-len(text), text.casefold(), text, str(row[occurrence_key]))


def make_exact_units(
    rows: list[dict[str, Any]], *, kind: str, generation_case_id: str
) -> list[dict[str, Any]]:
    occurrence_key = "ec_occurrence_id" if kind == "ec" else "dc_occurrence_id"
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["generation_case_id"] != generation_case_id:
            continue
        grouped[normalize_claim_text(row["claim_text"])].append(row)

    units: list[dict[str, Any]] = []
    for normalized_text, members in grouped.items():
        members.sort(key=lambda row: representative_sort_key(row, occurrence_key))
        representative = members[0]
        occurrence_ids = sorted(str(row[occurrence_key]) for row in members)
        unit_id = f"{kind}u_{sha256_json({'case': generation_case_id, 'text': normalized_text})[:32]}"
        units.append(
            {
                "unit_id": unit_id,
                "claim_text": representative["claim_text"],
                "normalized_claim_text": normalized_text,
                "representative_occurrence_id": representative[occurrence_key],
                "occurrence_ids": occurrence_ids,
                "occurrence_count": len(occurrence_ids),
            }
        )
    units.sort(key=lambda unit: (normalize_claim_text(unit["claim_text"]), unit["unit_id"]))
    return units


def build_jobs(
    *,
    rows_by_kind: dict[str, list[dict[str, Any]]],
    case_ids: list[str],
    config: dict[str, Any],
    prompt_spec: dict[str, Any],
    schema_spec: dict[str, Any],
    model_key: str,
    model: dict[str, Any],
    deployment: str,
) -> list[dict[str, Any]]:
    max_units = int(
        (config.get("deduplication") or {}).get(
            "max_claim_units_per_case_and_kind", 400
        )
    )
    request_parameters = dict(model.get("request_parameters") or {})
    jobs: list[dict[str, Any]] = []
    for generation_case_id in case_ids:
        for kind in ("ec", "dc"):
            if kind not in rows_by_kind:
                continue
            units = make_exact_units(
                rows_by_kind[kind],
                kind=kind,
                generation_case_id=generation_case_id,
            )
            if not units:
                raise InputValidationError(
                    f"No {kind.upper()} occurrences for generation case {generation_case_id}"
                )
            if len(units) > max_units:
                raise InputValidationError(
                    f"{generation_case_id} has {len(units)} {kind.upper()} claim units; "
                    f"configured maximum is {max_units}. Refusing to split the set because "
                    "cross-batch duplicates could be missed."
                )
            dynamic_input = {
                "claim_units": [
                    {
                        "unit_id": unit["unit_id"],
                        "claim_text": unit["claim_text"],
                    }
                    for unit in units
                ],
            }
            job_input_hash = sha256_json(dynamic_input)
            call_identity = {
                "claim_kind": kind,
                "generation_case_id": generation_case_id,
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
            prefix = "ecdup" if kind == "ec" else "dcdup"
            jobs.append(
                {
                    "claim_kind": kind,
                    "generation_case_id": generation_case_id,
                    "units": units,
                    "dynamic_input": dynamic_input,
                    "job_input_hash": job_input_hash,
                    "call_identity": call_identity,
                    "call_id": f"{prefix}_{sha256_json(call_identity)[:32]}",
                    "request_parameters": request_parameters,
                    "requires_model": len(units) > 1,
                }
            )
    jobs.sort(key=lambda job: (job["generation_case_id"], job["claim_kind"]))
    return jobs


def validate_partition_response(
    payload: Any, *, expected_unit_ids: Iterable[str]
) -> dict[str, Any]:
    expected = set(expected_unit_ids)
    if not isinstance(payload, dict) or set(payload) != {"groups"}:
        raise OutputValidationError("Response root must contain exactly the groups field")
    groups = payload["groups"]
    if not isinstance(groups, list) or not groups:
        raise OutputValidationError("groups must be a non-empty array")

    seen: set[str] = set()
    validated_groups: list[dict[str, Any]] = []
    for index, group in enumerate(groups, start=1):
        if not isinstance(group, dict) or set(group) != {
            "canonical_unit_id",
            "member_unit_ids",
        }:
            raise OutputValidationError(
                f"Group {index} must contain exactly canonical_unit_id and member_unit_ids"
            )
        canonical_unit_id = group["canonical_unit_id"]
        member_unit_ids = group["member_unit_ids"]
        if not isinstance(canonical_unit_id, str) or not canonical_unit_id:
            raise OutputValidationError(f"Group {index} canonical_unit_id must be non-empty")
        if not isinstance(member_unit_ids, list) or not member_unit_ids:
            raise OutputValidationError(f"Group {index} member_unit_ids must be non-empty")
        if any(not isinstance(unit_id, str) or not unit_id for unit_id in member_unit_ids):
            raise OutputValidationError(f"Group {index} contains an invalid unit ID")
        if len(member_unit_ids) != len(set(member_unit_ids)):
            raise OutputValidationError(f"Group {index} repeats a member unit ID")
        members = set(member_unit_ids)
        if canonical_unit_id not in members:
            raise OutputValidationError(
                f"Group {index} canonical_unit_id is not one of its members"
            )
        unknown = sorted(members - expected)
        if unknown:
            raise OutputValidationError(f"Group {index} contains unknown unit IDs: {unknown}")
        repeated = sorted(members & seen)
        if repeated:
            raise OutputValidationError(f"Unit IDs occur in multiple groups: {repeated}")
        seen.update(members)
        validated_groups.append(
            {
                "canonical_unit_id": canonical_unit_id,
                "member_unit_ids": sorted(members),
            }
        )
    missing = sorted(expected - seen)
    if missing:
        raise OutputValidationError(f"Partition omitted unit IDs: {missing}")
    validated_groups.sort(
        key=lambda group: (group["member_unit_ids"][0], group["canonical_unit_id"])
    )
    return {"groups": validated_groups}


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


def usage_sum(values: Iterable[dict[str, int | None]]) -> dict[str, int | None]:
    values = list(values)
    result: dict[str, int | None] = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        numbers = [value.get(key) for value in values]
        integers = [number for number in numbers if isinstance(number, int)]
        result[key] = sum(integers) if integers else None
    return result


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
    expected_unit_ids = [unit["unit_id"] for unit in job["units"]]
    common = {
        "schema_version": CALL_SCHEMA_VERSION,
        "call_id": job["call_id"],
        "claim_kind": job["claim_kind"],
        "generation_case_id": job["generation_case_id"],
        "call_identity": job["call_identity"],
        "dynamic_input": job["dynamic_input"],
        "model_key": model_key,
        "model_id": model.get("model_id"),
        "model_version": model.get("model_version"),
        "deployment_name": deployment,
        "request_parameters": job["request_parameters"],
        "started_at_utc": utc_now(),
    }

    if not job["requires_model"]:
        validated = {
            "groups": [
                {
                    "canonical_unit_id": expected_unit_ids[0],
                    "member_unit_ids": expected_unit_ids,
                }
            ]
        }
        return {
            **common,
            "finished_at_utc": utc_now(),
            "call_status": "success",
            "model_called": False,
            "attempts": [],
            "raw_output": "",
            "parsed_output": validated,
            "validated_output": validated,
            "output_valid": True,
            "validation_error": None,
            "error_type": None,
            "error_message": None,
            "http_status": None,
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        }

    base_messages = [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": canonical_json(job["dynamic_input"])},
    ]
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
        messages = list(base_messages)
        if last_validation_error:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "The previous response failed deterministic partition validation: "
                        f"{last_validation_error}. Recompute and return a complete corrected "
                        "partition of every supplied unit_id exactly once."
                    ),
                }
            )
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
                    "http_status": get_status_code(error),
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
                "output_valid": False,
                "validation_error": last_validation_error,
                "error_type": type(error).__name__,
                "error_message": str(error)[:4000],
                "http_status": get_status_code(error),
                "usage": usage_sum(attempt["usage"] for attempt in attempts),
            }

        api_response = serialize_sdk_response(response)
        usage = extract_usage(api_response)
        last_raw = getattr(response, "output_text", None) or ""
        last_parsed = None
        validated: dict[str, Any] | None = None
        try:
            last_parsed = json.loads(last_raw)
            validated = validate_partition_response(
                last_parsed,
                expected_unit_ids=expected_unit_ids,
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
        if validated is not None:
            return {
                **common,
                "finished_at_utc": utc_now(),
                "call_status": "success",
                "model_called": True,
                "attempts": attempts,
                "raw_output": last_raw,
                "parsed_output": last_parsed,
                "validated_output": validated,
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
        "output_valid": False,
        "validation_error": last_validation_error,
        "error_type": None,
        "error_message": None,
        "http_status": None,
        "usage": usage_sum(attempt["usage"] for attempt in attempts),
    }


def make_semantic_claim_records(
    *,
    job: dict[str, Any],
    validated_output: dict[str, Any],
    occurrence_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    kind = job["claim_kind"]
    occurrence_key = "ec_occurrence_id" if kind == "ec" else "dc_occurrence_id"
    occurrence_by_id = {str(row[occurrence_key]): row for row in occurrence_rows}
    unit_by_id = {unit["unit_id"]: unit for unit in job["units"]}
    records: list[dict[str, Any]] = []

    for group in validated_output["groups"]:
        member_units = [unit_by_id[unit_id] for unit_id in group["member_unit_ids"]]
        canonical_unit = unit_by_id[group["canonical_unit_id"]]
        occurrence_ids = sorted(
            occurrence_id
            for unit in member_units
            for occurrence_id in unit["occurrence_ids"]
        )
        occurrences = [occurrence_by_id[occurrence_id] for occurrence_id in occurrence_ids]
        case_ids = {str(row["case_id"]) for row in occurrences}
        if len(case_ids) != 1:
            raise InputValidationError(
                f"Dedup group spans multiple case_id values: {sorted(case_ids)}"
            )
        merge_type = "singleton"
        if len(member_units) > 1:
            merge_type = "semantic_merge"
        elif len(occurrence_ids) > 1:
            merge_type = "exact_normalized_merge"
        dedup_metadata = {
            "call_id": job["call_id"],
            "merge_type": merge_type,
            "canonical_unit_id": canonical_unit["unit_id"],
            "canonical_occurrence_id": canonical_unit["representative_occurrence_id"],
            "member_unit_ids": sorted(unit["unit_id"] for unit in member_units),
            "member_occurrence_ids": occurrence_ids,
        }

        if kind == "ec":
            ec_id = f"ec_{sha256_json({'case': job['generation_case_id'], 'occurrences': occurrence_ids})[:32]}"
            provenance = [
                {
                    "ec_occurrence_id": row["ec_occurrence_id"],
                    "claim_text": row["claim_text"],
                    "evidence_id": row["evidence_id"],
                    "prompt_label": row.get("prompt_label"),
                    "retrieval_text_hash": row.get("retrieval_text_hash"),
                    "source_spans": row["source_spans"],
                    "context_resolutions": row["context_resolutions"],
                    "evidence_provenance": row["evidence_provenance"],
                }
                for row in occurrences
            ]
            records.append(
                {
                    "schema_version": EC_OUTPUT_SCHEMA_VERSION,
                    "generation_case_id": job["generation_case_id"],
                    "case_id": next(iter(case_ids)),
                    "ec_id": ec_id,
                    "ec_text": canonical_unit["claim_text"],
                    "evidence_card_ids": sorted({str(row["evidence_id"]) for row in occurrences}),
                    "ec_occurrence_ids": occurrence_ids,
                    "ec_provenance": provenance,
                    "supported_dc_ids": [],
                    "semantic_dedup": dedup_metadata,
                }
            )
        else:
            output_ids = {str(row["generation_output_id"]) for row in occurrences}
            if len(output_ids) != 1:
                raise InputValidationError(
                    "A deduplicated DC group spans multiple generated disclosures"
                )
            dc_id = f"dc_{sha256_json({'case': job['generation_case_id'], 'occurrences': occurrence_ids})[:32]}"
            provenance = [
                {
                    "dc_occurrence_id": row["dc_occurrence_id"],
                    "claim_text": row["claim_text"],
                    "generation_output_id": row["generation_output_id"],
                    "generated_text_hash": row["generated_text_hash"],
                    "source_spans": row["source_spans"],
                    "context_resolutions": row["context_resolutions"],
                }
                for row in occurrences
            ]
            records.append(
                {
                    "schema_version": DC_OUTPUT_SCHEMA_VERSION,
                    "generation_case_id": job["generation_case_id"],
                    "case_id": next(iter(case_ids)),
                    "generated_disclosure_id": next(iter(output_ids)),
                    "dc_id": dc_id,
                    "dc_text": canonical_unit["claim_text"],
                    "dc_occurrence_ids": occurrence_ids,
                    "dc_provenance": provenance,
                    "candidate_ec_ids": [],
                    "supporting_ec_ids": [],
                    "support_structure": None,
                    "support_verdict": None,
                    "unsupported_tags": [],
                    "rationale": None,
                    "semantic_dedup": dedup_metadata,
                }
            )
    text_key = "ec_text" if kind == "ec" else "dc_text"
    id_key = "ec_id" if kind == "ec" else "dc_id"
    records.sort(key=lambda row: (normalize_claim_text(row[text_key]), row[id_key]))
    return records


def output_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "calls": output_dir / "semantic_dedup_calls.jsonl",
        "failures": output_dir / "semantic_dedup_failures.jsonl",
        "ec_claims": output_dir / "ec_claims.jsonl",
        "dc_claims": output_dir / "dc_claims.jsonl",
        "quality": output_dir / "quality_summary.json",
        "manifest": output_dir / "semantic_dedup_run_manifest.json",
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


def load_call_records(path: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    latest: dict[str, dict[str, Any]] = {}
    all_records: list[dict[str, Any]] = []
    if not path.is_file():
        return latest, all_records
    for record in read_jsonl(path):
        call_id = record.get("call_id")
        if not isinstance(call_id, str) or not call_id:
            raise InputValidationError(f"Call record without call_id in {path}")
        latest[call_id] = record
        all_records.append(record)
    return latest, all_records


def make_quality_summary(
    *,
    rows_by_kind: dict[str, list[dict[str, Any]]],
    selected_cases: list[str],
    jobs: list[dict[str, Any]],
    latest_calls: dict[str, dict[str, Any]],
    all_call_records: list[dict[str, Any]],
    ec_claims: list[dict[str, Any]],
    dc_claims: list[dict[str, Any]],
    dry_run: bool,
) -> dict[str, Any]:
    claims_by_kind = {"ec": ec_claims, "dc": dc_claims}
    kind_counts: dict[str, dict[str, Any]] = {}
    selected_case_set = set(selected_cases)
    for kind in ("ec", "dc"):
        kind_jobs = [job for job in jobs if job["claim_kind"] == kind]
        rows = [
            row
            for row in rows_by_kind.get(kind, [])
            if row["generation_case_id"] in selected_case_set
        ]
        exact_units = sum(len(job["units"]) for job in kind_jobs)
        semantic_claims = len(claims_by_kind[kind]) if not dry_run else None
        records = [
            latest_calls[job["call_id"]]
            for job in kind_jobs
            if job["call_id"] in latest_calls
        ]
        semantic_merges = (
            sum(
                claim["semantic_dedup"]["merge_type"] == "semantic_merge"
                for claim in claims_by_kind[kind]
            )
            if not dry_run
            else None
        )
        kind_counts[kind] = {
            "occurrences": len(rows),
            "exact_normalized_units": exact_units,
            "exact_normalized_reduction": len(rows) - exact_units,
            "deduplicated_claims": semantic_claims,
            "semantic_reduction": (
                exact_units - int(semantic_claims) if semantic_claims is not None else None
            ),
            "semantic_merge_groups": semantic_merges,
            "jobs_planned": len(kind_jobs),
            "calls_recorded": len(records),
            "calls_success": sum(record.get("call_status") == "success" for record in records),
            "calls_invalid_output": sum(
                record.get("call_status") == "invalid_output" for record in records
            ),
            "calls_api_error": sum(
                record.get("call_status") == "api_error" for record in records
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
        "generation_case_count": len(selected_cases),
        "claim_counts": kind_counts,
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
    required_kinds = ("ec", "dc") if args.only == "both" else (args.only,)
    input_paths = {"ec": args.ec_occurrences, "dc": args.dc_occurrences}
    for kind in required_kinds:
        path = input_paths[kind]
        if path is None:
            raise InputValidationError(f"--{kind}-occurrences is required for --only {args.only}")
        require_file(path, f"{kind.upper()} claim occurrences")

    config, prompt_text, prompt_path, schema, schema_path = (
        load_and_validate_configuration(args.config)
    )
    model_key, model, deployment, base_url = resolve_model(
        config,
        model_key_override=args.model_key,
        dry_run=args.dry_run,
    )
    rows_by_kind: dict[str, list[dict[str, Any]]] = {}
    for kind in required_kinds:
        path = input_paths[kind]
        assert path is not None
        rows = read_jsonl(path)
        validate_occurrences(rows, kind, path)
        rows_by_kind[kind] = rows

    cases = selected_case_ids(
        rows_by_kind,
        requested=split_values(args.case_id),
        max_cases=args.max_cases,
        only=args.only,
    )
    prompt_spec = config["prompt"]
    schema_spec = config["response_schema"]
    jobs = build_jobs(
        rows_by_kind=rows_by_kind,
        case_ids=cases,
        config=config,
        prompt_spec=prompt_spec,
        schema_spec=schema_spec,
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
    input_manifest = {
        kind: {
            "path": str(input_paths[kind]),
            "sha256": sha256_file(input_paths[kind]),
        }
        for kind in required_kinds
        if input_paths[kind] is not None
    }
    run_identity = {
        "script_version": SCRIPT_VERSION,
        "inputs": input_manifest,
        "config_path": str(args.config),
        "config_sha256": sha256_file(args.config),
        "prompt_sha256": sha256_file(prompt_path),
        "schema_sha256": sha256_file(schema_path),
        "only": args.only,
        "selected_generation_case_ids": cases,
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
        "planned_jobs": {
            "ec": sum(job["claim_kind"] == "ec" for job in jobs),
            "dc": sum(job["claim_kind"] == "dc" for job in jobs),
        },
        "planned_model_calls": sum(job["requires_model"] for job in jobs),
        "outputs": {key: str(path) for key, path in paths.items()},
    }
    write_json(paths["manifest"], manifest)

    latest_calls, all_call_records = load_call_records(paths["calls"])
    if args.dry_run:
        write_jsonl(paths["calls"], [])
        write_jsonl(paths["failures"], [])
        write_jsonl(paths["ec_claims"], [])
        write_jsonl(paths["dc_claims"], [])
        summary = make_quality_summary(
            rows_by_kind=rows_by_kind,
            selected_cases=cases,
            jobs=jobs,
            latest_calls={},
            all_call_records=[],
            ec_claims=[],
            dc_claims=[],
            dry_run=True,
        )
        write_json(paths["quality"], summary)
        manifest["completed_at_utc"] = utc_now()
        write_json(paths["manifest"], manifest)
        print("Dry run complete.")
        print(f"Selected generation cases: {len(cases)}")
        print(
            "Exact-normalized units: "
            f"EC={summary['claim_counts']['ec']['exact_normalized_units']} "
            f"DC={summary['claim_counts']['dc']['exact_normalized_units']}"
        )
        print(f"Planned model calls: {manifest['planned_model_calls']}")
        print(f"Run manifest: {paths['manifest']}")
        return

    client = make_client(config=config, model=model, base_url=str(base_url))
    pending_jobs = [
        job
        for job in jobs
        if latest_calls.get(job["call_id"], {}).get("call_status") != "success"
    ]
    print(
        f"Run plan: {len(jobs)} jobs total | {len(jobs) - len(pending_jobs)} "
        f"resume-skipped | {len(pending_jobs)} jobs this run",
        flush=True,
    )
    run_started = time.monotonic()
    for index, job in enumerate(pending_jobs, start=1):
        label = (
            f"[{index}/{len(pending_jobs)}] {job['claim_kind']} "
            f"{job['generation_case_id']} ({len(job['units'])} units)"
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
                schema_spec=schema_spec,
                model_key=model_key,
                model=model,
                config=config,
            )
        finally:
            stop_progress_heartbeat(heartbeat)
        append_jsonl(paths["calls"], record)
        latest_calls[job["call_id"]] = record
        all_call_records.append(record)
        group_count = len((record.get("validated_output") or {}).get("groups") or [])
        usage = record.get("usage") or {}
        print(
            f"{label} finished: {record['call_status']} | groups {group_count} | "
            f"tokens {usage.get('input_tokens')}/{usage.get('output_tokens')} | "
            f"elapsed {format_duration(time.monotonic() - call_started)}",
            flush=True,
        )
        if args.request_delay_seconds and index < len(pending_jobs):
            time.sleep(args.request_delay_seconds)

    selected_case_set = set(cases)
    ec_claims: list[dict[str, Any]] = []
    dc_claims: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for job in jobs:
        record = latest_calls.get(job["call_id"])
        if not record or record.get("call_status") != "success":
            failures.append(
                {
                    "schema_version": "generation_claim_semantic_dedup_failure_v1",
                    "call_id": job["call_id"],
                    "claim_kind": job["claim_kind"],
                    "generation_case_id": job["generation_case_id"],
                    "call_status": (record or {}).get("call_status", "missing"),
                    "validation_error": (record or {}).get("validation_error"),
                    "error_type": (record or {}).get("error_type"),
                    "error_message": (record or {}).get("error_message"),
                }
            )
            continue
        occurrence_rows = [
            row
            for row in rows_by_kind[job["claim_kind"]]
            if row["generation_case_id"] in selected_case_set
        ]
        claims = make_semantic_claim_records(
            job=job,
            validated_output=record["validated_output"],
            occurrence_rows=occurrence_rows,
        )
        if job["claim_kind"] == "ec":
            ec_claims.extend(claims)
        else:
            dc_claims.extend(claims)
    ec_claims.sort(key=lambda row: (row["generation_case_id"], row["ec_text"], row["ec_id"]))
    dc_claims.sort(key=lambda row: (row["generation_case_id"], row["dc_text"], row["dc_id"]))
    write_jsonl(paths["ec_claims"], ec_claims)
    write_jsonl(paths["dc_claims"], dc_claims)
    write_jsonl(paths["failures"], failures)

    summary = make_quality_summary(
        rows_by_kind=rows_by_kind,
        selected_cases=cases,
        jobs=jobs,
        latest_calls=latest_calls,
        all_call_records=all_call_records,
        ec_claims=ec_claims,
        dc_claims=dc_claims,
        dry_run=False,
    )
    write_json(paths["quality"], summary)
    manifest["status"] = "complete" if not failures else "complete_with_failures"
    manifest["completed_at_utc"] = utc_now()
    manifest["result_counts"] = {
        "ec_claims": len(ec_claims),
        "dc_claims": len(dc_claims),
        "failures": len(failures),
    }
    write_json(paths["manifest"], manifest)

    print(f"Run status: {manifest['status']}")
    print(f"Deduplicated EC claims: {len(ec_claims)}")
    print(f"Deduplicated DC claims: {len(dc_claims)}")
    print(f"Quality summary: {paths['quality']}")
    print(f"Run manifest: {paths['manifest']}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
