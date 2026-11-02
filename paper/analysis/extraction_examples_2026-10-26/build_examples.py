from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
CASE_ID = (
    "w2__text_embedding_3_large__stratified_by_evidence_type_n10__"
    "air_france_klm__2023__e1_4_targets"
)
CASE_DIRECTORY = ROOT / "BACE/results/main_v1/cases" / CASE_ID
STAGES = ("direct", "integrated", "atomic")
ACCESS_DATE = "2026-10-26"
EC_LABEL = "Evidence 6"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_success(path: Path) -> tuple[dict, int]:
    candidates = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if line.strip():
            record = json.loads(line)
            if record.get("call_status") == "success":
                candidates.append((record, line_number))
    if not candidates:
        raise ValueError(f"No successful call in {path}")
    record, line_number = candidates[-1]
    if record["api_response"]["status"] != "completed":
        raise ValueError(f"Incomplete provider response in {path}")
    return record, line_number


def payload(record: dict) -> dict:
    return record.get("canonical_output") or record["parsed_output"]


def source_unit(task: str, record: dict) -> dict:
    output = payload(record)
    if task == "dc":
        return output
    return next(
        unit for unit in output["evidence_results"]
        if unit["prompt_label"] == EC_LABEL
    )


def patch_unit(task: str, record: dict) -> dict:
    patch = record["parsed_output"]
    if task == "dc":
        return patch
    return next(
        unit for unit in patch["evidence_results"]
        if unit["prompt_label"] == EC_LABEL
    )


def append_inventory(lines: list[str], unit: dict) -> None:
    for position, claim in enumerate(unit["claims"], 1):
        lines.append(f"{position}. {claim['claim_text']}")
        if claim.get("unresolved_context"):
            for uncertainty in claim["unresolved_context"]:
                lines.append(f"   - Unresolved context: {uncertainty}")
    lines.extend(["", "Exclusions:", ""])
    exclusions = unit.get("unextracted_spans", [])
    if not exclusions:
        lines.append("- None.")
    for exclusion in exclusions:
        lines.append(
            f"- `{exclusion['reason']}`: "
            f"{exclusion.get('explanation', '')}"
        )
        for quote in exclusion["source_quotes"]:
            lines.append(f"  - Source span: {quote}")
    lines.append("")


def append_patch(lines: list[str], patch: dict) -> None:
    lines.extend(["Applied patch (verbatim parsed JSON):", "", "```json"])
    lines.append(json.dumps(patch, ensure_ascii=False, indent=2))
    lines.extend(["```", ""])


def main() -> None:
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "BACE/script/evaluation"))
    from identified_claim_patches import canonicalize, make_claim_index

    provenance = {}
    records = {}
    for task in ("ec", "dc"):
        records[task] = {}
        for stage in STAGES:
            path = CASE_DIRECTORY / "extraction" / stage / f"{task}_extraction_calls.jsonl"
            record, line_number = load_success(path)
            records[task][stage] = record
            provenance[str(path.relative_to(ROOT))] = {
                "sha256": digest(path),
                "line": line_number,
                "call_id": record["call_id"],
                "call_status": record["call_status"],
            }

    for stage in STAGES:
        path = CASE_DIRECTORY / "extraction" / stage / "claim_extraction_run_manifest.json"
        manifest = json.loads(path.read_text())
        assert manifest["run_status"] == "complete"
        provenance[str(path.relative_to(ROOT))] = {"sha256": digest(path)}
        for task in ("ec", "dc"):
            prompt = manifest["prompts"][task]
            prompt_path = Path(prompt["path"])
            assert digest(prompt_path) == prompt["sha256"]
            records[task][stage]["example_prompt_provenance"] = prompt
            provenance[str(prompt_path.relative_to(ROOT))] = {
                "sha256": digest(prompt_path),
                "prompt_version": prompt["version"],
            }

    checks = []
    for task in ("ec", "dc"):
        for previous, stage in zip(STAGES, STAGES[1:]):
            record = records[task][stage]
            prior_payload = payload(records[task][previous])
            assert record["dynamic_input"]["draft_extraction"] == prior_payload
            assert record["dynamic_input"]["draft_claim_index"] == make_claim_index(task, prior_payload)
            assert canonicalize(task, record["parsed_output"], prior_payload) == payload(record)
            assert record["draft_call_id"] == records[task][previous]["call_id"]
            checks.append(f"{task}: {previous} -> {stage}: draft, IDs, call lineage and patch replay match")

    evidence_section = records["ec"]["direct"]["dynamic_input"]["evidence_section"]
    match = re.search(
        rf"^{re.escape(EC_LABEL)}\n\nSource:\n(?P<label>.*?)\n\nText:\n"
        r"(?P<text>.*?)(?=\n\nEvidence \d+\n|\Z)",
        evidence_section,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise ValueError("Selected EC source record not found")
    ec_text = match["text"]
    dc_text = records["dc"]["direct"]["dynamic_input"]["disclosure_text"]
    for stage in STAGES:
        assert records["ec"][stage]["dynamic_input"]["evidence_section"] == evidence_section
        assert records["dc"][stage]["dynamic_input"]["disclosure_text"] == dc_text
        for task, source in (("ec", ec_text), ("dc", dc_text)):
            unit = source_unit(task, records[task][stage])
            entries = unit["claims"] + unit.get("unextracted_spans", [])
            for entry in entries:
                for quote in entry["source_quotes"]:
                    assert quote in source, (task, stage, quote)
    checks.append("All selected-stage claim and exclusion quotations occur literally in their supplied source")

    occurrence_path = CASE_DIRECTORY / "extraction/atomic/ec_claim_occurrences.jsonl"
    occurrences = []
    for line_number, line in enumerate(occurrence_path.read_text().splitlines(), 1):
        if line.strip():
            occurrence = json.loads(line)
            if occurrence["prompt_label"] == EC_LABEL:
                occurrences.append({"line": line_number, "record": occurrence})
    assert [entry["record"]["claim_text"] for entry in occurrences] == [
        claim["claim_text"] for claim in source_unit("ec", records["ec"]["atomic"])["claims"]
    ]
    provenance[str(occurrence_path.relative_to(ROOT))] = {"sha256": digest(occurrence_path)}
    checks.append("Selected final EC inventory matches saved occurrence rows in order")

    examples = {
        "schema_version": "bace_saved_extraction_examples_v1",
        "access_date": ACCESS_DATE,
        "run": "main_v1",
        "generation_case_id": CASE_ID,
        "scope": "One complete EC source record and the complete DC disclosure, before semantic deduplication",
        "boundary": "Saved model outputs, not a new extraction, external truth verification or adjudicated gold labels",
        "checks": checks,
        "provenance": provenance,
        "examples": {},
    }
    for task, source in (("ec", ec_text), ("dc", dc_text)):
        example = {
            "source_text": source,
            "context_metadata": records[task]["direct"]["dynamic_input"]["context_metadata"],
            "stages": {},
        }
        if task == "ec":
            example["prompt_label"] = EC_LABEL
            example["source_label"] = match["label"]
            example["evidence_provenance"] = occurrences[0]["record"]["evidence_provenance"]
            example["final_occurrences"] = occurrences
        for stage in STAGES:
            record = records[task][stage]
            example["stages"][stage] = {
                "call_id": record["call_id"],
                "draft_call_id": record.get("draft_call_id"),
                "prompt": record["example_prompt_provenance"],
                "inventory": source_unit(task, record),
                "patch": None if stage == "direct" else patch_unit(task, record),
            }
        examples["examples"][task] = example

    lines = [
        "# Complete saved EC and DC extraction examples",
        "",
        f"Access date: {ACCESS_DATE}. Run: `main_v1`.",
        "",
        f"Generation case: `{CASE_ID}`.",
        "",
        "These are literal saved model outputs from the active direct-v8, integrated-v4 and atomicity-v2 pipeline. No model call or experiment was run. EC covers one complete supplied evidence record; DC covers the complete generated disclosure. All stages are before semantic deduplication. Stage-local list numbers are display positions, not immutable claim IDs.",
        "",
        "The generated disclosure and extracted claims can be unsupported or mistaken. Values inside them are reproduced source assertions, not independently verified company measurements. Successful schema validation and patch replay do not establish semantic correctness. The supplied EC excerpt was checked locally; the original publisher PDF was not independently audited for this example.",
        "",
        "## Stage counts",
        "",
        "| Unit | Direct claims | Integrated claims | Atomic claims | Final exclusions |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for task in ("ec", "dc"):
        counts = [len(source_unit(task, records[task][stage])["claims"]) for stage in STAGES]
        exclusions = len(source_unit(task, records[task]["atomic"]).get("unextracted_spans", []))
        lines.append(f"| {task.upper()} | {counts[0]} | {counts[1]} | {counts[2]} | {exclusions} |")
    lines.extend([
        "",
        "Counts are computed from the exact inventories in `examples.json`; no deduplication is applied. DC may retain repeated underlying assertions produced by relationship-preserving splits.",
        "",
        "## Reading guide",
        "",
        "- EC: Integrated review changes an inferred possession-of-target claim into a source-faithful prospective outcome and records unresolved governing language. Atomicity review then separates approval from confirmation of temperature-pathway alignment.",
        "- DC: Integrated review expands the identity of the principal target in dependent claims. Atomicity review separates an absolute reduction assertion, the classification of an intensity target, and the explicit distinction between those metrics, preserving the relationship rather than replacing it with only two facts.",
        "- This is a 2023 task with a selected EC record attributed to a 2022 annual report. The extraction retains the 2022 report attribution; the task year does not create a 2023 measurement or action date.",
        "- The final EC wording is retained exactly, including generic references to submitted targets and the absence of an explicit November 2022 date in the confirmation child. This reproduction is not a certification that every output satisfies every prompt rule.",
        "",
    ])

    for task in ("ec", "dc"):
        example = examples["examples"][task]
        lines.extend([f"## {task.upper()} example", "", "### Supplied source", ""])
        if task == "ec":
            lines.extend([
                f"Record: `{EC_LABEL}`. Source: `{example['source_label']}`.",
                "",
                "The source display below removes the PDF bullet control character U+0007 only. The raw input is preserved unchanged in `examples.json`.",
                "",
            ])
        lines.extend([example["source_text"].replace("\u0007", ""), ""])
        for stage in STAGES:
            stage_example = example["stages"][stage]
            lines.extend([
                f"### {stage.capitalize()} extraction result",
                "",
                f"Prompt: `{stage_example['prompt']['version']}`.",
                "",
            ])
            if stage != "direct":
                append_patch(lines, stage_example["patch"])
            lines.extend(["Complete resulting inventory (claim text unchanged):", ""])
            append_inventory(lines, stage_example["inventory"])

    lines.extend(["## Reproduction checks", ""])
    lines.extend(f"- {check}." for check in checks)
    lines.extend(["", "## Provenance", ""])
    for path, details in provenance.items():
        locator = f":{details['line']}" if "line" in details else ""
        lines.append(f"- `{ROOT / path}{locator}`; SHA-256: `{details['sha256']}`.")
    lines.extend([
        "",
        "`examples.json` preserves all selected inventory fields, source quotations, uncertainties, exclusions, immutable patch references and source hashes. This report does not include or infer support-assessment verdicts. Rebuild with the independent system Python: `python paper/analysis/extraction_examples_2026-10-26/build_examples.py` from the repository root.",
        "",
    ])
    for path, details in provenance.items():
        assert digest(ROOT / path) == details["sha256"]
    OUTPUT.joinpath("examples.json").write_text(
        json.dumps(examples, ensure_ascii=False, indent=2) + "\n"
    )
    OUTPUT.joinpath("examples.md").write_text("\n".join(lines))
    print(json.dumps({
        "report": str(OUTPUT / "examples.md"),
        "structured_examples": str(OUTPUT / "examples.json"),
        "checks_passed": len(checks),
        "original_artifacts_unchanged": True,
    }, indent=2))


if __name__ == "__main__":
    main()
