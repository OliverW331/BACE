#!/usr/bin/env python3
"""Run W2 hybrid retrieval sanity checks over evidence-card packages.

This script performs deterministic, package-manifest-constrained retrieval for
transparent evidence-card RAG experiments. It is designed for the master thesis
workflow where canonical evidence cards already exist and retrieval embeddings
have already been built.

Core design:
- The candidate pool is loaded from the Company x Target Reporting Year package
  manifest. Company and source-year boundaries are hard filters.
- Query bundles are deterministically rendered from case metadata, task specs,
  and query-bundle templates.
- BM25 and dense retrieval are run over the same eligible corpus.
- Reciprocal Rank Fusion (RRF) fuses ranked lists.
- The script writes review tables, channel diagnostics, summaries, and a run
  manifest. It does not run generation.

Default main method:
    hybrid_rrf = BM25 + dense embedding retrieval + Reciprocal Rank Fusion

Expected input layout:
    evidence_pilot/
      canonical/indexes/all_csv_metric_cards.jsonl
      canonical/indexes/all_pdf_narrative_cards.jsonl
      canonical/indexes/all_pdf_table_row_cards.jsonl
      builds/<package_build_name>/package_index.csv
      builds/<package_build_name>/companies/*/manifests/package_*.json
      embeddings/<embedding_build_name>/...

The embedding artifact layout may differ across runs. The script therefore tries
to auto-discover a vector matrix (.npy) and an evidence_id mapping file. If it
cannot find unambiguous artifacts, it fails during input validation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

SCRIPT_VERSION = "run_w2_retrieval_sanity_check_v2.0"
DEFAULT_ALLOWED_MANIFEST_KEYS = ["csv_metric", "pdf_narrative", "pdf_table_row"]
DEFAULT_ALLOWED_EVIDENCE_TYPES = {"csv_metric", "pdf_table_row", "narrative"}
DEFAULT_RRF_K = 60
DEFAULT_TOP_N_PER_CHANNEL = 50

ACCEPTANCE_CRITERIA: dict[str, list[str]] = {
    "phase_1_input_validation": [
        "The evidence root exists and contains canonical evidence indexes.",
        "The requested package build exists and package manifests can be resolved from package_index.csv or manifest globbing.",
        "The task-spec JSON exists and contains all requested task_ids.",
        "The query-bundle template exists or default deterministic query construction is explicitly enabled.",
        "The retrieval-config JSON exists and declares retrieval_algorithm_key=hybrid_rrf unless overridden explicitly.",
        "The embedding build/model artifacts expose a dense embedding matrix and evidence_id-to-row mapping when dense retrieval is enabled.",
        "The dense query encoder model can be resolved from retrieval config, embedding metadata, or built-in model registry.",
    ],
    "phase_2_case_and_boundary_construction": [
        "Each sanity-check case is Company x Target Reporting Year x ESRS E1 Task.",
        "Each case loads exactly one Company x Target Reporting Year package manifest.",
        "Candidate evidence_card_ids are read from manifest.evidence_card_ids for csv_metric, pdf_narrative, and pdf_table_row only.",
        "All candidate cards exist in the canonical evidence-card lookup.",
        "All candidate cards have company_id equal to the case company_id.",
        "CSV candidates have source_year inside manifest.included_source_years.csv.",
        "PDF candidates have source_year inside manifest.included_source_years.pdf.",
        "pdf_table_markdown is excluded from the main retrieval pool unless explicitly enabled in config.",
    ],
    "phase_3_query_bundle_construction": [
        "Query bundles are rendered deterministically from case metadata, task specs, and query-bundle templates.",
        "Each query bundle contains ordered subqueries with stable subquery_id values.",
        "Query text includes the target reporting year, ESRS reference/task name, and task-specific evidence needs.",
        "Query text does not include generation-only instructions such as paragraph length, professional tone, or write-one-paragraph instructions.",
        "The full query bundle, each subquery, and the template/config files are SHA256-hashed and logged.",
    ],
    "phase_4_bm25_channel": [
        "BM25 runs only over the package-manifest-constrained eligible corpus.",
        "BM25 uses deterministic tokenization and deterministic tie-breaking by evidence_id.",
        "For each subquery, BM25 top_n, ranks, and scores are logged.",
        "Empty or untokenizable evidence_text is handled deterministically and does not crash retrieval.",
    ],
    "phase_5_dense_channel": [
        "Dense retrieval runs only over the same eligible corpus as BM25.",
        "Every eligible evidence_id used for dense retrieval maps to a row in the embedding matrix, or the missing mapping is logged and excluded.",
        "The query prefix, embedding model key, model path, similarity metric, and normalization settings are logged.",
        "Dense ranks and scores are deterministic for the same embeddings and query text, allowing small floating-point tolerance.",
    ],
    "phase_6_hybrid_fusion": [
        "For each subquery, BM25 and dense ranked lists are fused with Reciprocal Rank Fusion.",
        "Bundle-level fusion combines subquery-level fused ranked lists using deterministic RRF.",
        "The RRF k parameter, channel top_n, final top_k values, and algorithm key are logged.",
        "Ties are resolved deterministically by evidence_id.",
    ],
    "phase_7_coverage_and_diagnostics": [
        "The script logs evidence-type coverage for final top-k results for each case.",
        "Fallback retrieval is disabled by default and, if enabled later, must be deterministic and logged.",
        "Channel diagnostics record BM25-only, dense-only, subquery-hybrid, and final bundle rankings sufficiently for audit.",
        "The script distinguishes retrieval failure, missing evidence type, empty candidate pool, and missing embedding mapping conditions.",
    ],
    "phase_8_outputs_and_reproducibility": [
        "The script writes sanity_check_cases.csv, retrieval_query_bundles.jsonl, top-k results JSONL, review table CSV, diagnostics JSONL, summaries, and manifest JSON.",
        "Every retrieved evidence card in the review table includes provenance fields and retrieval_text preview/full text.",
        "The run manifest records script version, input paths, hashes, build names, model key, retrieval config, case count, and output files.",
        "Running the same command twice with the same inputs produces the same cases, query hashes, retrieved evidence IDs, ranks, and scores within floating-point tolerance.",
    ],
}

BUILTIN_DENSE_MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "qwen3-0.6b": {
        "provider": "huggingface",
        "model_name_or_path": "Qwen/Qwen3-Embedding-0.6B",
        "access_type": "open_weight",
        "query_prefix": "",
        "trust_remote_code": True,
    },
    "bge-m3": {
        "provider": "huggingface",
        "model_name_or_path": "BAAI/bge-m3",
        "access_type": "open_weight",
        "query_prefix": "",
        "trust_remote_code": False,
    },
    "snowflake-m-v1.5": {
        "provider": "huggingface",
        "model_name_or_path": "Snowflake/snowflake-arctic-embed-m-v1.5",
        "access_type": "open_weight",
        "query_prefix": "",
        "trust_remote_code": True,
    },
    "nomic-v1.5": {
        "provider": "huggingface",
        "model_name_or_path": "nomic-ai/nomic-embed-text-v1.5",
        "access_type": "open_weight",
        "query_prefix": "search_query: ",
        "trust_remote_code": True,
    },
    "e5-large-instruct": {
        "provider": "huggingface",
        "model_name_or_path": "intfloat/multilingual-e5-large-instruct",
        "access_type": "open_weight",
        "query_prefix": "Instruct: Retrieve relevant ESRS E1 evidence from company evidence cards.\nQuery: ",
        "trust_remote_code": False,
    },
    "text-embedding-3-small": {
        "provider": "openai",
        "model_name_or_path": "text-embedding-3-small",
        "access_type": "closed_api",
        "query_prefix": "",
        "embedding_dimension": 1536,
    },
    # Backward-compatible aliases from earlier retrieval-script drafts.
    "qwen3_embedding_0_6b": {
        "provider": "huggingface",
        "model_name_or_path": "Qwen/Qwen3-Embedding-0.6B",
        "access_type": "open_weight",
        "query_prefix": "",
        "trust_remote_code": True,
    },
    "bge_m3": {
        "provider": "huggingface",
        "model_name_or_path": "BAAI/bge-m3",
        "access_type": "open_weight",
        "query_prefix": "",
        "trust_remote_code": False,
    },
    "multilingual_e5_large_instruct": {
        "provider": "huggingface",
        "model_name_or_path": "intfloat/multilingual-e5-large-instruct",
        "access_type": "open_weight",
        "query_prefix": "Instruct: Retrieve relevant ESRS E1 evidence from company evidence cards.\nQuery: ",
        "trust_remote_code": False,
    },
}

DEFAULT_EVIDENCE_BLOCK_ORDER = ["narrative", "pdf_table_row", "csv_metric"]


@dataclass(frozen=True)
class EmbeddingArtifacts:
    model_dir: Path
    matrix_path: Path
    id_mapping_path: Path
    metadata_path: Path | None
    embedding_matrix: np.ndarray
    evidence_id_to_index: dict[str, int]
    index_to_evidence_id: dict[int, str]
    metadata: dict[str, Any]


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any, *, overwrite: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        fail(f"Output file exists and --overwrite was not set: {path}")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, records: Iterable[Mapping[str, Any]], *, overwrite_first: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite_first else "a"
    with path.open(mode, encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        fieldnames = keys
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: stringify_csv_value(row.get(k)) for k in fieldnames})


def stringify_csv_value(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return value


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip()


def fail(message: str) -> None:
    raise RuntimeError(message)


def log_pass(phase: str, detail: str = "") -> None:
    suffix = f" - {detail}" if detail else ""
    print(f"[PASS] {phase}{suffix}")


def log_warn(phase: str, detail: str = "") -> None:
    suffix = f" - {detail}" if detail else ""
    print(f"[WARN] {phase}{suffix}")


def print_acceptance_criteria() -> None:
    print("\nAcceptance criteria for run_w2_retrieval_sanity_check.py")
    for phase, criteria in ACCEPTANCE_CRITERIA.items():
        print(f"\n{phase}:")
        for item in criteria:
            print(f"  - {item}")
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run package-manifest-constrained hybrid W2 retrieval sanity checks."
    )
    parser.add_argument("--evidence-root", type=Path, default=Path("evidence_pilot"))
    parser.add_argument("--package-build-name", required=True)
    parser.add_argument("--embedding-build-name", required=True)
    parser.add_argument("--embedding-model-key", required=True)
    parser.add_argument("--task-spec", type=Path, required=True)
    parser.add_argument("--query-bundle-template", type=Path, required=True)
    parser.add_argument("--retrieval-config", type=Path, required=True)
    parser.add_argument("--target-years", type=int, nargs="+", required=True)
    parser.add_argument("--task-ids", nargs="+", required=True)
    parser.add_argument("--company-limit", type=int, default=None)
    parser.add_argument("--selected-company-ids", type=Path, default=None)
    parser.add_argument("--top-k", type=int, nargs="+", default=[15, 30, 45])
    parser.add_argument("--per-evidence-type-top-n", type=int, nargs="+", default=[5, 10, 15])
    parser.add_argument(
        "--selection-modes",
        nargs="+",
        choices=["global_top_k", "stratified_by_evidence_type"],
        default=["global_top_k"],
        help="Final evidence selection modes applied after hybrid RRF ranking.",
    )
    parser.add_argument("--candidate-pool", choices=["package_manifest"], default="package_manifest")
    parser.add_argument("--retrieval-algorithm", default="hybrid_rrf")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--include-table-markdown", action="store_true")
    parser.add_argument("--print-acceptance-criteria", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs/build cases but do not run retrieval.")
    parser.add_argument("--openai-api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--openai-base-url", default=None)
    parser.add_argument("--openai-dimensions", type=int, default=None)
    parser.add_argument("--openai-max-retries", type=int, default=3)
    parser.add_argument("--openai-request-timeout", type=float, default=60.0)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.print_acceptance_criteria:
        print_acceptance_criteria()
    if not args.evidence_root.exists():
        fail(f"Evidence root does not exist: {args.evidence_root}")
    if not args.task_spec.exists():
        fail(f"Task spec JSON not found: {args.task_spec}")
    if not args.query_bundle_template.exists():
        fail(f"Query-bundle template JSON not found: {args.query_bundle_template}")
    if not args.retrieval_config.exists():
        fail(f"Retrieval config JSON not found: {args.retrieval_config}")
    if any(k <= 0 for k in args.top_k):
        fail("--top-k values must be positive integers.")
    if any(k <= 0 for k in args.per_evidence_type_top_n):
        fail("--per-evidence-type-top-n values must be positive integers.")
    if args.company_limit is not None and args.company_limit < 1:
        fail("--company-limit must be >= 1.")
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.overwrite:
        fail(f"Output dir exists and is not empty. Use --overwrite or choose another dir: {args.output_dir}")
    if args.output_dir.exists() and args.overwrite:
        # Delete only known output files, not the whole directory, to avoid accidents.
        for path in args.output_dir.glob("*"):
            if path.is_file():
                path.unlink()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    log_pass("phase_1_input_validation", "basic CLI paths and output directory are valid")


def load_task_specs(path: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(path)
    if isinstance(payload, dict) and isinstance(payload.get("tasks"), list):
        tasks = payload["tasks"]
    elif isinstance(payload, dict) and isinstance(payload.get("tasks"), dict):
        tasks = list(payload["tasks"].values())
    elif isinstance(payload, list):
        tasks = payload
    elif isinstance(payload, dict):
        # Accept a dict keyed by task_id if all values look like task records.
        tasks = [value for value in payload.values() if isinstance(value, dict) and "task_id" in value]
    else:
        fail(f"Unsupported task spec structure: {path}")
    task_map: dict[str, dict[str, Any]] = {}
    for task in tasks:
        task_id = clean_text(task.get("task_id"))
        if not task_id:
            fail(f"Task without task_id in {path}")
        task_map[task_id] = task
    return task_map


def load_query_templates(path: Path) -> dict[str, list[dict[str, str]]]:
    payload = read_json(path)
    if isinstance(payload, dict) and "templates" in payload:
        payload = payload["templates"]
    if not isinstance(payload, dict):
        fail(f"Query-bundle template must be a JSON object keyed by task_id or default: {path}")
    templates: dict[str, list[dict[str, str]]] = {}
    for task_id, value in payload.items():
        if isinstance(value, dict) and "subqueries" in value:
            subqueries = value["subqueries"]
        else:
            subqueries = value
        if not isinstance(subqueries, list):
            fail(f"Template for {task_id} must be a list of subqueries.")
        normalized: list[dict[str, str]] = []
        for item in subqueries:
            if not isinstance(item, dict):
                fail(f"Subquery template for {task_id} must be an object.")
            subquery_id = clean_text(item.get("subquery_id"))
            template = clean_text(item.get("template") or item.get("query_text"))
            evidence_need = clean_text(item.get("evidence_need"))
            if not subquery_id or not template:
                fail(f"Each subquery template for {task_id} needs subquery_id and template/query_text.")
            normalized.append({
                "subquery_id": subquery_id,
                "evidence_need": evidence_need,
                "template": template,
            })
        templates[task_id] = normalized
    return templates


def load_retrieval_config(path: Path, algorithm_override: str) -> dict[str, Any]:
    config = read_json(path)
    if not isinstance(config, dict):
        fail(f"Retrieval config must be JSON object: {path}")
    config.setdefault("retrieval_algorithm_key", algorithm_override)
    if config.get("retrieval_algorithm_key") != algorithm_override:
        log_warn(
            "phase_1_input_validation",
            f"CLI retrieval algorithm {algorithm_override} overrides config key {config.get('retrieval_algorithm_key')}",
        )
        config["retrieval_algorithm_key"] = algorithm_override
    if config["retrieval_algorithm_key"] != "hybrid_rrf":
        fail("This script version currently supports --retrieval-algorithm hybrid_rrf only.")
    config.setdefault("bm25", {})
    config.setdefault("dense", {})
    config.setdefault("fusion", {})
    config.setdefault("evidence_type_coverage", {})
    config.setdefault("final_selection", {})
    config["bm25"].setdefault("enabled", True)
    config["bm25"].setdefault("top_n_per_subquery", DEFAULT_TOP_N_PER_CHANNEL)
    config["dense"].setdefault("enabled", True)
    config["dense"].setdefault("top_n_per_subquery", DEFAULT_TOP_N_PER_CHANNEL)
    config["dense"].setdefault("similarity", "cosine")
    config["dense"].setdefault("normalize_query_embedding", True)
    config["dense"].setdefault("normalize_corpus_embeddings", False)
    config["fusion"].setdefault("method", "reciprocal_rank_fusion")
    config["fusion"].setdefault("rrf_k", DEFAULT_RRF_K)
    config["fusion"].setdefault("subquery_fusion", "rrf")
    config["fusion"].setdefault("channel_fusion", "rrf")
    config["evidence_type_coverage"].setdefault("log_coverage", True)
    config["evidence_type_coverage"].setdefault("fallback_enabled", False)
    config["final_selection"].setdefault("available_modes", ["global_top_k", "stratified_by_evidence_type"])
    config["final_selection"].setdefault("global_top_k", {})
    config["final_selection"].setdefault("stratified_by_evidence_type", {})
    config["final_selection"]["stratified_by_evidence_type"].setdefault("evidence_block_order", DEFAULT_EVIDENCE_BLOCK_ORDER)
    config["final_selection"]["stratified_by_evidence_type"].setdefault("deficit_redistribution", False)
    config["final_selection"]["stratified_by_evidence_type"].setdefault("task_specific_quota_used", False)
    if config["evidence_type_coverage"].get("fallback_enabled"):
        fail("Fallback retrieval is intentionally disabled in v2. Set fallback_enabled=false for sanity check.")
    return config


def selected_company_ids(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    if not path.exists():
        fail(f"Selected-company file not found: {path}")
    ids: set[str] = set()
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if "company_id" not in (reader.fieldnames or []):
                fail(f"Selected-company CSV must contain company_id column: {path}")
            for row in reader:
                company_id = clean_text(row.get("company_id"))
                if company_id:
                    ids.add(company_id)
    else:
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            ids.add(text.split(",")[0].strip())
    return ids


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                record = json.loads(text)
            except json.JSONDecodeError as exc:
                fail(f"Invalid JSONL at {path}:{line_no}: {exc}")
            if isinstance(record, dict):
                yield record
            else:
                fail(f"JSONL record is not an object at {path}:{line_no}")


def load_evidence_cards(evidence_root: Path) -> dict[str, dict[str, Any]]:
    index_root = evidence_root / "canonical" / "indexes"
    paths = [
        index_root / "all_csv_metric_cards.jsonl",
        index_root / "all_pdf_narrative_cards.jsonl",
        index_root / "all_pdf_table_row_cards.jsonl",
    ]
    # Fall back to all_pdf_cards if split indexes are unavailable.
    if not any(p.exists() for p in [paths[1], paths[2]]) and (index_root / "all_pdf_cards.jsonl").exists():
        paths.append(index_root / "all_pdf_cards.jsonl")
    card_lookup: dict[str, dict[str, Any]] = {}
    found_any = False
    for path in paths:
        if not path.exists():
            continue
        found_any = True
        for card in read_jsonl(path):
            evidence_id = clean_text(card.get("evidence_id"))
            if not evidence_id:
                continue
            if evidence_id in card_lookup:
                # Keep first occurrence. Split + combined indexes may duplicate PDF cards.
                continue
            card_lookup[evidence_id] = card
    if not found_any:
        fail(f"No canonical evidence-card JSONL indexes found under {index_root}")
    log_pass("phase_1_input_validation", f"loaded {len(card_lookup):,} canonical evidence cards")
    return card_lookup


def load_package_manifests(
    evidence_root: Path,
    package_build_name: str,
    target_years: set[int],
    selected_companies: set[str] | None,
    company_limit: int | None,
) -> list[dict[str, Any]]:
    build_root = evidence_root / "builds" / package_build_name
    if not build_root.exists():
        fail(f"Package build root not found: {build_root}")
    manifest_paths: list[Path] = []
    package_index = build_root / "package_index.csv"
    if package_index.exists():
        with package_index.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if "manifest_path" in (reader.fieldnames or []):
                for row in reader:
                    raw_path = clean_text(row.get("manifest_path"))
                    if not raw_path:
                        continue
                    path = Path(raw_path)
                    if not path.is_absolute():
                        # The original script wrote relative-or-current working directory paths.
                        if path.exists():
                            resolved = path
                        else:
                            resolved = build_root / path
                    else:
                        resolved = path
                    if resolved.exists():
                        manifest_paths.append(resolved)
    if not manifest_paths:
        manifest_paths = sorted(build_root.glob("companies/*/manifests/package_*.json"))
    if not manifest_paths:
        fail(f"No package manifests found under {build_root}")

    manifests: list[dict[str, Any]] = []
    for path in sorted(set(manifest_paths)):
        manifest = read_json(path)
        company_id = clean_text(manifest.get("company_id"))
        target_year = int(manifest.get("target_reporting_year"))
        if target_year not in target_years:
            continue
        if selected_companies is not None and company_id not in selected_companies:
            continue
        manifest["_manifest_path"] = str(path)
        manifests.append(manifest)

    manifests.sort(key=lambda m: (clean_text(m.get("company_name")), clean_text(m.get("company_id")), int(m.get("target_reporting_year"))))
    if selected_companies is None and company_limit is not None:
        company_order: list[str] = []
        seen: set[str] = set()
        for manifest in manifests:
            company_id = clean_text(manifest.get("company_id"))
            if company_id not in seen:
                seen.add(company_id)
                company_order.append(company_id)
            if len(company_order) >= company_limit:
                break
        keep = set(company_order[:company_limit])
        manifests = [m for m in manifests if clean_text(m.get("company_id")) in keep]

    if not manifests:
        fail("No manifests remain after target-year/company filters.")
    log_pass("phase_1_input_validation", f"loaded {len(manifests):,} package manifests after filters")
    return manifests


def discover_embedding_artifacts(
    evidence_root: Path,
    embedding_build_name: str,
    embedding_model_key: str,
    config: dict[str, Any],
) -> EmbeddingArtifacts:
    if not config.get("dense", {}).get("enabled", True):
        fail("Dense retrieval is disabled, but hybrid_rrf requires dense channel in this script version.")
    build_root = evidence_root / "embeddings" / embedding_build_name
    if not build_root.exists():
        fail(f"Embedding build root not found: {build_root}")

    possible_dirs = [
        build_root / embedding_model_key,
        build_root / "models" / embedding_model_key,
        build_root / sanitize_key(embedding_model_key),
    ]
    possible_dirs = [path for path in possible_dirs if path.exists()]
    if not possible_dirs:
        # Fall back to build root only when the user supplied explicit artifact paths in config.
        dense_cfg = config.get("dense", {})
        if clean_text(dense_cfg.get("embedding_matrix_path")) or clean_text(dense_cfg.get("id_mapping_path")):
            possible_dirs = [build_root]
        else:
            fail(f"No embedding model directory candidates found under {build_root} for model key {embedding_model_key}")

    matrix_path = find_embedding_matrix(possible_dirs, config)
    mapping_path = find_id_mapping(possible_dirs, config)
    metadata_path = find_metadata(possible_dirs)
    metadata = read_json(metadata_path) if metadata_path else {}

    matrix = np.load(matrix_path, mmap_mode="r")
    if matrix.ndim != 2:
        fail(f"Embedding matrix must be 2-D: {matrix_path}, shape={matrix.shape}")
    evidence_id_to_index, index_to_evidence_id = load_embedding_id_mapping(mapping_path)
    if not evidence_id_to_index:
        fail(f"Empty evidence_id mapping: {mapping_path}")
    max_index = max(evidence_id_to_index.values())
    if max_index >= matrix.shape[0]:
        fail(
            f"Mapping row index {max_index} exceeds embedding matrix rows {matrix.shape[0]}: {mapping_path}"
        )
    log_pass(
        "phase_1_input_validation",
        f"loaded dense matrix {matrix.shape} and {len(evidence_id_to_index):,} evidence-id mappings",
    )
    return EmbeddingArtifacts(
        model_dir=matrix_path.parent,
        matrix_path=matrix_path,
        id_mapping_path=mapping_path,
        metadata_path=metadata_path,
        embedding_matrix=matrix,
        evidence_id_to_index=evidence_id_to_index,
        index_to_evidence_id=index_to_evidence_id,
        metadata=metadata,
    )


def sanitize_key(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value)


def find_embedding_matrix(possible_dirs: list[Path], config: dict[str, Any]) -> Path:
    explicit = clean_text(config.get("dense", {}).get("embedding_matrix_path"))
    if explicit:
        path = Path(explicit)
        if path.exists():
            return path
        fail(f"Configured dense.embedding_matrix_path does not exist: {path}")
    names = ["embeddings.npy", "evidence_embeddings.npy", "embedding_matrix.npy", "vectors.npy", "matrix.npy"]
    candidates: list[Path] = []
    for directory in possible_dirs:
        for name in names:
            candidates.extend(directory.rglob(name))
    if not candidates:
        for directory in possible_dirs:
            candidates.extend(directory.rglob("*.npy"))
    if not candidates:
        fail("Could not discover embedding matrix .npy file. Configure dense.embedding_matrix_path.")
    candidates = sorted(set(candidates), key=lambda p: (preferred_matrix_score(p), str(p)))
    return candidates[0]


def preferred_matrix_score(path: Path) -> tuple[int, int]:
    name = path.name.lower()
    score = 100
    for token in ["embedding", "embeddings", "vector", "vectors", "matrix"]:
        if token in name:
            score -= 10
    if "query" in name:
        score += 50
    try:
        size_score = -int(path.stat().st_size // 1024)
    except OSError:
        size_score = 0
    return (score, size_score)


def find_id_mapping(possible_dirs: list[Path], config: dict[str, Any]) -> Path:
    explicit = clean_text(config.get("dense", {}).get("id_mapping_path"))
    if explicit:
        path = Path(explicit)
        if path.exists():
            return path
        fail(f"Configured dense.id_mapping_path does not exist: {path}")
    names = [
        "card_metadata.jsonl",
        "evidence_ids.jsonl",
        "evidence_ids.json",
        "index_to_evidence_id.json",
        "evidence_id_to_index.json",
        "embedding_metadata.jsonl",
        "metadata.jsonl",
        "embedding_records.jsonl",
        "evidence_ids.csv",
        "embedding_metadata.csv",
        "metadata.csv",
    ]
    candidates: list[Path] = []
    for directory in possible_dirs:
        for name in names:
            candidates.extend(directory.rglob(name))
    if not candidates:
        for directory in possible_dirs:
            for pattern in ["*evidence*id*.json*", "*metadata*.jsonl", "*metadata*.csv"]:
                candidates.extend(directory.rglob(pattern))
    if not candidates:
        fail("Could not discover evidence_id mapping file. Configure dense.id_mapping_path.")
    candidates = sorted(set(candidates), key=lambda p: (preferred_mapping_score(p), str(p)))
    return candidates[0]


def preferred_mapping_score(path: Path) -> int:
    name = path.name.lower()
    score = 100
    if name == "card_metadata.jsonl":
        score -= 70
    if name == "evidence_ids.jsonl":
        score -= 50
    if "evidence" in name and "id" in name:
        score -= 20
    if "metadata" in name:
        score -= 5
    return score


def find_metadata(possible_dirs: list[Path]) -> Path | None:
    names = ["embedding_manifest.json", "manifest.json", "model_config.json", "metadata.json"]
    candidates: list[Path] = []
    for directory in possible_dirs:
        for name in names:
            candidates.extend(directory.rglob(name))
    return sorted(set(candidates), key=lambda p: str(p))[0] if candidates else None


def load_embedding_id_mapping(path: Path) -> tuple[dict[str, int], dict[int, str]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        records = list(read_jsonl(path))
        return mapping_from_records(records)
    if suffix == ".json":
        payload = read_json(path)
        return mapping_from_json_payload(payload)
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return mapping_from_records(list(reader))
    fail(f"Unsupported mapping file format: {path}")


def mapping_from_json_payload(payload: Any) -> tuple[dict[str, int], dict[int, str]]:
    if isinstance(payload, list):
        if all(isinstance(x, str) for x in payload):
            index_to_id = {idx: evidence_id for idx, evidence_id in enumerate(payload)}
            id_to_index = {evidence_id: idx for idx, evidence_id in index_to_id.items()}
            return id_to_index, index_to_id
        if all(isinstance(x, dict) for x in payload):
            return mapping_from_records(payload)
    if isinstance(payload, dict):
        # evidence_id -> index
        if payload and all(isinstance(k, str) and isinstance(v, int) for k, v in payload.items()):
            id_to_index = {str(k): int(v) for k, v in payload.items()}
            index_to_id = {v: k for k, v in id_to_index.items()}
            return id_to_index, index_to_id
        # index -> evidence_id
        if payload and all(str(k).isdigit() and isinstance(v, str) for k, v in payload.items()):
            index_to_id = {int(k): str(v) for k, v in payload.items()}
            id_to_index = {v: k for k, v in index_to_id.items()}
            return id_to_index, index_to_id
        for key in ["records", "items", "embeddings", "metadata", "evidence_ids"]:
            if key in payload:
                return mapping_from_json_payload(payload[key])
    fail("Could not parse embedding evidence_id mapping payload.")


def mapping_from_records(records: Sequence[Mapping[str, Any]]) -> tuple[dict[str, int], dict[int, str]]:
    id_to_index: dict[str, int] = {}
    index_to_id: dict[int, str] = {}
    for default_index, record in enumerate(records):
        evidence_id = clean_text(
            record.get("evidence_id")
            or record.get("id")
            or record.get("card_id")
            or record.get("evidence_card_id")
        )
        if not evidence_id:
            continue
        raw_index = record.get("embedding_row")
        if raw_index is None:
            raw_index = record.get("embedding_index")
        if raw_index is None:
            raw_index = record.get("index")
        if raw_index is None:
            raw_index = record.get("row_index")
        index = int(raw_index) if clean_text(raw_index) else default_index
        id_to_index[evidence_id] = index
        index_to_id[index] = evidence_id
    return id_to_index, index_to_id


class SimpleBM25:
    def __init__(self, docs_tokens: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.docs_tokens = docs_tokens
        self.k1 = k1
        self.b = b
        self.n_docs = len(docs_tokens)
        self.doc_lengths = [len(doc) for doc in docs_tokens]
        self.avgdl = sum(self.doc_lengths) / max(1, self.n_docs)
        self.doc_freqs: list[Counter[str]] = [Counter(doc) for doc in docs_tokens]
        df: Counter[str] = Counter()
        for doc_counter in self.doc_freqs:
            for token in doc_counter.keys():
                df[token] += 1
        self.idf = {
            token: math.log(1 + (self.n_docs - freq + 0.5) / (freq + 0.5))
            for token, freq in df.items()
        }

    def score(self, query_tokens: list[str]) -> list[float]:
        scores: list[float] = []
        q_terms = list(dict.fromkeys(query_tokens))
        for doc_idx, doc_counter in enumerate(self.doc_freqs):
            dl = self.doc_lengths[doc_idx]
            score = 0.0
            for token in q_terms:
                tf = doc_counter.get(token, 0)
                if tf <= 0:
                    continue
                idf = self.idf.get(token, 0.0)
                denom = tf + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1e-9))
                score += idf * (tf * (self.k1 + 1)) / denom
            scores.append(float(score))
        return scores


def tokenize(text: str) -> list[str]:
    # Keep technical terms/numbers useful for ESRS retrieval: E1-6, Scope 1, tCO2e, 2023.
    tokens = re.findall(r"[A-Za-z]+\d*|\d+(?:\.\d+)?|[A-Za-z]+-[A-Za-z0-9]+|E\d+-\d+", text.lower())
    return tokens


def build_cases(
    manifests: list[dict[str, Any]],
    requested_task_ids: list[str],
    task_specs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for manifest in manifests:
        company_id = clean_text(manifest.get("company_id"))
        target_year = int(manifest.get("target_reporting_year"))
        for task_id in requested_task_ids:
            task = task_specs[task_id]
            case_id = f"{company_id}__ty{target_year}__{task_id}__W2__sanity"
            cases.append(
                {
                    "case_id": case_id,
                    "company_id": company_id,
                    "company_slug": clean_text(manifest.get("company_slug")),
                    "company_name": clean_text(manifest.get("company_name")),
                    "industry": clean_text(manifest.get("primary_sics_sector")),
                    "target_reporting_year": target_year,
                    "task_id": task_id,
                    "esrs_reference": clean_text(task.get("esrs_reference")),
                    "task_name": clean_text(task.get("task_name")),
                    "workflow": "W2",
                    "run_id": "sanity",
                    "package_id": clean_text(manifest.get("package_id")),
                    "manifest_path": clean_text(manifest.get("_manifest_path")),
                    "manifest": manifest,
                }
            )
    cases.sort(key=lambda c: (c["company_id"], c["target_reporting_year"], c["task_id"]))
    log_pass("phase_2_case_and_boundary_construction", f"built {len(cases):,} W2 sanity-check cases")
    return cases


def get_allowed_evidence_ids(manifest: dict[str, Any], include_table_markdown: bool = False) -> list[str]:
    ids_by_type = manifest.get("evidence_card_ids", {})
    keys = list(DEFAULT_ALLOWED_MANIFEST_KEYS)
    if include_table_markdown:
        keys.append("pdf_table_markdown")
    allowed: list[str] = []
    for key in keys:
        value = ids_by_type.get(key, [])
        if isinstance(value, list):
            allowed.extend(clean_text(x) for x in value if clean_text(x))
    # Stable de-duplication.
    return sorted(set(allowed))


def validate_candidate_pool(case: dict[str, Any], cards: dict[str, dict[str, Any]], include_table_markdown: bool) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    manifest = case["manifest"]
    allowed_ids = get_allowed_evidence_ids(manifest, include_table_markdown)
    if not allowed_ids:
        return [], [], {"boundary_validation_passed": True, "candidate_pool_warning": "empty_allowed_evidence_ids"}
    csv_years = {int(y) for y in manifest.get("included_source_years", {}).get("csv", [])}
    pdf_years = {int(y) for y in manifest.get("included_source_years", {}).get("pdf", [])}
    company_id = case["company_id"]
    eligible_cards: list[dict[str, Any]] = []
    missing = 0
    errors: list[str] = []
    for evidence_id in allowed_ids:
        card = cards.get(evidence_id)
        if not card:
            missing += 1
            continue
        card_company = clean_text(card.get("company_id"))
        if card_company != company_id:
            errors.append(f"wrong_company:{evidence_id}:{card_company}")
            continue
        evidence_type = clean_text(card.get("evidence_type"))
        source_type = clean_text(card.get("source_type"))
        try:
            source_year = int(card.get("source_year"))
        except (TypeError, ValueError):
            errors.append(f"missing_or_invalid_source_year:{evidence_id}")
            continue
        if source_type == "csv" or evidence_type == "csv_metric":
            if source_year not in csv_years:
                errors.append(f"csv_year_out_of_window:{evidence_id}:{source_year}")
                continue
        elif source_type == "pdf" or evidence_type in {"narrative", "pdf_table_row", "pdf_table_markdown"}:
            if source_year not in pdf_years:
                errors.append(f"pdf_year_out_of_window:{evidence_id}:{source_year}")
                continue
            if evidence_type == "pdf_table_markdown" and not include_table_markdown:
                errors.append(f"table_markdown_not_allowed:{evidence_id}")
                continue
        else:
            errors.append(f"unknown_source_type:{evidence_id}:{source_type}:{evidence_type}")
            continue
        if evidence_type not in DEFAULT_ALLOWED_EVIDENCE_TYPES and evidence_type != "pdf_table_markdown":
            errors.append(f"evidence_type_not_allowed:{evidence_id}:{evidence_type}")
            continue
        eligible_cards.append(card)
    if errors:
        fail(
            f"Boundary validation failed for case {case['case_id']} with {len(errors)} errors. "
            f"First errors: {errors[:5]}"
        )
    validation = {
        "boundary_validation_passed": True,
        "missing_manifest_references": missing,
        "allowed_evidence_count": len(allowed_ids),
        "eligible_corpus_size": len(eligible_cards),
        "csv_source_years": sorted(csv_years),
        "pdf_source_years": sorted(pdf_years),
    }
    return allowed_ids, eligible_cards, validation


def render_query_bundle(
    case: dict[str, Any],
    task: dict[str, Any],
    templates: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    task_id = case["task_id"]
    subquery_templates = templates.get(task_id) or templates.get("default")
    if not subquery_templates:
        fail(f"No query-bundle template found for task_id {task_id} and no default template provided.")
    values = query_template_values(case, task)
    subqueries: list[dict[str, Any]] = []
    for item in subquery_templates:
        text = item["template"].format(**values)
        subqueries.append(
            {
                "subquery_id": item["subquery_id"],
                "evidence_need": item.get("evidence_need", ""),
                "query_text": text,
                "subquery_hash": sha256_text(text),
            }
        )
    bundle_payload = {
        "case_id": case["case_id"],
        "query_bundle_id": f"{case['case_id']}__query_bundle_v1",
        "task_id": task_id,
        "target_reporting_year": case["target_reporting_year"],
        "subqueries": subqueries,
    }
    bundle_payload["query_bundle_hash"] = sha256_text(json.dumps(bundle_payload, ensure_ascii=False, sort_keys=True))
    return bundle_payload


def query_template_values(case: dict[str, Any], task: dict[str, Any]) -> dict[str, str]:
    expected_content = task.get("expected_evidence_content") or []
    if isinstance(expected_content, str):
        expected_content = [expected_content]
    query_facets = task.get("query_facets") or []
    if isinstance(query_facets, str):
        query_facets = [query_facets]
    return {
        "case_id": case["case_id"],
        "company_id": case["company_id"],
        "company_name": case["company_name"],
        "target_reporting_year": str(case["target_reporting_year"]),
        "task_id": case["task_id"],
        "esrs_reference": case.get("esrs_reference", ""),
        "task_name": case.get("task_name", ""),
        "retrieval_intent": clean_text(task.get("retrieval_intent")),
        "expected_evidence_content": "; ".join(clean_text(x) for x in expected_content),
        "expected_evidence_content_bullets": "\n".join(f"- {clean_text(x)}" for x in expected_content),
        "query_facets": "; ".join(clean_text(x) for x in query_facets),
    }


def rank_bm25(query_text: str, eligible_cards: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    docs = [clean_text(card.get("retrieval_text") or card.get("original_text") or "") for card in eligible_cards]
    doc_tokens = [tokenize(text) for text in docs]
    query_tokens = tokenize(query_text)
    if not eligible_cards:
        return []
    model = SimpleBM25(doc_tokens)
    scores = model.score(query_tokens)
    rows = []
    for idx, (card, score) in enumerate(zip(eligible_cards, scores)):
        rows.append({
            "evidence_id": card["evidence_id"],
            "score": float(score),
            "_tie": card["evidence_id"],
        })
    rows.sort(key=lambda r: (-r["score"], r["_tie"]))
    ranked = []
    for rank, row in enumerate(rows[:top_n], start=1):
        ranked.append({"evidence_id": row["evidence_id"], "rank": rank, "score": row["score"]})
    return ranked


_QUERY_ENCODER_CACHE: dict[str, Any] = {}


def resolve_dense_model_config(embedding_model_key: str, retrieval_config: dict[str, Any], artifacts: EmbeddingArtifacts) -> dict[str, Any]:
    """Resolve the query-side dense encoder from the embedding artifact manifest first.

    The embedding manifest is the source of truth because the query-side encoder must
    match the document-side embedding model already used to create embeddings.npy.
    Retrieval config may still provide runtime settings such as normalization and
    OpenAI request behavior, but it should not silently override the artifact model.
    """
    dense_config = retrieval_config.get("dense", {})
    registry_entry = dict(BUILTIN_DENSE_MODEL_REGISTRY.get(embedding_model_key, {}))
    manifest = artifacts.metadata or {}

    resolved: dict[str, Any] = {}
    resolved.update(registry_entry)

    # Prefer artifact-manifest fields written by embed_evidence_cards.py v2.
    for src_key, dst_key in [
        ("provider", "provider"),
        ("model_name_or_path", "model_name_or_path"),
        ("model_name", "model_name_or_path"),
        ("sentence_transformers_model_name", "model_name_or_path"),
        ("query_prefix", "query_prefix"),
        ("access_type", "access_type"),
        ("trust_remote_code", "trust_remote_code"),
        ("embedding_dimension", "embedding_dimension"),
    ]:
        value = manifest.get(src_key)
        if isinstance(value, bool) or clean_text(value):
            resolved[dst_key] = value

    # Retrieval config can fill missing fields, but should not override the artifact identity.
    for src_key, dst_key in [
        ("provider", "provider"),
        ("model_name_or_path", "model_name_or_path"),
        ("model_name", "model_name_or_path"),
        ("sentence_transformers_model_name", "model_name_or_path"),
        ("query_prefix", "query_prefix"),
        ("trust_remote_code", "trust_remote_code"),
    ]:
        if dst_key not in resolved or not (isinstance(resolved.get(dst_key), bool) or clean_text(resolved.get(dst_key))):
            value = dense_config.get(src_key)
            if isinstance(value, bool) or clean_text(value):
                resolved[dst_key] = value

    if not clean_text(resolved.get("model_name_or_path")):
        fail("Could not resolve dense query encoder model from embedding manifest, registry, or retrieval config.")

    resolved.setdefault("provider", "huggingface")
    resolved.setdefault("query_prefix", "")
    resolved["normalize_query_embedding"] = bool(dense_config.get("normalize_query_embedding", True))
    # Corpus embeddings were already normalized during embedding build; keep this false unless explicitly requested.
    resolved["normalize_corpus_embeddings"] = bool(dense_config.get("normalize_corpus_embeddings", False))
    resolved["similarity"] = clean_text(dense_config.get("similarity")) or "cosine"
    resolved["openai_api_key_env"] = clean_text(dense_config.get("openai_api_key_env")) or "OPENAI_API_KEY"
    resolved["openai_base_url"] = dense_config.get("openai_base_url")
    resolved["openai_dimensions"] = dense_config.get("openai_dimensions")
    resolved["openai_max_retries"] = int(dense_config.get("openai_max_retries", 3))
    resolved["openai_request_timeout"] = float(dense_config.get("openai_request_timeout", 60.0))
    resolved["artifact_model_dir"] = str(artifacts.model_dir)
    resolved["artifact_manifest_path"] = str(artifacts.metadata_path) if artifacts.metadata_path else None
    return resolved


def embed_query(query_text: str, model_config: dict[str, Any]) -> np.ndarray:
    provider = clean_text(model_config.get("provider")) or "huggingface"
    query_prefix = model_config.get("query_prefix", "") or ""
    query_for_embedding = f"{query_prefix}{query_text}"
    if provider == "openai":
        return embed_query_openai(query_for_embedding, model_config)
    if provider == "huggingface":
        return embed_query_huggingface(query_for_embedding, model_config)
    fail(f"Unsupported dense query embedding provider: {provider}")


def embed_query_huggingface(query_for_embedding: str, model_config: dict[str, Any]) -> np.ndarray:
    model_name = model_config["model_name_or_path"]
    trust_remote_code = bool(model_config.get("trust_remote_code", False))
    cache_key = f"huggingface::{model_name}::{trust_remote_code}"
    if cache_key not in _QUERY_ENCODER_CACHE:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError:
            fail("sentence-transformers is required for Hugging Face dense query embedding. Install sentence-transformers.")
        try:
            _QUERY_ENCODER_CACHE[cache_key] = SentenceTransformer(model_name, trust_remote_code=trust_remote_code)
        except TypeError:
            # Older sentence-transformers versions may not expose trust_remote_code.
            _QUERY_ENCODER_CACHE[cache_key] = SentenceTransformer(model_name)
    model = _QUERY_ENCODER_CACHE[cache_key]
    vector = model.encode([query_for_embedding], convert_to_numpy=True, show_progress_bar=False)[0].astype(np.float32)
    if model_config.get("normalize_query_embedding", True):
        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector = vector / norm
    return vector.astype(np.float32)


def embed_query_openai(query_for_embedding: str, model_config: dict[str, Any]) -> np.ndarray:
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        fail("OpenAI query embedding requires the openai package. Install with: pip install openai")
    import os

    api_key_env = clean_text(model_config.get("openai_api_key_env")) or "OPENAI_API_KEY"
    api_key = os.environ.get(api_key_env)
    if not api_key:
        fail(f"OpenAI query embedding requested, but environment variable {api_key_env} is not set.")
    base_url = model_config.get("openai_base_url")
    client_key = f"openai::{base_url or 'default'}::{api_key_env}"
    if client_key not in _QUERY_ENCODER_CACHE:
        kwargs: dict[str, Any] = {
            "api_key": api_key,
            "max_retries": int(model_config.get("openai_max_retries", 3)),
            "timeout": float(model_config.get("openai_request_timeout", 60.0)),
        }
        if base_url:
            kwargs["base_url"] = base_url
        _QUERY_ENCODER_CACHE[client_key] = OpenAI(**kwargs)
    client = _QUERY_ENCODER_CACHE[client_key]
    create_kwargs: dict[str, Any] = {
        "model": model_config["model_name_or_path"],
        "input": [query_for_embedding],
    }
    dimensions = model_config.get("openai_dimensions")
    if dimensions:
        create_kwargs["dimensions"] = int(dimensions)
    response = client.embeddings.create(**create_kwargs)
    vector = np.asarray(response.data[0].embedding, dtype=np.float32)
    if model_config.get("normalize_query_embedding", True):
        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector = vector / norm
    return vector.astype(np.float32)


def rank_dense(
    query_text: str,
    eligible_cards: list[dict[str, Any]],
    artifacts: EmbeddingArtifacts,
    model_config: dict[str, Any],
    top_n: int,
) -> tuple[list[dict[str, Any]], int]:
    if not eligible_cards:
        return [], 0
    query_vec = embed_query(query_text, model_config)
    if query_vec.shape[0] != artifacts.embedding_matrix.shape[1]:
        fail(
            f"Query vector dim {query_vec.shape[0]} != corpus embedding dim {artifacts.embedding_matrix.shape[1]}"
        )
    indices: list[int] = []
    ids: list[str] = []
    missing_mapping = 0
    for card in eligible_cards:
        evidence_id = card["evidence_id"]
        idx = artifacts.evidence_id_to_index.get(evidence_id)
        if idx is None:
            missing_mapping += 1
            continue
        ids.append(evidence_id)
        indices.append(idx)
    if not indices:
        return [], missing_mapping
    matrix = np.asarray(artifacts.embedding_matrix[indices], dtype=np.float32)
    if model_config.get("normalize_corpus_embeddings", False):
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        matrix = matrix / norms
    scores = matrix @ query_vec
    rows = [
        {"evidence_id": eid, "score": float(score), "_tie": eid}
        for eid, score in zip(ids, scores.tolist())
    ]
    rows.sort(key=lambda r: (-r["score"], r["_tie"]))
    ranked = []
    for rank, row in enumerate(rows[:top_n], start=1):
        ranked.append({"evidence_id": row["evidence_id"], "rank": rank, "score": row["score"]})
    return ranked, missing_mapping


def rrf_fuse(named_ranked_lists: list[tuple[str, list[dict[str, Any]]]], rrf_k: int) -> list[dict[str, Any]]:
    scores: dict[str, float] = defaultdict(float)
    details: dict[str, dict[str, Any]] = defaultdict(dict)
    for list_name, ranked in named_ranked_lists:
        for item in ranked:
            evidence_id = item["evidence_id"]
            rank = int(item["rank"])
            scores[evidence_id] += 1.0 / (rrf_k + rank)
            details[evidence_id][f"{list_name}_rank"] = rank
            details[evidence_id][f"{list_name}_score"] = item.get("score")
    fused = []
    for evidence_id, score in scores.items():
        row = {"evidence_id": evidence_id, "rrf_score": float(score)}
        row.update(details[evidence_id])
        fused.append(row)
    fused.sort(key=lambda r: (-r["rrf_score"], r["evidence_id"]))
    for rank, row in enumerate(fused, start=1):
        row["rank"] = rank
    return fused


def run_case_retrieval(
    case: dict[str, Any],
    task: dict[str, Any],
    query_bundle: dict[str, Any],
    eligible_cards: list[dict[str, Any]],
    artifacts: EmbeddingArtifacts,
    dense_model_config: dict[str, Any],
    retrieval_config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    bm25_top_n = int(retrieval_config["bm25"].get("top_n_per_subquery", DEFAULT_TOP_N_PER_CHANNEL))
    dense_top_n = int(retrieval_config["dense"].get("top_n_per_subquery", DEFAULT_TOP_N_PER_CHANNEL))
    rrf_k = int(retrieval_config["fusion"].get("rrf_k", DEFAULT_RRF_K))
    diagnostics: list[dict[str, Any]] = []
    subquery_fused_lists: list[tuple[str, list[dict[str, Any]]]] = []
    best_bm25: dict[str, dict[str, Any]] = {}
    best_dense: dict[str, dict[str, Any]] = {}
    missing_embedding_mappings = 0

    for subquery in query_bundle["subqueries"]:
        subquery_id = subquery["subquery_id"]
        text = subquery["query_text"]
        bm25_ranked = rank_bm25(text, eligible_cards, bm25_top_n)
        dense_ranked, missing = rank_dense(text, eligible_cards, artifacts, dense_model_config, dense_top_n)
        missing_embedding_mappings += missing
        for item in bm25_ranked:
            eid = item["evidence_id"]
            if eid not in best_bm25 or item["rank"] < best_bm25[eid]["rank"]:
                best_bm25[eid] = {"rank": item["rank"], "score": item["score"], "subquery_id": subquery_id}
        for item in dense_ranked:
            eid = item["evidence_id"]
            if eid not in best_dense or item["rank"] < best_dense[eid]["rank"]:
                best_dense[eid] = {"rank": item["rank"], "score": item["score"], "subquery_id": subquery_id}
        subquery_fused = rrf_fuse(
            [(f"{subquery_id}__bm25", bm25_ranked), (f"{subquery_id}__dense", dense_ranked)],
            rrf_k,
        )
        subquery_fused_lists.append((subquery_id, subquery_fused))
        diagnostics.append(
            {
                "case_id": case["case_id"],
                "task_id": case["task_id"],
                "query_bundle_id": query_bundle["query_bundle_id"],
                "subquery_id": subquery_id,
                "subquery_hash": subquery["subquery_hash"],
                "retrieval_algorithm_key": retrieval_config["retrieval_algorithm_key"],
                "bm25_top_n": bm25_top_n,
                "dense_top_n": dense_top_n,
                "rrf_k": rrf_k,
                "bm25_top_ids": [x["evidence_id"] for x in bm25_ranked],
                "bm25_scores": [x["score"] for x in bm25_ranked],
                "dense_top_ids": [x["evidence_id"] for x in dense_ranked],
                "dense_scores": [x["score"] for x in dense_ranked],
                "subquery_hybrid_top_ids": [x["evidence_id"] for x in subquery_fused[: max(bm25_top_n, dense_top_n)]],
                "subquery_hybrid_rrf_scores": [x["rrf_score"] for x in subquery_fused[: max(bm25_top_n, dense_top_n)]],
                "missing_embedding_mappings": missing,
            }
        )

    final_fused = rrf_fuse(subquery_fused_lists, rrf_k)
    # Enrich with best channel ranks.
    for row in final_fused:
        eid = row["evidence_id"]
        if eid in best_bm25:
            row["bm25_best_rank"] = best_bm25[eid]["rank"]
            row["bm25_best_score"] = best_bm25[eid]["score"]
            row["bm25_best_subquery_id"] = best_bm25[eid]["subquery_id"]
        if eid in best_dense:
            row["dense_best_rank"] = best_dense[eid]["rank"]
            row["dense_best_score"] = best_dense[eid]["score"]
            row["dense_best_subquery_id"] = best_dense[eid]["subquery_id"]
    run_stats = {"missing_embedding_mappings": missing_embedding_mappings}
    return final_fused, diagnostics, run_stats


def card_preview(card: Mapping[str, Any], max_chars: int = 280) -> str:
    text = clean_text(card.get("retrieval_text") or card.get("original_text") or "")
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def build_selection_specs(args: argparse.Namespace, retrieval_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build deterministic final-selection settings from CLI arguments.

    Ranking is always hybrid_rrf. These specs only control how many fused-ranked
    evidence cards enter a result set / review table.
    """
    specs: list[dict[str, Any]] = []
    final_cfg = retrieval_config.get("final_selection", {})
    strat_cfg = final_cfg.get("stratified_by_evidence_type", {}) if isinstance(final_cfg, dict) else {}
    evidence_block_order = strat_cfg.get("evidence_block_order") or DEFAULT_EVIDENCE_BLOCK_ORDER
    for mode in args.selection_modes:
        if mode == "global_top_k":
            for top_k in args.top_k:
                specs.append({
                    "selection_mode": "global_top_k",
                    "setting_name": f"global_top_k_{top_k}",
                    "top_k": int(top_k),
                    "per_evidence_type_top_n": None,
                    "evidence_block_order": [],
                })
        elif mode == "stratified_by_evidence_type":
            for n in args.per_evidence_type_top_n:
                specs.append({
                    "selection_mode": "stratified_by_evidence_type",
                    "setting_name": f"stratified_by_evidence_type_n{n}",
                    "top_k": None,
                    "per_evidence_type_top_n": int(n),
                    "evidence_block_order": list(evidence_block_order),
                })
        else:
            fail(f"Unsupported selection mode: {mode}")
    if not specs:
        fail("No final selection specs were built.")
    return specs


def select_final_evidence(
    final_ranked: list[dict[str, Any]],
    card_lookup: dict[str, dict[str, Any]],
    spec: dict[str, Any],
) -> list[dict[str, Any]]:
    mode = spec["selection_mode"]
    if mode == "global_top_k":
        selected = [dict(item) for item in final_ranked[: int(spec["top_k"])]]
        for prompt_rank, item in enumerate(selected, start=1):
            item["prompt_rank"] = prompt_rank
        return selected

    if mode == "stratified_by_evidence_type":
        n = int(spec["per_evidence_type_top_n"])
        order = list(spec.get("evidence_block_order") or DEFAULT_EVIDENCE_BLOCK_ORDER)
        by_type: dict[str, list[dict[str, Any]]] = {evidence_type: [] for evidence_type in order}
        for item in final_ranked:
            card = card_lookup[item["evidence_id"]]
            evidence_type = clean_text(card.get("evidence_type"))
            if evidence_type not in by_type:
                continue
            if len(by_type[evidence_type]) < n:
                by_type[evidence_type].append(dict(item))
        selected: list[dict[str, Any]] = []
        for evidence_type in order:
            selected.extend(by_type.get(evidence_type, []))
        for prompt_rank, item in enumerate(selected, start=1):
            item["prompt_rank"] = prompt_rank
        return selected

    fail(f"Unsupported selection mode: {mode}")


def make_result_records(
    case: dict[str, Any],
    query_bundle: dict[str, Any],
    final_ranked: list[dict[str, Any]],
    card_lookup: dict[str, dict[str, Any]],
    validation: dict[str, Any],
    selection_specs: list[dict[str, Any]],
    retrieval_config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for spec in selection_specs:
        selected = select_final_evidence(final_ranked, card_lookup, spec)
        cards_payload = []
        for item in selected:
            card = card_lookup[item["evidence_id"]]
            cards_payload.append(card_payload_for_result(item, card))
        setting_name = spec["setting_name"]
        records[setting_name] = {
            "case_id": case["case_id"],
            "task_id": case["task_id"],
            "company_id": case["company_id"],
            "company_name": case["company_name"],
            "target_reporting_year": case["target_reporting_year"],
            "package_id": case["package_id"],
            "manifest_path": case["manifest_path"],
            "retrieval_algorithm_key": retrieval_config["retrieval_algorithm_key"],
            "final_selection_mode": spec["selection_mode"],
            "selection_setting": setting_name,
            "top_k": spec.get("top_k"),
            "per_evidence_type_top_n": spec.get("per_evidence_type_top_n"),
            "evidence_block_order": spec.get("evidence_block_order"),
            "query_bundle_id": query_bundle["query_bundle_id"],
            "query_bundle_hash": query_bundle["query_bundle_hash"],
            "retrieved_evidence_ids": [x["evidence_id"] for x in selected],
            "retrieval_scores_or_ranks": [
                {"prompt_rank": x.get("prompt_rank"), "final_rank": x["rank"], "final_rrf_score": x["rrf_score"]}
                for x in selected
            ],
            "evidence_type_distribution": dict(Counter(clean_text(card_lookup[x["evidence_id"]].get("evidence_type")) for x in selected)),
            "source_year_distribution": dict(Counter(int(card_lookup[x["evidence_id"]].get("source_year")) for x in selected)),
            "eligible_corpus_size": validation.get("eligible_corpus_size"),
            "csv_source_years": validation.get("csv_source_years"),
            "pdf_source_years": validation.get("pdf_source_years"),
            "boundary_validation_passed": validation.get("boundary_validation_passed"),
            "retrieved_cards": cards_payload,
        }
    return records


def card_payload_for_result(item: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    return {
        "prompt_rank": item.get("prompt_rank"),
        "final_rank": item.get("rank"),
        "final_rrf_score": item.get("rrf_score"),
        "bm25_best_rank": item.get("bm25_best_rank"),
        "bm25_best_score": item.get("bm25_best_score"),
        "dense_best_rank": item.get("dense_best_rank"),
        "dense_best_score": item.get("dense_best_score"),
        "evidence_id": card.get("evidence_id"),
        "source_type": card.get("source_type"),
        "evidence_type": card.get("evidence_type"),
        "source_year": card.get("source_year"),
        "document_type": card.get("document_type"),
        "source_file": card.get("source_file"),
        "page_start": card.get("page_start"),
        "page_end": card.get("page_end"),
        "metric": card.get("metric"),
        "value_text": card.get("value_text"),
        "unit": card.get("unit"),
        "retrieval_text": card.get("retrieval_text"),
    }


def make_review_rows(
    case: dict[str, Any],
    task: dict[str, Any],
    query_bundle: dict[str, Any],
    final_ranked: list[dict[str, Any]],
    card_lookup: dict[str, dict[str, Any]],
    validation: dict[str, Any],
    selection_specs: list[dict[str, Any]],
    retrieval_config: dict[str, Any],
) -> list[dict[str, Any]]:
    expected_types = task.get("expected_evidence_types") or []
    expected_content = task.get("expected_evidence_content") or []
    rows: list[dict[str, Any]] = []
    for spec in selection_specs:
        selected = select_final_evidence(final_ranked, card_lookup, spec)
        for item in selected:
            card = card_lookup[item["evidence_id"]]
            rows.append(
                {
                    "case_id": case["case_id"],
                    "company_id": case["company_id"],
                    "company_name": case["company_name"],
                    "target_reporting_year": case["target_reporting_year"],
                    "task_id": case["task_id"],
                    "esrs_reference": case.get("esrs_reference"),
                    "task_name": case.get("task_name"),
                    "package_id": case["package_id"],
                    "manifest_path": case["manifest_path"],
                    "retrieval_algorithm_key": retrieval_config["retrieval_algorithm_key"],
                    "final_selection_mode": spec["selection_mode"],
                    "selection_setting": spec["setting_name"],
                    "top_k_setting": spec.get("top_k") or "",
                    "per_evidence_type_top_n_setting": spec.get("per_evidence_type_top_n") or "",
                    "query_bundle_id": query_bundle["query_bundle_id"],
                    "subquery_ids": [q["subquery_id"] for q in query_bundle["subqueries"]],
                    "prompt_rank": item.get("prompt_rank"),
                    "final_rank": item.get("rank"),
                    "final_rrf_score": item.get("rrf_score"),
                    "bm25_best_rank": item.get("bm25_best_rank"),
                    "bm25_best_score": item.get("bm25_best_score"),
                    "dense_best_rank": item.get("dense_best_rank"),
                    "dense_best_score": item.get("dense_best_score"),
                    "appeared_in_bm25": bool(item.get("bm25_best_rank")),
                    "appeared_in_dense": bool(item.get("dense_best_rank")),
                    "evidence_id": card.get("evidence_id"),
                    "source_type": card.get("source_type"),
                    "evidence_type": card.get("evidence_type"),
                    "source_year": card.get("source_year"),
                    "document_type": card.get("document_type"),
                    "source_file": card.get("source_file"),
                    "page_start": card.get("page_start"),
                    "page_end": card.get("page_end"),
                    "metric": card.get("metric"),
                    "value_text": card.get("value_text"),
                    "unit": card.get("unit"),
                    "retrieval_text_preview": card_preview(card),
                    "full_retrieval_text": clean_text(card.get("retrieval_text") or card.get("original_text") or ""),
                    "eligible_corpus_size": validation.get("eligible_corpus_size"),
                    "allowed_evidence_count": validation.get("allowed_evidence_count"),
                    "csv_source_years": validation.get("csv_source_years"),
                    "pdf_source_years": validation.get("pdf_source_years"),
                    "boundary_validation_passed": validation.get("boundary_validation_passed"),
                    "expected_evidence_types": expected_types,
                    "expected_evidence_content": expected_content,
                    "manual_relevance_label": "",
                    "manual_relevance_notes": "",
                    "retrieval_failure_type": "",
                }
            )
    return rows


def make_case_summary_rows(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in case_rows:
        grouped[(row["case_id"], clean_text(row.get("selection_setting")))].append(row)
    summaries: list[dict[str, Any]] = []
    for (case_id, setting_name), rows in sorted(grouped.items()):
        first = rows[0]
        evidence_types = Counter(clean_text(r.get("evidence_type")) for r in rows)
        years = sorted({int(r["source_year"]) for r in rows if clean_text(r.get("source_year"))})
        summaries.append(
            {
                "case_id": case_id,
                "company_id": first.get("company_id"),
                "company_name": first.get("company_name"),
                "target_reporting_year": first.get("target_reporting_year"),
                "task_id": first.get("task_id"),
                "final_selection_mode": first.get("final_selection_mode"),
                "selection_setting": setting_name,
                "top_k": first.get("top_k_setting"),
                "per_evidence_type_top_n": first.get("per_evidence_type_top_n_setting"),
                "retrieved_count": len(rows),
                "csv_metric_count": evidence_types.get("csv_metric", 0),
                "pdf_narrative_count": evidence_types.get("narrative", 0),
                "pdf_table_row_count": evidence_types.get("pdf_table_row", 0),
                "has_csv_metric": evidence_types.get("csv_metric", 0) > 0,
                "has_pdf_narrative": evidence_types.get("narrative", 0) > 0,
                "has_pdf_table_row": evidence_types.get("pdf_table_row", 0) > 0,
                "source_year_min": min(years) if years else "",
                "source_year_max": max(years) if years else "",
                "eligible_corpus_size": first.get("eligible_corpus_size"),
            }
        )
    return summaries


def make_task_summary_rows(case_summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in case_summary_rows:
        grouped[(row["task_id"], clean_text(row.get("selection_setting")))].append(row)
    summaries: list[dict[str, Any]] = []
    for (task_id, setting_name), rows in sorted(grouped.items()):
        n = len(rows)
        first = rows[0]
        summaries.append(
            {
                "task_id": task_id,
                "final_selection_mode": first.get("final_selection_mode"),
                "selection_setting": setting_name,
                "top_k": first.get("top_k"),
                "per_evidence_type_top_n": first.get("per_evidence_type_top_n"),
                "case_count": n,
                "avg_csv_metric_count": sum(int(r["csv_metric_count"]) for r in rows) / max(1, n),
                "avg_pdf_narrative_count": sum(int(r["pdf_narrative_count"]) for r in rows) / max(1, n),
                "avg_pdf_table_row_count": sum(int(r["pdf_table_row_count"]) for r in rows) / max(1, n),
                "cases_with_csv_metric": sum(bool(r["has_csv_metric"]) for r in rows),
                "cases_with_pdf_narrative": sum(bool(r["has_pdf_narrative"]) for r in rows),
                "cases_with_pdf_table_row": sum(bool(r["has_pdf_table_row"]) for r in rows),
                "cases_with_no_results": sum(int(r["retrieved_count"]) == 0 for r in rows),
            }
        )
    return summaries


def make_cases_csv_rows(cases: list[dict[str, Any]], validations: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        val = validations.get(case["case_id"], {})
        rows.append(
            {
                "case_id": case["case_id"],
                "company_id": case["company_id"],
                "company_name": case["company_name"],
                "target_reporting_year": case["target_reporting_year"],
                "task_id": case["task_id"],
                "esrs_reference": case["esrs_reference"],
                "task_name": case["task_name"],
                "workflow": case["workflow"],
                "run_id": case["run_id"],
                "package_id": case["package_id"],
                "manifest_path": case["manifest_path"],
                "allowed_evidence_count": val.get("allowed_evidence_count", ""),
                "eligible_corpus_size": val.get("eligible_corpus_size", ""),
                "csv_source_years": val.get("csv_source_years", ""),
                "pdf_source_years": val.get("pdf_source_years", ""),
                "boundary_validation_passed": val.get("boundary_validation_passed", ""),
            }
        )
    return rows


def manifest_payload(
    args: argparse.Namespace,
    retrieval_config: dict[str, Any],
    dense_model_config: dict[str, Any],
    artifacts: EmbeddingArtifacts,
    cases: list[dict[str, Any]],
    output_files: dict[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": "retrieval_sanity_check_manifest_v2",
        "script_name": "run_w2_retrieval_sanity_check.py",
        "script_version": SCRIPT_VERSION,
        "run_timestamp_utc": now_utc_iso(),
        "acceptance_criteria": ACCEPTANCE_CRITERIA,
        "input_paths": {
            "evidence_root": str(args.evidence_root),
            "task_spec": str(args.task_spec),
            "query_bundle_template": str(args.query_bundle_template),
            "retrieval_config": str(args.retrieval_config),
            "embedding_matrix": str(artifacts.matrix_path),
            "embedding_id_mapping": str(artifacts.id_mapping_path),
            "embedding_metadata": str(artifacts.metadata_path) if artifacts.metadata_path else None,
        },
        "input_hashes": {
            "task_spec_sha256": sha256_file(args.task_spec),
            "query_bundle_template_sha256": sha256_file(args.query_bundle_template),
            "retrieval_config_sha256": sha256_file(args.retrieval_config),
        },
        "package_build_name": args.package_build_name,
        "embedding_build_name": args.embedding_build_name,
        "embedding_model_key": args.embedding_model_key,
        "dense_model_config": dense_model_config,
        "retrieval_config": retrieval_config,
        "candidate_pool_source": args.candidate_pool,
        "target_years": args.target_years,
        "task_ids": args.task_ids,
        "selection_modes": args.selection_modes,
        "top_k_values": args.top_k,
        "per_evidence_type_top_n_values": args.per_evidence_type_top_n,
        "company_limit": args.company_limit,
        "selected_company_ids_file": str(args.selected_company_ids) if args.selected_company_ids else None,
        "case_count": len(cases),
        "output_files": output_files,
    }


def main() -> None:
    args = parse_args()
    validate_args(args)
    task_specs = load_task_specs(args.task_spec)
    missing_tasks = [task_id for task_id in args.task_ids if task_id not in task_specs]
    if missing_tasks:
        fail(f"Requested task_ids missing from task spec: {missing_tasks}")
    query_templates = load_query_templates(args.query_bundle_template)
    retrieval_config = load_retrieval_config(args.retrieval_config, args.retrieval_algorithm)
    card_lookup = load_evidence_cards(args.evidence_root)
    manifests = load_package_manifests(
        args.evidence_root,
        args.package_build_name,
        set(args.target_years),
        selected_company_ids(args.selected_company_ids),
        args.company_limit,
    )
    cases = build_cases(manifests, args.task_ids, task_specs)

    artifacts = discover_embedding_artifacts(
        args.evidence_root,
        args.embedding_build_name,
        args.embedding_model_key,
        retrieval_config,
    )
    dense_model_config = resolve_dense_model_config(args.embedding_model_key, retrieval_config, artifacts)
    if clean_text(args.openai_api_key_env):
        dense_model_config["openai_api_key_env"] = args.openai_api_key_env
    if args.openai_base_url:
        dense_model_config["openai_base_url"] = args.openai_base_url
    if args.openai_dimensions:
        dense_model_config["openai_dimensions"] = args.openai_dimensions
    dense_model_config["openai_max_retries"] = args.openai_max_retries
    dense_model_config["openai_request_timeout"] = args.openai_request_timeout
    selection_specs = build_selection_specs(args, retrieval_config)

    validations: dict[str, dict[str, Any]] = {}
    eligible_by_case: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        _allowed_ids, eligible_cards, validation = validate_candidate_pool(case, card_lookup, args.include_table_markdown)
        validations[case["case_id"]] = validation
        eligible_by_case[case["case_id"]] = eligible_cards
    log_pass("phase_2_case_and_boundary_construction", "all candidate pools passed hard-boundary validation")

    cases_csv_rows = make_cases_csv_rows(cases, validations)
    write_csv(args.output_dir / "sanity_check_cases.csv", cases_csv_rows)

    if args.dry_run:
        write_json(
            args.output_dir / "retrieval_sanity_check_manifest.json",
            {
                "script_version": SCRIPT_VERSION,
                "dry_run": True,
                "case_count": len(cases),
                "embedding_model_key": args.embedding_model_key,
                "dense_model_config": dense_model_config,
                "selection_specs": selection_specs,
                "acceptance_criteria": ACCEPTANCE_CRITERIA,
            },
        )
        print(f"[DONE] Dry run completed. Cases written to {args.output_dir / 'sanity_check_cases.csv'}")
        return

    query_records: list[dict[str, Any]] = []
    diagnostics_records: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    results_by_setting: dict[str, list[dict[str, Any]]] = {spec["setting_name"]: [] for spec in selection_specs}

    for idx, case in enumerate(cases, start=1):
        print(f"[RUN] {idx:,}/{len(cases):,} {case['case_id']}")
        task = task_specs[case["task_id"]]
        query_bundle = render_query_bundle(case, task, query_templates)
        query_records.append(query_bundle)
        final_ranked, diagnostics, run_stats = run_case_retrieval(
            case,
            task,
            query_bundle,
            eligible_by_case[case["case_id"]],
            artifacts,
            dense_model_config,
            retrieval_config,
        )
        diagnostics_records.extend(diagnostics)
        result_records = make_result_records(
            case,
            query_bundle,
            final_ranked,
            card_lookup,
            validations[case["case_id"]],
            selection_specs,
            retrieval_config,
        )
        for setting_name, record in result_records.items():
            record["missing_embedding_mappings"] = run_stats.get("missing_embedding_mappings", 0)
            results_by_setting[setting_name].append(record)
        review_rows.extend(
            make_review_rows(
                case,
                task,
                query_bundle,
                final_ranked,
                card_lookup,
                validations[case["case_id"]],
                selection_specs,
                retrieval_config,
            )
        )

    append_jsonl(args.output_dir / "retrieval_query_bundles.jsonl", query_records, overwrite_first=True)
    append_jsonl(args.output_dir / "retrieval_channel_diagnostics.jsonl", diagnostics_records, overwrite_first=True)
    output_files: dict[str, str] = {
        "sanity_check_cases": str(args.output_dir / "sanity_check_cases.csv"),
        "retrieval_query_bundles": str(args.output_dir / "retrieval_query_bundles.jsonl"),
        "retrieval_channel_diagnostics": str(args.output_dir / "retrieval_channel_diagnostics.jsonl"),
    }
    for setting_name, records in results_by_setting.items():
        path = args.output_dir / f"retrieval_results_hybrid_rrf_{setting_name}.jsonl"
        append_jsonl(path, records, overwrite_first=True)
        output_files[f"retrieval_results_{setting_name}"] = str(path)

    review_path = args.output_dir / "retrieval_review_table_hybrid_rrf.csv"
    write_csv(review_path, review_rows)
    output_files["retrieval_review_table"] = str(review_path)

    case_summary_rows = make_case_summary_rows(review_rows)
    case_summary_path = args.output_dir / "retrieval_summary_by_case.csv"
    write_csv(case_summary_path, case_summary_rows)
    output_files["retrieval_summary_by_case"] = str(case_summary_path)

    task_summary_rows = make_task_summary_rows(case_summary_rows)
    task_summary_path = args.output_dir / "retrieval_summary_by_task.csv"
    write_csv(task_summary_path, task_summary_rows)
    output_files["retrieval_summary_by_task"] = str(task_summary_path)

    manifest_path = args.output_dir / "retrieval_sanity_check_manifest.json"
    write_json(
        manifest_path,
        manifest_payload(args, retrieval_config, dense_model_config, artifacts, cases, output_files),
    )
    output_files["retrieval_sanity_check_manifest"] = str(manifest_path)

    log_pass("phase_3_query_bundle_construction", f"wrote {len(query_records):,} query bundles")
    log_pass("phase_4_bm25_channel", "BM25 channel completed for all subqueries")
    log_pass("phase_5_dense_channel", "Dense channel completed for all subqueries")
    log_pass("phase_6_hybrid_fusion", "Hybrid RRF fusion completed for all cases")
    log_pass("phase_7_coverage_and_diagnostics", f"wrote diagnostics rows: {len(diagnostics_records):,}")
    log_pass("phase_8_outputs_and_reproducibility", f"outputs written under {args.output_dir}")
    print(f"[DONE] Review table: {review_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f"[FAIL] {exc}", file=sys.stderr)
        sys.exit(1)
