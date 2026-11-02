"""Recalculate report results without changing experiment or analysis artifacts."""

import csv
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "BACE/analysis/outputs/snapshot"
SEED = 20260921
DRAWS = 2000
INPUTS = {}
TOKENS = {}


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def tracked(path):
    path = Path(path)
    INPUTS[str(path.relative_to(ROOT))] = digest(path)
    return path


def read_json(path):
    return json.loads(tracked(path).read_text())


def read_csv(path):
    with tracked(path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def read_jsonl(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def write_csv(name, records):
    with (OUT / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def markdown_table(headers, records):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"] + ["| " + " | ".join(map(str, record)) + " |" for record in records])


def interval(records, value):
    grouped = defaultdict(list)
    for record in records:
        grouped[record["company_id"]].append(value(record))
    ordered = [grouped[company] for company in sorted(grouped)]
    totals = np.array([sum(values) for values in ordered])
    counts = np.array([len(values) for values in ordered])
    positions = np.random.default_rng(SEED).integers(0, len(ordered), size=(DRAWS, len(ordered)))
    replicates = totals[positions].sum(axis=1) / counts[positions].sum(axis=1)
    low, high = np.quantile(replicates, [0.025, 0.975])
    return {"mean": float(totals.sum() / counts.sum()), "low": float(low), "high": float(high), "companies": len(ordered), "disclosures": int(counts.sum())}


def percentage(value):
    return f"{100 * value:.1f}%"


def estimate_text(result):
    return f"{percentage(result['mean'])} ({100 * result['low']:.1f}-{100 * result['high']:.1f})"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, tracked(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


manifest = read_json(SNAPSHOT / "manifest.json")
source_index = read_json(SNAPSHOT / "sources.json")
print(f"Verifying {len(source_index):,} consumed-source hashes", flush=True)
for source, expected in source_index.items():
    actual = digest(ROOT / source)
    if actual != expected:
        raise ValueError(f"Saved analysis source changed: {source}")
for table, expected in manifest["tables"].items():
    if digest(SNAPSHOT / f"{table}.csv") != expected:
        raise ValueError(f"Snapshot table changed: {table}")
print("Source and snapshot hashes match", flush=True)

metrics = read_csv(SNAPSHOT / "metrics.csv")
claims = read_csv(SNAPSHOT / "claims.csv")
selection = read_csv(SNAPSHOT / "selection.csv")
canonical = read_csv(SNAPSHOT / "canonical_counts.csv")
visible = read_csv(SNAPSHOT / "visible.csv")
execution = read_json(ROOT / "BACE/results/main_v1/execution_status.json")
run_manifest = read_json(ROOT / "BACE/results/main_v1/manifest.json")
sample = read_json(ROOT / "BACE/evidence/sample/sample.json")
quality = read_json(ROOT / "BACE/evidence/quality_exclusions.json")
pdf_build = read_json(ROOT / "BACE/evidence/pdf_build_report.json")
vector_manifest = read_json(ROOT / "BACE/evidence/embeddings/manifest.json")
freeze = read_json(ROOT / "BACE/config/freeze.json")
reference_paths = [
    "BACE/PROTOCOL.md", "BACE/config/experiment.json", "BACE/config/tasks.json",
    "BACE/evidence/sample/sampling_frame.json", "BACE/script/select_sample.py",
    "BACE/script/prepare_evidence.py", "BACE/script/data_2_evidence/csv_2_evidence.py",
    "BACE/script/data_2_evidence/pdf_2_evidence.py", "BACE/evidence/mapping_corrections.json",
    "BACE/config/retrieval/retrieval_algorithm_config_text_embedding_3_large_top200_v1.json",
    "BACE/config/queries.json", "BACE/config/prompts/generation_prompt_templates.json",
    "BACE/script/generation/run_w2_generation.py", "BACE/script/pipeline.py",
    "BACE/evidence/inputs/generation_input_manifest.json",
    "BACE/config/evaluation/configs/external_evaluation_config.json",
    "BACE/analysis/ANALYSIS_SPEC.md", "BACE/analysis/analysis_data.py",
    "paper/analysis/fig3/case_evidence.json",
    "paper/analysis/fig3/original_source_checks.json",
]
reference_paths.extend(str(path.relative_to(ROOT)) for path in (ROOT / "BACE/config/evaluation").rglob("generation_claim_*" ) if path.is_file())
for relative in reference_paths:
    tracked(ROOT / relative)
    if relative.startswith("BACE/") and relative[5:] in freeze["files"]:
        assert INPUTS[relative] == freeze["files"][relative[5:]], relative

concept_stages = [
    ("Direct extraction", "generation_claim_extraction_config_v8.json", "DEFINITION; PROCEDURE; OUTPUT; EVIDENCE/DISCLOSURE RULES", "5.2: admission, atomicity, source roles and context"),
    ("Identified-patch review", "generation_claim_patch_review_config_v4.json", "BACE OPERATIONAL DEFINITION; WORK SEQUENCE; EDIT OUTPUT CONTRACT", "5.2: source-faithful repair and addressed edits"),
    ("Atomicity review", "generation_claim_atomicity_review_config_v2.json", "TASK: CONSERVATIVE SPLITTING OF ALREADY ADMITTED CLAIMS; For each existing claim; OUTPUT", "5.2: constrained splitting"),
    ("Semantic deduplication", "generation_claim_semantic_dedup_config.json", "Semantic-equivalence criterion; Partition contract", "5.2: mutual entailment, canonical text and counting"),
    ("Candidate selection", "generation_claim_candidate_selection_config.json", "Candidate criterion; Recall and selectivity; Evidence boundary; Output contract", "5.3: material relevance and capacity limits"),
    ("Support assessment", "generation_claim_support_config.json", "Support assessment; Support type; Minimality; Output contract", "5.4: complete entailment, support types and minimal sets"),
    ("Unsupported diagnosis", "generation_claim_unsupported_diagnosis_config.json", "Exclusive classification; Rationale; Output contract", "5.5: six ordered, exclusive diagnoses"),
]
concept_records = []
concept_table = [["Operational definition v2", "`prompts/generation_claim_definition_v2.txt`", "Referenced by patch/atomicity configs; ADMISSION, ATOMICITY, FIDELITY"]]
for stage, config_name, locator, report_use in concept_stages:
    config_path = ROOT / "BACE/config/evaluation/configs" / config_name
    config = read_json(config_path)
    references = []
    for field in ["prompts", "prompt", "response_schemas", "response_schema", "operational_definition"]:
        entries = config.get(field, {})
        if "file" in entries:
            entries = {"shared": entries}
        for role, reference in entries.items():
            source_path = (config_path.parent / reference["file"]).resolve()
            relative = str(source_path.relative_to(ROOT))
            tracked(source_path)
            assert INPUTS[relative] == reference["sha256"], relative
            if relative[5:] in freeze["files"]:
                assert INPUTS[relative] == freeze["files"][relative[5:]], relative
            references.append({"kind": field, "role": role, "path": relative, "sha256": INPUTS[relative], "version": reference.get("version", source_path.stem), "version_origin": "Declared configuration version" if "version" in reference else "Filename identifier; no separate declared version", "locator": locator if field in ["prompt", "prompts"] else "Entire schema" if field in ["response_schema", "response_schemas"] else "ADMISSION; ATOMICITY; FIDELITY"})
    concept_records.append({"stage": stage, "report_use": report_use, "config_path": str(config_path.relative_to(ROOT)), "config_sha256": digest(config_path), "config_schema_version": config["schema_version"], "parameters": {key: config[key] for key in ["output_validation", "deduplication", "selection", "assessment", "diagnosis"] if key in config}, "references": references})
    prompt_names = [f"`prompts/{Path(reference['path']).name}`" for reference in references if reference["kind"] in ["prompt", "prompts"]]
    concept_table.append([stage, "; ".join(prompt_names), f"`configs/{config_name}`; {locator}"])
TOKENS["concept_source_table"] = markdown_table(["Definition stage", "Prompt or definition file", "Configuration and source locator"], concept_table)
runtime_sources = []
for filename, locator in [
    ("run_generation_claim_semantic_dedup.py", "make_exact_units; build_jobs"),
    ("run_generation_claim_candidate_selection.py", "build_jobs"),
    ("run_generation_claim_support_assessment.py", "build_jobs; execute_job"),
    ("run_generation_claim_unsupported_diagnosis.py", "build_jobs"),
]:
    source_path = ROOT / "BACE/script/evaluation" / filename
    relative = str(source_path.relative_to(ROOT))
    tracked(source_path)
    if relative[5:] in freeze["files"]:
        assert INPUTS[relative] == freeze["files"][relative[5:]], relative
    runtime_sources.append({"path": relative, "sha256": INPUTS[relative], "locator": locator, "report_use": "5.2-5.4 and Appendix C: capacity guards and deterministic empty-candidate result"})
dump("concept_provenance.json", {"status": "SOURCE_REPORTED_SPECIFICATION_VERIFIED", "access_date": "2026-11-02", "run": "main_v1", "interpretation": "Prompt/config definitions, not independent output-validity measurements", "stages": concept_records, "runtime_sources": runtime_sources})
tracked(OUT / "upstream_README.md")
dump("upstream_source.json", {"status": "SOURCE_REPORTED", "access_date": "2026-11-02", "repository": "forsterkerstin/corporate-sustainability-tracker", "commit": "3d8ccb1d0f0e6f212924b372f2da8510ee457d3b", "source_url": "https://raw.githubusercontent.com/forsterkerstin/corporate-sustainability-tracker/3d8ccb1d0f0e6f212924b372f2da8510ee457d3b/README.md", "local_file": "upstream_README.md", "sha256": digest(OUT / "upstream_README.md"), "locator": "Workflow overview; Download the dataset", "support": "Upstream extraction, processed metric CSV layout and unit harmonization", "limit": "Does not verify byte-level equivalence of every local input to the remote dataset release"})
complete = [record for record in metrics if all(record[key] == "True" for key in ["bace_complete", "ragchecker_complete", "ragas_complete"])]
assert len(metrics) == 1800 and len({record['generation_case_id'] for record in metrics}) == 1800
assert {record["generation_case_id"] for record in complete} == set(execution["completed_case_ids"])
assert len(complete) == 1798 and len(claims) == 94955
calculations = load_module("bace_report_metrics", ROOT / "BACE/script/evaluation/metrics.py")
adapter = load_module("bace_report_adapter", ROOT / "BACE/script/evaluation/external_evaluation.py")
claim_labels = Counter()
for record in metrics:
    base = ROOT / "BACE/results/main_v1/cases" / record["generation_case_id"]
    adapted = adapter.adapt_case(read_jsonl(base / "inputs/generation_cases.jsonl")[0], read_jsonl(base / "generation/generated_disclosures.jsonl")[0])
    recalculated = {}
    if record["bace_complete"] == "True":
        recalculated.update(calculations.bace_metrics(read_jsonl(base / "bace/dedup/ec_claims.jsonl"), read_jsonl(base / "bace/dedup/dc_claims.jsonl"), read_jsonl(base / "bace/support/dc_support_sets.jsonl"), read_jsonl(base / "bace/diagnosis/dc_unsupported_diagnoses.jsonl"), read_jsonl(base / "bace/candidates/dc_candidate_ecs.jsonl")))
    for framework in ["ragchecker", "ragas"]:
        recalculated.update(calculations.external_metrics(read_jsonl(base / f"evaluation/{framework}/results.jsonl")[-1], framework, adapted))
    for field, actual in recalculated.items():
        if actual is None:
            assert not record[field]
        elif not math.isclose(float(record[field]), actual, abs_tol=1e-12, rel_tol=1e-12):
            raise ValueError(f"Raw/snapshot disagreement: {record['generation_case_id']} {field}")
print("All saved case metrics and comparator input mappings match", flush=True)

methods = []
for name, prefix, numerator_keys, denominator_key, score_key in [
    ("BACE", "bace", ["bace_supported_direct", "bace_supported_inferred"], "bace_dc_count", "bace_support_rate_all_dc"),
    ("RAGChecker", "ragchecker", ["ragchecker_supported"], "ragchecker_claim_count", "ragchecker_faithfulness"),
    ("RAGAS", "ragas", ["ragas_supported"], "ragas_claim_count", "ragas_faithfulness"),
]:
    result = interval(complete, lambda record: float(record[score_key]))
    result.update(method=name, numerator=sum(sum(int(float(record[key])) for key in numerator_keys) for record in complete), denominator=sum(int(float(record[denominator_key])) for record in complete), median_claims=float(np.median([float(record[denominator_key]) for record in complete])))
    result["pooled"] = result["numerator"] / result["denominator"]
    methods.append(result)
    TOKENS[prefix + "_macro"] = percentage(result["mean"])
    TOKENS[prefix + "_pooled"] = percentage(result["pooled"])
    TOKENS[prefix + "_ci"] = f"{100 * result['low']:.1f}-{100 * result['high']:.1f}%"

differences = []
for framework in ["ragchecker", "ragas"]:
    result = interval(complete, lambda record: float(record["bace_support_rate_all_dc"]) - float(record[f"{framework}_faithfulness"]))
    result["comparison"] = "BACE minus " + framework
    differences.append(result)
TOKENS["method_table"] = markdown_table(["Evaluator", "Disclosures", "Macro rate, % (95% CI)", "Supported / native claims", "Claim-pooled rate", "Median claims"], [[record["method"], record["disclosures"], estimate_text(record), f"{record['numerator']:,} / {record['denominator']:,}", percentage(record["pooled"]), f"{record['median_claims']:.0f}"] for record in methods])
TOKENS["difference_table"] = markdown_table(["Paired comparison", "Mean difference, percentage points", "95% company-cluster interval"], [[record["comparison"], f"{100 * record['mean']:.1f}", f"{100 * record['low']:.1f} to {100 * record['high']:.1f}"] for record in differences])

task_order = ["E1-1", "E1-3", "E1-4", "E1-6", "S1-1", "S1-4", "S1-5", "S1-14", "G1-1", "G1-2", "G1-3", "G1-4"]
tasks = []
for task in task_order:
    records = [record for record in complete if record["task"] == task]
    result = interval(records, lambda record: float(record["bace_support_rate_all_dc"]))
    result.update(task=task, title=records[0]["task_title"])
    tasks.append(result)
lowest_task = min(tasks, key=lambda record: record["mean"])
highest_task = max(tasks, key=lambda record: record["mean"])
TOKENS["lowest_task_rate"] = percentage(lowest_task["mean"])
TOKENS["highest_task_rate"] = percentage(highest_task["mean"])
assert lowest_task["task"] == "S1-5" and highest_task["task"] == "G1-1"
TOKENS["task_results_table"] = markdown_table(["Task", "Disclosures", "BACE macro support, % (95% CI)"], [[record["task"], record["disclosures"], estimate_text(record)] for record in tasks])

label_names = {"factual_boundary_distortion": "Factual boundary distortion", "evidence_conflation": "Evidence conflation", "non_disclosure_statement": "Non-disclosure statement", "inferential_inflation": "Inferential inflation", "unsupported_novelty": "Unsupported novelty", "contradiction": "Contradiction"}
label_counts = Counter(record["label"] for record in claims)
unsupported = sum(label_counts[label] for label in label_names)
diagnoses = [{"label": label, "name": name, "count": label_counts[label], "denominator_unsupported": unsupported, "share": label_counts[label] / unsupported} for label, name in label_names.items()]
for label in ["direct", "inferred"]:
    assert label_counts[label] == sum(int(float(record[f"bace_supported_{label}"])) for record in complete)
assert unsupported == sum(int(float(record["bace_unsupported"])) for record in complete)
TOKENS["diagnosis_table"] = markdown_table(["Automated diagnosis", "DCs", "Share of unsupported DCs"], [[record["name"], f"{record['count']:,}", percentage(record["share"])] for record in diagnoses])
TOKENS["direct_count"] = f"{label_counts['direct']:,}"
TOKENS["inferred_count"] = f"{label_counts['inferred']:,}"
TOKENS["unsupported_count"] = f"{unsupported:,}"
TOKENS["direct_share"] = percentage(label_counts["direct"] / len(claims))
TOKENS["inferred_share"] = percentage(label_counts["inferred"] / len(claims))
TOKENS["unsupported_share"] = percentage(unsupported / len(claims))
TOKENS["boundary_conflation_count"] = f"{label_counts['factual_boundary_distortion'] + label_counts['evidence_conflation']:,}"
TOKENS["boundary_conflation_share"] = percentage((label_counts["factual_boundary_distortion"] + label_counts["evidence_conflation"]) / unsupported)

secondary = {}
for field in ["bace_eccr", "bace_inference_rate", "bace_support_rate_excluding_non_disclosure_sensitivity"]:
    valid = [record for record in complete if record[field]]
    secondary[field] = interval(valid, lambda record: float(record[field]))
uplift = [float(record["bace_support_rate_excluding_non_disclosure_sensitivity"]) - float(record["bace_support_rate_all_dc"]) for record in complete]
secondary["sensitivity_uplift"] = {"median_pp": float(100 * np.median(uplift)), "maximum_pp": float(100 * max(uplift))}
for field, key in [("bace_eccr", "eccr_macro"), ("bace_inference_rate", "inference_macro"), ("bace_support_rate_excluding_non_disclosure_sensitivity", "sensitivity_macro")]:
    TOKENS[key] = percentage(secondary[field]["mean"])
TOKENS["uplift_median"] = f"{secondary['sensitivity_uplift']['median_pp']:.1f}"
TOKENS["uplift_maximum"] = f"{secondary['sensitivity_uplift']['maximum_pp']:.1f}"

corpus_counts = Counter()
for record in canonical:
    corpus_counts[record["type"]] += int(record["cards"])
assert sum(corpus_counts.values()) == vector_manifest["card_count"]
assert quality["excluded_count"] == 44
assert pdf_build["counts"]["narrative"] - quality["retained_counts"]["narrative"] == 30
assert pdf_build["counts"]["table_row"] - quality["retained_counts"]["pdf_table_row"] == 14
TOKENS["corpus_table"] = markdown_table(["Retained canonical evidence type", "Distinct cards", "Preparation"], [[kind, f"{corpus_counts[kind]:,}", method] for kind, method in [("CSV metric", "Deterministic rendering of valid, nonempty extracted rows"), ("PDF narrative", "PyMuPDF narrative extraction and chunking"), ("PDF table row", "pdfplumber table detection and row serialization")]] + [["Total", f"{sum(corpus_counts.values()):,}", "All indexed using the same embedding identity"]])
TOKENS["sector_table"] = markdown_table(["SICS sector", "Eligible companies", "Selected companies"], [[sector, sample["eligible_counts"][sector], sample["quotas"][sector]] for sector in sorted(sample["quotas"])])
selected = sorted([record for record in selection if record["selected"] == "True"], key=lambda record: (record["primary_sics_sector"], record["company_name"]))
TOKENS["company_table"] = markdown_table(["Company", "Country in register", "SICS sector"], [[record["company_name"], record["country"], record["primary_sics_sector"]] for record in selected])
visible_per_case = Counter(record["generation_case_id"] for record in visible)
TOKENS["visible_count"] = f"{len(visible):,}"
TOKENS["visible_mean"] = f"{len(visible) / len(metrics):.2f}"
TOKENS["visible_range"] = f"{min(visible_per_case.values())}-{max(visible_per_case.values())}"

stage_counts = [{"stage": key, "completed": sum(record[key] == "True" for record in metrics), "planned": len(metrics)} for key in metrics[0] if key.startswith("stage_")]
TOKENS["completion_table"] = markdown_table(["Stage", "Completed / planned"], [[record["stage"].replace("stage_", "").capitalize(), f"{record['completed']:,} / {record['planned']:,}"] for record in stage_counts])
TOKENS["length_range"] = f"{min(int(record['word_count']) for record in metrics)}-{max(int(record['word_count']) for record in metrics)}"

write_csv("method_results.csv", methods)
write_csv("paired_differences.csv", differences)
write_csv("task_results.csv", tasks)
write_csv("diagnoses.csv", diagnoses)
write_csv("selected_companies.csv", selected)
write_csv("stage_completeness.csv", stage_counts)
ledger = {"status": "COMPUTED_VERIFIED", "cohort": "Common complete BACE/RAGChecker/RAGAS disclosures from main_v1 only", "planned_disclosures": len(metrics), "analysed_disclosures": len(complete), "company_clusters": 30, "methods": methods, "paired_differences": differences, "tasks": tasks, "diagnoses": diagnoses, "claim_counts": dict(label_counts), "secondary_metrics": secondary, "canonical_card_counts": dict(corpus_counts), "pdf_sources": pdf_build["report_count"], "quality_excluded_cards": quality["excluded_count"], "visible_occurrences": len(visible), "visible_cards_min": min(visible_per_case.values()), "visible_cards_max": max(visible_per_case.values()), "stage_counts": stage_counts, "bootstrap": {"unit": "Company; retain all observed disclosures within each sampled cluster", "draws": DRAWS, "seed": SEED, "generator": "numpy.random.default_rng", "interval": "Uncorrected 2.5th/97.5th percentiles", "null_handling": "Exclude missing method scores before the explicitly matched comparison; never impute zero", "interpretation": "Descriptive company-cluster resampling uncertainty, not model-run or source-error uncertainty"}, "tokens": TOKENS}
dump("numeric_ledger.json", ledger)
template = tracked(OUT / "REPORT.template.md").read_text()
for key, value in TOKENS.items():
    template = template.replace("{{" + key + "}}", value)
if "{{" in template:
    raise ValueError("Unresolved report token")
(OUT / "REPORT.md").write_text(template)
dump("provenance.json", {"access_date": "2026-11-02", "run": "main_v1", "recorded_run_freeze_sha256": run_manifest["freeze_sha256"], "generation_input_sha256": run_manifest["generation_input_sha256"], "current_saved_execution_timestamp_utc": execution["updated_at_utc"], "source_index": {"path": str((SNAPSHOT / "sources.json").relative_to(ROOT)), "sha256": digest(SNAPSHOT / "sources.json"), "verified_files": len(source_index)}, "verification": ["Every saved consumed-source hash matched", "Every snapshot CSV hash matched", "All 1,800 native comparator mappings and scores rechecked against saved results", "All 1,798 BACE metrics recalculated from raw deduplicated claims, candidates, support sets and diagnoses", "Operational prompt and response-schema references match declared configuration hashes"], "audit_limits": ["No model/API evaluation was rerun", "No experiment environment, prompt, artifact or input dataset was modified", "Hash and schema verification do not verify semantic judgments or original-source truth", "No independent extraction or candidate-recall study was completed", "Original source PDFs and remote model routing were not comprehensively re-audited in this report"], "inputs": INPUTS, "script": "prepare_report.py", "script_sha256": digest(__file__), "command": "python -B paper/reports/main_experiment_2026-11-02/prepare_report.py", "python": sys.version, "numpy": np.__version__, "outputs": {path.name: digest(path) for path in OUT.glob("*.csv")}, "definition_record": {"path": "concept_provenance.json", "sha256": digest(OUT / "concept_provenance.json")}})
print(json.dumps({"methods": methods, "secondary": secondary, "labels": dict(label_counts)}, indent=2), flush=True)
