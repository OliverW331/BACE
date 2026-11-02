"""Verify Figure 3 counts, fixed cases and original report passages.

Run with the independent writing Python (PyMuPDF). All experiment inputs are
read-only; only new figure preparation artifacts are written under paper/.
"""
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import pymupdf as fitz

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
INPUTS = {}
LABELS = ["non_disclosure_statement", "contradiction", "evidence_conflation",
          "factual_boundary_distortion", "inferential_inflation", "unsupported_novelty"]
NAMES = ["Non-disclosure statement", "Contradiction", "Evidence conflation",
         "Factual boundary distortion", "Inferential inflation", "Unsupported novelty"]
CASE_SPECS = {
    "wartsila": ("factual_boundary_distortion", "dc_0a68745f651e5169efaa2c0409458081", "ec_930a1671acf6ad70bbe3d74a620a9e26", 20260924),
    "asml": ("contradiction", "dc_7448bba670219eca599b5121b2de5985", "ec_5bbf4eea25fd1efe534d87d723f1cd46", 20260922)
}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(2**20):
            h.update(block)
    return h.hexdigest()


def register(relative):
    path = ROOT/relative
    INPUTS[relative] = {"sha256": sha(path), "bytes": path.stat().st_size}
    return path


def read_json(relative):
    return json.loads(register(relative).read_text())


def read_csv(relative):
    with register(relative).open(newline="") as stream:
        return list(csv.DictReader(stream))


def save_json(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n")


def save_csv(name, rows):
    with (OUT/name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = read_csv("BACE/analysis/outputs/snapshot/metrics.csv")
    complete = [r for r in rows if r["bace_complete"].lower() == "true"]
    assert len(rows) == 1800 and len(complete) == 1798
    execution = read_json("BACE/results/main_v1/execution_status.json")
    assert {r["generation_case_id"] for r in complete} == set(execution["completed_case_ids"])
    assert len({r["company_id"] for r in complete}) == 30
    unsupported = sum(int(float(r["bace_unsupported"])) for r in complete)
    assert unsupported == 42646
    for r in complete:
        assert sum(int(float(r["bace_"+label])) for label in LABELS) == int(float(r["bace_unsupported"]))
    saved = read_csv("BACE/analysis/outputs/figures/02/02_label_composition__data.csv")
    assert [r["label"] for r in saved] == LABELS
    composition = []
    for label, title, row in zip(LABELS, NAMES, saved):
        count = sum(int(float(r["bace_"+label])) for r in complete)
        percent = 100*count/unsupported
        assert count == int(row["count"]) and abs(percent-float(row["percent_unsupported"])) < 1e-10
        composition.append(dict(label=label, display_label=title, count=count, denominator=unsupported,
                                percent=percent, status="COMPUTED_VERIFIED", source="BACE/analysis/outputs/snapshot/metrics.csv",
                                locator="bace_complete=True; bace_"+label, aggregation="Sum claim counts across completed cases; divide by all unsupported DCs"))
    numbers = read_json("paper/analysis/results_draft/verified_numbers.json")["diagnoses"]
    assert numbers["counts"] == {r["label"]:r["count"] for r in composition}
    combined = sum(r["count"] for r in composition if r["label"] in ["factual_boundary_distortion", "evidence_conflation"])
    assert combined == numbers["combined"] == 31335
    prompt = register("BACE/config/evaluation/prompts/generation_claim_unsupported_diagnosis_prompt_v1.txt").read_text()
    assert [prompt.index(f"{i}. `{label}`") for i,label in enumerate(LABELS,1)] == sorted(prompt.index(f"{i}. `{label}`") for i,label in enumerate(LABELS,1))
    assert "return the first applicable label" in prompt
    save_csv("diagnosis_composition.csv", composition)
    facts = dict(planned=1800, completed=1798, companies=30, incomplete=2,
                 unsupported_dc=unsupported, combined_count=combined, combined_percent=100*combined/unsupported,
                 status="COMPUTED_VERIFIED", aggregation="Pooled unsupported claims, one ordered diagnosis per claim; all six categories retained",
                 uncertainty="Descriptive counts and shares; no confidence interval or hypothesis test", counts={r["label"]:r["count"] for r in composition})
    save_json("verified_facts.json", facts)

    selected_records = {r["label"]:r for r in read_json("paper/analysis/storyline/example_candidates.json")}
    cases, text_ledger = {}, []
    raw_map = {"input":"inputs/generation_cases.jsonl", "response":"generation/generated_disclosures.jsonl",
               "dc":"bace/dedup/dc_claims.jsonl", "ec":"bace/dedup/ec_claims.jsonl",
               "support":"bace/support/dc_support_sets.jsonl", "diagnosis":"bace/diagnosis/dc_unsupported_diagnoses.jsonl",
               "candidates":"bace/candidates/dc_candidate_ecs.jsonl"}
    for name, (label, dc_id, ec_id, seed) in CASE_SPECS.items():
        source = f"BACE/analysis/outputs/examples/02_{label}.json"
        export = read_json(source)
        material, selection = export["material"], export["selection"]
        case_id = material["input"]["generation_case_id"]
        assert selection["dc_id"] == dc_id and selection["seed"] == seed
        assert selection == selected_records[label]["selection"]
        base = f"BACE/results/main_v1/cases/{case_id}/"
        for key, suffix in raw_map.items():
            raw = [json.loads(line) for line in register(base+suffix).read_text().splitlines() if line.strip()]
            assert material[key] == (raw[0] if key in ["input","response"] else raw), (name,key)
        dc = next(r for r in material["dc"] if r["dc_id"] == dc_id)
        diagnosis = next(r for r in material["diagnosis"] if r["dc_claim_id"] == dc_id)
        support = next(r for r in material["support"] if r["dc_claim_id"] == dc_id)
        candidate_ids = next(r["candidate_ec_ids"] for r in material["candidates"] if r["dc_claim_id"] == dc_id)
        assert len(set(candidate_ids)) == len(candidate_ids)
        ec_map = {r["ec_id"]:r for r in material["ec"]}
        candidates = [ec_map[cid] for cid in candidate_ids]
        assert ec_id in candidate_ids and diagnosis["unsupported_label"] == label and support["support_sets"] == []
        ec = ec_map[ec_id]
        card = export["selected_card"]
        assert card in material["input"]["prompt_evidence"]
        assert card["evidence_id"] in ec["evidence_card_ids"] and card["shown_in_prompt"]
        quote = selected_records[label]["generated_quote"]
        assert quote in material["response"]["generated_text"]
        assert dc["dc_text"] == selected_records[label]["dc_text"]
        case = dict(case_id=case_id, company=material["input"]["company_name"],
                    target_year=material["input"]["target_reporting_year"], task=material["input"]["task_id"],
                    selection=selection, dc_id=dc_id, dc_text=dc["dc_text"], generated_quote=quote,
                    generated_disclosure=material["response"]["generated_text"],
                    supplied_evidence=material["input"]["prompt_evidence"],
                    supplied_card=card, selected_ec_id=ec_id, selected_ec_text=ec["ec_text"],
                    candidate_ecs=candidates, candidate_ec_ids=candidate_ids,
                    support=support, diagnosis=diagnosis, analyst_note=export["analyst_note"],
                    selection_scope="Fixed seeded within-label example; manuscript subset editorially selected; not representative validation")
        cases[name] = case
        for role, text, locator in [("Extracted DC",dc["dc_text"],"material.dc: "+dc_id),
                                    ("Generated source quotation",quote,"material.response.generated_text"),
                                    ("Selected candidate EC",ec["ec_text"],"material.ec: "+ec_id),
                                    ("Supplied card",card["retrieval_text"],"selected_card.retrieval_text"),
                                    ("Recorded automatic rationale",diagnosis["rationale"],"material.diagnosis: "+dc_id)]:
            text_ledger.append(dict(case=name, role=role, text=text, source=source, locator=locator,
                                    verification="Exact match to saved case artifacts; automated interpretation is not independently validated",
                                    access_date="2026-10-02"))

    reports = {}
    for name, case in cases.items():
        card = case["supplied_card"]
        relative = "data/raw/reports_pdf/"+card["source_file"]
        path = register(relative)
        with fitz.open(path) as document:
            page = document[card["page_start"]-1]
            page_text = norm(page.get_text())
            if name == "wartsila":
                excerpt = "Wärtsilä uses an online solution for supply chain risk identification, assessment, and monitoring."
                assert excerpt in page_text and excerpt in card["retrieval_text"]
                assert "Annual Report 2019" in page_text and "132" in page_text
                case["display_card_excerpt"] = excerpt
                case["interpretation_limit"] = "The excerpt does not establish that the practice ceased."
                report = dict(title="Wärtsilä Annual Report 2019", pdf_page=132, printed_page=132, excerpt=excerpt,
                              version_note="Local PDF states it is composed of selected elements from the Annual Report; the checked passage is in Governance.")
            else:
                saved_source = read_csv("BACE/analysis/outputs/figures/02/02_asml_source_layout__data.csv")[0]
                assert sha(path) == saved_source["sha256"]
                scope1 = "Consists of the combustion of natural gas and purchased CO2"
                scope2 = "Calculated by multiplying electricity consumptions of the manufacturing locations by the local conversion factors"
                assert "CO2 footprint - direct scope 1 "+scope1 in page_text
                assert "CO2 footprint - indirect scope 2 "+scope2 in page_text
                assert "ASML INTEGRATED REPORT 2018 209" in page_text
                clip = fitz.Rect(*map(float, saved_source["clip_points"].split(',')))
                page.get_pixmap(matrix=fitz.Matrix(3,3),clip=clip).save(OUT/"asml_original_glossary.png")
                case["glossary_rows"] = [dict(label="CO2 footprint - direct scope 1", description=scope1),
                                         dict(label="CO2 footprint - indirect scope 2", description=scope2)]
                case["interpretation_limit"] = "The source challenges the rationale; it does not validate the full disclosure."
                report = dict(title="ASML Integrated Report 2018",pdf_page=216,printed_page=209,
                              glossary_rows=case["glossary_rows"],clip_points=saved_source["clip_points"],
                              version_note="Original local report PDF; SHA-256 matches the saved source-layout record.")
                for row in case["glossary_rows"]:
                    text_ledger.append(dict(case=name,role="Original glossary row",text=row["label"]+" | "+row["description"],
                                            source=relative,locator="Printed p. 209; PDF p. 216; two-column glossary",
                                            verification="Original page text and visual row association inspected; typeset transcription uses CO₂ and line wrapping",
                                            access_date="2026-10-02"))
        report.update(source_path=relative,sha256=sha(path),access_date="2026-10-02",status="VERIFIED_ORIGINAL_PASSAGE",
                      identifier=card["source_file"],use="Source check; original PDF page was not separately supplied to the generator")
        reports[name] = report
    save_json("case_evidence.json",cases)
    save_json("original_source_checks.json",reports)
    save_csv("text_evidence.csv",text_ledger)
    outputs = [OUT/name for name in ["diagnosis_composition.csv","verified_facts.json","case_evidence.json",
                                    "original_source_checks.json","text_evidence.csv","asml_original_glossary.png"]]
    record = dict(status="PASS",checked_at_utc=datetime.now(timezone.utc).isoformat(),prepared_date="2026-10-02",
                  command=f"{sys.executable} paper/analysis/fig3/prepare_data.py",script_sha256=sha(Path(__file__)),
                  python=sys.version,pymupdf=fitz.VersionBind,input_files=INPUTS,
                  outputs={str(p.relative_to(ROOT)):sha(p) for p in outputs},
                  counts_status="COMPUTED_VERIFIED",case_status="Saved automatic judgments verified; original-source interpretation checked by assistant, not independent human validation",
                  limits="Two fixed illustrative cases, no resampling or new model calls; no claim of representative error prevalence or external truth")
    save_json("data_provenance.json",record)
    print(json.dumps(dict(status="PASS",diagnosis_categories=len(composition),unsupported=unsupported,cases=list(cases),original_reports=len(reports))))


if __name__ == "__main__":
    main()
