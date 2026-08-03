#!/usr/bin/env python3
"""Build deterministic W2 generation inputs from frozen retrieval results.

This script is the bridge between W2 retrieval and GPT generation. It does not
run retrieval and does not call a generation model. It reads selected retrieval
result JSONL files, renders a frozen W2 prompt layout, and writes generation-ready
JSONL cases plus audit metadata.

Frozen prompt design:
- Company, reporting year, and task are merged into one instruction sentence.
- Prompt-local labels use Evidence 1, Evidence 2, ...
- Stable evidence_id values are NOT shown in the prompt.
- The generation_cases.jsonl keeps prompt_label -> evidence_id mapping.
- Evidence is grouped by evidence type, default order:
    narrative -> pdf_table_row -> csv_metric
- Prompt source labels are human-readable:
    PDF: <source_file> | Page <page_start[-page_end]>
    CSV: Corporate Sustainability Tracker | Source year <source_year>

Example:
    python script/rag/build_w2_generation_inputs.py \
      --evidence-root evidence_pilot \
      --retrieval-runs-root evidence_pilot/retrieval_runs \
      --retrieval-condition stratified_per_type \
      --embedding-model qwen3_0_6b \
      --selection-setting stratified_by_evidence_type_n10 \
      --task-spec config/tasks/esrs_e1_task_specs.json \
      --generation-template config/prompts/generation_prompt_templates.json \
      --output-dir evidence_pilot/generation_inputs/w2_main_qwen3_stratified_n10 \
      --write-previews \
      --overwrite
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCRIPT_VERSION = "build_w2_generation_inputs_v1.1"
GENERATION_INPUT_SCHEMA_VERSION = "w2_generation_cases_v1"
PROMPT_LAYOUT_VERSION = "w2_generation_prompt_layout_v1"

DEFAULT_EVIDENCE_GROUP_ORDER = ["narrative", "pdf_table_row", "csv_metric"]

EVIDENCE_GROUP_TITLES = {
    "narrative": "PDF Narrative Evidence",
    "pdf_table_row": "PDF Table Row Evidence",
    "csv_metric": "CSV Metric Evidence",
}

DEFAULT_TASK_TITLES = {
    "E1-1_transition_plan": "E1-1 transition plan",
    "E1-3_actions_resources": "E1-3 actions and resources",
    "E1-4_targets": "E1-4 climate-related targets",
    "E1-6_ghg_emissions": "E1-6 GHG emissions",
}

SELECTION_TO_RESULT_FILE = {
    "global_top_k_30": "retrieval_results_hybrid_rrf_global_top_k_30.jsonl",
    "global_top_k_45": "retrieval_results_hybrid_rrf_global_top_k_45.jsonl",
    "global_top_k_60": "retrieval_results_hybrid_rrf_global_top_k_60.jsonl",
    "stratified_by_evidence_type_n10": "retrieval_results_hybrid_rrf_stratified_by_evidence_type_n10.jsonl",
    "stratified_by_evidence_type_n15": "retrieval_results_hybrid_rrf_stratified_by_evidence_type_n15.jsonl",
    "stratified_by_evidence_type_n20": "retrieval_results_hybrid_rrf_stratified_by_evidence_type_n20.jsonl",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build deterministic W2 generation input JSONL from retrieval results."
    )
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--retrieval-runs-root", type=Path, required=True)
    parser.add_argument("--retrieval-condition", type=str, required=True)
    parser.add_argument(
        "--embedding-model",
        dest="embedding_models",
        nargs="+",
        required=True,
        help="One or more retrieval run folder names, e.g. qwen3_0_6b.",
    )
    parser.add_argument("--selection-setting", type=str, required=True)
    parser.add_argument("--task-spec", type=Path, required=True)
    parser.add_argument("--generation-template", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--evidence-group-order",
        nargs="+",
        default=None,
        choices=list(EVIDENCE_GROUP_TITLES.keys()),
        help=(
            "Optional CLI override. If omitted, w2.evidence_group_order is "
            "read from --generation-template."
        ),
    )
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--case-ids", nargs="+", default=None)
    parser.add_argument("--task-ids", nargs="+", default=None)
    parser.add_argument("--target-years", nargs="+", type=int, default=None)
    parser.add_argument("--company-names", nargs="+", default=None)
    parser.add_argument("--write-previews", action="store_true")
    parser.add_argument("--preview-limit", type=int, default=120)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def slugify(value: Any, max_len: int = 120) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = "unknown"
    return text[:max_len].strip("_")


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


def load_generation_config(path: Path) -> dict[str, Any]:
    """Load and validate the machine-readable generation prompt config.

    The JSON config is the source of truth for generation instruction wording,
    output length, W2 evidence block order, prompt-local labels, and citation
    policy. This script only renders that config deterministically.
    """
    obj = read_json(path)
    if not isinstance(obj, dict):
        raise RuntimeError(f"Generation prompt config must be a JSON object: {path}")

    instruction_template = clean_text(obj.get("instruction_template"))
    if not instruction_template:
        raise RuntimeError("Generation prompt config must define non-empty instruction_template.")

    required_placeholders = [
        "{company_name}",
        "{target_reporting_year}",
        "{task_title}",
    ]
    missing = [x for x in required_placeholders if x not in instruction_template]
    if missing:
        raise RuntimeError(f"instruction_template is missing required placeholders: {missing}")

    output_length = obj.get("output_length_words")
    if not isinstance(output_length, dict):
        raise RuntimeError("Generation prompt config must define output_length_words.")
    if output_length.get("minimum") != 300 or output_length.get("maximum") != 500:
        raise RuntimeError(
            "For this frozen generation run, expected "
            "output_length_words.minimum=300 and output_length_words.maximum=500."
        )

    w2 = obj.get("w2")
    if not isinstance(w2, dict):
        raise RuntimeError("Generation prompt config must define a w2 object.")

    if w2.get("evidence_id_in_prompt", False) is not False:
        raise RuntimeError("This script version expects w2.evidence_id_in_prompt=false.")
    if w2.get("citation_required", False) is not False:
        raise RuntimeError("This script version expects w2.citation_required=false.")

    group_order = w2.get("evidence_group_order", DEFAULT_EVIDENCE_GROUP_ORDER)
    if not isinstance(group_order, list) or not group_order:
        raise RuntimeError("w2.evidence_group_order must be a non-empty list.")
    invalid_groups = [x for x in group_order if x not in EVIDENCE_GROUP_TITLES]
    if invalid_groups:
        raise RuntimeError(f"Unsupported evidence types in w2.evidence_group_order: {invalid_groups}")

    label_format = clean_text(w2.get("evidence_label_format") or "Evidence {number}")
    if "{number}" not in label_format:
        raise RuntimeError("w2.evidence_label_format must contain {number}.")

    return obj


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
            if not isinstance(obj, dict):
                raise RuntimeError(f"Expected JSON object at {path}:{line_no}")
            rows.append(obj)
    return rows


def write_json(path: Path, payload: Any, *, overwrite: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise RuntimeError(f"Refusing to overwrite existing file: {path}")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, records: Iterable[dict[str, Any]], *, overwrite: bool = True) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise RuntimeError(f"Refusing to overwrite existing file: {path}")
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_csv(path: Path, rows: list[dict[str, Any]], *, overwrite: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise RuntimeError(f"Refusing to overwrite existing file: {path}")
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({k for row in rows for k in row.keys()})
    preferred = [
        "generation_case_id",
        "workflow",
        "embedding_model",
        "retrieval_condition",
        "selection_setting",
        "case_id",
        "company_name",
        "target_reporting_year",
        "task_id",
        "task_title",
        "retrieved_count",
        "csv_metric_count",
        "pdf_narrative_count",
        "pdf_table_row_count",
        "prompt_word_count",
        "prompt_char_count",
        "prompt_hash",
    ]
    fieldnames = [x for x in preferred if x in fieldnames] + [x for x in fieldnames if x not in preferred]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_task_specs(path: Path) -> dict[str, dict[str, Any]]:
    obj = read_json(path)
    if isinstance(obj, dict):
        if "tasks" in obj and isinstance(obj["tasks"], list):
            tasks = obj["tasks"]
        elif "task_specs" in obj and isinstance(obj["task_specs"], list):
            tasks = obj["task_specs"]
        else:
            # Already keyed by task_id.
            tasks = []
            for key, value in obj.items():
                if isinstance(value, dict):
                    row = dict(value)
                    row.setdefault("task_id", key)
                    tasks.append(row)
    elif isinstance(obj, list):
        tasks = obj
    else:
        raise RuntimeError(f"Unsupported task spec structure in {path}")

    out: dict[str, dict[str, Any]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = clean_text(task.get("task_id") or task.get("id"))
        if task_id:
            out[task_id] = task
    return out


def resolve_task_title(task_id: str, task: dict[str, Any] | None) -> str:
    task = task or {}
    esrs_ref = clean_text(task.get("esrs_reference") or task.get("esrs") or "")
    task_name = clean_text(
        task.get("task_title")
        or task.get("task_name")
        or task.get("title")
        or task.get("name")
        or ""
    )
    if esrs_ref and task_name:
        if task_name.lower().startswith(esrs_ref.lower()):
            return task_name
        return f"{esrs_ref} {task_name}"
    if task_name:
        return task_name
    if esrs_ref:
        return esrs_ref
    return DEFAULT_TASK_TITLES.get(task_id, task_id.replace("_", " "))


def retrieval_result_path(root: Path, condition: str, model: str, setting: str) -> Path:
    filename = SELECTION_TO_RESULT_FILE.get(setting)
    if not filename:
        # Conservative fallback for future settings.
        filename = f"retrieval_results_hybrid_rrf_{setting}.jsonl"
    return root / condition / model / filename


def maybe_filter_records(records: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    out = []
    case_id_set = set(args.case_ids or [])
    task_id_set = set(args.task_ids or [])
    target_year_set = set(args.target_years or [])
    company_set = {clean_text(x).lower() for x in (args.company_names or [])}

    for record in records:
        if case_id_set and clean_text(record.get("case_id")) not in case_id_set:
            continue
        if task_id_set and clean_text(record.get("task_id")) not in task_id_set:
            continue
        if target_year_set:
            try:
                year = int(record.get("target_reporting_year"))
            except Exception:
                year = None
            if year not in target_year_set:
                continue
        if company_set and clean_text(record.get("company_name")).lower() not in company_set:
            continue
        out.append(record)

    out = sorted(
        out,
        key=lambda r: (
            clean_text(r.get("company_name")),
            int(r.get("target_reporting_year") or 0),
            clean_text(r.get("task_id")),
            clean_text(r.get("case_id")),
        ),
    )
    if args.max_cases is not None:
        out = out[: args.max_cases]
    return out


def source_label_for_card(card: dict[str, Any]) -> str:
    evidence_type = clean_text(card.get("evidence_type"))
    source_year = clean_text(card.get("source_year"))
    source_file = clean_text(card.get("source_file"))
    document_type = clean_text(card.get("document_type"))

    page_start = clean_text(card.get("page_start"))
    page_end = clean_text(card.get("page_end"))

    if evidence_type == "csv_metric":
        if source_year:
            return f"Corporate Sustainability Tracker | Source year {source_year}"
        return "Corporate Sustainability Tracker"

    source = source_file or document_type or "PDF source"
    if page_start and page_end and page_start != page_end:
        return f"{source} | Pages {page_start}-{page_end}"
    if page_start:
        return f"{source} | Page {page_start}"
    if source_year:
        return f"{source} | Source year {source_year}"
    return source


def instruction_for_case(
    instruction_template: str,
    company_name: str,
    target_reporting_year: Any,
    task_title: str,
) -> str:
    return instruction_template.format(
        company_name=company_name,
        target_reporting_year=target_reporting_year,
        task_title=task_title,
    )


def evidence_sort_key(card: dict[str, Any]) -> tuple[int, int, str]:
    # Keep retrieval-script prompt_rank/final_rank within each group.
    prompt_rank = card.get("prompt_rank")
    final_rank = card.get("final_rank")
    try:
        pr = int(prompt_rank)
    except Exception:
        pr = 999999
    try:
        fr = int(final_rank)
    except Exception:
        fr = 999999
    return (pr, fr, clean_text(card.get("evidence_id")))


def normalize_evidence_type(value: Any) -> str:
    text = clean_text(value)
    if text == "pdf_narrative":
        return "narrative"
    return text


def grouped_cards(record: dict[str, Any], group_order: list[str]) -> dict[str, list[dict[str, Any]]]:
    cards = record.get("retrieved_cards")
    if not isinstance(cards, list):
        raise RuntimeError(f"Record {record.get('case_id')} does not contain retrieved_cards list.")
    groups: dict[str, list[dict[str, Any]]] = {g: [] for g in group_order}
    for card in cards:
        if not isinstance(card, dict):
            continue
        et = normalize_evidence_type(card.get("evidence_type"))
        if et in groups:
            groups[et].append(card)
    for et in groups:
        groups[et].sort(key=evidence_sort_key)
    return groups


def render_evidence_blocks(
    record: dict[str, Any],
    group_order: list[str],
    evidence_label_format: str,
) -> tuple[str, list[dict[str, Any]], dict[str, int]]:
    groups = grouped_cards(record, group_order)

    lines: list[str] = []
    prompt_evidence: list[dict[str, Any]] = []
    evidence_number = 1
    counts: Counter[str] = Counter()

    for group in group_order:
        cards = groups.get(group, [])
        if not cards:
            continue

        if lines:
            lines.append("")
            lines.append("-" * 50)
            lines.append("")

        lines.append(EVIDENCE_GROUP_TITLES.get(group, group))
        lines.append("")

        for card in cards:
            prompt_label = evidence_label_format.format(number=evidence_number)
            source_label = source_label_for_card(card)
            retrieval_text = clean_text(card.get("retrieval_text") or card.get("full_retrieval_text") or "")

            lines.append(prompt_label)
            lines.append("")
            lines.append("Source:")
            lines.append(source_label)
            lines.append("")
            lines.append("Text:")
            lines.append(retrieval_text if retrieval_text else "[No retrieval text available]")
            lines.append("")

            prompt_evidence.append(
                {
                    "prompt_label": prompt_label,
                    "evidence_id": card.get("evidence_id"),
                    "evidence_type": normalize_evidence_type(card.get("evidence_type")),
                    "source_type": card.get("source_type"),
                    "source_year": card.get("source_year"),
                    "source_label": source_label,
                    "source_file": card.get("source_file"),
                    "document_type": card.get("document_type"),
                    "page_start": card.get("page_start"),
                    "page_end": card.get("page_end"),
                    "metric": card.get("metric"),
                    "value_text": card.get("value_text"),
                    "unit": card.get("unit"),
                    "retrieval_rank": card.get("final_rank"),
                    "prompt_rank_from_retrieval": card.get("prompt_rank"),
                    "final_rrf_score": card.get("final_rrf_score"),
                    "bm25_best_rank": card.get("bm25_best_rank"),
                    "dense_best_rank": card.get("dense_best_rank"),
                    "retrieval_text": retrieval_text,
                    "retrieval_text_hash": sha256_text(retrieval_text),
                    "shown_in_prompt": True,
                }
            )
            counts[normalize_evidence_type(card.get("evidence_type"))] += 1
            evidence_number += 1

    evidence_block = "\n".join(lines).strip()
    return evidence_block, prompt_evidence, dict(counts)


def render_generation_prompt(instruction: str, evidence_block: str) -> str:
    return "\n\n".join(
        [
            "Instruction",
            instruction.strip(),
            "Evidence",
            evidence_block.strip() if evidence_block.strip() else "[No evidence retrieved]",
        ]
    ).strip() + "\n"


def generation_case_id_for(
    workflow: str,
    embedding_model: str,
    selection_setting: str,
    company_name: str,
    target_reporting_year: Any,
    task_id: str,
) -> str:
    return "__".join(
        [
            slugify(workflow),
            slugify(embedding_model),
            slugify(selection_setting),
            slugify(company_name, 60),
            slugify(target_reporting_year),
            slugify(task_id, 80),
        ]
    )


def build_generation_case(
    record: dict[str, Any],
    *,
    embedding_model: str,
    retrieval_condition: str,
    selection_setting: str,
    task_specs: dict[str, dict[str, Any]],
    group_order: list[str],
    generation_config: dict[str, Any],
) -> dict[str, Any]:
    task_id = clean_text(record.get("task_id"))
    task = task_specs.get(task_id, {})
    task_title = resolve_task_title(task_id, task)
    company_name = clean_text(record.get("company_name"))
    target_year = record.get("target_reporting_year")

    w2_config = generation_config.get("w2", {})
    instruction_template = generation_config["instruction_template"]
    evidence_label_format = clean_text(w2_config.get("evidence_label_format") or "Evidence {number}")

    instruction = instruction_for_case(
        instruction_template,
        company_name,
        target_year,
        task_title,
    )
    evidence_block, prompt_evidence, evidence_counts = render_evidence_blocks(
        record,
        group_order,
        evidence_label_format,
    )
    generation_prompt = render_generation_prompt(instruction, evidence_block)
    prompt_hash = sha256_text(generation_prompt)

    generation_case_id = generation_case_id_for(
        "W2",
        embedding_model,
        selection_setting,
        company_name,
        target_year,
        task_id,
    )

    return {
        "schema_version": GENERATION_INPUT_SCHEMA_VERSION,
        "generation_case_id": generation_case_id,
        "workflow": "W2",
        "case_id": record.get("case_id"),
        "company_id": record.get("company_id"),
        "company_name": company_name,
        "target_reporting_year": target_year,
        "task_id": task_id,
        "task_title": task_title,
        "package_id": record.get("package_id"),
        "retrieval_setting": {
            "embedding_model": embedding_model,
            "retrieval_condition": retrieval_condition,
            "selection_setting": selection_setting,
            "retrieval_algorithm": record.get("retrieval_algorithm_key"),
            "final_selection_mode": record.get("final_selection_mode"),
            "top_k": record.get("top_k"),
            "per_evidence_type_top_n": record.get("per_evidence_type_top_n"),
            "max_generation_cards": 30 if selection_setting == "stratified_by_evidence_type_n10" else None,
            "deficit_redistribution": False,
        },
        "instruction": instruction,
        "prompt_evidence": prompt_evidence,
        "generation_prompt": generation_prompt,
        "prompt_metadata": {
            "prompt_layout_version": PROMPT_LAYOUT_VERSION,
            "evidence_id_in_prompt": bool(w2_config.get("evidence_id_in_prompt", False)),
            "evidence_group_order": group_order,
            "evidence_label_format": evidence_label_format,
            "prompt_label_maps_to_evidence_id": bool(w2_config.get("prompt_label_maps_to_evidence_id", True)),
            "citation_required": bool(w2_config.get("citation_required", False)),
            "source_label_format": "PDF: <source> | Page(s) <page>; CSV: Corporate Sustainability Tracker | Source year <year>",
            "evidence_count": len(prompt_evidence),
            "evidence_type_distribution": evidence_counts,
            "prompt_hash": prompt_hash,
            "prompt_char_count": len(generation_prompt),
            "prompt_word_count": len(generation_prompt.split()),
        },
        "retrieval_record_metadata": {
            "query_bundle_id": record.get("query_bundle_id"),
            "query_bundle_hash": record.get("query_bundle_hash"),
            "eligible_corpus_size": record.get("eligible_corpus_size"),
            "boundary_validation_passed": record.get("boundary_validation_passed"),
            "csv_source_years": record.get("csv_source_years"),
            "pdf_source_years": record.get("pdf_source_years"),
            "missing_embedding_mappings": record.get("missing_embedding_mappings"),
            "source_year_distribution": record.get("source_year_distribution"),
        },
    }


def summary_row(case: dict[str, Any]) -> dict[str, Any]:
    dist = case["prompt_metadata"].get("evidence_type_distribution") or {}
    return {
        "generation_case_id": case["generation_case_id"],
        "workflow": case["workflow"],
        "embedding_model": case["retrieval_setting"]["embedding_model"],
        "retrieval_condition": case["retrieval_setting"]["retrieval_condition"],
        "selection_setting": case["retrieval_setting"]["selection_setting"],
        "case_id": case["case_id"],
        "company_name": case["company_name"],
        "target_reporting_year": case["target_reporting_year"],
        "task_id": case["task_id"],
        "task_title": case["task_title"],
        "retrieved_count": case["prompt_metadata"]["evidence_count"],
        "csv_metric_count": dist.get("csv_metric", 0),
        "pdf_narrative_count": dist.get("narrative", 0),
        "pdf_table_row_count": dist.get("pdf_table_row", 0),
        "prompt_word_count": case["prompt_metadata"]["prompt_word_count"],
        "prompt_char_count": case["prompt_metadata"]["prompt_char_count"],
        "prompt_hash": case["prompt_metadata"]["prompt_hash"],
    }


def preview_filename(case: dict[str, Any]) -> str:
    return "__".join(
        [
            slugify(case["retrieval_setting"]["embedding_model"], 40),
            slugify(case["company_name"], 50),
            slugify(case["target_reporting_year"], 10),
            slugify(case["task_id"], 80),
        ]
    ) + ".txt"


def write_prompt_previews(output_dir: Path, cases: list[dict[str, Any]], limit: int, overwrite: bool) -> int:
    preview_dir = output_dir / "prompt_previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for case in cases[:limit]:
        model = case["retrieval_setting"]["embedding_model"]
        model_dir = preview_dir / model
        model_dir.mkdir(parents=True, exist_ok=True)
        path = model_dir / preview_filename(case)
        if path.exists() and not overwrite:
            raise RuntimeError(f"Refusing to overwrite existing preview: {path}")
        path.write_text(case["generation_prompt"], encoding="utf-8")
        count += 1
    return count


def validate_args(args: argparse.Namespace) -> None:
    if not args.evidence_root.exists():
        raise RuntimeError(f"--evidence-root does not exist: {args.evidence_root}")
    if not args.retrieval_runs_root.exists():
        raise RuntimeError(f"--retrieval-runs-root does not exist: {args.retrieval_runs_root}")
    if not args.task_spec.exists():
        raise RuntimeError(f"--task-spec does not exist: {args.task_spec}")
    if not args.generation_template.exists():
        raise RuntimeError(f"--generation-template does not exist: {args.generation_template}")
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.overwrite and not args.dry_run:
        raise RuntimeError(f"Output directory is not empty. Use --overwrite: {args.output_dir}")


def main() -> None:
    args = parse_args()
    validate_args(args)

    if args.output_dir.exists() and args.overwrite and not args.dry_run:
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    task_specs = load_task_specs(args.task_spec)
    generation_config = load_generation_config(args.generation_template)
    w2_config = generation_config.get("w2", {})
    config_group_order = w2_config.get("evidence_group_order", DEFAULT_EVIDENCE_GROUP_ORDER)
    group_order = args.evidence_group_order or config_group_order
    group_order_source = "cli_override" if args.evidence_group_order else "generation_config"

    all_generation_cases: list[dict[str, Any]] = []
    input_files: list[dict[str, Any]] = []

    for model in args.embedding_models:
        result_path = retrieval_result_path(
            args.retrieval_runs_root,
            args.retrieval_condition,
            model,
            args.selection_setting,
        )
        if not result_path.exists():
            raise RuntimeError(f"Retrieval result file not found for model {model}: {result_path}")

        records = read_jsonl(result_path)
        records = maybe_filter_records(records, args)

        input_files.append(
            {
                "embedding_model": model,
                "retrieval_result_file": str(result_path),
                "sha256": sha256_file(result_path),
                "record_count_after_filters": len(records),
            }
        )

        for record in records:
            case = build_generation_case(
                record,
                embedding_model=model,
                retrieval_condition=args.retrieval_condition,
                selection_setting=args.selection_setting,
                task_specs=task_specs,
                group_order=group_order,
                generation_config=generation_config,
            )
            all_generation_cases.append(case)

    all_generation_cases = sorted(
        all_generation_cases,
        key=lambda c: (
            c["retrieval_setting"]["embedding_model"],
            clean_text(c["company_name"]),
            int(c["target_reporting_year"] or 0),
            clean_text(c["task_id"]),
            clean_text(c["case_id"]),
        ),
    )

    summary_rows = [summary_row(c) for c in all_generation_cases]
    summary_counts = Counter(
        (
            c["retrieval_setting"]["embedding_model"],
            c["task_id"],
        )
        for c in all_generation_cases
    )

    manifest = {
        "schema_version": "w2_generation_input_manifest_v1",
        "script_version": SCRIPT_VERSION,
        "created_at_utc": now_utc_iso(),
        "evidence_root": str(args.evidence_root),
        "retrieval_runs_root": str(args.retrieval_runs_root),
        "retrieval_condition": args.retrieval_condition,
        "selection_setting": args.selection_setting,
        "embedding_models": args.embedding_models,
        "task_spec_file": str(args.task_spec),
        "task_spec_sha256": sha256_file(args.task_spec),
        "generation_template_file": str(args.generation_template),
        "generation_template_sha256": sha256_file(args.generation_template),
        "generation_config_version": generation_config.get("config_version"),
        "generation_config_status": generation_config.get("status"),
        "prompt_layout_version": PROMPT_LAYOUT_VERSION,
        "generation_input_schema_version": GENERATION_INPUT_SCHEMA_VERSION,
        "instruction_template": generation_config.get("instruction_template"),
        "output_length_words": generation_config.get("output_length_words"),
        "evidence_id_in_prompt": bool(w2_config.get("evidence_id_in_prompt", False)),
        "prompt_label_maps_to_evidence_id": bool(w2_config.get("prompt_label_maps_to_evidence_id", True)),
        "citation_required": bool(w2_config.get("citation_required", False)),
        "evidence_label_format": clean_text(w2_config.get("evidence_label_format") or "Evidence {number}"),
        "evidence_group_order": group_order,
        "evidence_group_order_source": group_order_source,
        "input_files": input_files,
        "filters": {
            "max_cases": args.max_cases,
            "case_ids": args.case_ids,
            "task_ids": args.task_ids,
            "target_years": args.target_years,
            "company_names": args.company_names,
        },
        "generation_case_count": len(all_generation_cases),
        "case_counts_by_model_task": {
            f"{model}::{task_id}": count
            for (model, task_id), count in sorted(summary_counts.items())
        },
        "outputs": {
            "generation_cases_jsonl": str(args.output_dir / "generation_cases.jsonl"),
            "generation_cases_summary_csv": str(args.output_dir / "generation_cases_summary.csv"),
            "generation_input_manifest_json": str(args.output_dir / "generation_input_manifest.json"),
            "prompt_previews_dir": str(args.output_dir / "prompt_previews") if args.write_previews else None,
        },
    }

    if args.dry_run:
        print("[DRY RUN] Would write generation cases:", len(all_generation_cases))
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return

    cases_path = args.output_dir / "generation_cases.jsonl"
    summary_path = args.output_dir / "generation_cases_summary.csv"
    manifest_path = args.output_dir / "generation_input_manifest.json"

    write_jsonl(cases_path, all_generation_cases, overwrite=True)
    write_csv(summary_path, summary_rows, overwrite=True)
    write_json(manifest_path, manifest, overwrite=True)

    preview_count = 0
    if args.write_previews:
        preview_count = write_prompt_previews(
            args.output_dir,
            all_generation_cases,
            args.preview_limit,
            overwrite=True,
        )

    print(f"[DONE] Wrote {len(all_generation_cases):,} generation cases")
    print(f"[DONE] generation_cases.jsonl: {cases_path}")
    print(f"[DONE] generation_cases_summary.csv: {summary_path}")
    print(f"[DONE] generation_input_manifest.json: {manifest_path}")
    if args.write_previews:
        print(f"[DONE] prompt previews written: {preview_count:,}")


if __name__ == "__main__":
    main()
