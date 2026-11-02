"""Verify the first Results draft against the saved BACE analysis.

Read-only with respect to experiment artifacts. Recompute point estimates,
reuse saved bootstrap endpoints, and write provenance only under paper/.
"""
import csv
import hashlib
import importlib.util
import json
import math
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
DATA = ROOT / "BACE/analysis/outputs"
INPUTS = {}


def register(path):
    path = Path(path)
    key = str(path.relative_to(ROOT))
    if key not in INPUTS:
        h = hashlib.sha256()
        with path.open("rb") as stream:
            while block := stream.read(2**20):
                h.update(block)
        INPUTS[key] = {"sha256": h.hexdigest(), "bytes": path.stat().st_size}
    return key


def read_json(path):
    register(path)
    return json.loads(path.read_text())


def read_csv(path):
    register(path)
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def close(a, b):
    assert math.isclose(float(a), float(b), rel_tol=0, abs_tol=1e-10), (a, b)


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    prior_manifests = [ROOT / "paper/analysis/storyline/provenance.json",
                      ROOT / "paper/analysis/disagreement_cases/bundle_provenance.json"]
    prior_checks = []
    for path in prior_manifests:
        manifest = read_json(path)
        for relative, old in manifest["input_files"].items():
            register(ROOT / relative)
            assert INPUTS[relative]["sha256"] == old["sha256"], relative
        prior_checks.append({"manifest": str(path.relative_to(ROOT)),
                             "unchanged_input_count": len(manifest["input_files"])})

    metrics = read_csv(DATA / "snapshot/metrics.csv")
    snapshot = read_json(DATA / "snapshot/manifest.json")
    assert INPUTS["BACE/analysis/outputs/snapshot/metrics.csv"]["sha256"] == snapshot["tables"]["metrics"]
    complete = [r for r in metrics if r["bace_complete"].lower() == "true"]
    score_columns = {"BACE": "bace_support_rate_all_dc", "RAGChecker": "ragchecker_faithfulness", "RAGAS": "ragas_faithfulness"}
    common = [r for r in metrics if all(r[c] != "" for c in score_columns.values())]
    ids = {r["generation_case_id"] for r in complete}
    execution = read_json(ROOT / "BACE/results/main_v1/execution_status.json")
    assert ids == {r["generation_case_id"] for r in common} == set(execution["completed_case_ids"])
    assert len(ids) == len(complete) == len(common)
    cohort = dict(planned=len(metrics), completed=len(complete), paired=len(common),
                  companies=len({r["company_id"] for r in complete}),
                  years=sorted({int(r["year"]) for r in complete}), tasks=len({r["task"] for r in complete}),
                  run_status=execution["status"], failures=execution["failures"])
    sample = read_json(ROOT / "BACE/evidence/sample/sample.json")
    sampling = {"register": sample["population_count"], "eligible": sample["eligible_count"],
                "selected": len(sample["selected"]), "sectors": len(sample["quotas"]), "seed": sample["seed"]}
    assert sampling["selected"] == sum(sample["quotas"].values()) == cohort["companies"]

    counts = {label: sum(int(float(r[col])) for r in complete) for label, col in
              {"Direct": "bace_supported_direct", "Inferred": "bace_supported_inferred", "Unsupported": "bace_unsupported"}.items()}
    total_dc = sum(int(float(r["bace_dc_count"])) for r in complete)
    assert sum(counts.values()) == total_dc
    for row in read_csv(DATA / "figures/01/01_support_distribution__claim_counts.csv"):
        assert counts[row["status"]] == int(float(row["count"]))
    summaries = {r["method"]: r for r in read_csv(DATA / "figures/03/03_native_comparison__cohort_summary.csv") if r["cohort"] == "Common"}
    means = {method: statistics.mean(float(r[col]) for r in common) for method, col in score_columns.items()}
    for method, value in means.items():
        close(value, summaries[method]["mean"])
        assert int(summaries[method]["disclosures"]) == len(common)
        assert int(summaries[method]["draws"]) == 2000
    support = dict(macro_pct=100 * means["BACE"], saved_95_interval_pct=[100 * float(summaries["BACE"][k]) for k in ["low", "high"]],
                   total_dc=total_dc, counts=counts, pooled_pct=100 * (counts["Direct"] + counts["Inferred"]) / total_dc,
                   percentages={label: 100 * n / total_dc for label, n in counts.items()})
    tasks = read_csv(DATA / "figures/01/01_task_support__data.csv")
    for row in tasks:
        group = [r for r in complete if r["task"] == row["task"]]
        assert len(group) == int(row["disclosures"])
        close(statistics.mean(float(r[score_columns["BACE"]]) for r in group), row["mean"])
    sensitivity_rows = read_csv(DATA / "figures/01/01_secondary_metrics__data.csv")
    assert {r["generation_case_id"] for r in sensitivity_rows} == ids
    changes = [100 * (float(r["bace_support_rate_excluding_non_disclosure_sensitivity"]) - float(r["bace_support_rate_all_dc"])) for r in sensitivity_rows]
    sensitivity = {"median_change_pp": statistics.median(changes), "max_change_pp": max(changes)}
    labels = read_csv(DATA / "figures/02/02_label_composition__data.csv")
    for row in labels:
        assert int(row["count"]) == sum(int(float(r["bace_" + row["label"]])) for r in complete)
    assert sum(int(row["count"]) for row in labels) == counts["Unsupported"]
    by_label = {r["label"]: int(r["count"]) for r in labels}
    combined = by_label["factual_boundary_distortion"] + by_label["evidence_conflation"]
    diagnoses = dict(counts=by_label, denominator=counts["Unsupported"], combined=combined,
                     combined_pct=100 * combined / counts["Unsupported"])
    paired_rows = read_csv(DATA / "figures/03/03_native_comparison__paired_differences.csv")
    differences = []
    for method, row in zip(["RAGChecker", "RAGAS"], paired_rows):
        assert row["contrast"] == "BACE − " + method
        diff = statistics.mean(float(r[score_columns["BACE"]]) - float(r[score_columns[method]]) for r in common)
        close(diff, row["mean"])
        differences.append(dict(comparator=method, mean_pp=100 * diff,
            saved_95_interval_pp=[100 * float(row[k]) for k in ["low", "high"]]))
    inventories = read_csv(DATA / "figures/03/03_claim_inventories__data.csv")
    assert {r["generation_case_id"] for r in inventories} == ids
    medians = {k: statistics.median(float(r[k]) for r in inventories) for k in ["bace_dc_count", "ragchecker_claim_count", "ragas_claim_count"]}

    # Reuse only the prior read-only XLSX reader; do not invoke its main routine.
    helper = ROOT / "paper/analysis/storyline/verify_storyline_evidence.py"
    register(helper)
    spec = importlib.util.spec_from_file_location("bace_draft_workbook_reader", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validation, reviewer_inputs = {}, []
    for reviewer in ["A", "B"]:
        path = ROOT / f"BACE/analysis/validation/human_validation_600_reviewer_{reviewer}.xlsx"
        register(path)
        rows = module.workbook(path)
        validation[reviewer] = dict(sample_rows=len(rows), unique_ids=len({r["A"] for r in rows}),
            support_cells_filled=sum(bool(r.get("F")) for r in rows), diagnosis_cells_filled=sum(bool(r.get("G")) for r in rows))
        reviewer_inputs.append([{k: r.get(k, "") for k in "ABCDE"} for r in rows])
    assert reviewer_inputs[0] == reviewer_inputs[1]
    human_manifest = read_json(ROOT / "BACE/analysis/validation/_private/sample_manifest.json")
    validation["manifest_status"] = human_manifest["status"]
    validation["primary_n"] = human_manifest["study_design"]["primary_n"]
    validation["supplement_n"] = human_manifest["study_design"]["supplement_n"]
    assert all(validation[k]["support_cells_filled"] == validation[k]["diagnosis_cells_filled"] == 0 for k in ["A", "B"])

    results = dict(cohort=cohort, sampling=sampling, support=support, tasks=tasks, sensitivity=sensitivity,
        diagnoses=diagnoses, comparators=dict(means_pct={k: 100 * v for k, v in means.items()}, paired_differences=differences),
        inventory_medians=medians, validation=validation,
        status={"point_estimates": "COMPUTED_VERIFIED", "interval_endpoints": "SOURCE_REPORTED",
                "human_agreement": "COMPUTATION_PENDING"},
        aggregation="Macro: equally weighted completed disclosures. Pooled: equally weighted DCs. Diagnoses: all BACE-unsupported DCs. Native comparisons: paired disclosures with different within-disclosure claim inventories.",
        uncertainty="Saved 95% percentile company-cluster intervals; 2000 draws, seed 20260921. No bootstrap rerun or hypothesis test in this script.")
    save("verified_numbers.json", results)

    draft_path = ROOT / "paper/08_results_draft.md"
    draft = draft_path.read_text()
    manuscript = draft.split("<!-- MANUSCRIPT_START -->")[1].split("<!-- MANUSCRIPT_END -->")[0]
    paragraphs = dict(re.findall(r"<!-- (R\d+) -->\s*(.*?)(?=<!-- R\d+ -->|\Z)", manuscript, re.S))
    assert list(paragraphs) == [f"R{i:02}" for i in range(1, 15)]
    checks = {
        "R01": [f"{cohort['companies']} companies", f"{cohort['planned']:,}", f"{cohort['completed']:,}", f"{cohort['tasks']} tasks"],
        "R03": [f"{support['macro_pct']:.1f}%", "–".join(f"{v:.1f}" for v in support["saved_95_interval_pct"]),
                f"{support['pooled_pct']:.1f}%", f"{total_dc:,}"] + [f"{v:,}" for v in counts.values()] + [f"{v:.1f}%" for v in support["percentages"].values()],
        "R04": [f"{100 * min(float(r['mean']) for r in tasks):.1f}%", f"{100 * max(float(r['mean']) for r in tasks):.1f}%", "149", "150"],
        "R05": [f"{v:.1f} percentage points" for v in sensitivity.values()],
        "R06": [f"{combined:,}", f"{counts['Unsupported']:,}", f"{diagnoses['combined_pct']:.1f}%", f"{by_label['factual_boundary_distortion']:,}", f"{by_label['evidence_conflation']:,}"],
        "R09": [f"{100 * value:.1f}%" for value in means.values()] + [f"{row['mean_pp']:.1f}".replace("-", "−") for row in differences]
                + [" to ".join(f"{v:.1f}".replace("-", "−") for v in row["saved_95_interval_pp"]) for row in differences],
        "R10": [str(int(v)) for v in medians.values()],
    }
    for pid, fragments in checks.items():
        for fragment in fragments:
            assert fragment in paragraphs[pid], (pid, fragment)
    assert cohort["planned"] == 1800 and cohort["completed"] == 1798
    assert {int(r["disclosures"]) for r in tasks} == {149, 150}

    # Numerical examples remain SOURCE_REPORTED, with native verdict checks.
    case_checks = {}
    for name, pid in [("sca_incidents_workers", "R11"), ("continental_coverage", "R12"), ("banco_bpm_actual_as_target", "R13")]:
        b = read_json(ROOT / "paper/analysis/disagreement_cases" / (name + ".json"))
        assert b["bace_support"]["support_sets"] == []
        assert all(c["supported"] is True for c in b["native_claims"].values())
        assert all(b["checks"].values())
        case_checks[pid] = dict(name=name, source_status="SOURCE_REPORTED", selection=b["selection"],
            source_qualifiers_preserved=b["source_inspection"]["key_source_qualifiers_present_in_bace_candidates"])
    assert case_checks["R13"]["source_qualifiers_preserved"] is False

    occurrences = read_json(OUT / "citation_occurrences.json")
    for occurrence in occurrences:
        path = ROOT / occurrence["fulltext_path"]
        register(path)
        fulltext = re.sub(r"\s+", " ", path.read_text())
        for fragment in occurrence["verified_excerpt_fragments"]:
            assert fragment in fulltext, (occurrence["id"], fragment)
        register(ROOT / occurrence["retrieval_record"])

    docs = [draft_path, ROOT / "paper/09_methods_evidence_outline.md", ROOT / "paper/10_methods_draft.md", ROOT / "paper/README.md"]
    broken = []
    # Provenance files are generated after document checks. Avoid circular
    # hashes between the Results and Methods verification outputs.
    methods_out = ROOT / "paper/analysis/methods_draft"
    pending_outputs = {OUT / "provenance.json", methods_out / "provenance.json"}
    for path in docs:
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" in link or link.startswith("#"):
                continue
            target = (path.parent / link.split("#")[0]).resolve()
            if target not in pending_outputs and not target.exists():
                broken.append({"file": str(path.relative_to(ROOT)), "target": link})
            elif target.exists() and target.is_file() and not any(target.is_relative_to(folder) for folder in (OUT, methods_out)) and target not in docs:
                register(target)
    assert not broken, broken
    prose = re.sub(r"<!--.*?-->", "", manuscript, flags=re.S)
    prose = "\n".join(line for line in prose.splitlines() if not line.startswith("#"))
    word_count = len(prose.split())
    output_paths = docs + [OUT / "verified_numbers.json", OUT / "citation_occurrences.json"]
    save("provenance.json", dict(status="PASS", prepared_date="2026-10-01", prepared_timezone="Europe/Zurich",
        checked_at_utc=datetime.now(timezone.utc).isoformat(), python=sys.version,
        command="/home/muwang/.local/share/bace-writing-skills/venv/bin/python paper/analysis/results_draft/verify_draft.py",
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), input_files=INPUTS,
        prior_manifest_checks=prior_checks, paragraphs=list(paragraphs), numeric_text_checks=checks,
        example_checks=case_checks, broken_local_links=broken,
        manuscript_word_count=word_count, word_count_rule="Whitespace-delimited prose tokens between manuscript markers, excluding headings and HTML comments.",
        outputs={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in output_paths},
        limitations="Artifact and arithmetic verification only. Interval inference was not rerun; no model calls, experiment changes or independent human adjudication."))
    print(json.dumps({"status": "PASS", "completed_cases": len(complete), "results_words": word_count,
        "paragraphs": len(paragraphs), "case_examples": len(case_checks), "broken_links": len(broken)}))


if __name__ == "__main__":
    main()
