#!/usr/bin/env python3
"""Run the retrieval-judge pilot with a configurable Azure OpenAI model.

The frozen prompts, allowed labels, sample, and parser remain model-independent.
API keys are read only from environment variables and are never written to output.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env", override=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, default=Path("retrieval_judge_pilot_sample.csv"))
    parser.add_argument("--config", type=Path, default=Path("retrieval_judge_config.json"))
    parser.add_argument("--judge-model-key", default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("pilot_results"))
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument(
        "--only",
        choices=["both", "contribution", "usability"],
        default="both",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"Missing {label}: {path}")


def render_prompt(template: str, row: dict[str, str]) -> str:
    values = {
        "company_name": row["company_name"],
        "target_reporting_year": row["target_reporting_year"],
        "task_id": row["task_id"],
        "task_title": row["task_title"],
        "task_definition": row["task_definition"],
        "evidence_type": row["evidence_type"],
        "source_year": row["source_year"],
        "source_label": row["source_label"],
        "generation_visible_text": row["generation_visible_text"],
    }
    return template.format(**values)


def validate_prompt_hash(prompt_path: Path, expected_hash: str, prompt_name: str) -> None:
    actual_hash = sha256_file(prompt_path)
    if actual_hash != expected_hash:
        raise RuntimeError(
            f"{prompt_name} prompt hash mismatch.\n"
            f"Expected: {expected_hash}\n"
            f"Actual:   {actual_hash}\n"
            f"File:     {prompt_path}"
        )


def normalize_azure_base_url(endpoint: str) -> str:
    """Convert an Azure resource endpoint or portal target URI to the v1 base URL."""
    endpoint = endpoint.strip()
    if not endpoint:
        raise RuntimeError("Azure OpenAI retrieval-judge endpoint is empty.")

    parts = urlsplit(endpoint)
    if parts.scheme != "https" or not parts.netloc:
        raise RuntimeError(
            "Azure OpenAI retrieval-judge endpoint must be a full HTTPS URL, for example "
            "https://RESOURCE.cognitiveservices.azure.com/"
        )

    path = parts.path.rstrip("/")

    # Accept a copied portal URI such as /openai/responses?api-version=...
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


def get_model_value(
    model_config: dict[str, Any],
    fixed_key: str,
    env_key_field: str,
) -> str | None:
    env_name = model_config.get(env_key_field)
    if env_name and os.environ.get(env_name):
        return os.environ[env_name]
    value = model_config.get(fixed_key)
    return str(value) if value is not None else None


def make_openai_client(*, api_key: str, base_url: str):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The openai package is required for real API calls. "
            "Install it with: pip install --upgrade openai"
        ) from exc

    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=180.0,
        max_retries=4,
    )


def serialize_sdk_response(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if hasattr(response, "to_dict"):
        return response.to_dict()
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


def call_responses_api(
    *,
    client: Any,
    deployment_name: str,
    prompt: str,
    request_parameters: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    response = client.responses.create(
        model=deployment_name,
        input=prompt,
        **request_parameters,
    )
    raw_output = response.output_text or ""
    return raw_output, serialize_sdk_response(response)


def call_chat_completions_api(
    *,
    client: Any,
    model_id: str,
    prompt: str,
    request_parameters: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    response = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        **request_parameters,
    )
    raw_output = response.choices[0].message.content or ""
    return raw_output, serialize_sdk_response(response)


def classify(raw_output: str, allowed: list[str]) -> tuple[str | None, bool]:
    parsed = raw_output.strip()
    return (parsed if parsed in allowed else None, parsed in allowed)


def guard_output_paths(output_paths: list[Path], overwrite: bool) -> None:
    existing = [str(path) for path in output_paths if path.exists()]
    if existing and not overwrite:
        raise RuntimeError(
            "Output files already exist. Use --overwrite or select another output directory:\n"
            + "\n".join(existing)
        )


def main() -> None:
    args = parse_args()

    require_file(args.config, "judge config")
    require_file(args.sample, "pilot sample")

    config = json.loads(args.config.read_text(encoding="utf-8"))
    model_key_env = config.get("current_primary_judge_env")
    model_key = (
        args.judge_model_key
        or os.environ.get(str(model_key_env or ""))
        or config["current_primary_judge"]
    )

    if model_key not in config["models"]:
        raise RuntimeError(f"Unknown judge model key: {model_key}")

    model_config = config["models"][model_key]
    api_style = model_config.get("api_style")
    if api_style not in {"responses", "chat_completions"}:
        raise RuntimeError(f"Unsupported api_style for {model_key}: {api_style!r}")

    prompt_dir = args.config.parent
    contribution_spec = config["prompts"]["contribution"]
    usability_spec = config["prompts"]["usability"]
    contribution_path = prompt_dir / contribution_spec["file"]
    usability_path = prompt_dir / usability_spec["file"]

    require_file(contribution_path, "contribution prompt")
    require_file(usability_path, "usability prompt")

    validate_prompt_hash(contribution_path, contribution_spec["sha256"], "Contribution")
    validate_prompt_hash(usability_path, usability_spec["sha256"], "Usability")

    contribution_template = contribution_path.read_text(encoding="utf-8")
    usability_template = usability_path.read_text(encoding="utf-8")

    with args.sample.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    if args.max_rows is not None:
        if args.max_rows < 1:
            raise RuntimeError("--max-rows must be at least 1.")
        rows = rows[: args.max_rows]

    if not rows:
        raise RuntimeError("The selected pilot sample is empty.")

    client = None
    effective_model_name = model_config.get("model_id")
    effective_base_url = None

    if not args.dry_run:
        api_key_env = model_config.get("api_key_env")
        if not api_key_env:
            raise RuntimeError(f"No api_key_env configured for {model_key}.")

        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing API key environment variable: {api_key_env}")

        if api_style == "responses" and model_config.get("provider") == "azure_openai":
            endpoint_env = model_config.get("endpoint_env")
            endpoint = os.environ.get(endpoint_env or "")
            if not endpoint:
                raise RuntimeError(
                    f"Missing Azure endpoint environment variable: {endpoint_env}"
                )

            effective_base_url = normalize_azure_base_url(endpoint)
            effective_model_name = get_model_value(
                model_config,
                "deployment_name",
                "deployment_name_env",
            )
            if not effective_model_name:
                raise RuntimeError(f"No deployment name configured for {model_key}.")
        else:
            effective_base_url = get_model_value(
                model_config,
                "base_url",
                "base_url_env",
            )
            if not effective_base_url:
                raise RuntimeError(f"No base URL configured for {model_key}.")

        client = make_openai_client(api_key=api_key, base_url=effective_base_url)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results_jsonl_path = args.output_dir / "retrieval_judge_pilot_results.jsonl"
    results_csv_path = args.output_dir / "retrieval_judge_pilot_results.csv"
    manifest_path = args.output_dir / "retrieval_judge_pilot_run_manifest.json"

    guard_output_paths(
        [results_jsonl_path, results_csv_path, manifest_path],
        args.overwrite,
    )

    started_at = utc_now()
    output_rows: list[dict[str, Any]] = []
    raw_records: list[dict[str, Any]] = []
    usage_totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    valid_counts = {"contribution": 0, "usability": 0}
    call_counts = {"contribution": 0, "usability": 0}

    classification_tasks = (
        ["contribution", "usability"] if args.only == "both" else [args.only]
    )

    for row_index, row in enumerate(rows, start=1):
        result: dict[str, Any] = {
            **row,
            "judge_model_key": model_key,
            "judge_model_id": model_config.get("model_id", ""),
            "judge_model_version": model_config.get("model_version", ""),
            "judge_deployment_name": effective_model_name or "",
            "judge_provider": model_config.get("provider", ""),
            "judge_api_style": api_style,
            "contribution_raw_output": "",
            "contribution_classification": "",
            "contribution_output_valid": "",
            "usability_raw_output": "",
            "usability_classification": "",
            "usability_output_valid": "",
        }

        for classification_task in classification_tasks:
            template = (
                contribution_template
                if classification_task == "contribution"
                else usability_template
            )
            prompt = render_prompt(template, row)
            allowed = config["allowed_outputs"][classification_task]

            if args.dry_run:
                raw_output = allowed[0]
                api_response = {
                    "dry_run": True,
                    "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                }
            elif api_style == "responses":
                raw_output, api_response = call_responses_api(
                    client=client,
                    deployment_name=str(effective_model_name),
                    prompt=prompt,
                    request_parameters=model_config.get("request_parameters", {}),
                )
            else:
                raw_output, api_response = call_chat_completions_api(
                    client=client,
                    model_id=str(effective_model_name),
                    prompt=prompt,
                    request_parameters=model_config.get("request_parameters", {}),
                )

            parsed, valid = classify(raw_output, allowed)
            usage = extract_usage(api_response)

            result[f"{classification_task}_raw_output"] = raw_output
            result[f"{classification_task}_classification"] = parsed or ""
            result[f"{classification_task}_output_valid"] = str(valid).lower()

            call_counts[classification_task] += 1
            if valid:
                valid_counts[classification_task] += 1

            for token_key in usage_totals:
                value = usage.get(token_key)
                if isinstance(value, int):
                    usage_totals[token_key] += value

            raw_records.append(
                {
                    "sample_id": row["sample_id"],
                    "classification_task": classification_task,
                    "prompt": prompt,
                    "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    "raw_output": raw_output,
                    "parsed_classification": parsed,
                    "output_valid": valid,
                    "model_key": model_key,
                    "model_id": model_config.get("model_id"),
                    "model_version": model_config.get("model_version"),
                    "deployment_name": effective_model_name,
                    "provider": model_config.get("provider"),
                    "api_style": api_style,
                    "usage": usage,
                    "api_response": api_response,
                    "timestamp_utc": utc_now(),
                }
            )

        output_rows.append(result)
        print(f"[{row_index}/{len(rows)}] {row['sample_id']}", flush=True)

    with results_jsonl_path.open("w", encoding="utf-8") as file:
        for record in raw_records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    fieldnames = list(output_rows[0].keys())
    with results_csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    finished_at = utc_now()

    try:
        import openai
        openai_version = openai.__version__
    except Exception:
        openai_version = None

    run_manifest = {
        "schema_version": "retrieval_judge_pilot_run_manifest_v2",
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "model_key": model_key,
        "model_id": model_config.get("model_id"),
        "model_version": model_config.get("model_version"),
        "deployment_name": effective_model_name,
        "provider": model_config.get("provider"),
        "access_mode": model_config.get("access_mode"),
        "api_style": api_style,
        "base_url": effective_base_url,
        "request_parameters": model_config.get("request_parameters", {}),
        "openai_python_version": openai_version,
        "sample_file": str(args.sample),
        "sample_sha256": sha256_file(args.sample),
        "config_file": str(args.config),
        "config_sha256": sha256_file(args.config),
        "prompt_files": {
            "contribution": {
                "path": str(contribution_path),
                "sha256": sha256_file(contribution_path),
            },
            "usability": {
                "path": str(usability_path),
                "sha256": sha256_file(usability_path),
            },
        },
        "row_count": len(rows),
        "classification_mode": args.only,
        "classification_call_counts": call_counts,
        "valid_output_counts": valid_counts,
        "usage_totals": usage_totals,
        "dry_run": args.dry_run,
        "outputs": {
            "results_jsonl": str(results_jsonl_path),
            "results_csv": str(results_csv_path),
        },
    }

    manifest_path.write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("")
    print("Run complete.")
    print(f"Results CSV:   {results_csv_path}")
    print(f"Results JSONL: {results_jsonl_path}")
    print(f"Run manifest: {manifest_path}")
    print(f"Valid outputs: {valid_counts}")
    print(f"Token usage:   {usage_totals}")


if __name__ == "__main__":
    main()
