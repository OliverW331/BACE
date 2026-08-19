#!/usr/bin/env python3
"""Diagnose unsupported deduplicated DCs using their candidate EC sets.

The script validates support and candidate-selection results, creates stable
temporary claim IDs, and sends only one unsupported DC, its candidate ECs, and
prompt-visible case context to the configured LLM. Empty candidate sets remain
valid inputs because the DC meaning determines whether the failure is a
non-disclosure statement or unsupported novelty. No provenance is sent to the
model.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

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
    validate_generation_case,
    validate_file_hash,
    write_json,
    write_jsonl,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env", override=False)

SCRIPT_VERSION = "run_generation_claim_unsupported_diagnosis_v1"
CONFIG_SCHEMA_VERSION = "generation_claim_unsupported_diagnosis_config_v1"
CALL_SCHEMA_VERSION = "generation_claim_unsupported_diagnosis_call_v1"
FAILURE_SCHEMA_VERSION = "generation_claim_unsupported_diagnosis_failure_v1"
RUN_MANIFEST_SCHEMA_VERSION = "generation_claim_unsupported_diagnosis_run_manifest_v1"
QUALITY_SUMMARY_SCHEMA_VERSION = "generation_claim_unsupported_diagnosis_quality_summary_v1"
EC_INPUT_SCHEMA_VERSION = "deduplicated_ec_claim_v1"
DC_INPUT_SCHEMA_VERSION = "deduplicated_dc_claim_v1"
UNSUPPORTED_LABELS = (
    "non_disclosure_statement",
    "contradiction",
    "evidence_conflation",
    "factual_boundary_distortion",
    "inferential_inflation",
    "unsupported_novelty",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Assign one exclusive failure label to each unsupported disclosure "
            "claim using its candidate evidence-claim set."
        )
    )
    parser.add_argument("--ec-claims", type=Path, required=True)
    parser.add_argument("--dc-claims", type=Path, required=True)
    parser.add_argument("--candidate-selections", type=Path, required=True)
    parser.add_argument("--support-assessments", type=Path, required=True)
    parser.add_argument("--generation-cases", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "config/evaluation/configs/"
            "generation_claim_unsupported_diagnosis_config.json"
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="generation_claim_unsupported_diagnosis_run")
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


def split_values(values: Sequence[str]) -> set[str] | None:
    parsed: set[str] = set()
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                parsed.add(part)
    return parsed or None


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


def load_and_validate_configuration(
    config_path: Path,
) -> tuple[dict[str, Any], str, Path, dict[str, Any], Path]:
    require_file(config_path, "unsupported diagnosis config")
    config = read_json(config_path)
    if config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise InputValidationError(
            "Unsupported claim diagnosis config schema: "
            f"{config.get('schema_version')!r}"
        )

    config_dir = config_path.parent
    prompt_spec = config.get("prompt")
    if not isinstance(prompt_spec, dict):
        raise InputValidationError("Missing unsupported diagnosis prompt configuration")
    prompt_path = config_dir / str(prompt_spec.get("file") or "")
    require_file(prompt_path, "unsupported diagnosis prompt")
    validate_file_hash(
        prompt_path, prompt_spec.get("sha256"), "unsupported diagnosis prompt"
    )
    prompt_text = prompt_path.read_text(encoding="utf-8")

    schema_spec = config.get("response_schema")
    if not isinstance(schema_spec, dict):
        raise InputValidationError(
            "Missing unsupported diagnosis response_schema configuration"
        )
    schema_path = config_dir / str(schema_spec.get("file") or "")
    require_file(schema_path, "unsupported diagnosis response schema")
    validate_file_hash(
        schema_path,
        schema_spec.get("sha256"),
        "unsupported diagnosis response schema",
    )
    schema = read_json(schema_path)
    if schema.get("$id") != schema_spec.get("version"):
        raise InputValidationError(
            "Unsupported diagnosis response schema $id does not match configured version"
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
            f"Unknown unsupported diagnosis model key: {model_key!r}"
        )
    model = models[model_key]
    if model.get("provider") != "azure_openai" or model.get("api_style") != "responses":
        raise InputValidationError(
            "Unsupported diagnosis requires an Azure OpenAI Responses API model"
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
            "The openai package is required for live unsupported-diagnosis calls"
        ) from exc
    runtime = config.get("runtime") or {}
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=float(runtime.get("request_timeout_seconds", 600)),
        max_retries=0,
    )


def validate_claim_rows(
    ec_rows: list[dict[str, Any]],
    dc_rows: list[dict[str, Any]],
    *,
    ec_path: Path,
    dc_path: Path,
) -> None:
    if not ec_rows:
        raise InputValidationError(f"No deduplicated EC claims in {ec_path}")
    if not dc_rows:
        raise InputValidationError(f"No deduplicated DC claims in {dc_path}")

    specifications = (
        (
            "EC",
            ec_rows,
            ec_path,
            EC_INPUT_SCHEMA_VERSION,
            "ec_id",
            "ec_text",
            {"generation_case_id", "case_id", "ec_id", "ec_text"},
        ),
        (
            "DC",
            dc_rows,
            dc_path,
            DC_INPUT_SCHEMA_VERSION,
            "dc_id",
            "dc_text",
            {
                "generation_case_id",
                "case_id",
                "generated_disclosure_id",
                "dc_id",
                "dc_text",
            },
        ),
    )
    for kind, rows, path, expected_schema, id_key, text_key, required in specifications:
        seen_ids: set[str] = set()
        for row_number, row in enumerate(rows, start=1):
            label = f"{kind} claim {path}:{row_number}"
            if row.get("schema_version") != expected_schema:
                raise InputValidationError(
                    f"{label} has unsupported schema {row.get('schema_version')!r}"
                )
            missing = sorted(required - set(row))
            if missing:
                raise InputValidationError(f"{label} is missing required fields: {missing}")
            claim_id = row.get(id_key)
            if not isinstance(claim_id, str) or not claim_id:
                raise InputValidationError(f"{label}.{id_key} must be non-empty")
            if claim_id in seen_ids:
                raise InputValidationError(f"Duplicate {id_key}: {claim_id}")
            seen_ids.add(claim_id)
            if not isinstance(row.get(text_key), str) or not row[text_key].strip():
                raise InputValidationError(f"{label}.{text_key} must be non-empty")
            for field in ("generation_case_id", "case_id"):
                if not isinstance(row.get(field), str) or not row[field]:
                    raise InputValidationError(f"{label}.{field} must be non-empty")

    ec_cases = {str(row["generation_case_id"]) for row in ec_rows}
    dc_cases = {str(row["generation_case_id"]) for row in dc_rows}
    if ec_cases != dc_cases:
        raise InputValidationError(
            "Deduplicated EC and DC inputs must contain the same generation cases; "
            f"EC-only={sorted(ec_cases - dc_cases)[:5]}, "
            f"DC-only={sorted(dc_cases - ec_cases)[:5]}"
        )

    for generation_case_id in sorted(ec_cases):
        case_ecs = [row for row in ec_rows if row["generation_case_id"] == generation_case_id]
        case_dcs = [row for row in dc_rows if row["generation_case_id"] == generation_case_id]
        case_ids = {str(row["case_id"]) for row in case_ecs + case_dcs}
        if len(case_ids) != 1:
            raise InputValidationError(
                f"Generation case {generation_case_id} spans case_id values {sorted(case_ids)}"
            )
        disclosure_ids = {str(row["generated_disclosure_id"]) for row in case_dcs}
        if len(disclosure_ids) != 1:
            raise InputValidationError(
                f"Generation case {generation_case_id} spans generated disclosures "
                f"{sorted(disclosure_ids)}"
            )


def index_generation_case_context(
    rows: list[dict[str, Any]],
    *,
    claim_rows: list[dict[str, Any]],
    path: Path,
) -> dict[str, dict[str, Any]]:
    by_generation_case_id: dict[str, dict[str, Any]] = {}
    for row_number, row in enumerate(rows, start=1):
        validate_generation_case(row, row_number)
        generation_case_id = str(row["generation_case_id"])
        if generation_case_id in by_generation_case_id:
            raise InputValidationError(
                f"Duplicate generation_case_id in {path}: {generation_case_id}"
            )
        company_name = row.get("company_name")
        target_reporting_year = row.get("target_reporting_year")
        if not isinstance(company_name, str) or not company_name.strip():
            raise InputValidationError(
                f"Generation case {generation_case_id} has invalid company_name"
            )
        if not isinstance(target_reporting_year, (str, int)) or isinstance(
            target_reporting_year, bool
        ):
            raise InputValidationError(
                f"Generation case {generation_case_id} has invalid target_reporting_year"
            )
        by_generation_case_id[generation_case_id] = {
            "case_id": str(row["case_id"]),
            "context_metadata": {
                "company_name": company_name,
                "target_reporting_year": target_reporting_year,
            },
        }

    claim_case_ids = {
        str(row["generation_case_id"]): str(row["case_id"]) for row in claim_rows
    }
    missing = sorted(set(claim_case_ids) - set(by_generation_case_id))
    if missing:
        raise InputValidationError(
            f"Generation cases missing from {path}: {missing[:5]}"
        )
    mismatched = sorted(
        generation_case_id
        for generation_case_id, case_id in claim_case_ids.items()
        if by_generation_case_id[generation_case_id]["case_id"] != case_id
    )
    if mismatched:
        raise InputValidationError(
            "Generation case context has mismatched case_id values: "
            f"{mismatched[:5]}"
        )
    return by_generation_case_id


def validate_candidate_selections(
    rows: list[dict[str, Any]],
    *,
    ec_rows: list[dict[str, Any]],
    dc_rows: list[dict[str, Any]],
    path: Path,
) -> dict[str, dict[str, Any]]:
    if not rows:
        raise InputValidationError(f"No candidate selections in {path}")
    ec_case_by_id = {str(row["ec_id"]): str(row["generation_case_id"]) for row in ec_rows}
    dc_case_by_id = {str(row["dc_id"]): str(row["generation_case_id"]) for row in dc_rows}
    by_dc_id: dict[str, dict[str, Any]] = {}
    for row_number, row in enumerate(rows, start=1):
        label = f"Candidate selection {path}:{row_number}"
        if not isinstance(row, dict) or set(row) != {"dc_claim_id", "candidate_ec_ids"}:
            raise InputValidationError(
                f"{label} must contain exactly dc_claim_id and candidate_ec_ids"
            )
        dc_id = row["dc_claim_id"]
        candidate_ec_ids = row["candidate_ec_ids"]
        if not isinstance(dc_id, str) or not dc_id:
            raise InputValidationError(f"{label}.dc_claim_id must be non-empty")
        if dc_id not in dc_case_by_id:
            raise InputValidationError(f"{label} references unknown DC ID {dc_id!r}")
        if dc_id in by_dc_id:
            raise InputValidationError(f"Duplicate candidate selection for DC {dc_id}")
        if not isinstance(candidate_ec_ids, list):
            raise InputValidationError(f"{label}.candidate_ec_ids must be an array")
        if any(not isinstance(ec_id, str) or not ec_id for ec_id in candidate_ec_ids):
            raise InputValidationError(f"{label} contains an invalid EC ID")
        if len(candidate_ec_ids) != len(set(candidate_ec_ids)):
            raise InputValidationError(f"{label} contains a duplicate EC ID")
        unknown = sorted(set(candidate_ec_ids) - set(ec_case_by_id))
        if unknown:
            raise InputValidationError(f"{label} contains unknown EC IDs: {unknown}")
        cross_case = sorted(
            ec_id
            for ec_id in candidate_ec_ids
            if ec_case_by_id[ec_id] != dc_case_by_id[dc_id]
        )
        if cross_case:
            raise InputValidationError(
                f"{label} contains EC IDs from a different generation case: {cross_case}"
            )
        by_dc_id[dc_id] = {
            "dc_claim_id": dc_id,
            "candidate_ec_ids": list(candidate_ec_ids),
        }
    return by_dc_id


def validate_support_assessments(
    rows: list[dict[str, Any]],
    *,
    dc_rows: list[dict[str, Any]],
    candidate_by_dc_id: dict[str, dict[str, Any]],
    path: Path,
) -> dict[str, dict[str, Any]]:
    if not rows:
        raise InputValidationError(f"No support assessments in {path}")
    expected_dc_ids = {str(row["dc_id"]) for row in dc_rows}
    by_dc_id: dict[str, dict[str, Any]] = {}
    for row_number, row in enumerate(rows, start=1):
        label = f"Support assessment {path}:{row_number}"
        if not isinstance(row, dict) or set(row) != {"dc_claim_id", "support_sets"}:
            raise InputValidationError(
                f"{label} must contain exactly dc_claim_id and support_sets"
            )
        dc_id = row["dc_claim_id"]
        if not isinstance(dc_id, str) or not dc_id:
            raise InputValidationError(f"{label}.dc_claim_id must be non-empty")
        if dc_id not in expected_dc_ids:
            raise InputValidationError(f"{label} references unknown DC ID {dc_id!r}")
        if dc_id in by_dc_id:
            raise InputValidationError(f"Duplicate support assessment for DC {dc_id}")
        if dc_id not in candidate_by_dc_id:
            raise InputValidationError(
                f"{label} has no corresponding candidate-selection record"
            )
        support_sets = row["support_sets"]
        if not isinstance(support_sets, list):
            raise InputValidationError(f"{label}.support_sets must be an array")
        candidate_ids = candidate_by_dc_id[dc_id]["candidate_ec_ids"]
        candidate_order = {
            candidate_id: index for index, candidate_id in enumerate(candidate_ids)
        }
        normalized_sets: list[dict[str, Any]] = []
        seen_members: set[tuple[str, ...]] = set()
        for set_index, support_set in enumerate(support_sets, start=1):
            set_label = f"{label}.support_sets[{set_index - 1}]"
            if not isinstance(support_set, dict) or set(support_set) != {
                "ec_claim_ids",
                "support_type",
            }:
                raise InputValidationError(
                    f"{set_label} must contain exactly ec_claim_ids and support_type"
                )
            ec_claim_ids = support_set["ec_claim_ids"]
            support_type = support_set["support_type"]
            if not isinstance(ec_claim_ids, list) or not ec_claim_ids:
                raise InputValidationError(
                    f"{set_label}.ec_claim_ids must be a non-empty array"
                )
            if any(not isinstance(ec_id, str) or not ec_id for ec_id in ec_claim_ids):
                raise InputValidationError(f"{set_label} contains an invalid EC ID")
            if len(ec_claim_ids) != len(set(ec_claim_ids)):
                raise InputValidationError(f"{set_label} repeats an EC ID")
            unknown = sorted(set(ec_claim_ids) - set(candidate_order))
            if unknown:
                raise InputValidationError(
                    f"{set_label} contains EC IDs outside the candidate set: {unknown}"
                )
            if support_type not in {"direct", "inferred"}:
                raise InputValidationError(
                    f"{set_label}.support_type must be direct or inferred"
                )
            ordered = tuple(sorted(ec_claim_ids, key=candidate_order.__getitem__))
            if ordered in seen_members:
                raise InputValidationError(
                    f"{label} contains a duplicate support set: {list(ordered)}"
                )
            seen_members.add(ordered)
            normalized_sets.append(
                {"ec_claim_ids": list(ordered), "support_type": support_type}
            )
        by_dc_id[dc_id] = {
            "dc_claim_id": dc_id,
            "support_sets": normalized_sets,
        }
    missing = sorted(expected_dc_ids - set(by_dc_id))
    if missing:
        raise InputValidationError(
            f"Support-assessment input is missing DC IDs: {missing[:5]}"
        )
    return by_dc_id


def select_case_ids(
    ec_rows: list[dict[str, Any]],
    *,
    requested: set[str] | None,
    max_cases: int | None,
) -> list[str]:
    available = sorted({str(row["generation_case_id"]) for row in ec_rows})
    if requested:
        unknown = sorted(requested - set(available))
        if unknown:
            raise InputValidationError(f"Requested generation case IDs not found: {unknown}")
        available = [case_id for case_id in available if case_id in requested]
    if max_cases is not None:
        if max_cases < 1:
            raise InputValidationError("--max-cases must be at least 1")
        available = available[:max_cases]
    if not available:
        raise InputValidationError("No generation cases match the requested filters")
    return available


def make_temporary_ids(
    original_ids: Iterable[str], *, prefix: str, minimum_width: int
) -> tuple[dict[str, str], dict[str, str]]:
    ordered = sorted(set(original_ids))
    if not ordered:
        raise InputValidationError(f"Cannot create {prefix} temporary IDs for an empty set")
    width = max(minimum_width, len(str(len(ordered))))
    alias_by_original = {
        original_id: f"{prefix}_{index:0{width}d}"
        for index, original_id in enumerate(ordered, start=1)
    }
    original_by_alias = {alias: original for original, alias in alias_by_original.items()}
    return alias_by_original, original_by_alias


def build_jobs(
    *,
    ec_rows: list[dict[str, Any]],
    dc_rows: list[dict[str, Any]],
    case_context_by_id: dict[str, dict[str, Any]],
    candidate_by_dc_id: dict[str, dict[str, Any]],
    support_by_dc_id: dict[str, dict[str, Any]],
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
    diagnosis = config.get("diagnosis") or {}
    minimum_width = int(diagnosis.get("temporary_id_min_width", 3))
    max_candidates = int(diagnosis.get("max_candidate_claims_per_dc", 500))
    if minimum_width < 1:
        raise InputValidationError("temporary_id_min_width must be at least 1")
    if max_candidates < 1:
        raise InputValidationError("max_candidate_claims_per_dc must be at least 1")

    selected_case_set = set(case_ids)
    available_dc_ids = {
        str(row["dc_id"])
        for row in dc_rows
        if row["generation_case_id"] in selected_case_set
    }
    unsupported_dc_ids = {
        dc_id
        for dc_id in available_dc_ids
        if not support_by_dc_id[dc_id]["support_sets"]
    }
    if requested_dc_ids:
        unknown = sorted(requested_dc_ids - available_dc_ids)
        if unknown:
            raise InputValidationError(f"Requested DC IDs not found: {unknown}")
        supported = sorted(requested_dc_ids - unsupported_dc_ids)
        if supported:
            raise InputValidationError(
                "Requested DC IDs are supported and cannot be diagnosed: "
                f"{supported}"
            )

    selected_dc_rows = sorted(
        (
            row
            for row in dc_rows
            if row["generation_case_id"] in selected_case_set
            and str(row["dc_id"]) in unsupported_dc_ids
            and (not requested_dc_ids or str(row["dc_id"]) in requested_dc_ids)
        ),
        key=lambda row: (str(row["generation_case_id"]), str(row["dc_id"])),
    )
    if max_dcs is not None:
        if max_dcs < 1:
            raise InputValidationError("--max-dcs must be at least 1")
        selected_dc_rows = selected_dc_rows[:max_dcs]
    selected_dc_ids = {str(row["dc_id"]) for row in selected_dc_rows}
    missing_selections = sorted(selected_dc_ids - set(candidate_by_dc_id))
    if missing_selections:
        raise InputValidationError(
            "Candidate-selection input is missing selected DC IDs: "
            f"{missing_selections}"
        )

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
        ec_by_id = {str(row["ec_id"]): row for row in case_ecs}
        for dc_row in case_dcs:
            original_dc_id = str(dc_row["dc_id"])
            if original_dc_id not in selected_dc_ids:
                continue
            candidate_ids = candidate_by_dc_id[original_dc_id]["candidate_ec_ids"]
            if len(candidate_ids) > max_candidates:
                raise InputValidationError(
                    f"{original_dc_id} has {len(candidate_ids)} candidate ECs; "
                    f"configured maximum is {max_candidates}"
                )
            candidate_ids = sorted(candidate_ids, key=ec_alias_by_original.__getitem__)
            candidate_aliases = [ec_alias_by_original[ec_id] for ec_id in candidate_ids]
            ec_input = [
                {
                    "ec_claim_id": ec_alias_by_original[ec_id],
                    "ec_text": ec_by_id[ec_id]["ec_text"],
                }
                for ec_id in candidate_ids
            ]
            dc_alias = dc_alias_by_original[original_dc_id]
            dynamic_input = {
                "context_metadata": case_context_by_id[generation_case_id][
                    "context_metadata"
                ],
                "dc_claim": {
                    "dc_claim_id": dc_alias,
                    "dc_text": dc_row["dc_text"],
                },
                "ec_claims": ec_input,
            }
            job_input_hash = sha256_json(dynamic_input)
            call_identity = {
                "generation_case_id": generation_case_id,
                "dc_id": original_dc_id,
                "candidate_ec_ids": candidate_ids,
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
                    "candidate_ec_aliases": candidate_aliases,
                    "dynamic_input": dynamic_input,
                    "job_input_hash": job_input_hash,
                    "call_identity": call_identity,
                    "call_id": f"diagnosis_{sha256_json(call_identity)[:32]}",
                    "request_parameters": request_parameters,
                }
            )
    jobs.sort(key=lambda job: (job["generation_case_id"], job["dc_alias"]))
    if not jobs:
        raise InputValidationError("No unsupported DCs match the requested filters")
    return jobs


def validate_diagnosis_response(
    payload: Any,
    *,
    expected_dc_id: str,
    forbidden_claim_ids: Iterable[str],
) -> dict[str, Any]:
    expected_fields = {"dc_claim_id", "unsupported_label", "rationale"}
    if not isinstance(payload, dict) or set(payload) != expected_fields:
        raise OutputValidationError(
            "Response root must contain exactly dc_claim_id, unsupported_label, "
            "and rationale"
        )
    if payload["dc_claim_id"] != expected_dc_id:
        raise OutputValidationError(
            f"dc_claim_id must equal {expected_dc_id!r}, got {payload['dc_claim_id']!r}"
        )
    unsupported_label = payload["unsupported_label"]
    if unsupported_label not in UNSUPPORTED_LABELS:
        raise OutputValidationError(
            "unsupported_label must be one of: " + ", ".join(UNSUPPORTED_LABELS)
        )
    rationale = payload["rationale"]
    if not isinstance(rationale, str) or not rationale.strip():
        raise OutputValidationError("rationale must be a non-empty string")
    if rationale != rationale.strip():
        raise OutputValidationError("rationale must not have outer whitespace")
    referenced_ids = sorted(
        claim_id for claim_id in set(forbidden_claim_ids) if claim_id in rationale
    )
    if referenced_ids:
        raise OutputValidationError(
            f"rationale must not refer to temporary claim IDs: {referenced_ids}"
        )
    return {
        "dc_claim_id": expected_dc_id,
        "unsupported_label": unsupported_label,
        "rationale": rationale,
    }


def restore_original_ids(
    validated_output: dict[str, Any],
    *,
    original_dc_id: str,
) -> dict[str, Any]:
    return {
        "dc_claim_id": original_dc_id,
        "unsupported_label": validated_output["unsupported_label"],
        "rationale": validated_output["rationale"],
    }


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
        integers = [
            value.get(key)
            for value in values
            if isinstance(value.get(key), int)
        ]
        result[key] = sum(integers) if integers else None
    return result


def render_messages(
    prompt_text: str, dynamic_input: dict[str, Any]
) -> list[dict[str, str]]:
    # Preserve insertion order and serialize the supplied evidence before the target.
    user_content = json.dumps(
        dynamic_input,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": user_content},
    ]


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
    temporary_claim_ids = [job["dc_alias"], *job["candidate_ec_aliases"]]
    common = {
        "schema_version": CALL_SCHEMA_VERSION,
        "call_id": job["call_id"],
        "generation_case_id": job["generation_case_id"],
        "case_id": job["case_id"],
        "generated_disclosure_id": job["generated_disclosure_id"],
        "dc_id": job["dc_id"],
        "dc_temporary_id": job["dc_alias"],
        "candidate_ec_ids": job["call_identity"]["candidate_ec_ids"],
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
                "restored_output": None,
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
        restored: dict[str, Any] | None = None
        try:
            last_parsed = json.loads(last_raw)
            validated = validate_diagnosis_response(
                last_parsed,
                expected_dc_id=job["dc_alias"],
                forbidden_claim_ids=temporary_claim_ids,
            )
            restored = restore_original_ids(
                validated,
                original_dc_id=job["dc_id"],
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
        "calls": output_dir / "claim_unsupported_diagnosis_calls.jsonl",
        "failures": output_dir / "claim_unsupported_diagnosis_failures.jsonl",
        "results": output_dir / "dc_unsupported_diagnoses.jsonl",
        "quality": output_dir / "quality_summary.json",
        "manifest": output_dir / "claim_unsupported_diagnosis_run_manifest.json",
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
    jobs: list[dict[str, Any]],
    latest_calls: dict[str, dict[str, Any]],
    all_call_records: list[dict[str, Any]],
    results: list[dict[str, Any]],
    dry_run: bool,
) -> dict[str, Any]:
    records = [latest_calls[job["call_id"]] for job in jobs if job["call_id"] in latest_calls]
    candidate_counts = [len(job["candidate_ec_aliases"]) for job in jobs]
    label_counts = {
        label: sum(result["unsupported_label"] == label for result in results)
        for label in UNSUPPORTED_LABELS
    }
    label_rates = {
        label: (count / len(results) if results else 0.0)
        for label, count in label_counts.items()
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
        "generation_case_count": len({job["generation_case_id"] for job in jobs}),
        "unsupported_dc_count": len(jobs),
        "candidate_count_total": sum(candidate_counts),
        "candidate_count_min": min(candidate_counts),
        "candidate_count_max": max(candidate_counts),
        "candidate_count_mean": sum(candidate_counts) / len(candidate_counts),
        "jobs_planned": len(jobs),
        "model_calls_planned": len(jobs),
        "calls_recorded": len(records),
        "model_calls_recorded": sum(bool(record.get("model_called")) for record in records),
        "calls_success": sum(record.get("call_status") == "success" for record in records),
        "calls_invalid_output": sum(
            record.get("call_status") == "invalid_output" for record in records
        ),
        "calls_api_error": sum(
            record.get("call_status") == "api_error" for record in records
        ),
        "diagnosis_result_count": None if dry_run else len(results),
        "unsupported_label_counts": None if dry_run else label_counts,
        "unsupported_label_rates": None if dry_run else label_rates,
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
    require_file(args.candidate_selections, "candidate selections")
    require_file(args.support_assessments, "support assessments")
    require_file(args.generation_cases, "generation cases")

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
    candidate_rows = read_jsonl(args.candidate_selections)
    support_rows = read_jsonl(args.support_assessments)
    generation_case_rows = read_jsonl(args.generation_cases)
    validate_claim_rows(
        ec_rows,
        dc_rows,
        ec_path=args.ec_claims,
        dc_path=args.dc_claims,
    )
    candidate_by_dc_id = validate_candidate_selections(
        candidate_rows,
        ec_rows=ec_rows,
        dc_rows=dc_rows,
        path=args.candidate_selections,
    )
    support_by_dc_id = validate_support_assessments(
        support_rows,
        dc_rows=dc_rows,
        candidate_by_dc_id=candidate_by_dc_id,
        path=args.support_assessments,
    )
    case_context_by_id = index_generation_case_context(
        generation_case_rows,
        claim_rows=dc_rows,
        path=args.generation_cases,
    )
    case_ids = select_case_ids(
        ec_rows,
        requested=split_values(args.case_id),
        max_cases=args.max_cases,
    )
    jobs = build_jobs(
        ec_rows=ec_rows,
        dc_rows=dc_rows,
        case_context_by_id=case_context_by_id,
        candidate_by_dc_id=candidate_by_dc_id,
        support_by_dc_id=support_by_dc_id,
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
            "candidate_selections": {
                "path": str(args.candidate_selections),
                "sha256": sha256_file(args.candidate_selections),
            },
            "support_assessments": {
                "path": str(args.support_assessments),
                "sha256": sha256_file(args.support_assessments),
            },
            "generation_cases": {
                "path": str(args.generation_cases),
                "sha256": sha256_file(args.generation_cases),
            },
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
        print(f"Selected unsupported DCs: {len(jobs)}")
        print(f"Candidate ECs: {summary['candidate_count_total']}")
        print(f"Planned model calls: {summary['model_calls_planned']}")
        print(f"Run manifest: {paths['manifest']}")
        return

    pending_jobs = [
        job
        for job in jobs
        if latest_calls.get(job["call_id"], {}).get("call_status") != "success"
    ]
    client = (
        make_client(config=config, model=model, base_url=str(base_url))
        if pending_jobs
        else None
    )
    print(
        f"Run plan: {len(jobs)} jobs total | {len(jobs) - len(pending_jobs)} "
        f"resume-skipped | {len(pending_jobs)} jobs this run | "
        f"{len(pending_jobs)} model calls",
        flush=True,
    )
    run_started = time.monotonic()
    for index, job in enumerate(pending_jobs, start=1):
        label = (
            f"[{index}/{len(pending_jobs)}] {job['generation_case_id']} "
            f"{job['dc_alias']} ({len(job['dynamic_input']['ec_claims'])} candidate ECs)"
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
        unsupported_label = (record.get("validated_output") or {}).get(
            "unsupported_label"
        )
        usage = record.get("usage") or {}
        print(
            f"{label} finished: {record['call_status']} | label "
            f"{unsupported_label or '-'} | tokens {usage.get('input_tokens')}/"
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
        "dc_unsupported_diagnoses": len(results),
        "failures": len(failures),
    }
    write_json(paths["manifest"], manifest)

    print(f"Run status: {manifest['status']}")
    print(f"Diagnosed unsupported DCs: {summary['diagnosis_result_count']}")
    print(f"Unsupported label counts: {summary['unsupported_label_counts']}")
    print(f"Quality summary: {paths['quality']}")
    print(f"Run manifest: {paths['manifest']}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
