#!/usr/bin/env python3
"""
Run W2 disclosure generation from frozen generation inputs.

Methodological boundary
----------------------
This script treats generation_inputs/.../generation_cases.jsonl as frozen input.
It does NOT reconstruct prompts, retrieve evidence, rank evidence, segment claims,
judge evidence support, create citations, or ask the LLM to generate metadata.

The LLM is used for exactly one field:
    generated_text

All identifiers, hashes, word counts, character counts, length checks, CSV rows,
Markdown metadata, and manifest fields are produced deterministically by this
script, except provider runtime metadata such as response IDs, token usage, and
error messages.

Typical usage
-------------
python script/generation/run_w2_generation.py \
  --generation-cases generation_inputs/w2_main_text_embedding_3_large_stratified_n10/generation_cases.jsonl \
  --generation-input-manifest generation_inputs/w2_main_text_embedding_3_large_stratified_n10/generation_input_manifest.json \
  --output-dir generation_outputs/w2_main_text_embedding_3_large_stratified_n10/gpt_5_6_sol_run1 \
  --provider azure_openai \
  --model gpt-5.6-sol \
  --omit-temperature \
  --run-id gpt_5_6_sol_run1 \
  --max-cases 3 \
  --write-markdown \
  --overwrite
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env", override=False)


SCRIPT_VERSION = "run_w2_generation_v1.1"
GENERATED_DISCLOSURE_SCHEMA_VERSION = "generated_disclosure_v1"
GENERATED_DISCLOSURE_FAILURE_SCHEMA_VERSION = "generated_disclosure_failure_v1"
GENERATION_RUN_MANIFEST_SCHEMA_VERSION = "generation_run_manifest_v1"

LLM_GENERATED_FIELDS = ["generated_text"]

DETERMINISTIC_OR_SCRIPT_DERIVED_FIELDS = [
    "generation_output_id",
    "generation_case_id",
    "workflow",
    "run_id",
    "company_id",
    "company_name",
    "target_reporting_year",
    "task_id",
    "task_title",
    "generation_cases_path",
    "generation_cases_sha256",
    "generation_input_manifest_path",
    "generation_input_manifest_sha256",
    "prompt_hash",
    "prompt_hash_verified",
    "prompt_word_count",
    "prompt_char_count",
    "retrieval_setting",
    "evidence_count",
    "evidence_type_distribution",
    "generation_model",
    "generated_text_hash",
    "generated_word_count",
    "generated_char_count",
    "length_within_requested_range",
    "generation_status",
    "markdown_file",
    "summary_csv",
    "run_manifest",
]

RUNTIME_METADATA_FIELDS = [
    "created_at_utc",
    "provider_response_id",
    "provider_request_id",
    "usage",
    "error_type",
    "error_message",
    "retry_attempts",
]

LLM_NOT_USED_FOR = [
    "metadata construction",
    "word counting",
    "hashing",
    "claim segmentation",
    "evidence attribution",
    "evidence support evaluation",
    "citation generation",
    "quality scoring",
    "prompt construction",
    "prompt reconstruction",
    "retrieval",
    "retrieval ranking",
]

SUMMARY_FIELDS = [
    "generation_output_id",
    "generation_case_id",
    "workflow",
    "run_id",
    "company_name",
    "target_reporting_year",
    "task_id",
    "task_title",
    "generation_status",
    "generated_word_count",
    "generated_char_count",
    "length_within_requested_range",
    "evidence_count",
    "narrative_count",
    "pdf_table_row_count",
    "csv_metric_count",
    "prompt_hash",
    "generated_text_hash",
    "provider",
    "model",
    "temperature",
    "max_output_tokens",
    "reasoning_effort",
    "text_verbosity",
    "provider_response_id",
    "provider_request_id",
    "error_type",
]


# ---------------------------------------------------------------------------
# Generic utilities
# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{lineno}: {exc}") from exc
    return rows


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=False))
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def deterministic_word_count(text: str) -> int:
    """Fixed lightweight word-count function used for generated_text diagnostics."""
    return len(re.findall(r"\b\S+\b", text))


def safe_filename(value: str, max_len: int = 180) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._=-]+", "_", value).strip("._-")
    if not cleaned:
        cleaned = "generated_disclosure"
    return cleaned[:max_len]


def split_arg_values(values: Optional[Sequence[str]]) -> Optional[List[str]]:
    if not values:
        return None
    out: List[str] = []
    for v in values:
        for part in str(v).split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out or None


def get_nested(obj: Dict[str, Any], path: Sequence[str], default: Any = None) -> Any:
    cur: Any = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


# ---------------------------------------------------------------------------
# Input validation and selection
# ---------------------------------------------------------------------------


def validate_generation_input_manifest(manifest: Dict[str, Any], path: Path) -> None:
    required = [
        "schema_version",
        "script_version",
        "generation_case_count",
        "instruction_template",
        "evidence_id_in_prompt",
        "prompt_label_maps_to_evidence_id",
        "citation_required",
    ]
    missing = [k for k in required if k not in manifest]
    if missing:
        raise ValueError(f"Generation input manifest missing required fields {missing}: {path}")

    if manifest.get("evidence_id_in_prompt") is not False:
        raise ValueError("Expected generation_input_manifest.evidence_id_in_prompt == false")
    if manifest.get("prompt_label_maps_to_evidence_id") is not True:
        raise ValueError("Expected generation_input_manifest.prompt_label_maps_to_evidence_id == true")
    if manifest.get("citation_required") is not False:
        raise ValueError("Expected generation_input_manifest.citation_required == false")


def validate_generation_case(row: Dict[str, Any], index: int) -> None:
    required = [
        "generation_case_id",
        "workflow",
        "company_id",
        "company_name",
        "target_reporting_year",
        "task_id",
        "task_title",
        "generation_prompt",
        "prompt_metadata",
        "retrieval_setting",
    ]
    missing = [k for k in required if k not in row]
    if missing:
        raise ValueError(f"generation_cases row {index} missing fields: {missing}")
    if row.get("workflow") != "W2":
        raise ValueError(f"generation_cases row {index} expected workflow W2, got {row.get('workflow')!r}")
    if not isinstance(row.get("generation_prompt"), str) or not row["generation_prompt"].strip():
        raise ValueError(f"generation_cases row {index} has empty generation_prompt")
    prompt_metadata = row.get("prompt_metadata") or {}
    if not prompt_metadata.get("prompt_hash"):
        raise ValueError(f"generation_cases row {index} missing prompt_metadata.prompt_hash")
    if "evidence_count" not in prompt_metadata:
        raise ValueError(f"generation_cases row {index} missing prompt_metadata.evidence_count")

    computed_prompt_hash = sha256_text(row["generation_prompt"])
    if computed_prompt_hash != prompt_metadata.get("prompt_hash"):
        raise ValueError(
            f"generation_cases row {index} prompt hash mismatch for "
            f"{row.get('generation_case_id')}: manifest={prompt_metadata.get('prompt_hash')} "
            f"computed={computed_prompt_hash}"
        )


def load_and_validate_cases(cases_path: Path) -> List[Dict[str, Any]]:
    rows = read_jsonl(cases_path)
    for i, row in enumerate(rows, start=1):
        validate_generation_case(row, i)
    return rows


def apply_filters(
    rows: List[Dict[str, Any]],
    case_ids: Optional[Set[str]] = None,
    task_ids: Optional[Set[str]] = None,
    target_years: Optional[Set[int]] = None,
    company_names: Optional[Set[str]] = None,
    max_cases: Optional[int] = None,
) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    company_names_norm = {x.lower() for x in company_names} if company_names else None

    for row in rows:
        if case_ids and row.get("generation_case_id") not in case_ids and row.get("case_id") not in case_ids:
            continue
        if task_ids and row.get("task_id") not in task_ids:
            continue
        if target_years and int(row.get("target_reporting_year")) not in target_years:
            continue
        if company_names_norm and str(row.get("company_name", "")).lower() not in company_names_norm:
            continue
        selected.append(row)
        if max_cases is not None and len(selected) >= max_cases:
            break
    return selected


# ---------------------------------------------------------------------------
# Provider call and response extraction
# ---------------------------------------------------------------------------


def extract_usage(obj: Any) -> Dict[str, Optional[int]]:
    usage = getattr(obj, "usage", None)
    if usage is None and isinstance(obj, dict):
        usage = obj.get("usage")

    def get_attr_or_key(x: Any, name: str) -> Optional[int]:
        if x is None:
            return None
        if isinstance(x, dict):
            value = x.get(name)
        else:
            value = getattr(x, name, None)
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    return {
        "input_tokens": get_attr_or_key(usage, "input_tokens"),
        "output_tokens": get_attr_or_key(usage, "output_tokens"),
        "total_tokens": get_attr_or_key(usage, "total_tokens"),
    }


def response_to_dict(response: Any) -> Dict[str, Any]:
    if isinstance(response, dict):
        return response
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if hasattr(response, "dict"):
        return response.dict()
    return {}


def extract_response_text(response: Any) -> str:
    """Extract plain text from OpenAI Responses API response robustly."""
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    data = response_to_dict(response)
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    parts: List[str] = []
    for item in data.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            text = content.get("text") or content.get("output_text")
            if isinstance(text, str) and text:
                parts.append(text)
    if parts:
        return "\n".join(parts).strip()

    # Fallback for Chat Completions-like objects if used in the future.
    choices = data.get("choices", []) or []
    if choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message") or {}
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"].strip()

    raise ValueError("Could not extract non-empty generated text from provider response")


def normalize_azure_base_url(endpoint: str) -> str:
    parts = urlsplit(endpoint.strip())
    if parts.scheme != "https" or not parts.netloc:
        raise ValueError("Azure OpenAI generation endpoint must be a full HTTPS URL")
    path = parts.path.rstrip("/")
    for suffix in ("/openai/v1/responses", "/openai/responses"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    if path.endswith("/openai/v1"):
        normalized_path = path + "/"
    elif path.endswith("/openai"):
        normalized_path = path + "/v1/"
    else:
        normalized_path = path + "/openai/v1/"
    return urlunsplit((parts.scheme, parts.netloc, normalized_path, "", ""))


def generate_disclosure_openai_responses(
    prompt: str,
    provider: str,
    model: str,
    azure_deployment: Optional[str],
    temperature: Optional[float],
    max_output_tokens: Optional[int],
    omit_temperature: bool,
    reasoning_effort: Optional[str],
    text_verbosity: Optional[str],
    request_timeout: Optional[float],
    openai_max_retries: int,
) -> Dict[str, Any]:
    """Call OpenAI Responses API. The prompt is sent as the sole model input."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The 'openai' Python package is not installed. Install with: pip install openai"
        ) from exc

    client_kwargs: Dict[str, Any] = {"max_retries": openai_max_retries}
    api_model = model
    if provider == "azure_openai":
        api_key = os.environ.get("GENERATION_AZURE_OPENAI_API_KEY")
        endpoint = os.environ.get("GENERATION_AZURE_OPENAI_ENDPOINT")
        if not api_key:
            raise RuntimeError(
                "Missing Azure API key environment variable: "
                "GENERATION_AZURE_OPENAI_API_KEY"
            )
        if not endpoint:
            raise RuntimeError(
                "Missing Azure endpoint environment variable: "
                "GENERATION_AZURE_OPENAI_ENDPOINT"
            )
        if not azure_deployment:
            raise RuntimeError(
                "Missing Azure generation deployment environment variable: "
                "GENERATION_AZURE_OPENAI_DEPLOYMENT"
            )
        client_kwargs["api_key"] = api_key
        client_kwargs["base_url"] = normalize_azure_base_url(endpoint)
        api_model = azure_deployment
    if request_timeout is not None:
        client_kwargs["timeout"] = request_timeout
    client = OpenAI(**client_kwargs)

    kwargs: Dict[str, Any] = {
        "model": api_model,
        "input": prompt,
    }
    if max_output_tokens is not None:
        kwargs["max_output_tokens"] = max_output_tokens
    if reasoning_effort is not None:
        kwargs["reasoning"] = {"effort": reasoning_effort}
    if text_verbosity is not None:
        kwargs["text"] = {"verbosity": text_verbosity}
    if not omit_temperature and temperature is not None:
        kwargs["temperature"] = temperature

    response = client.responses.create(**kwargs)
    generated_text = extract_response_text(response)

    return {
        "generated_text": generated_text,
        "provider_response_id": getattr(response, "id", None),
        "provider_request_id": getattr(response, "_request_id", None),
        "usage": extract_usage(response),
    }


def generate_disclosure(
    provider: str,
    prompt: str,
    model: str,
    azure_deployment: Optional[str],
    temperature: Optional[float],
    max_output_tokens: Optional[int],
    omit_temperature: bool,
    reasoning_effort: Optional[str],
    text_verbosity: Optional[str],
    request_timeout: Optional[float],
    openai_max_retries: int,
) -> Dict[str, Any]:
    if provider not in {"openai", "azure_openai"}:
        raise ValueError(
            f"Unsupported provider: {provider}. Currently supported: openai, azure_openai"
        )
    return generate_disclosure_openai_responses(
        prompt=prompt,
        provider=provider,
        model=model,
        azure_deployment=azure_deployment,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        omit_temperature=omit_temperature,
        reasoning_effort=reasoning_effort,
        text_verbosity=text_verbosity,
        request_timeout=request_timeout,
        openai_max_retries=openai_max_retries,
    )


# ---------------------------------------------------------------------------
# Output construction
# ---------------------------------------------------------------------------


def evidence_distribution_from_case(row: Dict[str, Any]) -> Dict[str, int]:
    prompt_metadata = row.get("prompt_metadata") or {}
    dist = prompt_metadata.get("evidence_type_distribution")
    if isinstance(dist, dict):
        return {str(k): int(v) for k, v in dist.items()}

    counts: Dict[str, int] = {}
    for ev in row.get("prompt_evidence", []) or []:
        et = ev.get("evidence_type")
        if et:
            counts[str(et)] = counts.get(str(et), 0) + 1
    return counts


def build_generation_output_id(generation_case_id: str, run_id: str) -> str:
    return f"{generation_case_id}__{run_id}"


def make_success_record(
    row: Dict[str, Any],
    provider_result: Dict[str, Any],
    args: argparse.Namespace,
    generation_cases_path: Path,
    generation_cases_sha256: str,
    generation_input_manifest_path: Path,
    generation_input_manifest_sha256: str,
) -> Dict[str, Any]:
    prompt_metadata = row.get("prompt_metadata") or {}
    evidence_dist = evidence_distribution_from_case(row)
    generated_text = provider_result["generated_text"].strip()
    generated_word_count = deterministic_word_count(generated_text)
    generated_char_count = len(generated_text)
    min_words = args.min_output_words
    max_words = args.max_output_words

    return {
        "schema_version": GENERATED_DISCLOSURE_SCHEMA_VERSION,
        "generation_output_id": build_generation_output_id(row["generation_case_id"], args.run_id),
        "generation_case_id": row["generation_case_id"],
        "workflow": row.get("workflow"),
        "run_id": args.run_id,
        "company_id": row.get("company_id"),
        "company_name": row.get("company_name"),
        "target_reporting_year": row.get("target_reporting_year"),
        "task_id": row.get("task_id"),
        "task_title": row.get("task_title"),
        "generation_cases_path": str(generation_cases_path),
        "generation_cases_sha256": generation_cases_sha256,
        "generation_input_manifest_path": str(generation_input_manifest_path),
        "generation_input_manifest_sha256": generation_input_manifest_sha256,
        "prompt_hash": prompt_metadata.get("prompt_hash"),
        "prompt_hash_verified": sha256_text(row["generation_prompt"]) == prompt_metadata.get("prompt_hash"),
        "prompt_word_count": prompt_metadata.get("prompt_word_count"),
        "prompt_char_count": prompt_metadata.get("prompt_char_count"),
        "retrieval_setting": row.get("retrieval_setting"),
        "evidence_count": prompt_metadata.get("evidence_count"),
        "evidence_type_distribution": evidence_dist,
        "generation_model": {
            "provider": args.provider,
            "model": args.model,
            "deployment_name": args.azure_deployment if args.provider == "azure_openai" else None,
            "temperature": None if args.omit_temperature else args.temperature,
            "max_output_tokens": args.max_output_tokens,
            "reasoning_effort": args.reasoning_effort,
            "text_verbosity": args.text_verbosity,
            "api_interface": "responses",
        },
        "llm_generated_fields": LLM_GENERATED_FIELDS,
        "provider_response_id": provider_result.get("provider_response_id"),
        "provider_request_id": provider_result.get("provider_request_id"),
        "usage": provider_result.get("usage") or {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        },
        "generated_text": generated_text,
        "generated_text_hash": sha256_text(generated_text),
        "generated_word_count": generated_word_count,
        "generated_char_count": generated_char_count,
        "length_within_requested_range": bool(min_words <= generated_word_count <= max_words),
        "generation_status": "success",
        "error_type": None,
        "error_message": None,
        "retry_attempts": provider_result.get("retry_attempts", 0),
        "created_at_utc": utc_now_iso(),
    }


def make_failure_record(
    row: Dict[str, Any],
    args: argparse.Namespace,
    error_type: str,
    error_message: str,
    retry_attempts: int,
) -> Dict[str, Any]:
    return {
        "schema_version": GENERATED_DISCLOSURE_FAILURE_SCHEMA_VERSION,
        "generation_output_id": build_generation_output_id(row.get("generation_case_id", "unknown"), args.run_id),
        "generation_case_id": row.get("generation_case_id"),
        "workflow": row.get("workflow"),
        "run_id": args.run_id,
        "company_id": row.get("company_id"),
        "company_name": row.get("company_name"),
        "target_reporting_year": row.get("target_reporting_year"),
        "task_id": row.get("task_id"),
        "task_title": row.get("task_title"),
        "generation_model": {
            "provider": args.provider,
            "model": args.model,
            "deployment_name": args.azure_deployment if args.provider == "azure_openai" else None,
            "temperature": None if args.omit_temperature else args.temperature,
            "max_output_tokens": args.max_output_tokens,
            "reasoning_effort": args.reasoning_effort,
            "text_verbosity": args.text_verbosity,
            "api_interface": "responses",
        },
        "generation_status": "failed",
        "error_type": error_type,
        "error_message": error_message,
        "retry_attempts": retry_attempts,
        "created_at_utc": utc_now_iso(),
    }


def write_markdown_disclosure(record: Dict[str, Any], disclosures_dir: Path) -> Path:
    filename = safe_filename(record["generation_output_id"]) + ".md"
    path = disclosures_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    evidence_dist = record.get("evidence_type_distribution") or {}
    model = record.get("generation_model") or {}
    lines = [
        f"# {record.get('company_name')} — {record.get('target_reporting_year')} — {record.get('task_title')}",
        "",
        f"**Workflow:** {record.get('workflow')}  ",
        f"**Run ID:** {record.get('run_id')}  ",
        f"**Generation output ID:** {record.get('generation_output_id')}  ",
        f"**Generation case ID:** {record.get('generation_case_id')}  ",
        f"**Prompt hash:** {record.get('prompt_hash')}  ",
        f"**Evidence count:** {record.get('evidence_count')}  ",
        f"**Evidence distribution:** narrative={evidence_dist.get('narrative', 0)}, "
        f"pdf_table_row={evidence_dist.get('pdf_table_row', 0)}, "
        f"csv_metric={evidence_dist.get('csv_metric', 0)}  ",
        f"**Model:** {model.get('provider')} / {model.get('model')}  ",
        f"**Temperature:** {model.get('temperature')}  ",
        f"**Reasoning effort:** {model.get('reasoning_effort')}  ",
        f"**Text verbosity:** {model.get('text_verbosity')}  ",
        f"**Generated word count:** {record.get('generated_word_count')}  ",
        f"**Length within requested range:** {record.get('length_within_requested_range')}  ",
        "",
        "> Metadata above is deterministic runtime metadata. The disclosure text below is the only LLM-generated content in this file.",
        "",
        "---",
        "",
        record.get("generated_text", ""),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def summary_row_from_success(record: Dict[str, Any]) -> Dict[str, Any]:
    dist = record.get("evidence_type_distribution") or {}
    model = record.get("generation_model") or {}
    return {
        "generation_output_id": record.get("generation_output_id"),
        "generation_case_id": record.get("generation_case_id"),
        "workflow": record.get("workflow"),
        "run_id": record.get("run_id"),
        "company_name": record.get("company_name"),
        "target_reporting_year": record.get("target_reporting_year"),
        "task_id": record.get("task_id"),
        "task_title": record.get("task_title"),
        "generation_status": record.get("generation_status"),
        "generated_word_count": record.get("generated_word_count"),
        "generated_char_count": record.get("generated_char_count"),
        "length_within_requested_range": record.get("length_within_requested_range"),
        "evidence_count": record.get("evidence_count"),
        "narrative_count": dist.get("narrative", 0),
        "pdf_table_row_count": dist.get("pdf_table_row", 0),
        "csv_metric_count": dist.get("csv_metric", 0),
        "prompt_hash": record.get("prompt_hash"),
        "generated_text_hash": record.get("generated_text_hash"),
        "provider": model.get("provider"),
        "model": model.get("model"),
        "temperature": model.get("temperature"),
        "max_output_tokens": model.get("max_output_tokens"),
        "reasoning_effort": model.get("reasoning_effort"),
        "text_verbosity": model.get("text_verbosity"),
        "provider_response_id": record.get("provider_response_id"),
        "provider_request_id": record.get("provider_request_id"),
        "error_type": record.get("error_type"),
    }


def write_summary_csv_from_jsonl(generated_jsonl: Path, summary_csv: Path) -> int:
    records = read_jsonl(generated_jsonl) if generated_jsonl.exists() else []
    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(summary_row_from_success(record))
    return len(records)


def read_successful_case_ids(generated_jsonl: Path) -> Set[str]:
    if not generated_jsonl.exists():
        return set()
    successful: Set[str] = set()
    for record in read_jsonl(generated_jsonl):
        if record.get("generation_status") == "success" and record.get("generation_case_id"):
            successful.add(record["generation_case_id"])
    return successful


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


# ---------------------------------------------------------------------------
# Manifest construction
# ---------------------------------------------------------------------------


def build_run_manifest(
    args: argparse.Namespace,
    generation_cases_path: Path,
    generation_cases_sha256: str,
    generation_input_manifest_path: Path,
    generation_input_manifest_sha256: str,
    input_manifest: Dict[str, Any],
    selected_cases: List[Dict[str, Any]],
    case_count_success: int,
    case_count_failed: int,
    started_at_utc: str,
    completed_at_utc: Optional[str],
    dry_run: bool = False,
) -> Dict[str, Any]:
    output_dir = Path(args.output_dir)
    return {
        "schema_version": GENERATION_RUN_MANIFEST_SCHEMA_VERSION,
        "script_version": SCRIPT_VERSION,
        "run_id": args.run_id,
        "workflow": "W2",
        "dry_run": dry_run,
        "started_at_utc": started_at_utc,
        "completed_at_utc": completed_at_utc,
        "generation_cases_file": str(generation_cases_path),
        "generation_cases_sha256": generation_cases_sha256,
        "generation_input_manifest_file": str(generation_input_manifest_path),
        "generation_input_manifest_sha256": generation_input_manifest_sha256,
        "generation_input_manifest_summary": {
            "schema_version": input_manifest.get("schema_version"),
            "script_version": input_manifest.get("script_version"),
            "generation_config_version": input_manifest.get("generation_config_version"),
            "generation_config_status": input_manifest.get("generation_config_status"),
            "prompt_layout_version": input_manifest.get("prompt_layout_version"),
            "generation_input_schema_version": input_manifest.get("generation_input_schema_version"),
            "generation_case_count": input_manifest.get("generation_case_count"),
            "evidence_id_in_prompt": input_manifest.get("evidence_id_in_prompt"),
            "prompt_label_maps_to_evidence_id": input_manifest.get("prompt_label_maps_to_evidence_id"),
            "citation_required": input_manifest.get("citation_required"),
            "evidence_group_order": input_manifest.get("evidence_group_order"),
        },
        "generation_model": {
            "provider": args.provider,
            "model": args.model,
            "deployment_name": args.azure_deployment if args.provider == "azure_openai" else None,
            "temperature": None if args.omit_temperature else args.temperature,
            "max_output_tokens": args.max_output_tokens,
            "reasoning_effort": args.reasoning_effort,
            "text_verbosity": args.text_verbosity,
            "api_interface": "responses",
            "request_timeout": args.request_timeout,
            "openai_max_retries": args.openai_max_retries,
        },
        "field_origin_policy": {
            "llm_generated_fields": LLM_GENERATED_FIELDS,
            "deterministic_or_script_derived_fields": DETERMINISTIC_OR_SCRIPT_DERIVED_FIELDS,
            "runtime_metadata_fields": RUNTIME_METADATA_FIELDS,
            "llm_not_used_for": LLM_NOT_USED_FOR,
        },
        "prompt_policy": {
            "prompt_source": "generation_cases.jsonl::generation_prompt",
            "prompt_reassembled_in_this_script": False,
            "prompt_hash_used": True,
            "prompt_hash_verified_before_generation": True,
            "evidence_id_in_prompt": input_manifest.get("evidence_id_in_prompt"),
            "citation_required": input_manifest.get("citation_required"),
        },
        "filters": {
            "max_cases": args.max_cases,
            "case_ids": split_arg_values(args.case_ids),
            "task_ids": split_arg_values(args.task_ids),
            "target_years": split_arg_values(args.target_years),
            "company_names": split_arg_values(args.company_names),
        },
        "case_count_requested": len(selected_cases),
        "case_count_success": case_count_success,
        "case_count_failed": case_count_failed,
        "outputs": {
            "generated_disclosures_jsonl": str(output_dir / "generated_disclosures.jsonl"),
            "generated_disclosures_summary_csv": str(output_dir / "generated_disclosures_summary.csv"),
            "failed_cases_jsonl": str(output_dir / "failed_cases.jsonl"),
            "disclosures_dir": str(output_dir / "disclosures"),
        },
    }


# ---------------------------------------------------------------------------
# CLI and main
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run W2 GPT disclosure generation from frozen generation_cases.jsonl."
    )
    parser.add_argument("--generation-cases", required=True, type=Path)
    parser.add_argument("--generation-input-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--provider",
        default=os.environ.get("GENERATION_PROVIDER", "azure_openai"),
        choices=["openai", "azure_openai"],
    )
    parser.add_argument("--model", default=os.environ.get("GENERATION_MODEL_ID"))
    parser.add_argument(
        "--azure-deployment",
        default=os.environ.get("GENERATION_AZURE_OPENAI_DEPLOYMENT"),
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--omit-temperature",
        action="store_true",
        help="Omit the temperature parameter from the provider request. Useful for models that do not accept temperature.",
    )
    parser.add_argument("--max-output-tokens", type=int, default=None)
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "minimal", "low", "medium", "high", "xhigh"],
        default=None,
        help=(
            "Optional Responses API reasoning effort. If omitted, the model/API default is used "
            "and no reasoning field is sent in the request."
        ),
    )
    parser.add_argument(
        "--text-verbosity",
        choices=["low", "medium", "high"],
        default=None,
        help=(
            "Optional Responses API text verbosity. If omitted, the model/API default is used "
            "and no text.verbosity field is sent in the request."
        ),
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--min-output-words", type=int, default=300)
    parser.add_argument("--max-output-words", type=int, default=500)

    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--case-ids", nargs="*", default=None)
    parser.add_argument("--task-ids", nargs="*", default=None)
    parser.add_argument("--target-years", nargs="*", default=None)
    parser.add_argument("--company-names", nargs="*", default=None)

    parser.add_argument("--write-markdown", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--retry-attempts", type=int, default=0)
    parser.add_argument("--retry-sleep-seconds", type=float, default=5.0)
    parser.add_argument("--openai-max-retries", type=int, default=2)
    parser.add_argument("--request-timeout", type=float, default=600.0)
    parser.add_argument("--progress-every", type=int, default=10)

    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    if not args.model:
        raise ValueError("--model or GENERATION_MODEL_ID is required")
    if args.overwrite and args.resume:
        raise ValueError("--overwrite and --resume are mutually exclusive")
    if args.max_cases is not None and args.max_cases <= 0:
        raise ValueError("--max-cases must be positive")
    if args.min_output_words <= 0 or args.max_output_words <= 0:
        raise ValueError("Output word bounds must be positive")
    if args.min_output_words > args.max_output_words:
        raise ValueError("--min-output-words cannot exceed --max-output-words")
    if args.retry_attempts < 0:
        raise ValueError("--retry-attempts cannot be negative")
    if args.openai_max_retries < 0:
        raise ValueError("--openai-max-retries cannot be negative")
    if args.progress_every <= 0:
        raise ValueError("--progress-every must be positive")
    if args.sleep_seconds < 0 or args.retry_sleep_seconds < 0:
        raise ValueError("Sleep seconds cannot be negative")


def prepare_output_dir(args: argparse.Namespace) -> Tuple[Path, Path, Path, Path, Path]:
    output_dir: Path = args.output_dir
    generated_jsonl = output_dir / "generated_disclosures.jsonl"
    summary_csv = output_dir / "generated_disclosures_summary.csv"
    failed_jsonl = output_dir / "failed_cases.jsonl"
    manifest_json = output_dir / "generation_run_manifest.json"
    disclosures_dir = output_dir / "disclosures"

    if args.overwrite and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.write_markdown:
        disclosures_dir.mkdir(parents=True, exist_ok=True)

    if not args.resume and not args.overwrite:
        existing = [p for p in [generated_jsonl, summary_csv, failed_jsonl, manifest_json] if p.exists()]
        if existing:
            raise FileExistsError(
                "Output files already exist. Use --overwrite to start over or --resume to continue. "
                f"Existing: {[str(p) for p in existing]}"
            )

    return generated_jsonl, summary_csv, failed_jsonl, manifest_json, disclosures_dir


def run_generation(args: argparse.Namespace) -> int:
    validate_args(args)

    generation_cases_path: Path = args.generation_cases
    generation_input_manifest_path: Path = args.generation_input_manifest

    if not generation_cases_path.exists():
        raise FileNotFoundError(generation_cases_path)
    if not generation_input_manifest_path.exists():
        raise FileNotFoundError(generation_input_manifest_path)

    input_manifest = read_json(generation_input_manifest_path)
    validate_generation_input_manifest(input_manifest, generation_input_manifest_path)

    generation_cases_sha256 = sha256_file(generation_cases_path)
    generation_input_manifest_sha256 = sha256_file(generation_input_manifest_path)

    rows = load_and_validate_cases(generation_cases_path)

    case_ids = set(split_arg_values(args.case_ids) or []) or None
    task_ids = set(split_arg_values(args.task_ids) or []) or None
    target_year_values = split_arg_values(args.target_years)
    target_years = {int(y) for y in target_year_values} if target_year_values else None
    company_names = set(split_arg_values(args.company_names) or []) or None

    selected = apply_filters(
        rows,
        case_ids=case_ids,
        task_ids=task_ids,
        target_years=target_years,
        company_names=company_names,
        max_cases=args.max_cases,
    )

    started_at_utc = utc_now_iso()

    if args.dry_run:
        manifest_preview = build_run_manifest(
            args=args,
            generation_cases_path=generation_cases_path,
            generation_cases_sha256=generation_cases_sha256,
            generation_input_manifest_path=generation_input_manifest_path,
            generation_input_manifest_sha256=generation_input_manifest_sha256,
            input_manifest=input_manifest,
            selected_cases=selected,
            case_count_success=0,
            case_count_failed=0,
            started_at_utc=started_at_utc,
            completed_at_utc=None,
            dry_run=True,
        )
        manifest_preview["first_generation_case_ids"] = [r.get("generation_case_id") for r in selected[:5]]
        print("[DRY RUN] No provider call will be made.")
        print(json.dumps(manifest_preview, ensure_ascii=False, indent=2))
        return 0

    generated_jsonl, summary_csv, failed_jsonl, manifest_json, disclosures_dir = prepare_output_dir(args)

    already_successful: Set[str] = set()
    if args.resume:
        already_successful = read_successful_case_ids(generated_jsonl)
        print(f"[RESUME] already successful cases: {len(already_successful)}")

    success_count_before = count_jsonl(generated_jsonl)
    failed_count_before = count_jsonl(failed_jsonl)

    selected_to_run = [r for r in selected if r.get("generation_case_id") not in already_successful]
    print(f"[START] selected cases: {len(selected)} | to run: {len(selected_to_run)}")

    for i, row in enumerate(selected_to_run, start=1):
        case_id = row["generation_case_id"]
        if i == 1 or i % args.progress_every == 0 or i == len(selected_to_run):
            print(f"[PROGRESS] {i}/{len(selected_to_run)} {case_id}")

        last_error: Optional[BaseException] = None
        provider_result: Optional[Dict[str, Any]] = None
        attempts_made = 0

        for attempt in range(args.retry_attempts + 1):
            attempts_made = attempt
            try:
                provider_result = generate_disclosure(
                    provider=args.provider,
                    prompt=row["generation_prompt"],
                    model=args.model,
                    azure_deployment=args.azure_deployment,
                    temperature=args.temperature,
                    max_output_tokens=args.max_output_tokens,
                    omit_temperature=args.omit_temperature,
                    reasoning_effort=args.reasoning_effort,
                    text_verbosity=args.text_verbosity,
                    request_timeout=args.request_timeout,
                    openai_max_retries=args.openai_max_retries,
                )
                provider_result["retry_attempts"] = attempt
                break
            except Exception as exc:  # noqa: BLE001 - logged as runtime failure record.
                last_error = exc
                if attempt < args.retry_attempts:
                    time.sleep(args.retry_sleep_seconds)
                else:
                    provider_result = None

        if provider_result is None:
            failure = make_failure_record(
                row=row,
                args=args,
                error_type=type(last_error).__name__ if last_error else "unknown_error",
                error_message=str(last_error) if last_error else "Unknown error",
                retry_attempts=attempts_made,
            )
            append_jsonl(failed_jsonl, failure)
            print(f"[FAILED] {case_id}: {failure['error_type']}: {failure['error_message']}", file=sys.stderr)
        else:
            record = make_success_record(
                row=row,
                provider_result=provider_result,
                args=args,
                generation_cases_path=generation_cases_path,
                generation_cases_sha256=generation_cases_sha256,
                generation_input_manifest_path=generation_input_manifest_path,
                generation_input_manifest_sha256=generation_input_manifest_sha256,
            )
            append_jsonl(generated_jsonl, record)
            if args.write_markdown:
                write_markdown_disclosure(record, disclosures_dir)

        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    success_count_total = write_summary_csv_from_jsonl(generated_jsonl, summary_csv)
    failed_count_total = count_jsonl(failed_jsonl)

    completed_at_utc = utc_now_iso()
    run_manifest = build_run_manifest(
        args=args,
        generation_cases_path=generation_cases_path,
        generation_cases_sha256=generation_cases_sha256,
        generation_input_manifest_path=generation_input_manifest_path,
        generation_input_manifest_sha256=generation_input_manifest_sha256,
        input_manifest=input_manifest,
        selected_cases=selected,
        case_count_success=success_count_total,
        case_count_failed=failed_count_total,
        started_at_utc=started_at_utc,
        completed_at_utc=completed_at_utc,
        dry_run=False,
    )
    run_manifest["case_count_success_before_run"] = success_count_before
    run_manifest["case_count_failed_before_run"] = failed_count_before
    run_manifest["case_count_attempted_this_run"] = len(selected_to_run)
    write_json(manifest_json, run_manifest)

    print("[DONE]")
    print(json.dumps({
        "output_dir": str(args.output_dir),
        "case_count_requested": len(selected),
        "case_count_success": success_count_total,
        "case_count_failed": failed_count_total,
        "generated_disclosures_jsonl": str(generated_jsonl),
        "generated_disclosures_summary_csv": str(summary_csv),
        "generation_run_manifest_json": str(manifest_json),
    }, ensure_ascii=False, indent=2))

    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    return run_generation(args)


if __name__ == "__main__":
    raise SystemExit(main())
