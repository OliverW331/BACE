"""Audit Methods sources and Results correspondence without model calls.

Reuses the Results arithmetic/workbook check, verifies recorded configuration
and sampling facts, and writes only to paper/. Citation fragment checks confirm
source identity and occurrence placement; they do not automate semantic review.
"""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
INPUTS = {}
CROSSWALK = {
    "R01": [f"M{i:02}" for i in range(1, 10)],
    "R02": ["M07", "M10", "M11", "M12", "M13"],
    "R03": ["M09", "M14", "M18", "M19"],
    "R04": ["M03", "M09", "M18", "M19"],
    "R05": ["M14", "M15", "M18"],
    "R06": ["M13", "M14"],
    "R07": ["M04", "M13", "M20"],
    "R08": ["M05", "M10", "M13", "M20"],
    "R09": ["M09", "M14", "M16", "M17", "M18", "M19"],
    "R10": ["M16", "M17", "M18", "M21", "M22"],
    "R11": ["M11", "M13", "M16", "M17", "M21", "M22"],
    "R12": ["M11", "M13", "M16", "M17", "M21", "M22"],
    "R13": ["M05", "M11", "M13", "M16", "M17", "M21", "M22"],
    "R14": ["M20", "M21", "M22", "M23", "M24", "M25"],
}


def register(relative):
    path = ROOT / relative
    key = str(path.relative_to(ROOT))
    if key not in INPUTS:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while block := stream.read(2**20):
                digest.update(block)
        INPUTS[key] = {"sha256": digest.hexdigest(), "bytes": path.stat().st_size}
    return path


def read_json(relative):
    return json.loads(register(relative).read_text())


def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def manuscript(relative, prefix):
    text = register(relative).read_text()
    body = text.split("<!-- MANUSCRIPT_START -->")[1].split("<!-- MANUSCRIPT_END -->")[0]
    pairs = re.findall(rf"<!-- ({prefix}\d+) -->\s*(.*?)(?=<!-- {prefix}\d+ -->|\Z)", body, re.S)
    assert len(pairs) == len(dict(pairs)), "Duplicate paragraph IDs"
    return text, body, dict(pairs)


def main():
    # This checks saved point estimates, input hashes, paired cohorts and both
    # workbooks again after the manuscript revisions. It does not rerun inference.
    results_script = register("paper/analysis/results_draft/verify_draft.py")
    run = subprocess.run([sys.executable, str(results_script)], cwd=ROOT,
                         capture_output=True, text=True, check=True)
    print(run.stdout.strip())
    results = read_json("paper/analysis/results_draft/verified_numbers.json")
    results_prov = read_json("paper/analysis/results_draft/provenance.json")
    assert results_prov["status"] == "PASS"
    for relative, saved in results_prov["input_files"].items():
        register(relative)
        assert INPUTS[relative]["sha256"] == saved["sha256"], relative

    method_path = "paper/10_methods_draft.md"
    full, body, paragraphs = manuscript(method_path, "M")
    _, _, result_paragraphs = manuscript("paper/08_results_draft.md", "R")
    assert list(paragraphs) == [f"M{i:02}" for i in range(1, 26)]
    assert set(CROSSWALK) == set(result_paragraphs)
    assert all(set(ids) <= set(paragraphs) and ids for ids in CROSSWALK.values())
    assert set().union(*map(set, CROSSWALK.values())) == set(paragraphs)

    experiment = read_json("BACE/config/experiment.json")
    sample = read_json("BACE/evidence/sample/sample.json")
    tasks = read_json("BACE/config/tasks.json")["tasks"]
    retrieval = read_json("BACE/config/retrieval/retrieval_algorithm_config_text_embedding_3_large_top200_v1.json")
    embeddings = read_json("BACE/evidence/embeddings/manifest.json")
    corrections = read_json("BACE/evidence/mapping_corrections.json")
    external = read_json("BACE/config/evaluation/configs/external_evaluation_config.json")
    assert sample["population_count"] == 600 and sample["eligible_count"] == 250
    assert len(sample["selected"]) == sum(sample["quotas"].values()) == 30
    assert len(sample["quotas"]) == 11 and sample["seed"] == 20260916
    assert sample["selection_uses_experiment_scores"] is False
    assert len(tasks) == 12 and experiment["target_years"] == list(range(2019, 2024))
    assert len(tasks) * len(experiment["target_years"]) * len(sample["selected"]) == 1800

    # Parameter facts directly represented in the Methods prose.
    checks = {}
    def check(name, actual, expected):
        assert actual == expected, (name, actual, expected)
        checks[name] = actual

    check("windows", experiment["windows"], {"csv_window_years": 5, "csv_lag_years": 0, "pdf_window_years": 4, "pdf_lag_years": 1})
    for key, expected in {"model": "gpt-5.6-sol", "model_version": "2026-07-09", "reasoning_effort": "medium", "min_words": 300, "max_words": 500, "max_output_tokens": 8192, "retry_attempts": 2}.items():
        check("generation." + key, experiment["generation"][key], expected)
    check("runtime.max_stage_attempts", experiment["runtime"]["max_stage_attempts"], 3)
    for key, expected in {"unmapped_glyph_minimum_count": 10, "unmapped_glyph_fraction_threshold": 0.05, "maximum_card_tokens": 8191, "tokenizer": "cl100k_base"}.items():
        check("source_quality." + key, experiment["source_quality"][key], expected)
    check("quarantined_metric_mappings", len(corrections["exclusions"]), 4)
    for channel in ["bm25", "dense"]:
        check(channel + ".top_n_per_subquery", retrieval[channel]["top_n_per_subquery"], 200)
    check("rrf_k", retrieval["fusion"]["rrf_k"], 60)
    check("embedding_dimensions", embeddings["dimensions"], 3072)
    check("stored_embeddings_normalized", embeddings["normalized"], True)
    check("additional_corpus_normalization", retrieval["dense"]["normalize_corpus_embeddings"], False)
    check("reranker_enabled", retrieval["reranker"]["enabled"], False)
    selection = retrieval["final_selection"]["stratified_by_evidence_type"]
    check("per_type_limit", selection["main_generation_per_evidence_type_top_n"], 10)
    check("maximum_cards", selection["max_main_generation_cards"], 30)
    check("deficit_redistribution", selection["deficit_redistribution"], False)
    check("evidence_order", selection["evidence_block_order"], ["narrative", "pdf_table_row", "csv_metric"])
    for name, version in {"ragchecker": "0.1.9", "refchecker": "0.2.13", "ragas": "0.4.3"}.items():
        check(name + ".version", external["package_versions"][name], version)
    check("ragchecker.joint_check_num", external["frameworks"]["ragchecker"]["joint_check_num"], 5)

    stage_names = ["extraction_config_v8", "patch_review_config_v4", "atomicity_review_config_v2", "semantic_dedup_config", "candidate_selection_config", "support_config", "unsupported_diagnosis_config"]
    for name in stage_names:
        path = register("BACE/config/evaluation/configs/generation_claim_" + name + ".json")
        config = json.loads(path.read_text())
        model = config["models"][config["current_primary_model"]]
        check(name + ".model", model["model_id"], "gpt-5.6-sol")
        check(name + ".version", model["model_version"], "2026-07-09")
        check(name + ".reasoning", model["request_parameters"]["reasoning"]["effort"], "medium")
        # Verify the prompt/schema identities recorded by each stage config.
        def visit(value):
            if isinstance(value, dict):
                if "file" in value and "sha256" in value:
                    target = (path.parent / value["file"]).resolve()
                    register(target.relative_to(ROOT))
                    assert INPUTS[str(target.relative_to(ROOT))]["sha256"] == value["sha256"], str(target)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(config)

    bootstrap_path = register("BACE/analysis/analysis_data.py")
    tree = ast.parse(bootstrap_path.read_text())
    seed = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SEED" for t in node.targets))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "company_bootstrap")
    check("bootstrap.seed", seed, 20260921)
    check("bootstrap.draws", ast.literal_eval(function.args.defaults[0]), 2000)
    examples = read_json("paper/analysis/storyline/example_candidates.json")
    example_seeds = {r["label"]: r["selection"]["seed"] for r in examples}
    check("wartsila.selection_seed", example_seeds["factual_boundary_distortion"], 20260924)
    check("asml.selection_seed", example_seeds["contradiction"], 20260922)

    human = read_json("BACE/analysis/validation/_private/sample_manifest.json")
    design, records = human["study_design"], human["records"]
    assert len(records) == len({r["sample_id"] for r in records}) == 600
    groups = Counter(r["group"] for r in records)
    assert groups == {"primary": 400, "diagnosis_supplement": 200}
    primary_counts = Counter(r["automated_support_label"] for r in records if r["group"] == "primary")
    assert primary_counts == design["primary_support_quotas"] == {"Supported": 145, "Supported by inference": 75, "Unsupported": 180}
    assert sum(design["support_population"].values()) == results["support"]["total_dc"]
    check("human.status", human["status"], "prepared_not_annotated")
    check("human.seed", design["seed"], "bace-human-validation-v1-20260924")
    check("human.contradiction_cap", design["diagnosis_total_caps"]["contradiction"], 40)
    for reviewer in ["A", "B"]:
        assert results["validation"][reviewer] == {"sample_rows": 600, "unique_ids": 600, "support_cells_filled": 0, "diagnosis_cells_filled": 0}

    fragments = {
        "M01": ["600 companies", "250 met", "2015 to 2023", "2015 to 2022"],
        "M02": ["30 companies", "11 eligible sectors", "remaining 19", "20260916"],
        "M03": ["12 tasks", "2019 to 2023", "1,800 cases"],
        "M06": ["ten unmapped", "5%", "8,191", "four quarantined"],
        "M07": ["3,072-dimensional", "200 candidates", "constant of 60", "ten cards", "30 cards"],
        "M08": ["2026-07-09", "8,192", "300–500", "two retries", "three attempts"],
        "M09": ["1,798", "Banco BPM", "Investec", "without zero imputation"],
        "M16": ["0.1.9", "0.2.13", "0.4.3"],
        "M19": ["2,000", "20260921", "2.5th and 97.5th", "95%"],
        "M20": ["20260924", "20260922"], "M21": ["0.65"],
        "M23": ["600 unique", "400 primary", "200 supplementary", "145, 75 and 180", "at 40"],
        "M24": ["same 600", "1 October 2026", "blank support and diagnosis cells"],
    }
    for pid, expected in fragments.items():
        for fragment in expected:
            assert fragment in paragraphs[pid], (pid, fragment)

    occurrences = read_json("paper/analysis/methods_draft/citation_occurrences.json")
    bib = register("paper/references.bib").read_text()
    assert sorted(re.findall(r"\[@([^\]]+)\]", body)) == sorted(r["citation_key"] for r in occurrences)
    for occurrence in occurrences:
        key = occurrence["citation_key"]
        assert occurrence["claim"][:-1] + f" [@{key}]." in paragraphs["M16"]
        assert re.search(r"@\w+\s*\{\s*" + re.escape(key) + r"\s*,", bib)
        original = re.sub(r"\s+", " ", register(occurrence["fulltext_path"]).read_text())
        assert all(fragment in original for fragment in occurrence["verified_excerpt_fragments"])
        register(occurrence["retrieval_record"])

    broken = []
    for link in re.findall(r"\]\(([^)]+)\)", full):
        if "://" in link or link.startswith("#"):
            continue
        target = (ROOT / "paper" / link.split("#")[0]).resolve()
        if target == OUT / "provenance.json":
            continue
        if not target.is_file():
            broken.append(link)
        else:
            register(target.relative_to(ROOT))
    assert not broken, broken
    assert not results_prov["broken_local_links"]
    prose = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    prose = "\n".join(line for line in prose.splitlines() if not line.startswith("#"))
    save("results_methods_crosswalk.json", {
        "review_date": "2026-10-01", "results_to_methods": CROSSWALK,
        "coverage": "All 14 Results paragraphs mapped; all 25 Methods paragraphs represented.",
        "limits": "Authoring crosswalk checked for complete IDs and source links; coverage is not independent semantic validation."
    })
    save("verified_method_facts.json", {"configuration": checks, "sampling": results["sampling"],
         "cohort": results["cohort"], "human_groups": dict(groups), "human_primary_quotas": dict(primary_counts),
         "human_workbook_status": results["validation"], "numeric_text_checks": fragments,
         "bootstrap_status": "SOURCE_REPORTED; implementation parameters checked; inference not rerun."})
    outputs = [OUT / name for name in ["results_methods_crosswalk.json", "verified_method_facts.json", "citation_occurrences.json"]]
    report = {"status": "PASS", "prepared_date": "2026-10-01", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "command": f"{sys.executable} paper/analysis/methods_draft/verify_methods.py",
              "python": sys.version, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "input_files": INPUTS, "results_verification": json.loads(run.stdout),
              "methods_paragraphs": list(paragraphs), "results_paragraphs_mapped": len(CROSSWALK),
              "citation_occurrences": len(occurrences), "broken_local_links": broken,
              "methods_word_count": len(prose.split()),
              "word_count_rule": "Whitespace-delimited manuscript tokens excluding headings and HTML comments; includes equation tokens.",
              "outputs": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs},
              "limits": "Artifact identity, arithmetic, configuration and document checks. No new experiment, bootstrap run, external-truth assessment or independent human validation. Source-passage checks supplement the recorded semantic review; missing author facts remain unresolved."}
    save("provenance.json", report)
    print(json.dumps({"status": "PASS", "methods_words": report["methods_word_count"], "methods_paragraphs": len(paragraphs),
                      "results_paragraphs_mapped": len(CROSSWALK), "citation_occurrences": len(occurrences), "broken_links": len(broken)}))


if __name__ == "__main__":
    main()
