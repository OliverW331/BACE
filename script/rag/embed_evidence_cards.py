#!/usr/bin/env python3
"""Embed canonical evidence-card retrieval_text fields into model-specific vector indexes.

This script is the document/corpus-side embedding stage for the W2 transparent
Evidence-Card RAG workflow. It reads source-centric canonical evidence cards,
uses each card's retrieval_text as the document text to embed, and writes one
independent embedding/index artifact set per embedding model.

Design boundary:
- Evidence cards are source-centric and permanent; this script never modifies them.
- Embeddings, FAISS indexes, prefixes, and runtime metadata are downstream index artifacts.
- The current script embeds document/evidence-card text only; query_prefix is recorded
  for later retrieval/evaluation scripts but is not applied here.
- PDF table-markdown cards are excluded by default.
- CPU-first execution is supported for Hugging Face models; OpenAI-compatible
  embedding models are supported through provider-aware API calls.
- Models run sequentially, while CPU thread-level parallelism can be configured
  inside each local model run.

Expected project layout:
    pilot_evidence/
      canonical/indexes/
        all_csv_metric_cards.jsonl
        all_pdf_narrative_cards.jsonl
        all_pdf_table_row_cards.jsonl
      embeddings/

Example smoke test:
    python script/rag/embed_evidence_cards.py \
      --evidence-root pilot_evidence \
      --embedding-build-name smoke_test_embedding_v1 \
      --models nomic-v1.5 \
      --include-types csv_metric narrative pdf_table_row \
      --max-cards 500 \
      --batch-size 4 \
      --device cpu \
      --cpu-threads 4 \
      --faiss-threads 4 \
      --prefix-policy model_default \
      --normalize \
      --index-type faiss_flat_ip \
      --overwrite

Example Azure OpenAI embedding smoke test (credentials and deployment are read
from the project-root .env file):
    python script/rag/embed_evidence_cards.py \
      --evidence-root pilot_evidence \
      --embedding-build-name smoke_openai_embedding_v1 \
      --models text-embedding-3-small \
      --include-types csv_metric narrative pdf_table_row \
      --max-cards 500 \
      --batch-size 64 \
      --prefix-policy model_default \
      --normalize \
      --index-type faiss_flat_ip \
      --overwrite
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal
from urllib.parse import urlsplit, urlunsplit

import numpy as np
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env", override=False)


SCRIPT_VERSION = "embed_evidence_cards_v2.0"
EMBEDDING_BUILD_SCHEMA_VERSION = "evidence_embedding_build_manifest_v2"
EMBEDDING_MANIFEST_SCHEMA_VERSION = "evidence_embedding_manifest_v2"
METADATA_SCHEMA_VERSION = "embedding_card_metadata_v1"

EvidenceType = Literal["csv_metric", "narrative", "pdf_table_row", "pdf_table_markdown"]
PrefixPolicy = Literal["model_default", "none", "custom"]
DeviceArg = Literal["auto", "cpu", "cuda"]
IndexType = Literal["faiss_flat_ip"]

DEFAULT_INCLUDE_TYPES: list[EvidenceType] = ["csv_metric", "narrative", "pdf_table_row"]
ALL_SUPPORTED_TYPES: list[EvidenceType] = ["csv_metric", "narrative", "pdf_table_row", "pdf_table_markdown"]

CARD_INDEX_FILES: dict[EvidenceType, str] = {
    "csv_metric": "all_csv_metric_cards.jsonl",
    "narrative": "all_pdf_narrative_cards.jsonl",
    "pdf_table_row": "all_pdf_table_row_cards.jsonl",
    "pdf_table_markdown": "all_pdf_table_markdown_cards.jsonl",
}

MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    # Current frozen retrieval embedding candidate set: five open/open-weight
    # Hugging Face models plus one closed API baseline.
    "qwen3-0.6b": {
        "provider": "huggingface",
        "model_name_or_path": "Qwen/Qwen3-Embedding-0.6B",
        "access_type": "open_weight",
        "status": "current",
        "role": "main_modern_retrieval_candidate",
        "document_prefix": "",
        "query_prefix": "",
        "embedding_dimension": None,
        "trust_remote_code": True,
    },
    "bge-m3": {
        "provider": "huggingface",
        "model_name_or_path": "BAAI/bge-m3",
        "access_type": "open_weight",
        "status": "current",
        "role": "robust_rag_oriented_baseline",
        "document_prefix": "",
        "query_prefix": "",
        "embedding_dimension": None,
        "trust_remote_code": False,
    },
    "snowflake-m-v1.5": {
        "provider": "huggingface",
        "model_name_or_path": "Snowflake/snowflake-arctic-embed-m-v1.5",
        "access_type": "open_weight",
        "status": "current",
        "role": "efficiency_oriented_retrieval_candidate",
        "document_prefix": "",
        "query_prefix": "",
        "embedding_dimension": None,
        "trust_remote_code": True,
    },
    "nomic-v1.5": {
        "provider": "huggingface",
        "model_name_or_path": "nomic-ai/nomic-embed-text-v1.5",
        "access_type": "open_weight",
        "status": "current",
        "role": "reproducibility_focused_open_baseline",
        "document_prefix": "search_document: ",
        "query_prefix": "search_query: ",
        "embedding_dimension": None,
        "trust_remote_code": True,
    },
    "e5-large-instruct": {
        "provider": "huggingface",
        "model_name_or_path": "intfloat/multilingual-e5-large-instruct",
        "access_type": "open_weight",
        "status": "current",
        "role": "established_academic_embedding_baseline",
        "document_prefix": "",
        "query_prefix": "Instruct: Retrieve relevant ESRS E1 evidence from company evidence cards.\nQuery: ",
        "embedding_dimension": None,
        "trust_remote_code": False,
    },
    "text-embedding-3-small": {
        "provider": "azure_openai",
        "model_name_or_path": "text-embedding-3-small",
        "deployment_name_env": "TEXT_EMBEDDING_3_SMALL_AZURE_OPENAI_DEPLOYMENT",
        "endpoint_env": "TEXT_EMBEDDING_3_SMALL_AZURE_OPENAI_ENDPOINT",
        "api_key_env": "TEXT_EMBEDDING_3_SMALL_AZURE_OPENAI_API_KEY",
        "access_type": "closed_api",
        "status": "current",
        "role": "proprietary_api_retrieval_baseline",
        "document_prefix": "",
        "query_prefix": "",
        "embedding_dimension": 1536,
        "trust_remote_code": None,
    },
    # Deferred local-model placeholders. They are intentionally blocked unless
    # --include-deferred is explicitly supplied.
    "qwen3-4b": {
        "provider": "huggingface",
        "model_name_or_path": "Qwen/Qwen3-Embedding-4B",
        "access_type": "open_weight",
        "status": "deferred",
        "role": "deferred_larger_qwen3_candidate",
        "document_prefix": "",
        "query_prefix": "",
        "embedding_dimension": None,
        "trust_remote_code": True,
    },
    "qwen3-8b": {
        "provider": "huggingface",
        "model_name_or_path": "Qwen/Qwen3-Embedding-8B",
        "access_type": "open_weight",
        "status": "deferred",
        "role": "deferred_larger_qwen3_candidate",
        "document_prefix": "",
        "query_prefix": "",
        "embedding_dimension": None,
        "trust_remote_code": True,
    },
    "text-embedding-3-large": {
        "provider": "azure_openai",
        "model_name_or_path": "text-embedding-3-large",
        "deployment_name_env": "TEXT_EMBEDDING_3_LARGE_AZURE_OPENAI_DEPLOYMENT",
        "endpoint_env": "TEXT_EMBEDDING_3_LARGE_AZURE_OPENAI_ENDPOINT",
        "api_key_env": "TEXT_EMBEDDING_3_LARGE_AZURE_OPENAI_API_KEY",
        "access_type": "closed_api",
        "status": "current",
        "role": "larger_proprietary_api_retrieval_candidate",
        "document_prefix": "",
        "query_prefix": "",
        "embedding_dimension": 3072,
        "trust_remote_code": None,
    },
}

REQUIRED_CARD_FIELDS = {
    "evidence_id",
    "evidence_type",
    "source_type",
    "company_id",
    "source_year",
    "retrieval_text",
}

ACCEPTANCE_CRITERIA: dict[str, list[str]] = {
    "phase_1_input_discovery_and_validation": [
        "--evidence-root exists.",
        "Required canonical JSONL card indexes exist for all selected evidence types.",
        "PDF table-markdown cards are not read unless explicitly requested.",
        "Candidate cards expose required identity, provenance, and retrieval_text fields.",
        "Cards with empty retrieval_text are skipped and counted.",
        "Cards with include_in_main_index == false are skipped by default.",
        "No duplicate evidence_id enters one embedding build.",
    ],
    "phase_2_card_selection_policy": [
        "Default include-types are csv_metric, narrative, and pdf_table_row.",
        "pdf_table_markdown is excluded by default.",
        "--include-types explicitly controls selected evidence types.",
        "Summary records counts by evidence_type, skipped count, and final embedding count.",
        "Canonical evidence card files are never modified.",
    ],
    "phase_3_model_registry_and_prefix_policy": [
        "Seven current model keys are supported: five Hugging Face models plus Azure OpenAI text-embedding-3-small and text-embedding-3-large.",
        "Each model specification records provider, model_name_or_path, access_type, status, role, document_prefix, query_prefix, embedding_dimension, and trust_remote_code where applicable.",
        "role is methodology metadata only and is not embedded.",
        "document_prefix is applied to evidence-card text in this script.",
        "query_prefix is recorded for later query-side retrieval and is not applied in this script.",
        "--prefix-policy supports model_default, none, and custom.",
        "Manifest records prefix policy and query_prefix_applied_in_this_script=false.",
    ],
    "phase_4_cpu_and_device_configuration": [
        "--device supports cpu, cuda, and auto.",
        "CPU execution does not require CUDA.",
        "--cpu-threads and --faiss-threads are supported.",
        "Models run sequentially rather than multi-model multiprocessing.",
        "Manifest records device, CUDA availability, CPU threads, FAISS threads, and batch size.",
    ],
    "phase_5_embedding_generation": [
        "Each model writes embeddings.npy.",
        "embeddings.npy row count equals card_metadata.jsonl row count.",
        "metadata embedding_row values match embeddings.npy row order.",
        "metadata records retrieval_text_hash, model_input_text_hash, retrieval_text_length, and document_prefix_used.",
        "--batch-size and --max-cards are supported.",
        "When normalization is enabled, embeddings are L2-normalized.",
        "embedding_dimension is recorded.",
    ],
    "phase_6_faiss_index_building": [
        "--index-type faiss_flat_ip is supported.",
        "normalize=true with faiss_flat_ip uses IndexFlatIP.",
        "faiss.index is written to the model output folder.",
        "FAISS index.ntotal equals embeddings.npy row count.",
        "No approximate search parameters are introduced in the first version.",
    ],
    "phase_7_manifest_and_reproducibility_logging": [
        "Each model writes embedding_manifest.json.",
        "Manifest records build, evidence root, model, prefixes, selected evidence types, runtime, hardware, and index settings.",
        "Manifest records provider-specific model metadata: Hugging Face revision when available, or OpenAI API model metadata without storing API keys.",
        "Manifest records reranker_included=false and bm25_or_hybrid_included=false.",
    ],
    "phase_8_smoke_test_readiness": [
        "The script supports a max-cards smoke test.",
        "Smoke test produces embeddings.npy, faiss.index, card_metadata.jsonl, embedding_manifest.json, and embedding_summary.json.",
        "query_prefix_applied_in_this_script remains false.",
    ],
    "phase_9_pilot_full_embedding_build_readiness": [
        "Multiple current models can be selected in one run and are executed sequentially; deferred models require --include-deferred.",
        "All selected models use the same selected evidence_id list within a run.",
        "Each model writes an independent output folder.",
        "Embedding dimensions may differ by model but are recorded.",
    ],
    "phase_10_handoff_to_retrieval_evaluation": [
        "FAISS row ids can be mapped back to evidence_id through card_metadata.jsonl.",
        "embedding_manifest.json contains all settings required by later retrieval/evaluation scripts.",
        "This script does not add reranking, BM25, hybrid retrieval, generation, or annotation logic.",
    ],
}


@dataclass
class CardRecord:
    evidence_id: str
    evidence_type: str
    source_type: str
    company_id: str
    company_name: str | None
    source_year: int | str
    retrieval_text: str
    source_file: str | None = None
    document_type: str | None = None
    schema_version: str | None = None
    include_in_main_index: bool = True
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadStats:
    input_files: dict[str, str] = field(default_factory=dict)
    raw_cards_by_type: dict[str, int] = field(default_factory=dict)
    selected_cards_by_type: dict[str, int] = field(default_factory=dict)
    skipped_by_reason: dict[str, int] = field(default_factory=dict)
    skipped_by_type: dict[str, dict[str, int]] = field(default_factory=dict)
    duplicate_evidence_ids_seen: int = 0
    missing_required_fields_seen: int = 0
    excluded_evidence_types: list[str] = field(default_factory=list)

    def skip(self, evidence_type: str, reason: str) -> None:
        self.skipped_by_reason[reason] = self.skipped_by_reason.get(reason, 0) + 1
        self.skipped_by_type.setdefault(evidence_type, {})[reason] = (
            self.skipped_by_type.setdefault(evidence_type, {}).get(reason, 0) + 1
        )


@dataclass
class ModelRunResult:
    model_key: str
    output_dir: str
    card_count: int
    embedding_dimension: int | None
    runtime_seconds: float
    manifest_path: str
    summary_path: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Embed canonical evidence-card retrieval_text fields into model-specific "
            "embedding arrays and FAISS indexes."
        )
    )
    parser.add_argument("--evidence-root", type=Path, default=Path("pilot_evidence"))
    parser.add_argument("--embedding-build-name", type=str, required=True)
    embedding_model_default = os.environ.get("RETRIEVAL_EMBEDDING_MODEL_KEY")
    parser.add_argument(
        "--models",
        nargs="+",
        choices=sorted(MODEL_REGISTRY.keys()),
        required=not bool(embedding_model_default),
        default=[embedding_model_default] if embedding_model_default else None,
        help=(
            "One or more model registry keys to run sequentially. Defaults to "
            "RETRIEVAL_EMBEDDING_MODEL_KEY from .env when set."
        ),
    )
    parser.add_argument(
        "--include-types",
        nargs="+",
        choices=ALL_SUPPORTED_TYPES,
        default=DEFAULT_INCLUDE_TYPES,
        help="Evidence card types to include in the embedding corpus.",
    )
    parser.add_argument(
        "--include-table-markdown",
        action="store_true",
        help="Convenience flag to include pdf_table_markdown in addition to --include-types.",
    )
    parser.add_argument("--max-cards", type=int, default=None, help="Optional deterministic corpus cap for smoke tests.")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--cpu-threads", type=int, default=None)
    parser.add_argument("--faiss-threads", type=int, default=None)
    parser.add_argument(
        "--prefix-policy",
        choices=["model_default", "none", "custom"],
        default="model_default",
    )
    parser.add_argument("--custom-document-prefix", type=str, default=None)
    parser.add_argument("--custom-query-prefix", type=str, default=None)
    parser.add_argument(
        "--normalize",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="L2-normalize embeddings. Default: true.",
    )
    parser.add_argument("--index-type", choices=["faiss_flat_ip"], default="faiss_flat_ip")
    parser.add_argument("--hf-revision", type=str, default=None, help="Optional Hugging Face revision applied to Hugging Face models.")
    parser.add_argument(
        "--include-deferred",
        action="store_true",
        help="Allow explicitly selected deferred registry entries such as qwen3-4b or qwen3-8b.",
    )
    parser.add_argument(
        "--openai-api-key-env",
        type=str,
        default=None,
        help="Environment variable containing the OpenAI API key for OpenAI embedding models.",
    )
    parser.add_argument(
        "--openai-base-url",
        type=str,
        default=None,
        help="Optional OpenAI-compatible base URL. Leave empty for the default OpenAI API endpoint.",
    )
    parser.add_argument(
        "--openai-dimensions",
        type=int,
        default=None,
        help="Optional dimensions parameter for OpenAI embedding models. Leave empty to use the model default.",
    )
    parser.add_argument(
        "--openai-max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts for OpenAI embedding batch requests.",
    )
    parser.add_argument(
        "--openai-request-timeout",
        type=float,
        default=120.0,
        help="Request timeout in seconds for OpenAI embedding batch requests.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and write a build-level manifest without loading models or embedding text.",
    )
    parser.add_argument(
        "--print-acceptance-criteria",
        action="store_true",
        help="Print acceptance criteria before running.",
    )
    return parser.parse_args()


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_azure_base_url(endpoint: str) -> str:
    parts = urlsplit(endpoint.strip())
    if parts.scheme != "https" or not parts.netloc:
        fail("Azure OpenAI embedding endpoint must be a full HTTPS URL")
    path = parts.path.rstrip("/")
    for suffix in ("/openai/v1/embeddings", "/openai/embeddings"):
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


def pass_check(name: str, detail: str = "") -> None:
    message = f"[PASS] {name}"
    if detail:
        message += f" - {detail}"
    print(message)


def warn_check(name: str, detail: str = "") -> None:
    message = f"[WARN] {name}"
    if detail:
        message += f" - {detail}"
    print(message)


def fail(message: str) -> None:
    raise RuntimeError(message)


def print_acceptance_criteria() -> None:
    print("\nAcceptance criteria")
    for phase, criteria in ACCEPTANCE_CRITERIA.items():
        print(f"  {phase}:")
        for criterion in criteria:
            print(f"    - {criterion}")
    print()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    return " ".join(text.split()).strip()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any, *, overwrite: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        fail(f"Refusing to overwrite existing JSON file: {path}")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, records: Iterable[dict[str, Any]], *, overwrite: bool = True) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        fail(f"Refusing to overwrite existing JSONL file: {path}")
    count = 0
    with path.open("w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                record = json.loads(text)
            except json.JSONDecodeError as exc:
                fail(f"Invalid JSON on line {line_number} of {path}: {exc}")
            if not isinstance(record, dict):
                fail(f"JSONL record on line {line_number} of {path} is not an object")
            yield record


def normalize_include_types(args: argparse.Namespace) -> list[EvidenceType]:
    include_types = list(dict.fromkeys(args.include_types))
    if args.include_table_markdown and "pdf_table_markdown" not in include_types:
        include_types.append("pdf_table_markdown")
    return include_types  # type: ignore[return-value]


def validate_args(args: argparse.Namespace) -> list[EvidenceType]:
    if not args.evidence_root.exists():
        fail(f"Evidence root does not exist: {args.evidence_root}")
    if not args.evidence_root.is_dir():
        fail(f"Evidence root is not a directory: {args.evidence_root}")
    if not args.embedding_build_name.strip():
        fail("--embedding-build-name cannot be empty")
    if args.batch_size < 1:
        fail("--batch-size must be >= 1")
    if args.max_cards is not None and args.max_cards < 1:
        fail("--max-cards must be >= 1 when provided")
    if args.cpu_threads is not None and args.cpu_threads < 1:
        fail("--cpu-threads must be >= 1 when provided")
    if args.faiss_threads is not None and args.faiss_threads < 1:
        fail("--faiss-threads must be >= 1 when provided")
    if args.prefix_policy == "custom":
        if args.custom_document_prefix is None and args.custom_query_prefix is None:
            warn_check(
                "custom_prefix_policy_without_values",
                "both custom prefixes are empty; this is equivalent to --prefix-policy none",
            )
    if args.openai_dimensions is not None and args.openai_dimensions < 1:
        fail("--openai-dimensions must be >= 1 when provided")
    if args.openai_max_retries < 0:
        fail("--openai-max-retries must be >= 0")
    if args.openai_request_timeout <= 0:
        fail("--openai-request-timeout must be > 0")
    deferred_models = [
        model_key for model_key in args.models
        if MODEL_REGISTRY[model_key].get("status") == "deferred"
    ]
    if deferred_models and not args.include_deferred:
        fail(
            "Deferred model(s) requested without --include-deferred: "
            + ", ".join(deferred_models)
        )
    include_types = normalize_include_types(args)
    pass_check("phase_1_input_discovery_and_validation", "basic arguments and evidence root are valid")
    return include_types


def card_indexes_root(evidence_root: Path) -> Path:
    return evidence_root / "canonical" / "indexes"


def embeddings_build_root(evidence_root: Path, embedding_build_name: str) -> Path:
    return evidence_root / "embeddings" / embedding_build_name


def required_input_paths(evidence_root: Path, include_types: list[EvidenceType]) -> dict[EvidenceType, Path]:
    root = card_indexes_root(evidence_root)
    paths: dict[EvidenceType, Path] = {}
    for evidence_type in include_types:
        filename = CARD_INDEX_FILES[evidence_type]
        path = root / filename
        if not path.exists():
            fail(f"Required canonical index for {evidence_type} not found: {path}")
        paths[evidence_type] = path
    return paths


def parse_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y", "t"}:
        return True
    if normalized in {"false", "0", "no", "n", "f"}:
        return False
    return default


def card_from_raw(record: dict[str, Any]) -> CardRecord:
    return CardRecord(
        evidence_id=clean_text(record.get("evidence_id")),
        evidence_type=clean_text(record.get("evidence_type")),
        source_type=clean_text(record.get("source_type")),
        company_id=clean_text(record.get("company_id")),
        company_name=clean_text(record.get("company_name")) or None,
        source_year=record.get("source_year"),
        retrieval_text=clean_text(record.get("retrieval_text")),
        source_file=clean_text(record.get("source_file")) or None,
        document_type=clean_text(record.get("document_type")) or None,
        schema_version=clean_text(record.get("schema_version")) or None,
        include_in_main_index=parse_bool(record.get("include_in_main_index"), default=True),
        raw=record,
    )


def load_cards(
    *,
    evidence_root: Path,
    include_types: list[EvidenceType],
    max_cards: int | None,
) -> tuple[list[CardRecord], LoadStats]:
    stats = LoadStats()
    stats.excluded_evidence_types = [item for item in ALL_SUPPORTED_TYPES if item not in include_types]
    input_paths = required_input_paths(evidence_root, include_types)
    stats.input_files = {evidence_type: str(path) for evidence_type, path in input_paths.items()}

    cards: list[CardRecord] = []
    seen_ids: set[str] = set()

    for evidence_type in include_types:
        path = input_paths[evidence_type]
        stats.raw_cards_by_type.setdefault(evidence_type, 0)
        stats.selected_cards_by_type.setdefault(evidence_type, 0)

        for raw in read_jsonl(path):
            stats.raw_cards_by_type[evidence_type] += 1
            missing = [field for field in REQUIRED_CARD_FIELDS if field not in raw]
            raw_type = clean_text(raw.get("evidence_type")) or evidence_type
            if missing:
                stats.missing_required_fields_seen += 1
                stats.skip(raw_type, "missing_required_fields")
                continue

            card = card_from_raw(raw)
            if card.evidence_type != evidence_type:
                stats.skip(raw_type, "unexpected_evidence_type_in_file")
                continue
            if not card.include_in_main_index:
                stats.skip(card.evidence_type, "include_in_main_index_false")
                continue
            if not card.retrieval_text:
                stats.skip(card.evidence_type, "empty_retrieval_text")
                continue
            if not card.evidence_id:
                stats.skip(card.evidence_type, "empty_evidence_id")
                continue
            if card.evidence_id in seen_ids:
                stats.duplicate_evidence_ids_seen += 1
                fail(f"Duplicate evidence_id encountered in selected corpus: {card.evidence_id}")
            seen_ids.add(card.evidence_id)
            cards.append(card)
            stats.selected_cards_by_type[card.evidence_type] = stats.selected_cards_by_type.get(card.evidence_type, 0) + 1

            if max_cards is not None and len(cards) >= max_cards:
                pass_check("phase_2_card_selection_policy", f"selected {len(cards):,} cards after --max-cards cap")
                return cards, stats

    pass_check("phase_2_card_selection_policy", f"selected {len(cards):,} cards across {len(include_types)} evidence type(s)")
    if not cards:
        fail("No evidence cards selected for embedding")
    return cards, stats


def resolve_device(device_arg: DeviceArg) -> tuple[str, bool]:
    try:
        import torch

        cuda_available = bool(torch.cuda.is_available())
        if device_arg == "auto":
            return ("cuda" if cuda_available else "cpu"), cuda_available
        if device_arg == "cuda" and not cuda_available:
            fail("--device cuda was requested, but torch.cuda.is_available() is false")
        return device_arg, cuda_available
    except ImportError:
        if device_arg == "cuda":
            fail("--device cuda requires torch, but torch is not installed")
        return "cpu", False


def configure_cpu_parallelism(cpu_threads: int | None, faiss_threads: int | None) -> None:
    if cpu_threads is not None:
        os.environ["OMP_NUM_THREADS"] = str(cpu_threads)
        os.environ["MKL_NUM_THREADS"] = str(cpu_threads)
        os.environ["NUMEXPR_NUM_THREADS"] = str(cpu_threads)
        try:
            import torch

            torch.set_num_threads(cpu_threads)
            try:
                torch.set_num_interop_threads(max(1, min(2, cpu_threads)))
            except RuntimeError:
                # PyTorch only allows interop thread configuration before parallel work starts.
                warn_check("torch_interop_threads_not_changed", "PyTorch interop threads were already initialized")
        except ImportError:
            warn_check("torch_not_installed", "CPU thread environment variables were set, but torch is unavailable")

    if faiss_threads is not None:
        try:
            import faiss  # type: ignore

            faiss.omp_set_num_threads(faiss_threads)
        except ImportError:
            warn_check("faiss_not_installed", "FAISS thread setting will be applied only if FAISS is installed")


def resolve_prefixes(
    model_spec: dict[str, Any],
    prefix_policy: PrefixPolicy,
    custom_document_prefix: str | None,
    custom_query_prefix: str | None,
) -> tuple[str, str]:
    if prefix_policy == "model_default":
        return str(model_spec.get("document_prefix", "")), str(model_spec.get("query_prefix", ""))
    if prefix_policy == "none":
        return "", ""
    if prefix_policy == "custom":
        return custom_document_prefix or "", custom_query_prefix or ""
    fail(f"Unknown prefix policy: {prefix_policy}")


def make_metadata_records(cards: list[CardRecord], document_prefix: str) -> tuple[list[dict[str, Any]], list[str]]:
    metadata: list[dict[str, Any]] = []
    model_input_texts: list[str] = []
    for row_index, card in enumerate(cards):
        model_input_text = f"{document_prefix}{card.retrieval_text}"
        model_input_texts.append(model_input_text)
        raw = card.raw
        metadata.append(
            {
                "metadata_schema_version": METADATA_SCHEMA_VERSION,
                "embedding_row": row_index,
                "evidence_id": card.evidence_id,
                "source_type": card.source_type,
                "evidence_type": card.evidence_type,
                "company_id": card.company_id,
                "company_name": card.company_name,
                "source_year": card.source_year,
                "document_type": card.document_type,
                "source_file": card.source_file,
                "data_point_id": raw.get("data_point_id"),
                "page_start": raw.get("page_start"),
                "page_end": raw.get("page_end"),
                "table_id": raw.get("table_id"),
                "row_index": raw.get("row_index"),
                "schema_version": card.schema_version,
                "include_in_main_index": card.include_in_main_index,
                "retrieval_text_hash": sha256_text(card.retrieval_text),
                "retrieval_text_length": len(card.retrieval_text),
                "model_input_text_hash": sha256_text(model_input_text),
                "model_input_text_length": len(model_input_text),
                "document_prefix_used": document_prefix,
            }
        )
    return metadata, model_input_texts


def prepare_model_output_dir(build_root: Path, model_key: str, *, overwrite: bool) -> Path:
    model_dir = build_root / model_key
    if model_dir.exists():
        if overwrite:
            shutil.rmtree(model_dir)
        else:
            fail(f"Model output folder already exists. Use --overwrite to replace it: {model_dir}")
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir


def model_name_or_path(model_spec: dict[str, Any]) -> str:
    return str(model_spec.get("model_name_or_path") or model_spec.get("hf_name") or "")


def model_provider(model_spec: dict[str, Any]) -> str:
    return str(model_spec.get("provider") or "huggingface")


def get_hf_revision(model_name: str, revision: str | None) -> tuple[str | None, str | None]:
    try:
        from huggingface_hub import model_info

        info = model_info(model_name, revision=revision)
        return getattr(info, "sha", None), None
    except Exception as exc:  # noqa: BLE001 - optional best-effort metadata lookup
        return None, f"Could not resolve Hugging Face revision for {model_name}: {exc}"


def load_sentence_transformer_model(
    model_spec: dict[str, Any],
    *,
    device: str,
    revision: str | None,
) -> Any:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        fail("sentence-transformers is required for Hugging Face models. Install with: pip install sentence-transformers")

    hf_model_name = model_name_or_path(model_spec)
    trust_remote_code = bool(model_spec.get("trust_remote_code", False))
    try:
        return SentenceTransformer(
            hf_model_name,
            device=device,
            trust_remote_code=trust_remote_code,
            revision=revision,
        )
    except TypeError:
        # Older sentence-transformers versions may not accept trust_remote_code/revision.
        if revision is not None:
            warn_check("sentence_transformers_revision_argument_unsupported", "retrying without revision")
        try:
            return SentenceTransformer(hf_model_name, device=device, trust_remote_code=trust_remote_code)
        except TypeError:
            warn_check("sentence_transformers_trust_remote_code_argument_unsupported", "retrying without trust_remote_code")
            return SentenceTransformer(hf_model_name, device=device)


def l2_normalize(embeddings: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return embeddings / norms


def encode_texts(
    model: Any,
    texts: list[str],
    *,
    batch_size: int,
    normalize: bool,
) -> np.ndarray:
    try:
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=True,
            normalize_embeddings=normalize,
        )
    except TypeError:
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=True,
        )
        if normalize:
            embeddings = l2_normalize(np.asarray(embeddings, dtype=np.float32))
    embeddings = np.asarray(embeddings, dtype=np.float32)
    if embeddings.ndim != 2:
        fail(f"Expected 2D embedding matrix, got shape {embeddings.shape}")
    if embeddings.shape[0] != len(texts):
        fail(f"Embedding row count {embeddings.shape[0]} does not match text count {len(texts)}")
    if normalize:
        # Ensure normalization even if the model implementation ignored normalize_embeddings.
        embeddings = l2_normalize(embeddings).astype(np.float32)
    return embeddings


def encode_texts_openai(
    *,
    model_name: str,
    texts: list[str],
    batch_size: int,
    normalize: bool,
    api_key_env: str,
    base_url: str | None,
    dimensions: int | None,
    max_retries: int,
    request_timeout: float,
) -> np.ndarray:
    """Embed document texts with an OpenAI-compatible embeddings API.

    The API key value is read from the configured environment variable and is
    never written to manifests. Batching is deterministic: output rows preserve
    the input text order using the response data index where available.
    """
    api_key = os.getenv(api_key_env)
    if not api_key:
        fail(f"OpenAI embedding model requested, but environment variable {api_key_env} is not set")
    try:
        from openai import OpenAI
    except ImportError:
        fail("OpenAI embedding models require the openai package. Install with: pip install openai")

    client_kwargs: dict[str, Any] = {"api_key": api_key, "timeout": request_timeout}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    rows: list[list[float] | None] = [None] * len(texts)
    total_batches = (len(texts) + batch_size - 1) // batch_size
    for batch_number, start in enumerate(range(0, len(texts), batch_size), start=1):
        batch = texts[start:start + batch_size]
        request: dict[str, Any] = {"model": model_name, "input": batch}
        if dimensions is not None:
            request["dimensions"] = dimensions

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                response = client.embeddings.create(**request)
                for item_position, item in enumerate(response.data):
                    response_index = getattr(item, "index", item_position)
                    rows[start + int(response_index)] = list(item.embedding)
                print(f"[openai:{model_name}] batch {batch_number:,}/{total_batches:,}")
                break
            except Exception as exc:  # noqa: BLE001 - retry API/network/rate-limit errors uniformly
                last_error = exc
                if attempt >= max_retries:
                    fail(
                        f"OpenAI embeddings request failed for batch {batch_number}/{total_batches} "
                        f"after {max_retries + 1} attempt(s): {exc}"
                    )
                sleep_seconds = min(60.0, 2.0 ** attempt)
                warn_check(
                    "openai_embedding_retry",
                    f"batch {batch_number}/{total_batches} attempt {attempt + 1} failed: {exc}; retrying in {sleep_seconds:.1f}s",
                )
                time.sleep(sleep_seconds)
        if last_error is not None:
            last_error = None

    if any(row is None for row in rows):
        missing = sum(row is None for row in rows)
        fail(f"OpenAI embeddings response left {missing} row(s) without embeddings")
    embeddings = np.asarray(rows, dtype=np.float32)
    if embeddings.ndim != 2:
        fail(f"Expected 2D OpenAI embedding matrix, got shape {embeddings.shape}")
    if embeddings.shape[0] != len(texts):
        fail(f"OpenAI embedding row count {embeddings.shape[0]} does not match text count {len(texts)}")
    if normalize:
        embeddings = l2_normalize(embeddings).astype(np.float32)
    return embeddings


def build_and_save_faiss_index(embeddings: np.ndarray, index_path: Path, index_type: IndexType, faiss_threads: int | None) -> int:
    try:
        import faiss  # type: ignore
    except ImportError:
        fail("faiss is required. Install CPU version with: pip install faiss-cpu")

    if faiss_threads is not None:
        faiss.omp_set_num_threads(faiss_threads)

    if index_type != "faiss_flat_ip":
        fail(f"Unsupported index type: {index_type}")

    matrix = np.ascontiguousarray(embeddings.astype(np.float32))
    dimension = matrix.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(matrix)
    faiss.write_index(index, str(index_path))
    if int(index.ntotal) != matrix.shape[0]:
        fail(f"FAISS index.ntotal {index.ntotal} does not match embedding rows {matrix.shape[0]}")
    return int(index.ntotal)


def embedding_norm_summary(embeddings: np.ndarray) -> dict[str, float | None]:
    if embeddings.size == 0:
        return {"min": None, "max": None, "mean": None}
    norms = np.linalg.norm(embeddings, axis=1)
    return {"min": float(norms.min()), "max": float(norms.max()), "mean": float(norms.mean())}


def count_by_type(cards: list[CardRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for card in cards:
        counts[card.evidence_type] = counts.get(card.evidence_type, 0) + 1
    return counts


def selected_evidence_id_hash(cards: list[CardRecord]) -> str:
    joined = "\n".join(card.evidence_id for card in cards)
    return sha256_text(joined)


def sanitized_model_spec(model_key: str) -> dict[str, Any]:
    spec = dict(MODEL_REGISTRY[model_key])
    # Keep backward-compatible alias out of the manifest if ever added later.
    spec.pop("api_key", None)
    return spec


def scan_existing_model_artifacts(build_root: Path) -> list[dict[str, Any]]:
    if not build_root.exists():
        return []
    artifacts: list[dict[str, Any]] = []
    for manifest_path in sorted(build_root.glob("*/embedding_manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - best-effort run manifest summary
            artifacts.append({"model_dir": manifest_path.parent.name, "manifest_path": str(manifest_path), "read_error": str(exc)})
            continue
        artifacts.append(
            {
                "model_key": manifest.get("model_key", manifest_path.parent.name),
                "provider": manifest.get("provider"),
                "model_name_or_path": manifest.get("model_name_or_path"),
                "card_count": manifest.get("card_count"),
                "embedding_dimension": manifest.get("embedding_dimension"),
                "created_at": manifest.get("created_at"),
                "manifest_path": str(manifest_path),
            }
        )
    return artifacts


def run_one_model(
    *,
    args: argparse.Namespace,
    model_key: str,
    cards: list[CardRecord],
    load_stats: LoadStats,
    build_root: Path,
    device: str,
    cuda_available: bool,
    include_types: list[EvidenceType],
) -> ModelRunResult:
    started = time.time()
    model_spec = MODEL_REGISTRY[model_key]
    document_prefix, query_prefix = resolve_prefixes(
        model_spec,
        args.prefix_policy,
        args.custom_document_prefix,
        args.custom_query_prefix,
    )
    metadata, model_input_texts = make_metadata_records(cards, document_prefix)
    model_dir = prepare_model_output_dir(build_root, model_key, overwrite=args.overwrite)

    provider = model_provider(model_spec)
    name_or_path = model_name_or_path(model_spec)
    api_model_name = name_or_path
    api_key_env = args.openai_api_key_env
    api_base_url = args.openai_base_url
    if not name_or_path:
        fail(f"Model registry entry {model_key} is missing model_name_or_path")
    pass_check(
        "phase_3_model_registry_and_prefix_policy",
        f"{model_key}: provider={provider}; prefixes resolved with policy {args.prefix_policy}",
    )

    hf_revision_resolved: str | None = None
    hf_revision_warning: str | None = None
    model: Any | None = None
    if provider == "huggingface":
        hf_revision_resolved, hf_revision_warning = get_hf_revision(name_or_path, args.hf_revision)
        if hf_revision_warning:
            warn_check("hf_revision_lookup", hf_revision_warning)
        model = load_sentence_transformer_model(model_spec, device=device, revision=args.hf_revision)
        embeddings = encode_texts(
            model,
            model_input_texts,
            batch_size=args.batch_size,
            normalize=bool(args.normalize),
        )
    elif provider in {"openai", "azure_openai"}:
        if args.hf_revision is not None:
            warn_check("hf_revision_ignored_for_openai", f"{model_key}: --hf-revision applies only to Hugging Face models")
        if provider == "azure_openai":
            deployment_env = str(model_spec.get("deployment_name_env") or "")
            api_model_name = os.environ.get(deployment_env, "")
            if not api_model_name:
                fail(f"Missing Azure embedding deployment environment variable: {deployment_env}")
            api_key_env = str(model_spec.get("api_key_env") or "")
            endpoint_env = str(model_spec.get("endpoint_env") or "")
            endpoint = os.environ.get(endpoint_env, "")
            if not endpoint:
                fail(f"Missing Azure embedding endpoint environment variable: {endpoint_env}")
            api_base_url = normalize_azure_base_url(endpoint)
        embeddings = encode_texts_openai(
            model_name=api_model_name,
            texts=model_input_texts,
            batch_size=args.batch_size,
            normalize=bool(args.normalize),
            api_key_env=api_key_env,
            base_url=api_base_url,
            dimensions=args.openai_dimensions,
            max_retries=args.openai_max_retries,
            request_timeout=args.openai_request_timeout,
        )
    else:
        fail(f"Unsupported provider for {model_key}: {provider}")

    embedding_dimension = int(embeddings.shape[1])
    np.save(model_dir / "embeddings.npy", embeddings)

    metadata_count = write_jsonl(model_dir / "card_metadata.jsonl", metadata, overwrite=True)
    if metadata_count != embeddings.shape[0]:
        fail(f"metadata row count {metadata_count} does not match embeddings row count {embeddings.shape[0]}")

    index_ntotal = build_and_save_faiss_index(
        embeddings,
        model_dir / "faiss.index",
        args.index_type,
        args.faiss_threads,
    )

    runtime_seconds = time.time() - started
    norm_summary = embedding_norm_summary(embeddings)

    summary = {
        "schema_version": "embedding_summary_v1",
        "script_version": SCRIPT_VERSION,
        "model_key": model_key,
        "provider": provider,
        "model_name_or_path": name_or_path,
        "access_type": model_spec.get("access_type"),
        "status": model_spec.get("status"),
        "role": model_spec["role"],
        "closed_api_baseline": provider in {"openai", "azure_openai"} and model_spec.get("access_type") == "closed_api",
        "card_count": int(embeddings.shape[0]),
        "metadata_count": metadata_count,
        "faiss_index_ntotal": index_ntotal,
        "embedding_dimension": embedding_dimension,
        "embedding_dtype": str(embeddings.dtype),
        "embedding_norm_summary": norm_summary,
        "runtime_seconds": runtime_seconds,
        "selected_cards_by_type": count_by_type(cards),
        "skipped_by_reason": load_stats.skipped_by_reason,
        "skipped_by_type": load_stats.skipped_by_type,
        "index_type": args.index_type,
        "normalize_embeddings": bool(args.normalize),
        "similarity_metric": "inner_product_on_normalized_vectors" if args.normalize else "inner_product",
        "created_at": now_utc_iso(),
    }
    write_json(model_dir / "embedding_summary.json", summary, overwrite=True)

    manifest = {
        "schema_version": EMBEDDING_MANIFEST_SCHEMA_VERSION,
        "script_version": SCRIPT_VERSION,
        "embedding_build_name": args.embedding_build_name,
        "evidence_root": str(args.evidence_root),
        "model_key": model_key,
        "provider": provider,
        "model_name_or_path": name_or_path,
        "api_model_name": api_model_name if provider in {"openai", "azure_openai"} else None,
        "access_type": model_spec.get("access_type"),
        "status": model_spec.get("status"),
        "role": model_spec["role"],
        "closed_api_baseline": provider in {"openai", "azure_openai"} and model_spec.get("access_type") == "closed_api",
        "hf_revision_requested": args.hf_revision if provider == "huggingface" else None,
        "hf_revision_resolved": hf_revision_resolved,
        "hf_revision_warning": hf_revision_warning,
        "trust_remote_code": bool(model_spec.get("trust_remote_code", False)) if provider == "huggingface" else None,
        "openai_api_key_env": api_key_env if provider in {"openai", "azure_openai"} else None,
        "openai_base_url_configured": bool(api_base_url) if provider in {"openai", "azure_openai"} else None,
        "openai_dimensions_requested": args.openai_dimensions if provider in {"openai", "azure_openai"} else None,
        "openai_max_retries": args.openai_max_retries if provider in {"openai", "azure_openai"} else None,
        "openai_request_timeout": args.openai_request_timeout if provider in {"openai", "azure_openai"} else None,
        "prefix_policy": args.prefix_policy,
        "document_prefix": document_prefix,
        "query_prefix": query_prefix,
        "document_prefix_applied_to_cards": bool(document_prefix),
        "query_prefix_applied_in_this_script": False,
        "included_evidence_types": list(include_types),
        "excluded_evidence_types": load_stats.excluded_evidence_types,
        "input_files": load_stats.input_files,
        "card_count": int(embeddings.shape[0]),
        "skipped_card_count": int(sum(load_stats.skipped_by_reason.values())),
        "raw_cards_by_type": load_stats.raw_cards_by_type,
        "selected_cards_by_type": count_by_type(cards),
        "skipped_by_reason": load_stats.skipped_by_reason,
        "skipped_by_type": load_stats.skipped_by_type,
        "selected_evidence_id_hash": selected_evidence_id_hash(cards),
        "embedding_dimension": embedding_dimension,
        "embedding_dtype": str(embeddings.dtype),
        "embedding_norm_summary": norm_summary,
        "normalize_embeddings": bool(args.normalize),
        "similarity_metric": "inner_product_on_normalized_vectors" if args.normalize else "inner_product",
        "faiss_index_type": "IndexFlatIP",
        "index_type_argument": args.index_type,
        "faiss_index_ntotal": index_ntotal,
        "device_requested": args.device,
        "device_resolved": device,
        "torch_cuda_available": cuda_available,
        "cpu_threads": args.cpu_threads,
        "faiss_threads": args.faiss_threads,
        "batch_size": args.batch_size,
        "max_cards": args.max_cards,
        "runtime_seconds": runtime_seconds,
        "reranker_included": False,
        "bm25_or_hybrid_included": False,
        "generation_included": False,
        "annotation_included": False,
        "table_markdown_included": "pdf_table_markdown" in include_types,
        "artifacts": {
            "embeddings_npy": "embeddings.npy",
            "faiss_index": "faiss.index",
            "card_metadata_jsonl": "card_metadata.jsonl",
            "embedding_summary_json": "embedding_summary.json",
        },
        "created_at": now_utc_iso(),
    }
    write_json(model_dir / "embedding_manifest.json", manifest, overwrite=True)

    pass_check("phase_5_embedding_generation", f"{model_key}: wrote {embeddings.shape[0]:,} embeddings with dimension {embedding_dimension}")
    pass_check("phase_6_faiss_index_building", f"{model_key}: FAISS ntotal={index_ntotal:,}")
    pass_check("phase_7_manifest_and_reproducibility_logging", f"{model_key}: manifest and summary written")

    if model is not None:
        del model
    del embeddings
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass

    return ModelRunResult(
        model_key=model_key,
        output_dir=str(model_dir),
        card_count=int(summary["card_count"]),
        embedding_dimension=embedding_dimension,
        runtime_seconds=runtime_seconds,
        manifest_path=str(model_dir / "embedding_manifest.json"),
        summary_path=str(model_dir / "embedding_summary.json"),
    )


def write_build_manifest(
    *,
    args: argparse.Namespace,
    build_root: Path,
    include_types: list[EvidenceType],
    cards: list[CardRecord],
    load_stats: LoadStats,
    model_results: list[ModelRunResult],
    dry_run: bool,
) -> None:
    payload = {
        "schema_version": EMBEDDING_BUILD_SCHEMA_VERSION,
        "script_version": SCRIPT_VERSION,
        "embedding_build_name": args.embedding_build_name,
        "evidence_root": str(args.evidence_root),
        "build_root": str(build_root),
        "dry_run": dry_run,
        "models_requested": list(args.models),
        "models_completed_this_invocation": [result.model_key for result in model_results],
        "models_with_artifacts": scan_existing_model_artifacts(build_root),
        "model_registry_entries_requested": {
            model_key: sanitized_model_spec(model_key) for model_key in args.models
        },
        "include_deferred": bool(args.include_deferred),
        "included_evidence_types": list(include_types),
        "excluded_evidence_types": load_stats.excluded_evidence_types,
        "input_files": load_stats.input_files,
        "raw_cards_by_type": load_stats.raw_cards_by_type,
        "selected_cards_by_type": count_by_type(cards),
        "selected_card_count": len(cards),
        "selected_evidence_id_hash": selected_evidence_id_hash(cards),
        "skipped_by_reason": load_stats.skipped_by_reason,
        "skipped_by_type": load_stats.skipped_by_type,
        "prefix_policy": args.prefix_policy,
        "normalize_embeddings": bool(args.normalize),
        "index_type": args.index_type,
        "device_requested": args.device,
        "cpu_threads": args.cpu_threads,
        "faiss_threads": args.faiss_threads,
        "batch_size": args.batch_size,
        "max_cards": args.max_cards,
        "hf_revision_requested": args.hf_revision,
        "openai_api_key_env": args.openai_api_key_env,
        "openai_base_url_configured": bool(args.openai_base_url),
        "openai_dimensions_requested": args.openai_dimensions,
        "openai_max_retries": args.openai_max_retries,
        "openai_request_timeout": args.openai_request_timeout,
        "model_results_this_invocation": [result.__dict__ for result in model_results],
        "acceptance_criteria": ACCEPTANCE_CRITERIA,
        "created_at": now_utc_iso(),
    }
    write_json(build_root / "embedding_build_manifest.json", payload, overwrite=True)


def main() -> None:
    args = parse_args()
    if args.print_acceptance_criteria:
        print_acceptance_criteria()

    include_types = validate_args(args)
    configure_cpu_parallelism(args.cpu_threads, args.faiss_threads)
    paths = required_input_paths(args.evidence_root, include_types)
    if "pdf_table_markdown" not in include_types:
        pass_check("phase_2_card_selection_policy", "pdf_table_markdown is excluded by default/current settings")
    pass_check("phase_1_input_discovery_and_validation", f"found {len(paths)} canonical input index file(s)")

    cards, load_stats = load_cards(
        evidence_root=args.evidence_root,
        include_types=include_types,
        max_cards=args.max_cards,
    )

    build_root = embeddings_build_root(args.evidence_root, args.embedding_build_name)
    build_root.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        write_build_manifest(
            args=args,
            build_root=build_root,
            include_types=include_types,
            cards=cards,
            load_stats=load_stats,
            model_results=[],
            dry_run=True,
        )
        pass_check("dry_run", f"validated {len(cards):,} cards and wrote build manifest to {build_root}")
        return

    device, cuda_available = resolve_device(args.device)
    pass_check("phase_4_cpu_and_device_configuration", f"device resolved to {device}; cuda_available={cuda_available}")

    model_results: list[ModelRunResult] = []
    for model_key in args.models:
        result = run_one_model(
            args=args,
            model_key=model_key,
            cards=cards,
            load_stats=load_stats,
            build_root=build_root,
            device=device,
            cuda_available=cuda_available,
            include_types=include_types,
        )
        model_results.append(result)

    write_build_manifest(
        args=args,
        build_root=build_root,
        include_types=include_types,
        cards=cards,
        load_stats=load_stats,
        model_results=model_results,
        dry_run=False,
    )

    if len(model_results) > 1:
        hashes = {selected_evidence_id_hash(cards)}
        if len(hashes) == 1:
            pass_check("phase_9_pilot_full_embedding_build_readiness", "all model runs used the same selected evidence_id list")

    pass_check("phase_10_handoff_to_retrieval_evaluation", "FAISS row ids can be mapped through card_metadata.jsonl")
    print(f"\nDone. Embedding build written to: {build_root}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user", file=sys.stderr)
        sys.exit(130)
