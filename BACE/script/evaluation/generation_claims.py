#!/usr/bin/env python3
"""Shared deterministic helpers for generation claim extraction.

The LLM constructs atomic claims through a strict structured-output schema.
Source quotations may be retained as best-effort provenance metadata, but the
schema-only extraction mode does not use quotation matching to accept or reject
model output.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlsplit, urlunsplit


EC_OCCURRENCE_SCHEMA_VERSION = "ec_claim_occurrence_v1"
DC_OCCURRENCE_SCHEMA_VERSION = "dc_claim_occurrence_v1"
SUPPORTED_GENERATION_CASE_SCHEMAS = {"w2_generation_cases_v1"}
SUPPORTED_DISCLOSURE_SCHEMAS = {"generated_disclosure_v1"}
NO_CLAIM_REASONS = {
    "no_evaluable_factual_proposition",
    "insufficient_context_or_extraction_noise",
}
CONTEXT_METADATA_FIELDS = {
    "company_name",
    "source_year",
    "target_reporting_year",
}


class ClaimExtractionError(RuntimeError):
    """Base error for deterministic claim-extraction failures."""


class InputValidationError(ClaimExtractionError):
    """Raised when a frozen generation input is inconsistent."""


class OutputValidationError(ClaimExtractionError):
    """Raised when an LLM response violates the extraction contract."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_text(canonical_json(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"Cannot read JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InputValidationError(f"Expected a JSON object in {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise InputValidationError(
                        f"Invalid JSONL at {path}:{line_number}: {exc}"
                    ) from exc
                if not isinstance(row, dict):
                    raise InputValidationError(
                        f"Expected a JSON object at {path}:{line_number}"
                    )
                rows.append(row)
    except OSError as exc:
        raise InputValidationError(f"Cannot read JSONL file {path}: {exc}") from exc
    return rows


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")
        file.flush()


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise InputValidationError(f"Missing {label}: {path}")


def require_keys(value: dict[str, Any], keys: Sequence[str], label: str) -> None:
    missing = [key for key in keys if key not in value]
    if missing:
        raise InputValidationError(f"{label} is missing required fields: {missing}")


def validate_file_hash(path: Path, expected: str | None, label: str) -> None:
    if not expected:
        raise InputValidationError(f"No expected SHA256 is recorded for {label}")
    actual = sha256_file(path)
    if actual != expected:
        raise InputValidationError(
            f"SHA256 mismatch for {label}: expected {expected}, got {actual} ({path})"
        )


def normalize_azure_base_url(endpoint: str) -> str:
    """Normalize an Azure resource endpoint or copied responses URL."""
    endpoint = endpoint.strip()
    parts = urlsplit(endpoint)
    if parts.scheme != "https" or not parts.netloc:
        raise InputValidationError(
            "Azure OpenAI endpoint must be a full HTTPS URL, for example "
            "https://RESOURCE.cognitiveservices.azure.com/"
        )

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


def validate_generation_case(row: dict[str, Any], row_number: int) -> None:
    label = f"generation case row {row_number}"
    require_keys(
        row,
        [
            "schema_version",
            "generation_case_id",
            "case_id",
            "company_id",
            "company_name",
            "target_reporting_year",
            "task_id",
            "task_title",
            "prompt_evidence",
            "generation_prompt",
            "prompt_metadata",
        ],
        label,
    )
    if row["schema_version"] not in SUPPORTED_GENERATION_CASE_SCHEMAS:
        raise InputValidationError(
            f"Unsupported generation case schema in {label}: {row['schema_version']!r}"
        )
    if not isinstance(row["prompt_evidence"], list):
        raise InputValidationError(f"{label}.prompt_evidence must be an array")
    if not isinstance(row["generation_prompt"], str) or not row["generation_prompt"]:
        raise InputValidationError(f"{label}.generation_prompt must be non-empty")

    expected_prompt_hash = row["prompt_metadata"].get("prompt_hash")
    if expected_prompt_hash and sha256_text(row["generation_prompt"]) != expected_prompt_hash:
        raise InputValidationError(f"{label} generation_prompt hash mismatch")

    shown = [card for card in row["prompt_evidence"] if card.get("shown_in_prompt") is True]
    expected_count = row["prompt_metadata"].get("evidence_count")
    if expected_count != len(shown):
        raise InputValidationError(
            f"{label} has {len(shown)} shown evidence cards but prompt metadata "
            f"records {expected_count}"
        )

    for card_number, card in enumerate(shown, start=1):
        card_label = f"{label} evidence card {card_number}"
        require_keys(
            card,
            [
                "evidence_id",
                "prompt_label",
                "evidence_type",
                "source_label",
                "retrieval_text",
                "retrieval_text_hash",
            ],
            card_label,
        )
        if not isinstance(card["retrieval_text"], str) or not card["retrieval_text"]:
            raise InputValidationError(f"{card_label}.retrieval_text must be non-empty")
        actual_hash = sha256_text(card["retrieval_text"])
        if actual_hash != card["retrieval_text_hash"]:
            raise InputValidationError(
                f"{card_label} retrieval_text hash mismatch: expected "
                f"{card['retrieval_text_hash']}, got {actual_hash}"
            )

    extract_prompt_evidence_section(row, label=label)


def extract_prompt_evidence_section(
    case: dict[str, Any], *, label: str | None = None
) -> str:
    """Return the exact Evidence section shown to the generation model.

    The section is copied from ``generation_prompt`` rather than reconstructed
    from hidden evidence-card metadata. Deterministic checks ensure that every
    shown card's label, source label, and retrieval text occur in the recorded
    prompt in the same order.
    """
    case_label = label or f"generation case {case.get('generation_case_id')!r}"
    prompt = case.get("generation_prompt")
    if not isinstance(prompt, str) or not prompt:
        raise InputValidationError(f"{case_label}.generation_prompt must be non-empty")

    delimiter = "\n\nEvidence\n\n"
    if delimiter not in prompt:
        raise InputValidationError(
            f"{case_label}.generation_prompt does not contain the expected Evidence section"
        )
    _instruction, evidence_body = prompt.split(delimiter, 1)
    evidence_section = "Evidence\n\n" + evidence_body

    shown = [card for card in case["prompt_evidence"] if card.get("shown_in_prompt") is True]
    labels: set[str] = set()
    evidence_ids: set[str] = set()
    search_offset = 0
    for card_number, card in enumerate(shown, start=1):
        prompt_label = card["prompt_label"]
        evidence_id = card["evidence_id"]
        if prompt_label in labels:
            raise InputValidationError(
                f"{case_label} contains duplicate prompt label {prompt_label!r}"
            )
        if evidence_id in evidence_ids:
            raise InputValidationError(
                f"{case_label} contains duplicate evidence ID {evidence_id!r}"
            )
        labels.add(prompt_label)
        evidence_ids.add(evidence_id)

        rendered_record = "\n\n".join(
            [
                prompt_label,
                f"Source:\n{card['source_label']}",
                f"Text:\n{card['retrieval_text']}",
            ]
        )
        record_offset = evidence_section.find(rendered_record, search_offset)
        if record_offset < 0:
            raise InputValidationError(
                f"{case_label} evidence card {card_number} does not match the label, "
                "source, text, or order recorded in generation_prompt"
            )
        search_offset = record_offset + len(rendered_record)

    return evidence_section


def validate_generated_disclosure(row: dict[str, Any], row_number: int) -> None:
    label = f"generated disclosure row {row_number}"
    require_keys(
        row,
        [
            "schema_version",
            "generation_case_id",
            "generation_output_id",
            "generation_status",
            "generated_text",
            "generated_text_hash",
        ],
        label,
    )
    if row["schema_version"] not in SUPPORTED_DISCLOSURE_SCHEMAS:
        raise InputValidationError(
            f"Unsupported generated disclosure schema in {label}: {row['schema_version']!r}"
        )
    if row["generation_status"] != "success":
        raise InputValidationError(
            f"{label} is not successful: {row['generation_status']!r}"
        )
    if not isinstance(row["generated_text"], str) or not row["generated_text"]:
        raise InputValidationError(f"{label}.generated_text must be non-empty")
    actual_hash = sha256_text(row["generated_text"])
    if actual_hash != row["generated_text_hash"]:
        raise InputValidationError(
            f"{label} generated_text hash mismatch: expected "
            f"{row['generated_text_hash']}, got {actual_hash}"
        )


def select_cases(
    cases: list[dict[str, Any]],
    disclosures: list[dict[str, Any]],
    *,
    case_ids: set[str] | None = None,
    company_ids: set[str] | None = None,
    task_ids: set[str] | None = None,
    max_cases: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, int]]:
    for index, case in enumerate(cases, start=1):
        validate_generation_case(case, index)
    for index, disclosure in enumerate(disclosures, start=1):
        validate_generated_disclosure(disclosure, index)

    case_by_id: dict[str, dict[str, Any]] = {}
    for case in cases:
        case_id = case["generation_case_id"]
        if case_id in case_by_id:
            raise InputValidationError(f"Duplicate generation_case_id: {case_id}")
        case_by_id[case_id] = case

    disclosure_by_case: dict[str, dict[str, Any]] = {}
    output_ids: set[str] = set()
    for disclosure in disclosures:
        generation_case_id = disclosure["generation_case_id"]
        output_id = disclosure["generation_output_id"]
        if generation_case_id in disclosure_by_case:
            raise InputValidationError(
                f"Multiple successful disclosures for generation case {generation_case_id}"
            )
        if output_id in output_ids:
            raise InputValidationError(f"Duplicate generation_output_id: {output_id}")
        if generation_case_id not in case_by_id:
            raise InputValidationError(
                f"Generated disclosure references unknown generation case {generation_case_id}"
            )
        disclosure_by_case[generation_case_id] = disclosure
        output_ids.add(output_id)

    selected: list[dict[str, Any]] = []
    filtered_without_disclosure = 0
    for case in cases:
        if case_ids and case["generation_case_id"] not in case_ids:
            continue
        if company_ids and case["company_id"] not in company_ids:
            continue
        if task_ids and case["task_id"] not in task_ids:
            continue
        if case["generation_case_id"] not in disclosure_by_case:
            filtered_without_disclosure += 1
            continue
        selected.append(case)

    if max_cases is not None:
        if max_cases < 1:
            raise InputValidationError("--max-cases must be at least 1")
        selected = selected[:max_cases]
    if not selected:
        raise InputValidationError("No successful generation cases match the filters")

    selected_disclosures = {
        case["generation_case_id"]: disclosure_by_case[case["generation_case_id"]]
        for case in selected
    }
    selection_counts = {
        "generation_cases_total": len(cases),
        "successful_disclosures_total": len(disclosures),
        "selected_successful_cases": len(selected),
        "matching_cases_without_successful_disclosure": filtered_without_disclosure,
    }
    return selected, selected_disclosures, selection_counts


def _evidence_provenance(card: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "evidence_id",
        "prompt_label",
        "evidence_type",
        "source_type",
        "source_year",
        "source_label",
        "source_file",
        "document_type",
        "page_start",
        "page_end",
        "metric",
        "value_text",
        "unit",
        "retrieval_text_hash",
        "prompt_rank_from_retrieval",
    ]
    return {key: card.get(key) for key in keys}


def build_ec_jobs(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build one EC extraction job per generation case.

    The LLM receives only prompt-visible context metadata and the exact
    prompt-visible Evidence section. Hidden evidence IDs and provenance remain
    outside the dynamic input and are restored only after output validation.
    """
    jobs: list[dict[str, Any]] = []
    for case in cases:
        evidence_section = extract_prompt_evidence_section(case)
        dynamic_input = {
            "context_metadata": {
                "company_name": case["company_name"],
                "target_reporting_year": case["target_reporting_year"],
                "task_title": case["task_title"],
            },
            "evidence_section": evidence_section,
        }
        evidence_records = []
        for position, card in enumerate(
            (
                card
                for card in case["prompt_evidence"]
                if card.get("shown_in_prompt") is True
            ),
            start=1,
        ):
            evidence_records.append(
                {
                    "prompt_position": position,
                    "prompt_label": card["prompt_label"],
                    "evidence_id": card["evidence_id"],
                    "retrieval_text": card["retrieval_text"],
                    "retrieval_text_hash": card["retrieval_text_hash"],
                    "evidence_provenance": _evidence_provenance(card),
                }
            )
        jobs.append(
            {
                "task": "ec",
                "job_input_hash": sha256_json(
                    {
                        "generation_case_id": case["generation_case_id"],
                        "dynamic_input": dynamic_input,
                    }
                ),
                "dynamic_input": dynamic_input,
                "evidence_section_sha256": sha256_text(evidence_section),
                "evidence_records": evidence_records,
                "generation_case_id": case["generation_case_id"],
                "case_id": case["case_id"],
                "company_id": case["company_id"],
                "task_id": case["task_id"],
                "target_reporting_year": case["target_reporting_year"],
            }
        )
    jobs.sort(key=lambda item: item["generation_case_id"])
    return jobs


def build_dc_jobs(
    cases: list[dict[str, Any]],
    disclosures_by_case: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for case in cases:
        disclosure = disclosures_by_case[case["generation_case_id"]]
        context_metadata = {
            "company_name": str(case["company_name"]),
            "target_reporting_year": str(case["target_reporting_year"]),
        }
        dynamic_input = {
            "context_metadata": context_metadata,
            "disclosure_text": disclosure["generated_text"],
        }
        jobs.append(
            {
                "task": "dc",
                "job_input_hash": sha256_json(
                    {
                        "generation_output_id": disclosure["generation_output_id"],
                        "dynamic_input": dynamic_input,
                    }
                ),
                "dynamic_input": dynamic_input,
                "source_text": disclosure["generated_text"],
                "context_metadata": context_metadata,
                "generation_case_id": case["generation_case_id"],
                "case_id": case["case_id"],
                "company_id": case["company_id"],
                "task_id": case["task_id"],
                "target_reporting_year": case["target_reporting_year"],
                "generation_output_id": disclosure["generation_output_id"],
                "generated_text_hash": disclosure["generated_text_hash"],
            }
        )
    jobs.sort(key=lambda item: item["generation_case_id"])
    return jobs


def add_call_identity(
    job: dict[str, Any],
    *,
    prompt_version: str,
    prompt_sha256: str,
    schema_version: str,
    schema_sha256: str,
    model_key: str,
    model_id: str,
    model_version: str | None,
    deployment_name: str,
    request_parameters: dict[str, Any],
) -> dict[str, Any]:
    identity = {
        "task": job["task"],
        "job_input_hash": job["job_input_hash"],
        "prompt_version": prompt_version,
        "prompt_sha256": prompt_sha256,
        "schema_version": schema_version,
        "schema_sha256": schema_sha256,
        "model_key": model_key,
        "model_id": model_id,
        "model_version": model_version,
        "deployment_name": deployment_name,
        "request_parameters": request_parameters,
    }
    prefix = "ecx" if job["task"] == "ec" else "dcx"
    enriched = dict(job)
    enriched["call_identity"] = identity
    enriched["call_id"] = f"{prefix}_{sha256_json(identity)[:32]}"
    return enriched


def render_messages(prompt_text: str, dynamic_input: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": canonical_json(dynamic_input)},
    ]


def make_structured_text_config(
    schema: dict[str, Any], *, name: str, strict: bool
) -> dict[str, Any]:
    api_schema = {
        key: value
        for key, value in schema.items()
        if key not in {"$schema", "$id"}
    }
    return {
        "format": {
            "type": "json_schema",
            "name": name,
            "strict": strict,
            "schema": api_schema,
        }
    }


def _find_exact_occurrences(source_text: str, quote: str) -> list[int]:
    starts: list[int] = []
    offset = 0
    while True:
        index = source_text.find(quote, offset)
        if index < 0:
            return starts
        starts.append(index)
        offset = index + 1


def annotate_source_quotes(
    source_text: str, source_quotes: Any
) -> tuple[list[str], list[dict[str, Any]], str]:
    """Attach best-effort exact positions without validating model output.

    Every submitted string is preserved. Missing or repeated matches are
    represented explicitly and never raise an output-validation error.
    """
    quotes = list(source_quotes) if isinstance(source_quotes, list) else []
    spans: list[dict[str, Any]] = []
    statuses: list[str] = []
    for quote_index, quote in enumerate(quotes):
        if not isinstance(quote, str) or not quote:
            spans.append(
                {
                    "quote_index": quote_index,
                    "quote": quote,
                    "start": None,
                    "end": None,
                    "match_count": 0,
                    "candidate_spans": [],
                    "match_status": "not_matchable",
                }
            )
            statuses.append("not_matchable")
            continue
        starts = _find_exact_occurrences(source_text, quote)
        candidate_spans = [
            {"start": start, "end": start + len(quote)} for start in starts
        ]
        if len(starts) == 1:
            status = "exact_unique"
        elif starts:
            status = "exact_ambiguous"
        else:
            status = "unmatched"
        spans.append(
            {
                "quote_index": quote_index,
                "quote": quote,
                "start": starts[0] if starts else None,
                "end": starts[0] + len(quote) if starts else None,
                "match_count": len(starts),
                "candidate_spans": candidate_spans,
                "match_status": status,
            }
        )
        statuses.append(status)

    if not statuses:
        grounding_status = "not_provided"
    elif all(status == "exact_unique" for status in statuses):
        grounding_status = "exact_unique"
    elif all(status in {"exact_unique", "exact_ambiguous"} for status in statuses):
        grounding_status = "exact_with_ambiguity"
    elif any(status == "unmatched" for status in statuses):
        grounding_status = "contains_unmatched_quote"
    else:
        grounding_status = "not_matchable"
    return quotes, spans, grounding_status


def validate_ec_extraction_response(
    payload: Any,
    *,
    evidence_records: list[dict[str, Any]],
    require_unique_quotes: bool,
) -> dict[str, Any]:
    """Validate grouped EC output and restore hidden evidence-card identities."""
    if not isinstance(payload, dict):
        raise OutputValidationError("Response root must be an object")
    if set(payload) != {"evidence_results"}:
        raise OutputValidationError(
            "EC response root fields must be exactly ['evidence_results']"
        )
    results = payload["evidence_results"]
    if not isinstance(results, list):
        raise OutputValidationError("evidence_results must be an array")
    if len(results) != len(evidence_records):
        raise OutputValidationError(
            f"evidence_results must contain exactly {len(evidence_records)} items"
        )

    validated_results: list[dict[str, Any]] = []
    for result_index, (result, record) in enumerate(zip(results, evidence_records)):
        label = f"evidence_results[{result_index}]"
        if not isinstance(result, dict):
            raise OutputValidationError(f"{label} must be an object")
        if set(result) != {"prompt_label", "claims"}:
            raise OutputValidationError(
                f"{label} fields must be exactly ['claims', 'prompt_label']"
            )
        expected_prompt_label = record["prompt_label"]
        if result["prompt_label"] != expected_prompt_label:
            raise OutputValidationError(
                f"{label}.prompt_label must be {expected_prompt_label!r}; "
                "all labels must appear exactly once and in input order"
            )
        claims = result["claims"]
        if not isinstance(claims, list):
            raise OutputValidationError(f"{label}.claims must be an array")

        validated_claims: list[dict[str, Any]] = []
        occurrence_signatures: set[str] = set()
        source_text = record["retrieval_text"]
        for claim_index, claim in enumerate(claims):
            claim_label = f"{label}.claims[{claim_index}]"
            if not isinstance(claim, dict):
                raise OutputValidationError(f"{claim_label} must be an object")
            if set(claim) != {"claim_text", "source_quotes"}:
                raise OutputValidationError(
                    f"{claim_label} fields must be exactly "
                    "['claim_text', 'source_quotes']"
                )
            claim_text = claim["claim_text"]
            if not isinstance(claim_text, str) or not claim_text.strip():
                raise OutputValidationError(
                    f"{claim_label}.claim_text must be non-empty"
                )
            if claim_text != claim_text.strip():
                raise OutputValidationError(
                    f"{claim_label}.claim_text must not have outer whitespace"
                )

            quotes = claim["source_quotes"]
            if not isinstance(quotes, list) or not quotes:
                raise OutputValidationError(
                    f"{claim_label}.source_quotes must be non-empty"
                )
            if len(quotes) != len(set(quotes)):
                raise OutputValidationError(
                    f"{claim_label}.source_quotes contains duplicates"
                )

            spans: list[dict[str, Any]] = []
            for quote_index, quote in enumerate(quotes):
                quote_label = f"{claim_label}.source_quotes[{quote_index}]"
                if not isinstance(quote, str) or not quote:
                    raise OutputValidationError(f"{quote_label} must be non-empty")
                starts = _find_exact_occurrences(source_text, quote)
                if not starts:
                    raise OutputValidationError(
                        f"{quote_label} is not an exact substring of the Text for "
                        f"{expected_prompt_label!r}"
                    )
                if require_unique_quotes and len(starts) != 1:
                    raise OutputValidationError(
                        f"{quote_label} occurs {len(starts)} times in its record; "
                        "a unique quote is required"
                    )
                start = starts[0]
                spans.append(
                    {
                        "quote_index": quote_index,
                        "quote": quote,
                        "start": start,
                        "end": start + len(quote),
                    }
                )

            occurrence_signature = sha256_json(
                {"claim_text": claim_text, "source_spans": spans}
            )
            if occurrence_signature in occurrence_signatures:
                raise OutputValidationError(
                    f"{claim_label} duplicates an already returned claim occurrence "
                    "within the same evidence record"
                )
            occurrence_signatures.add(occurrence_signature)
            validated_claims.append(
                {
                    "claim_text": claim_text,
                    "source_quotes": list(quotes),
                    "source_spans": spans,
                }
            )

        validated_results.append(
            {
                "prompt_label": expected_prompt_label,
                "evidence_id": record["evidence_id"],
                "claims": validated_claims,
            }
        )

    return {"evidence_results": validated_results}


def validate_extraction_response(
    payload: Any,
    *,
    source_text: str,
    context_metadata: dict[str, str],
    require_unique_quotes: bool,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise OutputValidationError("Response root must be an object")
    expected_root_keys = {"claims", "no_claim_reason"}
    if set(payload) != expected_root_keys:
        raise OutputValidationError(
            f"Response root fields must be exactly {sorted(expected_root_keys)}"
        )

    claims = payload["claims"]
    no_claim_reason = payload["no_claim_reason"]
    if not isinstance(claims, list):
        raise OutputValidationError("claims must be an array")
    if claims and no_claim_reason is not None:
        raise OutputValidationError("no_claim_reason must be null when claims are returned")
    if not claims and no_claim_reason not in NO_CLAIM_REASONS:
        raise OutputValidationError(
            "An empty claims array requires a permitted no_claim_reason"
        )

    validated_claims: list[dict[str, Any]] = []
    occurrence_signatures: set[str] = set()
    for claim_index, claim in enumerate(claims):
        label = f"claims[{claim_index}]"
        if not isinstance(claim, dict):
            raise OutputValidationError(f"{label} must be an object")
        expected_claim_keys = {"claim_text", "source_quotes", "context_resolutions"}
        if set(claim) != expected_claim_keys:
            raise OutputValidationError(
                f"{label} fields must be exactly {sorted(expected_claim_keys)}"
            )

        claim_text = claim["claim_text"]
        if not isinstance(claim_text, str) or not claim_text.strip():
            raise OutputValidationError(f"{label}.claim_text must be non-empty")
        if claim_text != claim_text.strip():
            raise OutputValidationError(
                f"{label}.claim_text must not have outer whitespace"
            )

        quotes = claim["source_quotes"]
        if not isinstance(quotes, list) or not quotes:
            raise OutputValidationError(f"{label}.source_quotes must be non-empty")
        if len(quotes) != len(set(quotes)):
            raise OutputValidationError(f"{label}.source_quotes contains duplicates")

        spans: list[dict[str, Any]] = []
        for quote_index, quote in enumerate(quotes):
            quote_label = f"{label}.source_quotes[{quote_index}]"
            if not isinstance(quote, str) or not quote:
                raise OutputValidationError(f"{quote_label} must be non-empty")
            starts = _find_exact_occurrences(source_text, quote)
            if not starts:
                raise OutputValidationError(
                    f"{quote_label} is not an exact substring of the source text"
                )
            if require_unique_quotes and len(starts) != 1:
                raise OutputValidationError(
                    f"{quote_label} occurs {len(starts)} times; a unique quote is required"
                )
            start = starts[0]
            end = start + len(quote)
            if source_text[start:end] != quote:
                raise OutputValidationError(f"Internal offset validation failed for {quote_label}")
            spans.append(
                {
                    "quote_index": quote_index,
                    "quote": quote,
                    "start": start,
                    "end": end,
                }
            )

        resolutions = claim["context_resolutions"]
        if not isinstance(resolutions, list):
            raise OutputValidationError(f"{label}.context_resolutions must be an array")
        validated_resolutions: list[dict[str, str]] = []
        for resolution_index, resolution in enumerate(resolutions):
            resolution_label = f"{label}.context_resolutions[{resolution_index}]"
            if not isinstance(resolution, dict):
                raise OutputValidationError(f"{resolution_label} must be an object")
            expected_resolution_keys = {
                "surface_form",
                "resolved_value",
                "metadata_field",
            }
            if set(resolution) != expected_resolution_keys:
                raise OutputValidationError(
                    f"{resolution_label} fields must be exactly "
                    f"{sorted(expected_resolution_keys)}"
                )
            surface_form = resolution["surface_form"]
            resolved_value = resolution["resolved_value"]
            metadata_field = resolution["metadata_field"]
            if metadata_field not in CONTEXT_METADATA_FIELDS:
                raise OutputValidationError(
                    f"{resolution_label}.metadata_field is not permitted"
                )
            if metadata_field not in context_metadata:
                raise OutputValidationError(
                    f"{resolution_label} uses metadata not supplied to the model"
                )
            if not isinstance(surface_form, str) or not surface_form:
                raise OutputValidationError(
                    f"{resolution_label}.surface_form must be non-empty"
                )
            if surface_form not in source_text:
                raise OutputValidationError(
                    f"{resolution_label}.surface_form is not present in the source text"
                )
            expected_value = str(context_metadata[metadata_field])
            if resolved_value != expected_value:
                raise OutputValidationError(
                    f"{resolution_label}.resolved_value must equal supplied "
                    f"{metadata_field} metadata"
                )
            validated_resolutions.append(
                {
                    "surface_form": surface_form,
                    "resolved_value": resolved_value,
                    "metadata_field": metadata_field,
                }
            )

        validated_claim = {
            "claim_text": claim_text,
            "source_quotes": list(quotes),
            "source_spans": spans,
            "context_resolutions": validated_resolutions,
        }
        occurrence_signature = sha256_json(
            {"claim_text": claim_text, "source_spans": spans}
        )
        if occurrence_signature in occurrence_signatures:
            raise OutputValidationError(
                f"{label} duplicates an already returned claim occurrence"
            )
        occurrence_signatures.add(occurrence_signature)
        validated_claims.append(validated_claim)

    return {
        "claims": validated_claims,
        "no_claim_reason": no_claim_reason,
    }


def make_ec_occurrences(
    jobs: list[dict[str, Any]],
    successful_calls: dict[str, dict[str, Any]],
    *,
    use_parsed_output: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for job in jobs:
        call = successful_calls.get(job["call_id"])
        if not call:
            continue
        records_by_label = {
            record["prompt_label"]: record for record in job["evidence_records"]
        }
        output = (
            call.get("parsed_output")
            if use_parsed_output
            else call.get("validated_output")
        ) or {}
        for result_index, result in enumerate(output.get("evidence_results") or []):
            record = records_by_label[result["prompt_label"]]
            provenance = record["evidence_provenance"]
            for claim_index, claim in enumerate(result.get("claims") or []):
                if use_parsed_output:
                    source_quotes, source_spans, grounding_status = annotate_source_quotes(
                        record["retrieval_text"], claim.get("source_quotes")
                    )
                    occurrence_basis = {
                        "generation_case_id": job["generation_case_id"],
                        "evidence_id": record["evidence_id"],
                        "result_index": result_index,
                        "claim_index": claim_index,
                        "claim_text": claim.get("claim_text"),
                    }
                else:
                    source_spans = claim["source_spans"]
                    source_quotes = list(claim.get("source_quotes") or [])
                    grounding_status = "validated_exact_unique"
                    occurrence_basis = {
                        "generation_case_id": job["generation_case_id"],
                        "evidence_id": record["evidence_id"],
                        "claim_text": claim["claim_text"],
                        "source_spans": source_spans,
                    }
                rows.append(
                    {
                        "schema_version": EC_OCCURRENCE_SCHEMA_VERSION,
                        "generation_case_id": job["generation_case_id"],
                        "case_id": job["case_id"],
                        "ec_occurrence_id": f"eco_{sha256_json(occurrence_basis)[:32]}",
                        "extraction_call_id": job["call_id"],
                        "claim_text": claim["claim_text"],
                        "context_resolutions": [],
                        **(
                            {"unresolved_context": list(claim["unresolved_context"])}
                            if "unresolved_context" in claim
                            else {}
                        ),
                        "source_quotes": source_quotes,
                        "grounding_status": grounding_status,
                        "evidence_id": record["evidence_id"],
                        "prompt_label": provenance["prompt_label"],
                        "retrieval_text_hash": record["retrieval_text_hash"],
                        "source_spans": source_spans,
                        "evidence_provenance": provenance,
                        "_prompt_position": record["prompt_position"],
                        "_claim_index": claim_index,
                    }
                )
    rows.sort(
        key=lambda row: (
            row["generation_case_id"],
            row["_prompt_position"],
            row["_claim_index"]
            if use_parsed_output
            else row["source_spans"][0]["start"],
            row["ec_occurrence_id"],
        )
    )
    for row in rows:
        row.pop("_prompt_position")
        row.pop("_claim_index")
    return rows


def make_dc_occurrences(
    jobs: list[dict[str, Any]],
    successful_calls: dict[str, dict[str, Any]],
    *,
    use_parsed_output: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for job in jobs:
        call = successful_calls.get(job["call_id"])
        if not call:
            continue
        output = (
            call.get("parsed_output")
            if use_parsed_output
            else call.get("validated_output")
        ) or {}
        for claim_index, claim in enumerate(output.get("claims") or []):
            if use_parsed_output:
                source_quotes, source_spans, grounding_status = annotate_source_quotes(
                    job["source_text"], claim.get("source_quotes")
                )
                occurrence_basis = {
                    "generation_case_id": job["generation_case_id"],
                    "generation_output_id": job["generation_output_id"],
                    "claim_index": claim_index,
                    "claim_text": claim.get("claim_text"),
                }
            else:
                source_spans = claim["source_spans"]
                source_quotes = list(claim.get("source_quotes") or [])
                grounding_status = "validated_exact_unique"
                occurrence_basis = {
                    "generation_case_id": job["generation_case_id"],
                    "generation_output_id": job["generation_output_id"],
                    "claim_text": claim["claim_text"],
                    "source_spans": source_spans,
                }
            rows.append(
                {
                    "schema_version": DC_OCCURRENCE_SCHEMA_VERSION,
                    "generation_case_id": job["generation_case_id"],
                    "case_id": job["case_id"],
                    "dc_occurrence_id": f"dco_{sha256_json(occurrence_basis)[:32]}",
                    "extraction_call_id": job["call_id"],
                    "generation_output_id": job["generation_output_id"],
                    "generated_text_hash": job["generated_text_hash"],
                    "claim_text": claim["claim_text"],
                    "context_resolutions": list(claim.get("context_resolutions") or []),
                    **(
                        {"unresolved_context": list(claim["unresolved_context"])}
                        if "unresolved_context" in claim
                        else {}
                    ),
                    "source_quotes": source_quotes,
                    "grounding_status": grounding_status,
                    "source_spans": source_spans,
                    "_claim_index": claim_index,
                }
            )
    rows.sort(
        key=lambda row: (
            row["generation_case_id"],
            row["_claim_index"]
            if use_parsed_output
            else row["source_spans"][0]["start"],
            row["dc_occurrence_id"],
        )
    )
    for row in rows:
        row.pop("_claim_index")
    return rows


def serialize_sdk_response(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        value = response.model_dump()
        return value if isinstance(value, dict) else {"value": value}
    if hasattr(response, "to_dict"):
        value = response.to_dict()
        return value if isinstance(value, dict) else {"value": value}
    return {"repr": repr(response)}


def extract_usage(api_response: dict[str, Any]) -> dict[str, int | None]:
    usage = api_response.get("usage") or {}
    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens"))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens"))
    total_tokens = usage.get("total_tokens")
    if total_tokens is None and isinstance(input_tokens, int) and isinstance(output_tokens, int):
        total_tokens = input_tokens + output_tokens
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }
