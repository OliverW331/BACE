import csv
import hashlib
import json
import math
import random
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "BACE/analysis/outputs/snapshot"
SEED = 20261029
DRAWS = 5000
SUPPORTED = {"direct", "inferred"}
LABEL_COLUMNS = {
    "direct": "bace_supported_direct",
    "inferred": "bace_supported_inferred",
    "non_disclosure_statement": "bace_non_disclosure_statement",
    "contradiction": "bace_contradiction",
    "evidence_conflation": "bace_evidence_conflation",
    "factual_boundary_distortion": "bace_factual_boundary_distortion",
    "inferential_inflation": "bace_inferential_inflation",
    "unsupported_novelty": "bace_unsupported_novelty",
}


def read_json(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save_json(name, data):
    (OUTPUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def save_csv(name, records):
    with (OUTPUT / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def quantile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def ranks(values):
    positions = defaultdict(list)
    for position, (_, original) in enumerate(sorted((value, index) for index, value in enumerate(values)), 1):
        positions[values[original]].append(position)
    return [statistics.mean(positions[value]) for value in values]


def spearman(first, second):
    return statistics.correlation(ranks(first), ranks(second))


def bootstrap(records):
    groups = defaultdict(list)
    for company_id, value in records:
        groups[company_id].append(value)
    clusters = [(sum(groups[key]), len(groups[key])) for key in sorted(groups)]
    generator = random.Random(SEED)
    draws = []
    for _ in range(DRAWS):
        selection = [clusters[generator.randrange(len(clusters))] for _ in clusters]
        draws.append(sum(total for total, count in selection) / sum(count for total, count in selection))
    return {
        "mean": statistics.mean(value for company_id, value in records),
        "low": quantile(draws, 0.025),
        "high": quantile(draws, 0.975),
        "companies": len(groups),
        "observations": len(records),
        "positive_company_means": sum(statistics.mean(values) > 0 for values in groups.values()),
        "negative_company_means": sum(statistics.mean(values) < 0 for values in groups.values()),
    }


def grouped_summary(rows, group, column):
    groups = defaultdict(list)
    for row in rows:
        groups[row[group]].append((row["company_id"], row[column]))
    return [{group: key, **bootstrap(groups[key])} for key in sorted(groups)]


def verify_sources():
    source_map = read_json(SNAPSHOT / "sources.json")
    def verify(item):
        filename, expected = item
        path = ROOT / filename
        if not path.is_file():
            return {"file": filename, "status": "missing"}
        actual = digest(path)
        return None if actual == expected else {"file": filename, "status": "changed", "expected": expected, "actual": actual}
    with ThreadPoolExecutor(max_workers=8) as executor:
        mismatches = [result for result in executor.map(verify, source_map.items()) if result is not None]
    manifest = read_json(SNAPSHOT / "manifest.json")
    table_checks = {name: digest(SNAPSHOT / f"{name}.csv") == expected for name, expected in manifest["tables"].items()}
    result = {
        "source_files_checked": len(source_map),
        "mismatches": mismatches,
        "snapshot_table_hash_checks": table_checks,
        "builder_hash_matches": digest(ROOT / "BACE/analysis/analysis_data.py") == manifest["builder_sha256"],
        "scope": "Consumed source and stage files listed by the saved snapshot, not all model histories or source PDF semantic accuracy.",
    }
    save_json("integrity.json", result)
    if mismatches or not all(table_checks.values()) or not result["builder_hash_matches"]:
        raise ValueError("Snapshot is stale or modified; do not reuse its cohort without a separately versioned rebuild.")
    return result


def workbook_completion(path):
    namespace = {"sheet": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(node.itertext()) for node in ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))]
        worksheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        records = worksheet.findall("sheet:sheetData/sheet:row", namespace)
        completion = Counter()
        for row in records:
            if row.attrib["r"] == "1":
                continue
            for cell in row.findall("sheet:c", namespace):
                column = "".join(character for character in cell.attrib["r"] if character.isalpha())
                if column not in {"F", "G"}:
                    continue
                value_node = cell.find("sheet:v", namespace)
                if cell.attrib.get("t") == "s" and value_node is not None:
                    value = strings[int(value_node.text)]
                elif cell.attrib.get("t") == "inlineStr":
                    value = "".join(cell.find("sheet:is", namespace).itertext())
                else:
                    value = "" if value_node is None else value_node.text or ""
                if value.strip():
                    completion[column] += 1
        return {"file": str(path.relative_to(ROOT)), "sample_rows": len(records) - 1, "support_labels": completion["F"], "diagnosis_labels": completion["G"], "sha256": digest(path)}


def literal_pairs(claims, external, cohort):
    inventory = defaultdict(list)
    for row in claims:
        inventory[(row["generation_case_id"], " ".join(row["dc_text"].casefold().split()))].append(row)
    results = {}
    for framework in ("ragchecker", "ragas"):
        native = defaultdict(list)
        for row in external:
            if row["framework"] == framework and row["generation_case_id"] in cohort:
                native[(row["generation_case_id"], " ".join(row["claim_text"].casefold().split()))].append(row)
        matrix = Counter()
        diagnoses = Counter()
        cases = set()
        native_ambiguous = sum(len(values) for key, values in native.items() if len(values) > 1)
        for key, bace_rows in inventory.items():
            native_rows = native.get(key, [])
            if len(bace_rows) != 1 or len(native_rows) != 1:
                continue
            bace_supported = bace_rows[0]["label"] in SUPPORTED
            native_supported = native_rows[0]["supported"] == "True"
            matrix[f"bace_{int(bace_supported)}_native_{int(native_supported)}"] += 1
            cases.add(key[0])
            if not bace_supported and native_supported:
                diagnoses[bace_rows[0]["label"]] += 1
        count = sum(matrix.values())
        results[framework] = {
            "pairs": count,
            "cases": len(cases),
            "bace_dc_coverage": count / len(claims),
            "native_ambiguous_rows_excluded": native_ambiguous,
            "joint_verdict_counts": dict(matrix),
            "bace_unsupported_native_supported_by_label": dict(diagnoses),
            "bace_support_rate": (matrix["bace_1_native_1"] + matrix["bace_1_native_0"]) / count if count else None,
            "native_support_rate": (matrix["bace_1_native_1"] + matrix["bace_0_native_1"]) / count if count else None,
            "limit": "Unique literal overlap is selected and not representative; same text does not make evidence interfaces or judgment procedures equal.",
        }
    return results


def main():
    assert quantile([0, 10], 0.25) == 2.5
    assert ranks([3, 1, 1]) == [3, 1.5, 1.5]
    assert abs(spearman([1, 2, 3], [3, 2, 1]) + 1) < 1e-12
    print("Verifying saved snapshot inputs and source hashes...", flush=True)
    integrity = verify_sources()
    rows = read_csv(SNAPSHOT / "metrics.csv")
    complete = []
    for row in rows:
        for key, value in list(row.items()):
            if key.startswith("bace_") and key != "bace_complete" or key in {"year", "word_count", "visible_evidence_count", "ragchecker_claim_count", "ragchecker_supported", "ragchecker_faithfulness", "ragas_claim_count", "ragas_supported", "ragas_faithfulness"}:
                row[key] = float(value) if value else None
        if row["bace_complete"] == "True":
            complete.append(row)
    cohort = {row["generation_case_id"]: row for row in complete}
    claims = read_csv(SNAPSHOT / "claims.csv")
    external = read_csv(SNAPSHOT / "external_claims.csv")
    assert all(row["generation_case_id"] in cohort for row in claims)
    assert len(cohort) == len(complete) == 1798
    label_counts = Counter(row["label"] for row in claims)
    per_case_labels = defaultdict(Counter)
    per_case_candidates = Counter()
    per_case_multi_ec = Counter()
    for row in claims:
        case_id = row["generation_case_id"]
        per_case_labels[case_id][row["label"]] += 1
        assert (int(row["support_set_count"]) > 0) == (row["label"] in SUPPORTED)
        if int(row["support_set_count"]) > 0 and int(row["min_support_set_size"]) > 1:
            per_case_multi_ec[case_id] += 1
        if int(row["candidate_count"]) == 0:
            per_case_candidates[case_id] += 1
            assert row["label"] not in SUPPORTED
    per_native = defaultdict(Counter)
    for row in external:
        per_native[(row["generation_case_id"], row["framework"])]["claims"] += 1
        per_native[(row["generation_case_id"], row["framework"])]["supported"] += row["supported"] == "True"
    for row in complete:
        case_id = row["generation_case_id"]
        counts = per_case_labels[case_id]
        assert sum(counts.values()) == row["bace_dc_count"]
        for label, column in LABEL_COLUMNS.items():
            assert counts[label] == row[column]
        supported = counts["direct"] + counts["inferred"]
        assert abs(supported / sum(counts.values()) - row["bace_support_rate_all_dc"]) < 1e-12
        assert row["bace_unsupported"] == sum(counts.values()) - supported
        assert row["bace_multi_ec_required_dc_count"] == per_case_multi_ec[case_id]
        assert abs(supported / (sum(counts.values()) - counts["non_disclosure_statement"]) - row["bace_support_rate_excluding_non_disclosure_sensitivity"]) < 1e-12
        for framework in ("ragchecker", "ragas"):
            assert row[f"{framework}_complete"] == "True"
            native = per_native[(case_id, framework)]
            assert native["claims"] == row[f"{framework}_claim_count"]
            assert native["supported"] == row[f"{framework}_supported"]
            assert abs(native["supported"] / native["claims"] - row[f"{framework}_faithfulness"]) < 1e-12
        row["zero_candidate_upper_bound"] = row["bace_support_rate_all_dc"] + per_case_candidates[case_id] / row["bace_dc_count"]
    print("Recomputing point estimates, literal alignment and clustered contrasts...", flush=True)
    all_dc = len(claims)
    supported = label_counts["direct"] + label_counts["inferred"]
    unsupported = all_dc - supported
    rates = {}
    for name, column in {"bace": "bace_support_rate_all_dc", "ragchecker": "ragchecker_faithfulness", "ragas": "ragas_faithfulness", "non_disclosure_sensitivity": "bace_support_rate_excluding_non_disclosure_sensitivity", "zero_candidate_upper_bound": "zero_candidate_upper_bound"}.items():
        rates[name] = bootstrap([(row["company_id"], row[column]) for row in complete])
    tasks = grouped_summary(complete, "task", "bace_support_rate_all_dc")
    tasks_sensitivity = grouped_summary(complete, "task", "bace_support_rate_excluding_non_disclosure_sensitivity")
    years = grouped_summary(complete, "year", "bace_support_rate_all_dc")
    years_sensitivity = grouped_summary(complete, "year", "bace_support_rate_excluding_non_disclosure_sensitivity")
    domains = grouped_summary(complete, "standard", "bace_support_rate_all_dc")
    companies = grouped_summary(complete, "company_name", "bace_support_rate_all_dc")
    case_lookup = {(row["company_id"], int(row["year"]), row["task"]): row for row in complete}
    company_year = defaultdict(dict)
    for row in complete:
        company_year[(row["company_id"], int(row["year"]))][row["task"]] = row
    paired = {}
    for first, second in [("G1-1", "S1-5"), ("E1-4", "S1-5"), ("E1-6", "S1-5")]:
        records = [(company_id, cells[first]["bace_support_rate_all_dc"] - cells[second]["bace_support_rate_all_dc"]) for (company_id, year), cells in company_year.items() if first in cells and second in cells]
        paired[f"{first}_minus_{second}"] = bootstrap(records)
        sensitivity_records = [(company_id, cells[first]["bace_support_rate_excluding_non_disclosure_sensitivity"] - cells[second]["bace_support_rate_excluding_non_disclosure_sensitivity"]) for (company_id, year), cells in company_year.items() if first in cells and second in cells]
        paired[f"{first}_minus_{second}_non_disclosure_sensitivity"] = bootstrap(sensitivity_records)
    domain_pairs = defaultdict(list)
    for (company_id, year), cells in company_year.items():
        if len(cells) != 12:
            continue
        means = {domain: statistics.mean(row["bace_support_rate_all_dc"] for row in cells.values() if row["standard"] == domain) for domain in ("E1", "S1", "G1")}
        for domain in ("E1", "G1"):
            domain_pairs[f"{domain}_minus_S1"].append((company_id, means[domain] - means["S1"]))
    paired.update({name: bootstrap(records) for name, records in domain_pairs.items()})
    year_pairs = []
    for (company_id, year, task), first in case_lookup.items():
        second = case_lookup.get((company_id, 2023, task))
        if year == 2019 and second is not None:
            year_pairs.append((company_id, second["bace_support_rate_all_dc"] - first["bace_support_rate_all_dc"]))
    paired["2023_minus_2019"] = bootstrap(year_pairs)
    gaps = {framework: bootstrap([(row["company_id"], row[f"{framework}_faithfulness"] - row["bace_support_rate_all_dc"]) for row in complete]) for framework in ("ragchecker", "ragas")}
    scores = [row["bace_support_rate_all_dc"] for row in complete]
    distribution = {"median": statistics.median(scores), "q25": quantile(scores, 0.25), "q75": quantile(scores, 0.75), "minimum": min(scores), "maximum": max(scores), "below_half_cases": sum(value < 0.5 for value in scores), "at_least_80pct_cases": sum(value >= 0.8 for value in scores), "fully_supported_cases": sum(value == 1 for value in scores), "zero_support_cases": sum(value == 0 for value in scores)}
    diagnoses = []
    for label, count in label_counts.items():
        if label not in SUPPORTED:
            diagnoses.append({"label": label, "claims": count, "percent_unsupported": 100 * count / unsupported, "percent_all_dc": 100 * count / all_dc, "disclosures_with_label": sum(counts[label] > 0 for counts in per_case_labels.values())})
    task_diagnoses = []
    for task in sorted({row["task"] for row in complete}):
        cases = [row for row in complete if row["task"] == task]
        denominator = sum(row["bace_dc_count"] for row in cases)
        task_diagnoses.append({"task": task, "disclosures": len(cases), "all_dc": denominator, **{f"{label}_percent_all_dc": 100 * sum(row[column] for row in cases) / denominator for label, column in LABEL_COLUMNS.items()}})
    non_disclosure_removed = label_counts["non_disclosure_statement"]
    zero_candidates = sum(per_case_candidates.values())
    sensitivity = {"non_disclosure_removed": non_disclosure_removed, "unchanged_supported_numerator": supported, "remaining_dc": all_dc - non_disclosure_removed, "pooled_support": supported / (all_dc - non_disclosure_removed), "macro_increase_pp": 100 * (rates["non_disclosure_sensitivity"]["mean"] - rates["bace"]["mean"]), "zero_candidate_dc": zero_candidates, "zero_candidate_cases": len(per_case_candidates), "zero_candidate_fraction_unsupported": zero_candidates / unsupported, "zero_candidate_max_macro_increase_pp": 100 * (rates["zero_candidate_upper_bound"]["mean"] - rates["bace"]["mean"]), "limit": "Removal changes the estimand. Relabeling every zero-candidate DC is a hypothetical arithmetic upper bound for that subset only. Scenarios overlap and cannot be added."}
    aligned = literal_pairs(claims, external, cohort)
    saved_gap = read_json(ROOT / "paper/analysis/evaluator_gap/results.json")
    for framework, result in aligned.items():
        assert result["pairs"] == saved_gap["literal_alignment"][framework]["pairs"]
    evidence = {"case_level_ec": sum(row["bace_ec_count"] for row in complete), "case_level_used_ec": sum(row["bace_used_ec_count"] for row in complete), "macro_eccr": statistics.mean(row["bace_eccr"] for row in complete), "median_eccr": statistics.median(row["bace_eccr"] for row in complete), "pooled_eccr": sum(row["bace_used_ec_count"] for row in complete) / sum(row["bace_ec_count"] for row in complete), "inferred_fraction_supported": label_counts["inferred"] / supported, "multi_ec_required_dc": sum(row["bace_multi_ec_required_dc_count"] for row in complete), "limit": "ECs are case-level deduplicated inventories. Unused ECs may be redundant, irrelevant or outside task scope; ECCR is not recall or completeness."}
    associations = {framework: spearman(scores, [row[f"{framework}_faithfulness"] for row in complete]) for framework in ("ragchecker", "ragas")}
    associations.update({"bace_vs_word_count": spearman(scores, [row["word_count"] for row in complete]), "bace_vs_ec_count": spearman(scores, [row["bace_ec_count"] for row in complete])})
    leave_one_out = {}
    for column in ("bace_support_rate_all_dc", "bace_support_rate_excluding_non_disclosure_sensitivity"):
        estimates = [statistics.mean(row[column] for row in complete if row["company_id"] != company_id) for company_id in sorted({row["company_id"] for row in complete})]
        leave_one_out[column] = {"minimum": min(estimates), "maximum": max(estimates)}
    validation = [workbook_completion(ROOT / f"BACE/analysis/validation/human_validation_600_reviewer_{reviewer}.xlsx") for reviewer in ("A", "B")]
    result = {"status": "COMPUTED_VERIFIED", "analysis_status": "Post-experiment exploratory descriptive reanalysis; no model runs, new human labels or hypothesis tests.", "cohort": {"planned": len(rows), "bace_complete": len(complete), "companies": len({row["company_id"] for row in complete}), "years": sorted({int(row["year"]) for row in complete}), "tasks": sorted({row["task"] for row in complete}), "missing": [{key: row[key] for key in ("generation_case_id", "company_name", "year", "task", "state_status")} for row in rows if row["bace_complete"] != "True"]}, "bootstrap": {"seed": SEED, "draws": DRAWS, "rng": "Python random.Random (Mersenne Twister)", "unit": "Company; retain all matched observed records in each sampled company", "interval": "95% percentile; linear interpolation at (n-1)*p", "scope": "Sampling variability conditional on saved cohort; not model randomness, annotation error, missing-case uncertainty or population-representative inference", "multiplicity": "No hypothesis tests or corrected testing family; selected contrasts are exploratory, not confirmatory."}, "claims": {"all_dc": all_dc, "supported": supported, "unsupported": unsupported, "label_counts": dict(label_counts), "pooled_support": supported / all_dc}, "rates": rates, "distribution": distribution, "tasks": tasks, "years": years, "domains": domains, "paired_contrasts": paired, "native_minus_bace": gaps, "diagnoses": diagnoses, "sensitivity": sensitivity, "literal_alignment": aligned, "evidence_use": evidence, "spearman_descriptive": associations, "leave_one_company_out": leave_one_out, "human_review": validation, "secondary_saved_artifacts": {"ec_metadata_audit": {"status": "SOURCE_REPORTED", "file": "paper/analysis/ec_metadata_audit_2026-10-26/summary.json", "note": "Saved forensic census, not an intervention or corrected score; flagged references are not adjudicated errors."}, "prompt_sensitivity": {"status": "SOURCE_REPORTED", "file": "paper/analysis/prompt_gap_review_2026-10-22/results.json", "note": "Separate saved follow-up experiment on 1,796 paired disclosures, not the 1,798-case primary run; not rerun in this audit."}}}
    result["native_inventories"] = {framework: {"median_claims": statistics.median(row[count_column] for row in complete), "total_claims": int(sum(row[count_column] for row in complete)), "pooled_support": sum(row[support_column] for row in complete) / sum(row[count_column] for row in complete)} for framework, count_column, support_column in [("bace", "bace_dc_count", "bace_supported_direct"), ("ragchecker", "ragchecker_claim_count", "ragchecker_supported"), ("ragas", "ragas_claim_count", "ragas_supported")]}
    result["native_inventories"]["bace"]["pooled_support"] = supported / all_dc
    result["tasks_non_disclosure_sensitivity"] = tasks_sensitivity
    result["years_non_disclosure_sensitivity"] = years_sensitivity
    result["task_label_composition"] = task_diagnoses
    save_json("results.json", result)
    save_csv("task_summary.csv", tasks)
    save_csv("task_non_disclosure_sensitivity.csv", tasks_sensitivity)
    save_csv("year_summary.csv", years)
    save_csv("year_non_disclosure_sensitivity.csv", years_sensitivity)
    save_csv("task_label_composition.csv", task_diagnoses)
    save_csv("domain_summary.csv", domains)
    save_csv("paired_contrasts.csv", [{"contrast": name, **value} for name, value in paired.items()])
    save_csv("diagnoses.csv", diagnoses)
    save_csv("company_summary.csv", companies)
    save_csv("case_metrics.csv", [{key: row[key] for key in ("generation_case_id", "company_id", "company_name", "year", "task", "standard", "bace_dc_count", "bace_support_rate_all_dc", "bace_support_rate_excluding_non_disclosure_sensitivity", "ragchecker_faithfulness", "ragas_faithfulness")} for row in complete])
    source_paths = [SNAPSHOT / name for name in ("manifest.json", "sources.json", "metrics.csv", "claims.csv", "external_claims.csv")]
    source_paths.extend(ROOT / name for name in ("BACE/config/experiment.json", "BACE/analysis/ANALYSIS_SPEC.md", "BACE/script/evaluation/metrics.py", "paper/analysis/evaluator_gap/results.json", "paper/analysis/ec_metadata_audit_2026-10-26/summary.json", "paper/analysis/prompt_gap_review_2026-10-22/results.json"))
    save_json("provenance.json", {"access_date": "2026-10-29", "completed_at_utc": datetime.now(timezone.utc).isoformat(), "command": " ".join([sys.executable, str(Path(__file__).resolve())]), "python": sys.version, "dependencies": "Python standard library only; no project environment changed", "script_sha256": digest(Path(__file__)), "input_hashes": {str(path.relative_to(ROOT)): digest(path) for path in source_paths}, "integrity": {"source_files_checked": integrity["source_files_checked"], "mismatches": len(integrity["mismatches"])}, "numerical_locator": "results.json keys and corresponding CSV columns; per-case score numerators verified against complete DC/native verdict inventories", "read_only_boundary": "No experiment outputs, frozen prompts/configuration, source files, or reviewer workbooks modified."})
    print(json.dumps({"cohort": result["cohort"], "rates": rates, "distribution": distribution, "paired_contrasts": paired, "evidence_use": evidence, "human_review": validation, "hash_mismatches": len(integrity["mismatches"])}, indent=2), flush=True)


if __name__ == "__main__":
    main()
