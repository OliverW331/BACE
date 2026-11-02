"""Verify arithmetic and local readiness for the Results storyline.

Read saved experiment/analysis artifacts; write only into this directory.
Reuse saved bootstrap intervals without rerunning inference or model stages.
"""
import csv
import hashlib
import json
import math
import statistics
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2]
ANALYSIS = PROJECT / "BACE/analysis"
DATA = ANALYSIS / "outputs"
INPUTS = {}
LEDGER = []


def source(path):
    path = Path(path)
    name = str(path.relative_to(PROJECT))
    INPUTS[name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "bytes": path.stat().st_size}
    return name


def js(path):
    source(path)
    return json.loads(Path(path).read_text())


def rows(path):
    source(path)
    with Path(path).open(newline="") as f:
        return list(csv.DictReader(f))


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def record(identifier, value, unit, status, sources, locator, formula, denominator,
           uncertainty="Descriptive arithmetic; no new interval or hypothesis test."):
    LEDGER.append(dict(id=identifier, value=value, unit=unit, status=status,
                       sources=sources, locator=locator, formula=formula,
                       denominator=denominator, uncertainty=uncertainty))


def close(a, b):
    assert math.isclose(float(a), float(b), abs_tol=1e-12), (a, b)


def workbook(path):
    source(path)
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            shared = ["".join(t.text or "" for t in x.findall(".//s:t", ns))
                      for x in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        xml = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        def text(c):
            if c.get("t") == "inlineStr":
                return "".join(t.text or "" for t in c.findall(".//s:t", ns))
            v = c.find("s:v", ns)
            if v is None:
                return ""
            return shared[int(v.text)] if c.get("t") == "s" else v.text or ""
        result = []
        for r in xml.findall(".//s:row", ns):
            if r.get("r") == "1":
                continue
            cells = {"".join(filter(str.isalpha, c.get("r"))): text(c)
                     for c in r.findall("s:c", ns)}
            if cells.get("A"):
                result.append(cells)
    return result


def main():
    metrics_path = DATA / "snapshot/metrics.csv"
    metrics = rows(metrics_path)
    snapshot = js(DATA / "snapshot/manifest.json")
    assert INPUTS[str(metrics_path.relative_to(PROJECT))]["sha256"] == snapshot["tables"]["metrics"]
    source(ANALYSIS / "analysis_data.py")
    source(ANALYSIS / "scripts/build_notebooks.py")
    source(ANALYSIS / "ANALYSIS_SPEC.md")
    source(ANALYSIS / "requirements.lock.txt")
    analysis_manifest = js(DATA / "analysis_manifest.json")
    execution = js(PROJECT / "BACE/results/main_v1/execution_status.json")
    bace = [r for r in metrics if r["bace_complete"].lower() == "true"]
    native_columns = ["bace_support_rate_all_dc", "ragchecker_faithfulness", "ragas_faithfulness"]
    common = [r for r in metrics if all(r[c] != "" for c in native_columns)]
    ids = {r["generation_case_id"] for r in bace}
    assert len(ids) == len(bace) == analysis_manifest["common_completed_cases"]
    assert ids == {r["generation_case_id"] for r in common} == set(execution["completed_case_ids"])
    cohort = dict(planned_cases=len(metrics), completed_bace_cases=len(bace), paired_cases=len(common),
                  companies=len({r["company_id"] for r in bace}),
                  reporting_years=sorted({int(r["year"]) for r in bace}),
                  tasks=sorted({r["task"] for r in bace}),
                  run_status=execution["status"], excluded_cases=execution["failures"],
                  exclusions="Incomplete BACE branches; excluded from BACE summaries and paired comparisons, never scored as zero.")
    save("cohort.json", cohort)
    record("N0", cohort, "cases/companies/years/tasks", "COMPUTED_VERIFIED",
           [source(metrics_path), source(PROJECT / "BACE/results/main_v1/execution_status.json")],
           "bace_complete; native score columns; execution status", "Count explicit completed branches and intersect score availability.",
           "Planned case inventory and its completed subset.")

    fig1 = DATA / "figures/01"
    fig2 = DATA / "figures/02"
    fig3 = DATA / "figures/03"
    distribution = rows(fig1 / "01_support_distribution__disclosures.csv")
    assert {r["generation_case_id"] for r in distribution} == ids
    by_id = {r["generation_case_id"]: r for r in bace}
    for r in distribution:
        close(r[native_columns[0]], by_id[r["generation_case_id"]][native_columns[0]])
    counts = {r["status"]: int(float(r["count"])) for r in rows(fig1 / "01_support_distribution__claim_counts.csv")}
    count_columns = {"Direct": "bace_supported_direct", "Inferred": "bace_supported_inferred", "Unsupported": "bace_unsupported"}
    for status, col in count_columns.items():
        assert counts[status] == sum(int(float(r[col])) for r in bace)
    all_dc = sum(int(float(r["bace_dc_count"])) for r in bace)
    assert sum(counts.values()) == all_dc
    summary_path = fig3 / "03_native_comparison__cohort_summary.csv"
    summaries = {r["method"]: r for r in rows(summary_path) if r["cohort"] == "Common"}
    mean = statistics.mean(float(r[native_columns[0]]) for r in bace)
    close(mean, summaries["BACE"]["mean"])
    support = dict(macro_mean_pct=100 * mean,
                   macro_saved_95_interval_pct=[100 * float(summaries["BACE"][k]) for k in ["low", "high"]],
                   all_dc=all_dc, counts=counts,
                   percent_all_dc={k: 100 * v / all_dc for k, v in counts.items()},
                   pooled_support_pct=100 * (counts["Direct"] + counts["Inferred"]) / all_dc)
    uncertainty = "SOURCE_REPORTED: saved 95% percentile company-cluster interval, 2,000 draws, seed 20260921; not rerun. See analysis_data.py::company_bootstrap and ANALYSIS_SPEC.md."
    record("N1", support, "percent and DC counts", "COMPUTED_VERIFIED",
           [source(metrics_path), source(summary_path), source(fig1 / "01_support_distribution__claim_counts.csv")],
           "Common/BACE row; Direct, Inferred and Unsupported rows; bace_complete=True",
           "Macro: mean of per-disclosure supported/all-DC rates. Pooled: summed supported DCs / summed all DCs. Multiply rates by 100.",
           f"{len(bace)} equally weighted disclosures for macro; {all_dc} equally weighted DCs for pooled.", uncertainty)
    tasks_path = fig1 / "01_task_support__data.csv"
    tasks = rows(tasks_path)
    for t in tasks:
        group = [r for r in bace if r["task"] == t["task"]]
        assert len(group) == int(t["disclosures"])
        close(statistics.mean(float(r[native_columns[0]]) for r in group), t["mean"])
    record("N2", tasks, "fractions; disclosure counts", "SOURCE_REPORTED", [source(tasks_path), source(metrics_path)],
           "All task rows: mean, low, high, disclosures, companies, draws",
           "Saved task-specific disclosure means and intervals; means/counts independently checked.",
           "All completed disclosures in each task; all tasks retained in protocol order.", uncertainty)

    composition_path = fig2 / "02_label_composition__data.csv"
    labels = rows(composition_path)
    for row in labels:
        assert int(row["count"]) == sum(int(float(r["bace_" + row["label"]])) for r in bace)
        close(row["percent_unsupported"], 100 * int(row["count"]) / counts["Unsupported"])
    top_count = sum(int(r["count"]) for r in labels if r["label"] in {"factual_boundary_distortion", "evidence_conflation"})
    diagnosis = dict(all_labels=labels, boundary_and_conflation_count=top_count,
                     unsupported_denominator=counts["Unsupported"],
                     boundary_and_conflation_pct=100 * top_count / counts["Unsupported"])
    record("N3", diagnosis, "automated diagnoses and percent", "COMPUTED_VERIFIED",
           [source(composition_path), source(metrics_path)], "All six label rows; boundary-distortion and conflation counts",
           "Sum selected label counts / all unsupported DCs × 100; all six categories remain in the denominator.",
           f"{counts['Unsupported']} BACE-unsupported DCs, including non-disclosure statements.")

    score_path = fig3 / "03_native_comparison__scores.csv"
    scores = rows(score_path)
    assert {r["generation_case_id"] for r in scores} == ids
    for row in scores:
        for c in native_columns:
            close(row[c], by_id[row["generation_case_id"]][c])
    diffs_path = fig3 / "03_native_comparison__paired_differences.csv"
    diffs = rows(diffs_path)
    for method, col in zip(["RAGChecker", "RAGAS"], native_columns[1:]):
        d = next(r for r in diffs if r["contrast"].endswith(method))
        close(statistics.mean(float(r[native_columns[0]]) - float(r[col]) for r in scores), d["mean"])
        close(statistics.mean(float(r[col]) for r in scores), summaries[method]["mean"])
    record("N4", {"common_means": summaries, "paired_differences": diffs}, "fractions (multiply differences by 100 for percentage points)",
           "SOURCE_REPORTED", [source(score_path), source(summary_path), source(diffs_path)],
           "Common cohort rows; BACE minus comparator contrasts",
           "Subtract within disclosure, then average; saved point estimates independently checked.",
           f"{len(scores)} matched disclosures; native within-disclosure claim denominators differ.", uncertainty)
    inventory_path = fig3 / "03_claim_inventories__data.csv"
    inventories = rows(inventory_path)
    assert {r["generation_case_id"] for r in inventories} == ids
    medians = {c: statistics.median(float(r[c]) for r in inventories)
               for c in ["bace_dc_count", "ragchecker_claim_count", "ragas_claim_count"]}
    record("N5", medians, "claims per disclosure", "COMPUTED_VERIFIED", [source(inventory_path)],
           "bace_dc_count, ragchecker_claim_count, ragas_claim_count",
           "Median native claim inventory on the paired cohort.", f"{len(inventories)} disclosures per method.")
    sensitivity_path = fig1 / "01_secondary_metrics__data.csv"
    secondary = rows(sensitivity_path)
    assert {r["generation_case_id"] for r in secondary} == ids
    changes = [100 * (float(r["bace_support_rate_excluding_non_disclosure_sensitivity"]) -
                      float(r["bace_support_rate_all_dc"])) for r in secondary]
    record("N6", {"median_change_pp": statistics.median(changes), "max_change_pp": max(changes)},
           "percentage points", "COMPUTED_VERIFIED", [source(sensitivity_path)],
           "Sensitivity support minus all-DC support, paired per disclosure",
           "Median and maximum of within-disclosure score changes.",
           f"{len(secondary)} completed disclosures; excluding non-disclosure statements changes the score denominator.")

    validation_dir = ANALYSIS / "validation"
    validation_manifest = js(validation_dir / "_private/sample_manifest.json")
    reviewer_counts, matrices = {}, []
    for reviewer in ["A", "B"]:
        path = validation_dir / f"human_validation_600_reviewer_{reviewer}.xlsx"
        values = workbook(path)
        matrices.append({r["A"]: [r.get(c, "") for c in ["A", "B", "C", "D", "E"]] for r in values})
        reviewer_counts[reviewer] = dict(file=source(path), sample_rows=len(values),
             unique_ids=len({r["A"] for r in values}),
             support_cells_filled=sum(bool(r.get("F", "").strip()) for r in values),
             diagnosis_cells_filled=sum(bool(r.get("G", "").strip()) for r in values))
    assert matrices[0] == matrices[1]
    validation = dict(manifest_status=validation_manifest["status"], workbooks=reviewer_counts,
                      same_sample_inputs=True, study_design=validation_manifest["study_design"],
                      scope="Only local formal workbook copies inspected; annotations elsewhere are not inferred absent.",
                      top_level_files=sorted(p.name for p in validation_dir.iterdir() if p.is_file()))
    save("validation_status.json", validation)
    record("N7", reviewer_counts, "samples and filled cells", "COMPUTED_VERIFIED",
           [r["file"] for r in reviewer_counts.values()], "Claim_review: A2:A601, F2:G601",
           "Read XLSX XML; count sample IDs and nonempty classification cells; compare supplied inputs A–E.",
           "Each formal reviewer workbook; coordinator automatic-result workbook is excluded.")

    examples = []
    for label in ["factual_boundary_distortion", "evidence_conflation", "contradiction"]:
        path = DATA / f"examples/02_{label}.json"
        x = js(path); m = x["material"]; dc_id = x["selection"]["dc_id"]
        case_id = m["input"]["generation_case_id"]
        base = PROJECT / "BACE/results/main_v1/cases" / case_id
        paths = {"input":"inputs/generation_cases.jsonl", "response":"generation/generated_disclosures.jsonl",
                 "dc":"bace/dedup/dc_claims.jsonl", "ec":"bace/dedup/ec_claims.jsonl",
                 "diagnosis":"bace/diagnosis/dc_unsupported_diagnoses.jsonl", "candidates":"bace/candidates/dc_candidate_ecs.jsonl"}
        for key, rel in paths.items():
            rawpath = base / rel; source(rawpath)
            raw = [json.loads(line) for line in rawpath.read_text().splitlines() if line.strip()]
            assert (raw[0] if key in {"input", "response"} else raw) == m[key], (label, key)
        dc = next(d for d in m["dc"] if d["dc_id"] == dc_id)
        quotes = [q for p in dc["dc_provenance"] for q in p["source_quotes"]
                  if q in m["response"]["generated_text"]]
        assert quotes
        examples.append(dict(label=label, case_id=case_id, dc_id=dc_id, selection=x["selection"],
                             dc_text=dc["dc_text"], generated_quote=max(quotes, key=len),
                             selected_card=x["selected_card"], analyst_note=x["analyst_note"],
                             source=source(path), exported_material_matches_saved_case=True))
    source(ANALYSIS / "assets/failure_example_selection.json")
    source(DATA / "figures/02/02_asml_source_layout__data.csv")
    source(DATA / "figures/02/02_asml_source_layout.png")
    save("example_candidates.json", examples)
    save("numeric_ledger.json", LEDGER)
    save("verified_results.json", dict(cohort=cohort, support=support, diagnosis=diagnosis,
          task_range={"lowest": min(tasks, key=lambda x: float(x["mean"])), "highest": max(tasks, key=lambda x: float(x["mean"]))},
          native_claim_medians=medians, validation=reviewer_counts))
    save("provenance.json", dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),
          command="/home/muwang/.local/share/bace-writing-skills/venv/bin/python paper/analysis/storyline/verify_storyline_evidence.py",
          python=sys.version, script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          input_files=INPUTS, checks="PASS", bootstrap="Saved intervals reused; not rerun.",
          experiment_changes="None; only paper/analysis/storyline outputs written."))
    print(json.dumps(dict(status="PASS", completed=len(bace), macro_support_pct=100*mean,
                         dominant_diagnoses_pct=diagnosis["boundary_and_conflation_pct"],
                         native_medians=medians, ledger_records=len(LEDGER),
                         sensitivity=LEDGER[-2]["value"], reviewer_counts=reviewer_counts,
                         source_files=len(INPUTS)), indent=2))


if __name__ == "__main__":
    main()
