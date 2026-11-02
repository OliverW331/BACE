"""Descriptive diagnostics of saved native scores; no model calls or new labels."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import platform
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "BACE/analysis/outputs/snapshot"
INPUTS = {}
SUPPORTED = {"direct", "inferred"}


def read_bytes(path):
    data = path.read_bytes()
    INPUTS[str(path.relative_to(ROOT))] = {
        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)
    }
    return data


def read_csv(path):
    return list(csv.DictReader(io.StringIO(read_bytes(path).decode())))


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False,
                                     allow_nan=False) + "\n")


def write_csv(name, rows):
    with (OUT / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def integer(value):
    number = float(value)
    assert number.is_integer()
    return int(number)


def normalize(text):
    return " ".join(text.casefold().split())


def main():
    manifest = json.loads(read_bytes(SNAPSHOT / "manifest.json"))
    tables = {name: read_csv(SNAPSHOT / f"{name}.csv")
              for name in ("metrics", "claims", "external_claims")}
    for name in tables:
        path = str((SNAPSHOT / f"{name}.csv").relative_to(ROOT))
        assert INPUTS[path]["sha256"] == manifest["tables"][name], name
    read_bytes(ROOT / "BACE/analysis/analysis_data.py")
    read_bytes(ROOT / "BACE/analysis/validation/README.md")
    execution = json.loads(read_bytes(ROOT / "BACE/results/main_v1/execution_status.json"))
    assert execution["status"] not in {"running", "finalizing"}
    assert not execution.get("active_cases")
    rows = tables["metrics"]
    assert len({r["generation_case_id"] for r in rows}) == len(rows)
    common = {r["generation_case_id"]: r for r in rows
              if all(r[f"{f}_complete"] == "True"
                     for f in ("bace", "ragchecker", "ragas"))}
    assert set(common) == set(execution["completed_case_ids"])
    claims = [r for r in tables["claims"] if r["generation_case_id"] in common]
    assert len({(r["generation_case_id"], r["dc_id"]) for r in claims}) == len(claims)
    by_case = defaultdict(list)
    for r in claims:
        assert (integer(r["support_set_count"]) > 0) == (r["label"] in SUPPORTED)
        assert integer(r["candidate_count"]) > 0 or r["label"] not in SUPPORTED
        by_case[r["generation_case_id"]].append(r)
    externals = {f: [r for r in tables["external_claims"]
                     if r["framework"] == f and r["generation_case_id"] in common]
                 for f in ("ragchecker", "ragas")}
    external_by_case = {}
    for framework, erows in externals.items():
        counts = defaultdict(Counter)
        assert len({(r["generation_case_id"], r["claim_index"]) for r in erows}) == len(erows)
        for r in erows:
            assert r["supported"] in {"True", "False"}
            counts[r["generation_case_id"]]["total"] += 1
            counts[r["generation_case_id"]]["supported"] += r["supported"] == "True"
        external_by_case[framework] = counts

    case_diagnostics = []
    for cid, metric in common.items():
        cr = by_case[cid]
        n = len(cr)
        s = sum(r["label"] in SUPPORTED for r in cr)
        nd = sum(r["label"] == "non_disclosure_statement" for r in cr)
        zero = sum(integer(r["candidate_count"]) == 0 for r in cr)
        assert n == integer(metric["bace_dc_count"])
        assert s == integer(metric["bace_supported_direct"]) + integer(metric["bace_supported_inferred"])
        assert n - s == integer(metric["bace_unsupported"])
        assert nd == integer(metric["bace_non_disclosure_statement"])
        assert n - nd > 0
        assert math.isclose(s / n, float(metric["bace_support_rate_all_dc"]), abs_tol=1e-12)
        assert math.isclose(s / (n - nd), float(metric["bace_support_rate_excluding_non_disclosure_sensitivity"]), abs_tol=1e-12)
        item = {"generation_case_id": cid, "company_id": metric["company_id"],
                "company_name": metric["company_name"], "year": metric["year"],
                "task": metric["task"], "bace_dc_count": n, "bace_supported": s,
                "bace_unsupported": n - s, "bace_non_disclosure_statement": nd,
                "zero_candidate_dc_count": zero, "bace_native_rate": s / n,
                "bace_excluding_non_disclosure_rate": s / (n - nd),
                "hypothetical_all_zero_candidate_supported_rate": (s + zero) / n}
        for framework in externals:
            counts = external_by_case[framework][cid]
            assert counts["total"] == integer(metric[f"{framework}_claim_count"])
            assert counts["supported"] == integer(metric[f"{framework}_supported"])
            rate = counts["supported"] / counts["total"]
            assert math.isclose(rate, float(metric[f"{framework}_faithfulness"]), abs_tol=1e-12)
            item[f"{framework}_claim_count"] = counts["total"]
            item[f"{framework}_supported"] = counts["supported"]
            item[f"{framework}_rate"] = rate
        case_diagnostics.append(item)

    def average(column):
        return mean(r[column] for r in case_diagnostics)

    total = len(claims)
    supported = sum(r["label"] in SUPPORTED for r in claims)
    nd = sum(r["label"] == "non_disclosure_statement" for r in claims)
    zero_rows = [r for r in claims if integer(r["candidate_count"]) == 0]
    native = {"bace": average("bace_native_rate"),
              **{f: average(f"{f}_rate") for f in externals}}
    results = {
        "status": "COMPUTED_VERIFIED",
        "analysis_type": "Post-experiment exploratory descriptive diagnostics; no new model evaluations or human annotations.",
        "cohort": {"planned_cases": len(rows), "paired_cases": len(common),
                   "companies": len({r["company_id"] for r in common.values()}),
                   "excluded_cases": [r["generation_case_id"] for r in rows if r["generation_case_id"] not in common],
                   "missingness_rule": "Incomplete cases are excluded from all comparisons, never assigned zero."},
        "aggregation": "Native and sensitivity means give each paired disclosure equal weight. Pooled rates give each native claim equal weight. Exact-text rates use only the selected unique literal pairs.",
        "native_macro_rates": native,
        "native_pooled_rates": {"bace": supported / total,
                                **{f: sum(r["supported"] == "True" for r in erows) / len(erows)
                                   for f, erows in externals.items()}},
        "non_disclosure_sensitivity": {
            "removed_claims": nd, "all_bace_claims": total,
            "supported_numerator_unchanged": supported,
            "remaining_claims": total - nd,
            "macro_rate": average("bace_excluding_non_disclosure_rate"),
            "macro_increase_pp": 100 * (average("bace_excluding_non_disclosure_rate") - native["bace"]),
            "pooled_rate": supported / (total - nd),
            "remaining_comparator_minus_bace_macro_gap_pp": {
                f: 100 * (native[f] - average("bace_excluding_non_disclosure_rate")) for f in externals},
            "limit": "Removes only BACE-unsupported DCs diagnosed as non_disclosure_statement, not all non-disclosure assertions. This changes the estimand and is not a corrected accuracy estimate."},
        "zero_candidates": {
            "claims": len(zero_rows), "all_bace_claims": total,
            "all_unsupported_claims": total - supported,
            "fraction_all_claims": len(zero_rows) / total,
            "fraction_unsupported_claims": len(zero_rows) / (total - supported),
            "by_bace_diagnosis": dict(Counter(r["label"] for r in zero_rows)),
            "cases": len({r["generation_case_id"] for r in zero_rows}),
            "hypothetical_all_zero_candidate_supported_macro_rate": average("hypothetical_all_zero_candidate_supported_rate"),
            "maximum_macro_increase_from_relabeling_only_zero_candidate_dcs_pp": 100 * (average("hypothetical_all_zero_candidate_supported_rate") - native["bace"]),
            "limit": "An arithmetic upper bound for relabeling this subset only, not an estimate or bound for all extraction/candidate errors. Nonempty candidate sets can omit decisive premises. Actual support of zero-candidate DCs was not assessed. This scenario overlaps with the non-disclosure sensitivity and must not be added to it."},
        "claim_count_diagnostics": {}, "literal_alignment": {},
        "inference": {"intervals": "Not computed", "tests": "Not performed",
                      "resampling_seed": None, "independence": "Claims are nested in disclosures and companies. No independence-based inference is made."}}
    for framework in externals:
        subsets = {}
        for name, condition in {
            "bace_count_not_greater": lambda r: r["bace_dc_count"] <= r[f"{framework}_claim_count"],
            "bace_count_equal": lambda r: r["bace_dc_count"] == r[f"{framework}_claim_count"],
            "bace_count_greater": lambda r: r["bace_dc_count"] > r[f"{framework}_claim_count"],
        }.items():
            selected = [r for r in case_diagnostics if condition(r)]
            subsets[name] = {"cases": len(selected),
                             "mean_comparator_minus_bace_gap_pp": 100 * mean(r[f"{framework}_rate"] - r["bace_native_rate"] for r in selected) if selected else None}
        results["claim_count_diagnostics"][framework] = {
            "bace_median_count": median(r["bace_dc_count"] for r in case_diagnostics),
            "comparator_median_count": median(r[f"{framework}_claim_count"] for r in case_diagnostics),
            "conditional_subsets": subsets,
            "limit": "Equal counts do not align propositions. These selected descriptive groups cannot identify a causal segmentation effect."}

    left = defaultdict(list)
    for r in claims:
        left[(r["generation_case_id"], normalize(r["dc_text"]))].append(r)
    expected_alignment = {r["framework"]: r for r in read_csv(ROOT / "BACE/analysis/outputs/figures/03/03_alignment_coverage__data.csv")}
    aligned_rows = []
    for framework, erows in externals.items():
        right = defaultdict(list)
        for r in erows:
            right[(r["generation_case_id"], normalize(r["claim_text"]))].append(r)
        pairs = []
        for key in sorted(left.keys() & right.keys()):
            if len(left[key]) != 1 or len(right[key]) != 1:
                continue
            b, e = left[key][0], right[key][0]
            pairs.append({"generation_case_id": key[0], "framework": framework,
                          "bace_dc_id": b["dc_id"], "external_claim_index": e["claim_index"],
                          "bace_dc_text": b["dc_text"], "external_claim_text": e["claim_text"],
                          "bace_label": b["label"], "bace_supported": b["label"] in SUPPORTED,
                          "external_supported": e["supported"] == "True",
                          "candidate_count": integer(b["candidate_count"])})
        joint = Counter((p["bace_supported"], p["external_supported"]) for p in pairs)
        assert len(pairs) == integer(expected_alignment[framework]["matched_pairs"])
        assert joint[(True, True)] + joint[(False, False)] == integer(expected_alignment[framework]["agreements"])
        info = {"pairs": len(pairs), "cases": len({p["generation_case_id"] for p in pairs}),
                "bace_claim_coverage": len(pairs) / total,
                "bace_ambiguous_rows_excluded": sum(len(v) for v in left.values() if len(v) > 1),
                "external_ambiguous_rows_excluded": sum(len(v) for v in right.values() if len(v) > 1),
                "both_supported": joint[(True, True)], "both_unsupported": joint[(False, False)],
                "bace_unsupported_external_supported": joint[(False, True)],
                "bace_supported_external_unsupported": joint[(True, False)],
                "bace_pooled_support_rate": sum(p["bace_supported"] for p in pairs) / len(pairs) if pairs else None,
                "external_pooled_support_rate": sum(p["external_supported"] for p in pairs) / len(pairs) if pairs else None,
                "bace_unsupported_external_supported_by_bace_label": dict(Counter(p["bace_label"] for p in pairs if not p["bace_supported"] and p["external_supported"])),
                "limit": "Casefold and whitespace-normalized unique text matching within case; no semantic alignment. Verdicts are saved automated outcomes, not human truth. Selected overlap is not representative. Same wording removes one representation difference but leaves evidence representation and judgment procedures different."}
        for key in ("bace_ambiguous_rows_excluded", "external_ambiguous_rows_excluded"):
            assert info[key] == integer(expected_alignment[framework][key.replace("_excluded", "")])
        results["literal_alignment"][framework] = info
        aligned_rows.extend(pairs)

    write_csv("case_diagnostics.csv", case_diagnostics)
    write_csv("literal_pairs.csv", aligned_rows)
    write_json("results.json", results)
    # Confirm all consumed inputs remain unchanged after calculation.
    for name, info in INPUTS.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == info["sha256"]
    write_json("provenance.json", {
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "client_analysis_date": "2026-09-30", "python": sys.version,
        "executable": sys.executable, "platform": platform.platform(),
        "command": f"{sys.executable} paper/analysis/evaluator_gap/analyze_saved_gap.py",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": INPUTS,
        "verification": "Snapshot table hashes match the saved manifest; all paired case counts and support rates reconcile with claim-level rows. Literal alignment reproduces existing pair and agreement counts. Raw histories and the full experiment are not re-audited.",
        "model_calls": 0, "experiment_changes": "None",
        "dependencies": "Python standard library in the independent writing environment",
        "output_sha256": {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
                          for name in ("results.json", "case_diagnostics.csv", "literal_pairs.csv")}})
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
