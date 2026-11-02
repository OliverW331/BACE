import hashlib
import json
from pathlib import Path


def main():
    output_directory = Path(__file__).resolve().parent
    project_root = output_directory.parents[2]
    source_paths = [
        "paper/literature/SOURCE_INDEX.md",
        "docs/generation_evaluation.md",
        "BACE/config/evaluation/prompts/generation_claim_support_prompt_v1.txt",
        "BACE/config/evaluation/prompts/generation_claim_unsupported_diagnosis_prompt_v1.txt",
        "BACE/script/evaluation/run_generation_claim_unsupported_diagnosis.py",
        "BACE/script/evaluation/metrics.py",
        "paper/analysis/storyline_gap_check_2026-10-29/NOTE.md",
    ]
    for source_name in ["susgen2025", "chatreport2023", "esgbench2026"]:
        for filename in ["original.pdf", "fulltext.txt"]:
            source_paths.append(f"paper/literature/sources/{source_name}/{filename}")
    for filename in [
        "REPORT.md", "diagnoses.csv", "results.json", "reanalyse_main.py",
        "integrity.json", "provenance.json",
    ]:
        source_paths.append(f"paper/analysis/main_results_reaudit_2026-10-29/{filename}")
    records = []
    for relative_path in source_paths:
        source_file = project_root / relative_path
        contents = source_file.read_bytes()
        records.append({
            "path": relative_path,
            "bytes": len(contents),
            "sha256": hashlib.sha256(contents).hexdigest(),
        })
    artifact_records = []
    for artifact_file in sorted(output_directory.rglob("*")):
        if not artifact_file.is_file() or artifact_file.name == "manifest.json":
            continue
        contents = artifact_file.read_bytes()
        artifact_records.append({
            "path": str(artifact_file.relative_to(project_root)),
            "bytes": len(contents),
            "sha256": hashlib.sha256(contents).hexdigest(),
        })
    manifest = {
        "inspection_date": "2026-10-29",
        "scope": "Original-source comparison; no new experiment or statistical calculation",
        "inputs": records,
        "artifacts": artifact_records,
    }
    destination = output_directory / "manifest.json"
    destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {len(records)} inputs and {len(artifact_records)} artifacts")


if __name__ == "__main__":
    main()
