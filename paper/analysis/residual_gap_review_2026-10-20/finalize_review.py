"""Validate source excerpts and publish descriptive results from recorded AI review."""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
record = json.loads((OUT / "review_assessments.json").read_text())
selection_prov = json.loads((OUT / "selection_provenance.json").read_text())
boundary_path = ROOT / "paper/analysis/support_gap_composition_2026-10-20/boundary_sensitivity/results.json"
boundary_bytes = boundary_path.read_bytes()
boundary_results = json.loads(boundary_bytes)
native_residual = boundary_results["comparator_minus_bace_gap_pp"]["bace_excluding_boundary"]
assessments = record["assessments"]
assert {a["review_id"] for a in assessments} == {f"R{i:02d}" for i in range(1, 19)}
for name, expected in selection_prov["output_sha256"].items():
    assert hashlib.sha256((OUT / name).read_bytes()).hexdigest() == expected, name
(OUT / "reviews").mkdir(exist_ok=True)
ledger, linked_evidence, ec_audit = [], [], []
all_counts, disagreement_counts, control_counts = Counter(), Counter(), Counter()
known_findings = {}
for a in assessments:
    rid = a["review_id"]
    p = json.loads((OUT / "packets" / f"{rid}.json").read_text())
    s = p["selection"]
    cards = {c["prompt_label"]: c for c in p["evidence_cards"]}
    v = a["source_verdict"]
    assert v in {"SUPPORTED", "UNSUPPORTED", "UNRESOLVED"}
    b, e = s["bace_supported"] == "True", s["external_supported"] == "True"
    if v == "UNRESOLVED":
        outcome = "Unresolved"
    else:
        truth = v == "SUPPORTED"
        if b == e == truth:
            outcome = "Both supported by review"
        elif b == truth:
            outcome = "BACE better supported"
        elif e == truth:
            outcome = "Comparator better supported"
        else:
            outcome = "Neither supported by review"
    all_counts[outcome] += 1
    (disagreement_counts if b != e else control_counts)[outcome] += 1
    ledger.append({"review_id": rid, "framework": s["framework"],
        "company": s["company_name"], "year": s["year"], "task": s["task"],
        "selection_stratum": s["selection_stratum"], "generation_case_id": s["generation_case_id"],
        "bace_dc_id": s["bace_dc_id"], "external_claim_index": s["external_claim_index"],
        "target": s["bace_dc_text"], "bace_supported": b, "comparator_supported": e,
        "source_verdict": v, "review_outcome": outcome,
        "evidence_labels": "; ".join(dict.fromkeys(q["label"] for q in a["evidence"])),
        "reason": a["reason"], "pipeline_finding": a["pipeline_finding"],
        "unresolved_or_policy_limit": a["resolution"], "reviewer": record["reviewer"]})
    review_path = OUT / "reviews" / f"{rid}.md"
    lines = [f"# {rid}: {s['company_name']} ({s['year']}, {s['task']})", "",
             "Review status: completed AI internal source review; not human validation.", "",
             f"**Target:** {s['bace_dc_text']}", "",
             f"**Saved decisions:** BACE = {'supported' if b else 'unsupported'}; {s['framework']} = {'supported' if e else 'unsupported'}.", "",
             f"**Source verdict:** {v}. **Assessment:** {outcome}.", "", a["reason"], "",
             "## Decisive source passages", ""]
    for q in a["evidence"]:
        c = cards[q["label"]]
        assert q["quote"] in c["retrieval_text"], (rid, q)
        linked_evidence.append({"review_id": rid, "prompt_label": q["label"],
            "evidence_id": c["evidence_id"], "source_year": c["source_year"],
            "source_label": c["source_label"], "source_file": c["source_file"],
            "page_start": c.get("page_start"), "page_end": c.get("page_end"),
            "quote": q["quote"], "retrieval_text_sha256": hashlib.sha256(c["retrieval_text"].encode()).hexdigest(),
            "source_version": "Frozen main_v1 prompt-visible evidence", "access_date": "2026-10-20"})
        lines += [f"**{q['label']}** — {c['source_label']}; source year {c['source_year']}; page {c.get('page_start') or 'CSV metric'}.",
                  "", "> " + q["quote"], "", f"Evidence ID: `{c['evidence_id']}`", ""]
    for label in a.get("anchor_cards_for_ec_audit", []):
        c = cards[label]
        linked = [r for r in p["all_ecs"] if c["evidence_id"] in r["evidence_card_ids"]]
        assert not linked, (rid, label, "Unexpected final EC retained")
        ec_audit.append({"review_id": rid, "prompt_label": label, "evidence_id": c["evidence_id"],
                         "linked_final_ec_count": len(linked), "target_candidate_count": len(p["candidate_ecs"]),
                         "interpretation": "Verified absence from final EC provenance; does not alone establish a target false rejection."})
    lines += ["## Pipeline finding", "", a["pipeline_finding"], "", "## Interpretation limit and resolution", "", a["resolution"], "",
              "## Complete audit material", "",
              f"- [All supplied cards and complete generated disclosure]({OUT / 'packets' / (rid + '_sources.md')})",
              f"- [Original saved judgments and candidate ECs]({OUT / 'packets' / (rid + '_judgments.md')})",
              f"- [Full structured packet, including all final ECs]({OUT / 'packets' / (rid + '.json')})", ""]
    review_path.write_text("\n".join(lines))
    if rid == "R15":
        high = float(cards["Evidence 22"]["value_text"])
        other = float(cards["Evidence 24"]["value_text"])
        assert high == 3466400000 and other == 631400000
        known_findings["R15_high_impact_revenue_share_of_two_categories_percent"] = 100 * high / (high + other)


def save_csv(name, rows):
    with (OUT / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


save_csv("review_ledger.csv", ledger)
save_csv("source_passages.csv", linked_evidence)
save_csv("missing_ec_anchor_audit.csv", ec_audit)
source_frame = selection_prov["positive_disagreement_frame_excluding_boundary"]
frame_rows = []
for f, counts in source_frame.items():
    for cat, n in counts.items():
        frame_rows.append({"framework": f, "bace_diagnosis": cat, "positive_disagreements": n,
                           "all_non_boundary_positive_disagreements": sum(counts.values()),
                           "share_percent": 100 * n / sum(counts.values())})
save_csv("remaining_disagreement_composition.csv", frame_rows)
summary = {"completed_at_utc": datetime.now(timezone.utc).isoformat(),
    "review_type": record["review_type"], "reviewer": record["reviewer"],
    "reviewed_pairs": len(ledger), "reviewed_disagreements": sum(disagreement_counts.values()),
    "reviewed_agreement_controls": sum(control_counts.values()),
    "disagreement_outcomes": disagreement_counts, "control_outcomes": control_counts,
    "all_outcomes": all_counts,
    "positive_disagreement_outcomes": dict(Counter(r["review_outcome"] for r in ledger if not r["bace_supported"] and r["comparator_supported"])),
    "reverse_disagreement_outcomes": dict(Counter(r["review_outcome"] for r in ledger if r["bace_supported"] and not r["comparator_supported"])),
    "cases_with_verified_missing_final_ec_anchor": sorted({r["review_id"] for r in ec_audit}),
    "missing_anchor_cards": len(ec_audit), "verified_quote_occurrences": len(linked_evidence),
    "auxiliary_calculations": known_findings,
    "population_accuracy_estimate": "Not calculated: selected surface matches, stratified small illustrative review, AI judgments and unresolved cases.",
    "native_gap_decomposition": "Not identified from this review.",
    "external_model_calls": 0, "experiment_changes": []}
(OUT / "results.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
lines = ["# Who is better supported in the remaining disagreements?", "", "20 October 2026.", "",
         "**The reviewed disagreements run in both directions. Some BACE rejections miss accurate descriptions of the supplied input; some comparator decisions accept an additional unsupported proposition or reject a supported inference. Many remaining cases depend on time, scope or the meaning of a verb.**", "",
         "This is a completed, non-blinded AI internal review of 18 selected pairs: 12 positive disagreements outside BACE's factual-boundary category, four reverse disagreements, and two supported-agreement controls. Complete generated disclosures and all supplied cards were read. The sample was fixed by the rule in REVIEW_PLAN.md before reading its source evidence and judgment reasons. It is not independent human validation or a representative accuracy study.", "",
         "## Findings that can be discussed now", "",
         "1. **BACE can reject a correct statement about missing information.** R11 says that the available evidence does not contain Evonik's 2023 lost-time injury-rate result. The cards contain the 2022 result (0.25) and a 2023 target (no more than 0.26), but not the 2023 result. RAGAS accepts it. The full closed input supports that statement; BACE's own diagnosis even repeats the absence. R10 is a similar input-limited statement about SME-supplier arrangements. Neither finding establishes company-wide non-disclosure.", "",
         "2. **A comparator can accept a proposition beyond the metric supplied.** R05 adds that Intesa Sanpaolo 'monitored' a Scope 1 target. The evidence supplies a 2019 target and a reduction value, not the monitoring activity. Under the stated entailment rule BACE's rejection is better supported. This depends on retaining the distinction between reporting a metric and establishing an organizational activity.", "",
         "3. **BACE can also accept an unsupported inference.** In reverse disagreement R13, SES's assessment is performed in a legal context and according to EN 16247. The extracted target attributes the relation 'reflects the legal framework' to the standard itself. RAGAS rejects that added relation; BACE accepts it. The review favors RAGAS under the necessary-inference rule. Modifier attachment during target extraction also needs checking.", "",
         "4. **RAGChecker can reject a supported claim.** R16 says changing weather can affect food production systems. The supplied report explicitly says changing weather influences crop yields, and other cards connect it to agriculture and food security. BACE accepts; RAGChecker marks every card Neutral. R15 is another supported reverse disagreement under the ordinary business meaning of 'material', using current and prior high-impact revenues. It does not establish a formal regulatory materiality classification.", "",
         "5. **Some apparent novelty is missing from the final EC inventory, not the original input.** In R04, R07, R08 and R09, cards containing on-time payment, investment-property measures, the ASML Speak Up supplier channel or employee development reviews yield no final ECs. This is verified from EC provenance. Three targets have zero candidates; R04 gets only a payment-duration metric. Their ultimate support remains unresolved because historical applicability, missing table headings or action status still matter. The audit identifies upstream information loss, not four proven BACE false rejections.", "",
         "6. **Excluding one diagnostic label does not remove all boundary issues.** R02 is labeled evidence_conflation but its rationale is a historical-to-2021 transfer. R12 is labeled non_disclosure_statement but concerns 2022 evidence used in a 2023 disclosure. Agreement control R18 is also supported by both evaluators from earlier-year sources. A uniform continuity rule must apply to agreements as well as disagreements.", "",
         "## Counts within this review only", "",
         "| Reviewed set | BACE better supported | Comparator better supported | Unresolved | Both supported by review |",
         "|---|---:|---:|---:|---:|"]
for name, counts in [("Positive disagreements (12)", summary["positive_disagreement_outcomes"]),
                     ("Reverse disagreements (4)", summary["reverse_disagreement_outcomes"]),
                     ("Agreement controls (2)", control_counts)]:
    lines.append(f"| {name} | {counts.get('BACE better supported', 0)} | {counts.get('Comparator better supported', 0)} | {counts.get('Unresolved', 0)} | {counts.get('Both supported by review', 0)} |")
lines += ["", "These counts reflect the explicit review rules and interpretation limits in each case. They do not estimate how much of the native residual gap is attributable to either method. In particular, uncertain cases were retained rather than forced into a winner category.", "",
          "## Every reviewed pair", "", "| Case | Comparator | Company/year | Source verdict | Review assessment |", "|---|---|---|---|---|"]
for r in ledger:
    lines.append(f"| [{r['review_id']}]({OUT / 'reviews' / (r['review_id'] + '.md')}) | {r['framework']} | {r['company']} / {r['year']} | {r['source_verdict']} | {r['review_outcome']} |")
lines += ["", "## What remains necessary for a full answer", "",
          f"The non-boundary positive-disagreement frame contains {sum(source_frame['ragas'].values())} RAGAS pairs and {sum(source_frame['ragchecker'].values())} RAGChecker pairs; these are separate, selected matching subsets. Their composition is saved in remaining_disagreement_composition.csv. Most of the main experiment's targets remain outside these surface matches, and the native BACE sensitivity adjusted only BACE's denominator. This review therefore cannot apportion the complete residual {native_residual['ragas']:.2f}/{native_residual['ragchecker']:.2f} percentage-point gaps.", "",
          "Before estimating evaluator error rates, specify three support-policy decisions: whether unqualified historical practices may carry into the reporting year; how input-limited absence is verified; and which verbs/characterizations require separate evidence (for example monitored, delivered, allocated and material). Preserve or restore list and paragraph relations before assessing EC candidate recall. Then perform source-based human adjudication with both disagreement directions and agreement controls, keeping unresolved targets and extraction defects visible. No such additional human study or new model experiment has been performed here.", "",
          "## Reproducibility", "",
          "prepare_review.py fixes the sample and checks raw artifacts against the saved source ledger. review_assessments.json contains the AI judgments. finalize_review.py checks every quoted passage, audits missing EC provenance, computes the review counts and writes the per-case reports. The full packets retain original target IDs, all evidence cards, ECs, candidates, support sets and native comparator records. The scripts reproduce packet extraction and arithmetic; they do not constitute an independent rerun of the AI review.", ""]
(OUT / "REPORT.md").write_text("\n".join(lines))
output_names = ["review_ledger.csv", "source_passages.csv", "missing_ec_anchor_audit.csv",
                "remaining_disagreement_composition.csv", "results.json", "REPORT.md"]
(OUT / "review_provenance.json").write_text(json.dumps({
    "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "review_assessments_sha256": hashlib.sha256((OUT / "review_assessments.json").read_bytes()).hexdigest(),
    "selection_provenance_sha256": hashlib.sha256((OUT / "selection_provenance.json").read_bytes()).hexdigest(),
    "boundary_sensitivity_input": {"path": str(boundary_path.relative_to(ROOT)), "sha256": hashlib.sha256(boundary_bytes).hexdigest()},
    "verification": "All packet hashes, 18 unique review IDs, exact supplied-card quotes, missing final-EC provenance and review outcome arithmetic.",
    "command": "python paper/analysis/residual_gap_review_2026-10-20/finalize_review.py",
    "output_sha256": {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() for name in output_names},
    "per_case_report_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((OUT / "reviews").glob("*.md"))}
}, indent=2) + "\n")
print(json.dumps(summary, indent=2))
