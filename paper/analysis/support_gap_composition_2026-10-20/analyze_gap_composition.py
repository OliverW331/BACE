"""Describe saved support disagreements; no models, semantic matching or new labels."""
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
from statistics import mean

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "BACE/analysis/outputs/snapshot"
SUPPORTED = {"direct", "inferred"}
FRAMEWORKS = ("ragas", "ragchecker")
CATEGORIES = ("factual_boundary_distortion", "evidence_conflation",
              "inferential_inflation", "unsupported_novelty",
              "non_disclosure_statement", "contradiction")
INPUTS = {}
OUTPUTS = []


def read(path):
    data = path.read_bytes()
    INPUTS[str(path.relative_to(ROOT))] = {
        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    return data


def table(path):
    return list(csv.DictReader(io.StringIO(read(path).decode())))


def save_json(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False,
                                     allow_nan=False) + "\n")
    OUTPUTS.append(name)


def save_csv(name, rows):
    with (OUT / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    OUTPUTS.append(name)


def norm(text, period=True):
    text = " ".join(text.casefold().split())
    return text.removesuffix(".") if period else text


def index(rows, text_key, period=True):
    result = defaultdict(list)
    for row in rows:
        result[row["generation_case_id"], norm(row[text_key], period)].append(row)
    return result


def pair_keys(left, right):
    return sorted(k for k in left.keys() & right.keys()
                  if len(left[k]) == len(right[k]) == 1)


def pct(n, d):
    return 100 * n / d if d else None


def main():
    manifest = json.loads(read(SNAPSHOT / "manifest.json"))
    ledger = json.loads(read(SNAPSHOT / "sources.json"))
    tables = {n: table(SNAPSHOT / f"{n}.csv")
              for n in ("metrics", "claims", "external_claims")}
    for name in tables:
        assert INPUTS[str((SNAPSHOT / f"{name}.csv").relative_to(ROOT))]["sha256"] == manifest["tables"][name]
    execution = json.loads(read(ROOT / "BACE/results/main_v1/execution_status.json"))
    assert not execution.get("active_cases")
    metrics = {r["generation_case_id"]: r for r in tables["metrics"]
               if all(r[f"{f}_complete"] == "True" for f in ("bace", *FRAMEWORKS))}
    assert set(metrics) == set(execution["completed_case_ids"])
    claims = [r for r in tables["claims"] if r["generation_case_id"] in metrics]
    ext = {f: [r for r in tables["external_claims"]
               if r["framework"] == f and r["generation_case_id"] in metrics]
           for f in FRAMEWORKS}
    counts = defaultdict(Counter)
    for r in claims:
        counts[r["generation_case_id"]]["bace_total"] += 1
        counts[r["generation_case_id"]]["bace_supported"] += r["label"] in SUPPORTED
        counts[r["generation_case_id"]][r["label"]] += 1
        assert (int(r["support_set_count"]) > 0) == (r["label"] in SUPPORTED)
    for f, rows in ext.items():
        assert len({(r["generation_case_id"], r["claim_index"]) for r in rows}) == len(rows)
        for r in rows:
            assert r["supported"] in {"True", "False"}
            counts[r["generation_case_id"]][f + "_total"] += 1
            counts[r["generation_case_id"]][f + "_supported"] += r["supported"] == "True"
    for cid, m in metrics.items():
        c = counts[cid]
        for f in ("bace", *FRAMEWORKS):
            assert c[f + "_total"] == int(float(m["bace_dc_count" if f == "bace" else f + "_claim_count"]))
            s = (float(m["bace_supported_direct"]) + float(m["bace_supported_inferred"])) if f == "bace" else float(m[f + "_supported"])
            assert c[f + "_supported"] == s
            rate = float(m["bace_support_rate_all_dc" if f == "bace" else f + "_faithfulness"])
            assert math.isclose(c[f + "_supported"] / c[f + "_total"], rate, abs_tol=1e-12)
        for cat in CATEGORIES:
            assert c[cat] == int(float(m["bace_" + cat]))
    native = {f: 100 * mean(c[f + "_supported"] / c[f + "_total"] for c in counts.values())
              for f in ("bace", *FRAMEWORKS)}
    native_rows = [{"framework": f, "disclosures": len(metrics),
                    "native_claims": sum(c[f + "_total"] for c in counts.values()),
                    "native_supported": sum(c[f + "_supported"] for c in counts.values()),
                    "disclosure_macro_support_percent": native[f],
                    "native_macro_gap_vs_bace_pp": native[f] - native["bace"]}
                   for f in ("bace", *FRAMEWORKS)]
    save_csv("native_rates.csv", native_rows)
    fullcat = Counter(r["label"] for r in claims if r["label"] not in SUPPORTED)
    save_csv("all_bace_unsupported_categories.csv", [
        {"category": cat, "count": fullcat[cat], "all_bace_unsupported": sum(fullcat.values()),
         "share_percent": pct(fullcat[cat], sum(fullcat.values()))} for cat in CATEGORIES])

    prior = table(ROOT / "paper/analysis/evaluator_gap/literal_pairs.csv")
    prior_prov = json.loads(read(ROOT / "paper/analysis/evaluator_gap/provenance.json"))
    assert INPUTS["paper/analysis/evaluator_gap/literal_pairs.csv"]["sha256"] == prior_prov["output_sha256"]["literal_pairs.csv"]
    left = index(claims, "dc_text")
    strict_left = index(claims, "dc_text", False)
    all_pairs, coverage, joints, composition, accounting = [], [], [], [], []
    results = {}
    for f in FRAMEWORKS:
        right = index(ext[f], "claim_text")
        strict_right = index(ext[f], "claim_text", False)
        keys = pair_keys(left, right)
        strict_keys = pair_keys(strict_left, strict_right)
        pairs = []
        for k in keys:
            b, e, m = left[k][0], right[k][0], metrics[k[0]]
            pairs.append({"framework": f, "generation_case_id": k[0],
                "company_id": m["company_id"], "company_name": m["company_name"],
                "year": m["year"], "task": m["task"], "bace_dc_id": b["dc_id"],
                "external_claim_index": e["claim_index"], "bace_dc_text": b["dc_text"],
                "external_claim_text": e["claim_text"], "bace_label": b["label"],
                "bace_supported": b["label"] in SUPPORTED,
                "external_supported": e["supported"] == "True",
                "candidate_count": int(b["candidate_count"]),
                "strict_text_equal": norm(b["dc_text"], False) == norm(e["claim_text"], False)})
        if f == "ragas":
            identifying = lambda p: (p["generation_case_id"], p["bace_dc_id"], str(p["external_claim_index"]))
            assert {identifying(p) for p in pairs} == {identifying(p) for p in prior if p["framework"] == f}
        all_pairs.extend(pairs)
        joint = Counter((p["bace_supported"], p["external_supported"]) for p in pairs)
        positive = [p for p in pairs if not p["bace_supported"] and p["external_supported"]]
        reverse = [p for p in pairs if p["bace_supported"] and not p["external_supported"]]
        poscat = Counter(p["bace_label"] for p in positive)
        matchedcat = Counter(p["bace_label"] for p in pairs if not p["bace_supported"])
        assert sum(poscat.values()) == len(positive)
        n, nd = len(pairs), len({p["generation_case_id"] for p in pairs})
        ambiguous = [k for k in left.keys() & right.keys() if len(left[k]) != 1 or len(right[k]) != 1]
        coverage.append({"framework": f, "all_bace_claims": len(claims),
            "all_external_claims": len(ext[f]), "strict_unique_pairs": len(strict_keys),
            "period_normalized_unique_pairs": n, "matched_disclosures": nd,
            "matched_companies": len({p["company_id"] for p in pairs}),
            "bace_claim_coverage_percent": pct(n, len(claims)),
            "external_claim_coverage_percent": pct(n, len(ext[f])),
            "bace_rows_without_any_normalized_key_overlap": sum(len(v) for k, v in left.items() if k not in right),
            "bace_rows_excluded_at_ambiguous_overlap": sum(len(left[k]) for k in ambiguous),
            "external_rows_without_any_normalized_key_overlap": sum(len(v) for k, v in right.items() if k not in left),
            "external_rows_excluded_at_ambiguous_overlap": sum(len(right[k]) for k in ambiguous),
            "ambiguous_overlapping_keys": len(ambiguous)})
        cv = coverage[-1]
        assert n + cv["bace_rows_without_any_normalized_key_overlap"] + cv["bace_rows_excluded_at_ambiguous_overlap"] == len(claims)
        assert n + cv["external_rows_without_any_normalized_key_overlap"] + cv["external_rows_excluded_at_ambiguous_overlap"] == len(ext[f])
        for b in (True, False):
            for e in (True, False):
                joints.append({"framework": f, "bace_supported": b,
                               "external_supported": e, "pairs": joint[b, e],
                               "share_of_matched_pairs_percent": pct(joint[b, e], n)})
        casepairs = defaultdict(list)
        for p in pairs:
            casepairs[p["generation_case_id"]].append(p)
        for cat in CATEGORIES:
            composition.append({"framework": f, "category": cat,
                "positive_disagreements": poscat[cat], "all_positive_disagreements": len(positive),
                "positive_composition_percent": pct(poscat[cat], len(positive)),
                "matched_bace_unsupported_in_category": matchedcat[cat],
                "external_acceptance_in_matched_category_percent": pct(poscat[cat], matchedcat[cat]),
                "all_bace_unsupported_in_category": fullcat[cat],
                "category_matching_coverage_percent": pct(matchedcat[cat], fullcat[cat]),
                "positive_disagreements_with_zero_candidates": sum(p["bace_label"] == cat and p["candidate_count"] == 0 for p in positive)})
            accounting.append({"framework": f, "component": cat,
                "signed_pairs": poscat[cat], "matched_pairs_denominator": n,
                "pooled_gap_contribution_pp": pct(poscat[cat], n),
                "matched_disclosure_macro_contribution_pp": 100 * mean(
                    sum(not p["bace_supported"] and p["external_supported"] and p["bace_label"] == cat for p in ps) / len(ps)
                    for ps in casepairs.values())})
        reverse_macro = -100 * mean(sum(p["bace_supported"] and not p["external_supported"] for p in ps) / len(ps) for ps in casepairs.values())
        accounting.append({"framework": f, "component": "reverse_disagreement_correction",
            "signed_pairs": -len(reverse), "matched_pairs_denominator": n,
            "pooled_gap_contribution_pp": -pct(len(reverse), n),
            "matched_disclosure_macro_contribution_pp": reverse_macro})
        pooled_b = pct(sum(p["bace_supported"] for p in pairs), n)
        pooled_e = pct(sum(p["external_supported"] for p in pairs), n)
        macro_gap = 100 * mean(sum(int(p["external_supported"]) - int(p["bace_supported"]) for p in ps) / len(ps) for ps in casepairs.values())
        assert math.isclose(sum(r["pooled_gap_contribution_pp"] for r in accounting if r["framework"] == f), pooled_e - pooled_b, abs_tol=1e-10)
        assert math.isclose(sum(r["matched_disclosure_macro_contribution_pp"] for r in accounting if r["framework"] == f), macro_gap, abs_tol=1e-10)
        results[f] = {**cv, "both_supported": joint[True, True],
            "both_unsupported": joint[False, False], "positive_disagreements": len(positive),
            "reverse_disagreements": len(reverse), "matched_bace_unsupported": sum(matchedcat.values()),
            "external_acceptance_among_matched_bace_unsupported_percent": pct(len(positive), sum(matchedcat.values())),
            "matched_pooled_bace_support_percent": pooled_b,
            "matched_pooled_external_support_percent": pooled_e,
            "matched_pooled_gap_pp": pooled_e - pooled_b,
            "matched_disclosure_macro_gap_pp": macro_gap,
            "positive_disagreements_with_zero_candidates": sum(p["candidate_count"] == 0 for p in positive)}

    # Check every retained comparator target/verdict against the original snapshot source.
    audit = []
    grouped = defaultdict(list)
    for p in all_pairs:
        grouped[p["framework"], p["generation_case_id"]].append(p)
    for (f, cid), ps in sorted(grouped.items()):
        path = ROOT / "BACE/results/main_v1/cases" / cid / "evaluation" / f / "results.jsonl"
        rel = str(path.relative_to(ROOT))
        data = read(path)
        assert INPUTS[rel]["sha256"] == ledger[rel]
        record = json.loads(data.decode().splitlines()[-1])
        raw = {str(c["claim_index"]): c for c in record["claims"]}
        for p in ps:
            c = raw[p["external_claim_index"]]
            text = " ".join(c["claim"]) if isinstance(c["claim"], list) else c["claim"]
            assert text == p["external_claim_text"]
            assert c["supported"] == p["external_supported"]
        audit.append({"framework": f, "generation_case_id": cid,
                      "source": rel, "sha256": ledger[rel], "verified_pairs": len(ps)})
    save_csv("matched_pairs.csv", all_pairs)
    save_csv("matching_coverage.csv", coverage)
    save_csv("joint_judgments.csv", joints)
    save_csv("category_composition.csv", composition)
    save_csv("matched_gap_accounting.csv", accounting)
    save_csv("raw_comparator_audit.csv", audit)

    # A source-relative illustration, kept separate from surface-matched frequency estimates.
    sca = json.loads(read(ROOT / "paper/analysis/disagreement_cases/sca_incidents_workers.json"))
    raw_sources = {}
    for name, relative in sca["source_paths"].items():
        content = read(ROOT / relative)
        if relative in ledger:
            assert INPUTS[relative]["sha256"] == ledger[relative]
        raw_sources[name] = [json.loads(line) for line in content.decode().splitlines() if line.strip()]
    for card in sca["key_evidence_cards"]:
        assert card["retrieval_text"] in json.dumps(raw_sources["generation_input"], ensure_ascii=False)
    for f in FRAMEWORKS:
        c = next(c for c in raw_sources[f][-1]["claims"] if c["claim_index"] == sca["selection"][f + "_index"])
        assert c["supported"] is True
    dc_id = sca["selection"]["dc_id"]
    assert next(r for r in raw_sources["dc"] if r["dc_id"] == dc_id) == sca["disclosure_claim"]
    assert next(r for r in raw_sources["support"] if r["dc_claim_id"] == dc_id) == sca["bace_support"]
    assert next(r for r in raw_sources["diagnosis"] if r["dc_claim_id"] == dc_id) == sca["bace_diagnosis"]
    save_json("sca_source_example.json", {
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection": sca["selection"], "source_paths": sca["source_paths"],
        "disclosure_claim": sca["disclosure_claim"]["dc_text"],
        "bace_support": sca["bace_support"], "bace_diagnosis": sca["bace_diagnosis"],
        "key_evidence_cards": sca["key_evidence_cards"],
        "native_claims": sca["native_claims"],
        "interpretation": "The cited indicator counts incidents involving dismissal/discipline, not distinct workers. Five incidents do not establish five workers. Both comparators accepted worker-count assertions; BACE rejected its corresponding assertion. This demonstrates a source-relative unit mismatch in the inspected record, not external truth or an adjudicated error-rate estimate.",
        "included_in_surface_matched_counts": {f: any(p["framework"] == f and p["generation_case_id"] == sca["selection"]["case_id"] and p["bace_dc_id"] == sca["selection"]["dc_id"] for p in all_pairs) for f in FRAMEWORKS}})
    examples = json.loads(read(ROOT / "paper/analysis/evaluator_gap/literal_examples.json"))
    hop = next(e for e in examples["examples"] if e["pair"]["bace_dc_text"] == "Social reporting covers HOP!.")
    hop_sources = {}
    for relative, expected in examples["source_hashes"].items():
        if hop["pair"]["generation_case_id"] in relative:
            data = read(ROOT / relative)
            assert INPUTS[relative]["sha256"] == expected
            if relative in ledger:
                assert expected == ledger[relative]
            hop_sources[relative] = expected
    assert any(p["framework"] == "ragas" and p["generation_case_id"] == hop["pair"]["generation_case_id"] and p["bace_dc_id"] == hop["pair"]["bace_dc_id"] for p in all_pairs)
    assert hop["pair"]["candidate_count"] == "0" and not hop["candidate_ecs"]
    assert any("Social: Air France in France, HOP!" in c["retrieval_text"] for c in hop["all_prompt_evidence"])
    save_json("hop_candidate_example.json", {
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "example": hop, "verified_original_sources": hop_sources,
        "interpretation": "A social-reporting footnote in the supplied 2018 report includes HOP!, while BACE has no candidate EC. This exposes an evidence-path difference; it does not independently establish the full assertion's scope or applicability in the 2019 generated disclosure."})
    save_json("results.json", {
        "status": "COMPUTED_VERIFIED", "analysis_date": "2026-10-20",
        "design": "Post-experiment descriptive analysis of saved automated outcomes; no new model calls or human validation.",
        "planned_disclosures": len(tables["metrics"]), "complete_disclosures": len(metrics),
        "companies": len({m["company_id"] for m in metrics.values()}),
        "excluded_case_ids": sorted(set(r["generation_case_id"] for r in tables["metrics"]) - set(metrics)),
        "native_disclosure_macro_support_percent": native,
        "native_comparator_minus_bace_macro_gap_pp": {f: native[f] - native["bace"] for f in FRAMEWORKS},
        "all_bace_claims": len(claims), "all_bace_unsupported": sum(fullcat.values()),
        "matching_rule": "Same disclosure, casefold, collapse whitespace, remove one terminal period, unique on each side. All other text retained. No fuzzy or semantic matching.",
        "matched_subsets": results, "verified_original_comparator_files": len(audit),
        "verified_original_comparator_pairs": sum(a["verified_pairs"] for a in audit),
        "limits": ["Native scores have different claim inventories; native gaps are not false-negative rates.",
                   "Category shares describe only positive disagreements within selected surface-matched subsets, using BACE's automated diagnoses.",
                   "Reverse disagreements are retained in paired-gap accounting. Category counts do not decompose the complete native macro gap.",
                   "Same target wording leaves evidence representation, contextual interpretation and judgment procedures different.",
                   "The two comparator subsets differ and are not representative; their percentages do not rank accuracy.",
                   "Unmatched claims do not establish extraction omissions. No confidence intervals or hypothesis tests were computed."]})
    save_json("provenance.json", {
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": "python paper/analysis/support_gap_composition_2026-10-20/analyze_gap_composition.py",
        "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": INPUTS, "model_calls": 0, "experiment_changes": [],
        "verification": "Snapshot table hashes, all native counts and rates, prior RAGAS pair membership, unique matching, both gap identities, original comparator text/verdict for every retained pair, selected source example.",
        "output_sha256": {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() for name in OUTPUTS}})
    print(json.dumps({"native_rates": native_rows, "matched_subsets": results,
                      "categories": composition}, indent=2))


if __name__ == "__main__":
    main()
