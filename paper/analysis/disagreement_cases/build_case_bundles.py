"""Preserve selected native disagreements and verify their input provenance.

Semantic judgments are documented in 06_verified_disagreement_examples.md
and 07_expanded_disagreement_examples.md;
this script verifies records, native verdicts and source rows, not truth.
"""
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
INPUTS = {}
SELECTIONS = [
    dict(name="kinnevik_adoption", case_id="w2__text_embedding_3_large__stratified_by_evidence_type_n10__kinnevik__2020__e1_1_transition_plan",
         dc_id="dc_0ff3878beb20287502637f91ef1dd03c", ragchecker_index=1, ragas_index=0, key_cards=["Evidence 21"]),
    dict(name="continental_coverage", case_id="w2__text_embedding_3_large__stratified_by_evidence_type_n10__continental__2021__s1_4_workforce_actions_resources",
         dc_id="dc_36a636280cb20a73d7f616d90a887cfe", ragchecker_index=44, ragas_index=38, key_cards=["Evidence 21", "Evidence 27"]),
    dict(name="sca_incidents_workers", case_id="w2__text_embedding_3_large__stratified_by_evidence_type_n10__svenska_cellulosa__2022__g1_4_corruption_bribery_incidents",
         dc_id="dc_94969d707006865673f9d8456fa98a4f", ragchecker_index=25, ragas_index=31, key_cards=["Evidence 23", "Evidence 26"]),
    dict(name="deutsche_bank_employee_population", case_id="w2__text_embedding_3_large__stratified_by_evidence_type_n10__deutsche_bank__2020__s1_1_workforce_policies",
         dc_id="dc_caf6118fd0e40f922a5261620ed0bf59", ragchecker_index=18, ragas_index=31, key_cards=["Evidence 18", "Evidence 20"]),
    dict(name="banco_bpm_actual_as_target", case_id="w2__text_embedding_3_large__stratified_by_evidence_type_n10__banco_bpm__2023__e1_3_actions_resources",
         dc_id="dc_9481ed6b85983e7179efe1939f81b94f", ragchecker_index=21, ragas_index=22, key_cards=["Evidence 19"],
         candidate_qualifiers_preserved=False,
         original_pdf="data/raw/reports_pdf/1f87c1c3-4366-472a-a793-ac759c4c93cc_2022_SR.pdf", original_pdf_page=15),
]


def register(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(2**20):
            h.update(block)
    key = str(path.relative_to(ROOT))
    INPUTS[key] = {"sha256": h.hexdigest(), "bytes": path.stat().st_size}
    return key


def read(path):
    register(path)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    adapter = ROOT / "BACE/script/evaluation/external_evaluation.py"
    register(adapter)
    spec = importlib.util.spec_from_file_location("bace_readonly_adapter", adapter)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    bundles, wanted = [], {}
    for selection in SELECTIONS:
        base = ROOT / "BACE/results/main_v1/cases" / selection["case_id"]
        paths = {"generation_input": "inputs/generation_cases.jsonl", "response": "generation/generated_disclosures.jsonl",
                 "dc": "bace/dedup/dc_claims.jsonl", "ec": "bace/dedup/ec_claims.jsonl",
                 "candidates": "bace/candidates/dc_candidate_ecs.jsonl", "support": "bace/support/dc_support_sets.jsonl",
                 "diagnosis": "bace/diagnosis/dc_unsupported_diagnoses.jsonl",
                 "ragchecker": "evaluation/ragchecker/results.jsonl", "ragas": "evaluation/ragas/results.jsonl"}
        material = {k: read(base / v) for k, v in paths.items()}
        inp, response = material["generation_input"][0], material["response"][0]
        adapted = module.adapt_case(inp, response)
        dc = next(c for c in material["dc"] if c["dc_id"] == selection["dc_id"])
        candidate = next(c for c in material["candidates"] if c["dc_claim_id"] == selection["dc_id"])
        support = next(c for c in material["support"] if c["dc_claim_id"] == selection["dc_id"])
        diagnosis = next(c for c in material["diagnosis"] if c["dc_claim_id"] == selection["dc_id"])
        assert support["support_sets"] == []
        ecs = [next(e for e in material["ec"] if e["ec_id"] == i) for i in candidate["candidate_ec_ids"]]
        native = {}
        for framework in ["ragchecker", "ragas"]:
            record = material[framework][-1]
            for key in ["generation_case_id", "prompt_hash", "response_hash", "context_hash", "evidence_ids", "prompt_labels"]:
                assert record[key] == adapted[key], (framework, key)
            claim = next(c for c in record["claims"] if c["claim_index"] == selection[framework + "_index"])
            assert claim["supported"] is True
            if framework == "ragas":
                original = record["native_outputs"]["NLIStatementOutput"]["statements"][claim["claim_index"]]
                assert original["statement"] == claim["claim"] and original["verdict"] == 1 and original["reason"] == claim["reason"]
            else:
                original = record["native_result"]
                index = claim["claim_index"]
                assert original["response_claims"][index] == claim["claim"]
                for i, evidence_id in enumerate(record["evidence_ids"]):
                    assert original["retrieved2response"][index][i] == claim["evidence_verdicts"][evidence_id]
                assert "Entailment" in claim["evidence_verdicts"].values()
            native[framework] = claim
        quotations = [q for p in dc["dc_provenance"] for q in p["source_quotes"]]
        assert quotations and all(q in response["generated_text"] for q in quotations)
        key_cards = [c for c in inp["prompt_evidence"] if c["prompt_label"] in selection["key_cards"]]
        assert len(key_cards) == len(selection["key_cards"])
        for c in key_cards:
            assert any(c["evidence_id"] in e["evidence_card_ids"] for e in ecs)
            if c["evidence_id"].startswith("csv::"):
                _, company, year, indicator = c["evidence_id"].split("::")
                wanted[(company, year, indicator)] = c
        bundle = dict(selection=selection, source_paths={k: str((base / v).relative_to(ROOT)) for k, v in paths.items()},
                      generated_text=response["generated_text"], original_generated_quotations=quotations,
                      disclosure_claim=dc, bace_support=support, bace_diagnosis=diagnosis,
                      bace_candidate_ecs=ecs, native_claims=native, key_evidence_cards=key_cards,
                      full_prompt_evidence=inp["prompt_evidence"], verified_input_hashes={k: adapted[k] for k in ["prompt_hash", "response_hash", "context_hash"]},
                      checks={"native_labels_verified": True, "common_prompt_visible_context_verified": True,
                              "generated_quotations_exact": True, "key_source_cards_present_in_bace_candidates": True},
                      source_inspection={"key_source_qualifiers_present_in_bace_candidates": selection.get("candidate_qualifiers_preserved", True),
                                         "status": "Interpretive review recorded in the reports, not established by this script."})
        if "original_pdf" in selection:
            pdf = ROOT / selection["original_pdf"]
            register(pdf)
            page = str(selection["original_pdf_page"])
            text_command = ["pdftotext", "-f", page, "-l", page, "-layout", str(pdf), "-"]
            original_text = subprocess.run(text_command, check=True, capture_output=True, text=True).stdout
            text_path = OUT / "banco_bpm_2022_p15.txt"
            text_path.write_text(original_text)
            render_command = ["pdftoppm", "-f", page, "-l", page, "-scale-to", "2200", "-singlefile", "-png", str(pdf), str(OUT / "banco_bpm_2022_p15")]
            subprocess.run(render_command, check=True, capture_output=True)
            bundle["original_pdf_audit"] = dict(source=selection["original_pdf"], page=int(page),
                    text_artifact=str(text_path.relative_to(ROOT)), image_artifact=str((OUT / "banco_bpm_2022_p15.png").relative_to(ROOT)),
                    text_command=text_command, render_command=render_command,
                    scope="Original-page audit only. The page image and restored column headers were not provided to the evaluators.")
        bundles.append(bundle)

    source_csv = ROOT / "data/processed/results/esg_indicators_postprocessed.csv"
    register(source_csv)
    csv.field_size_limit(32 * 1024 * 1024)
    matches = []
    with source_csv.open(newline="") as f:
        for record_index, row in enumerate(csv.DictReader(f), 1):
            key = (row["company_id"], row["year"], row["data_point_id"])
            if key in wanted:
                card = wanted[key]
                assert row["data_point_description"] == card["metric"]
                assert row["value_final"] == card["value_text"] or float(row["value_final"]) == float(card["value_text"])
                matches.append(dict(data_record_index=record_index, source=str(source_csv.relative_to(ROOT)),
                                    evidence_id=card["evidence_id"], row=row))
    assert len(matches) == len(wanted)
    assert len({r["evidence_id"] for r in matches}) == len(wanted)
    save(OUT / "verified_source_rows.json", matches)
    for bundle in bundles:
        bundle["source_csv_record_indices"] = [r["data_record_index"] for r in matches
                      if r["evidence_id"] in {c["evidence_id"] for c in bundle["key_evidence_cards"]}]
        save(OUT / (bundle["selection"]["name"] + ".json"), bundle)
        name = bundle["selection"]["name"]
        lines = [f"# Full supplied evidence: {name}", "", "Generated disclosure", "", bundle["generated_text"], "", "## Prompt-visible evidence"]
        for c in bundle["full_prompt_evidence"]:
            lines += ["", f"### {c['prompt_label']}", "", f"Source: {c['source_label']}", "", f"ID: `{c['evidence_id']}`", "", c["retrieval_text"]]
        (OUT / (name + "_full_evidence.md")).write_text("\n".join(lines) + "\n")
    save(OUT / "bundle_provenance.json", dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),
         script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), python=sys.version,
         command="/home/muwang/.local/share/bace-writing-skills/venv/bin/python paper/analysis/disagreement_cases/build_case_bundles.py",
         input_files=INPUTS, selected_cases=SELECTIONS, status="PASS",
         scope="Native verdict and supplied-evidence provenance checks. Manual evidence interpretation is in the report; no new model calls or human validation."))
    print(json.dumps({"status": "PASS", "case_bundles": len(bundles), "source_rows": len(matches), "input_files": len(INPUTS)}))


if __name__ == "__main__":
    main()
