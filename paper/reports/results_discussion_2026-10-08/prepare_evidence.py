"""Prepare local evidence and figure assets for the English meeting report."""
import csv
import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
INPUTS = {}


def tracked(path):
    p = ROOT / path
    INPUTS[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return p


def read(path):
    return json.loads(tracked(path).read_text())


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


(OUT / "assets").mkdir(parents=True, exist_ok=True)
for src, dst in [
    ("paper/manuscript/figures/fig2_support.pdf", "main_support.pdf"),
    ("paper/manuscript/figures/fig4_native_comparison.pdf", "native_comparison.pdf"),
    ("paper/analysis/fig3/asml_original_glossary.png", "asml_glossary.png"),
    ("BACE/analysis/outputs/evaluator_gap/figures/04_prompt_sensitivity_effects.pdf", "prompt_effects.pdf"),
]:
    shutil.copy2(tracked(src), OUT / "assets" / dst)

fig3 = read("paper/analysis/fig3/case_evidence.json")
source_checks = read("paper/analysis/fig3/original_source_checks.json")
sca = read("paper/analysis/disagreement_cases/sca_incidents_workers.json")
prompt_examples = read("BACE/analysis/outputs/evaluator_gap/prompt_sensitivity/examples.json")
kinnevik = next(r for r in prompt_examples["examples"] if "kinnevik__" in r["generation_case_id"])
assert not kinnevik["original_support_sets"] and not kinnevik["ragas_style_support_sets"]
assert kinnevik["ragchecker_style_support_sets"]
assert hashlib.sha256(tracked(kinnevik["input_cache"]["path"]).read_bytes()).hexdigest() == kinnevik["input_cache"]["sha256"]
assert not sca["bace_support"]["support_sets"]
assert sca["native_claims"]["ragchecker"]["supported"]
assert sca["native_claims"]["ragas"]["supported"]
assert sca["key_evidence_cards"][0]["value_text"] == "5.0"

dc_id = "dc_47ce21b14a5440da963c92e768e469b0"
packet_path = "BACE/analysis/outputs/evaluator_gap/evidence_chain_sample/review/verdict_blinded_packet.jsonl"
with tracked(packet_path).open() as handle:
    diasorin = next(json.loads(line) for line in handle if dc_id in line)
assert len(diasorin["raw_cards"]) == 30
assert len(diasorin["all_ec"]) == 78
assert len(diasorin["candidate_ec"]) == 1
candidate = diasorin["candidate_ec"][0]
assert candidate in diasorin["all_ec"]
assert candidate["ec_claim_id"] == "ec_076"
call_records = {}
for condition in ["raw_cards", "all_ec", "candidate_ec"]:
    path = f"BACE/results/evidence_chain_sample_v1/runs/{condition}/calls.jsonl"
    with tracked(path).open() as handle:
        for line_number, line in enumerate(handle, 1):
            if dc_id in line:
                call = json.loads(line)
                assert call["dc_id"] == dc_id and call["output_valid"]
                call_records[condition] = {
                    "source_file": path, "line": line_number,
                    "line_sha256": hashlib.sha256(line.encode()).hexdigest(),
                    "call_id": call["call_id"], "call_identity": call["call_identity"],
                    "dynamic_input": call["dynamic_input"],
                    "restored_output": call["restored_output"],
                }
                break
    assert condition in call_records
assert call_records["raw_cards"]["restored_output"]["support_sets"][0]["ec_claim_ids"] == ["card_009"]
all_support = call_records["all_ec"]["restored_output"]["support_sets"]
assert all_support == [{"ec_claim_ids": [diasorin["ec_original_by_alias"]["ec_076"]], "support_type": "direct"}]
assert not call_records["candidate_ec"]["restored_output"]["support_sets"]
assert len({r["call_identity"]["prompt_sha256"] for r in call_records.values()}) == 1

original_passages = {}
for key, info in source_checks.items():
    pdf = tracked(info["source_path"])
    assert INPUTS[info["source_path"]] == info["sha256"]
    page = str(info["pdf_page"])
    text = subprocess.check_output(["pdftotext", "-f", page, "-l", page, "-layout", str(pdf), "-"]).decode()
    original_passages[key] = {**info, "access_date": "2026-10-08", "page_text": text}
    if key == "asml":
        assert "Consists of the combustion of natural gas and purchased CO2" in text
        assert "indirect scope 2" in text
    else:
        assert "online solution for supply chain risk identification" in text
pdf_path = "data/raw/reports_pdf/6ca72f0a-5046-4fef-87cb-aa49f1e74531_2022_AR.pdf"
page_text = subprocess.check_output(["pdftotext", "-f", "201", "-l", "201", "-layout", str(tracked(pdf_path)), "-"]).decode()
assert "regular training activities on topics under Legislative Decree 231/2001" in " ".join(page_text.split())
original_passages["diasorin"] = {"source_path": pdf_path, "pdf_page": 201,
    "title": "DiaSorin Annual Report 2022", "access_date": "2026-10-08", "page_text": page_text,
    "scope": "Original source check, not additional evidence supplied to the judge."}

cases = {
    "C1": {"question": "What does low support measure?", "company": "ASML", "bundle": fig3["asml"]},
    "C2": {"question": "What do automated diagnoses mean?", "company": "Wartsila", "bundle": fig3["wartsila"]},
    "C3": {"question": "How should native evaluator differences be interpreted?", "company": "SCA", "bundle": sca},
    "C4": {"question": "How much do judgment instructions matter?", "company": "Kinnevik", "bundle": kinnevik},
    "C5": {"question": "How much does evidence selection matter?", "company": "DiaSorin", "bundle": diasorin,
           "verified_calls": call_records,
           "interpretation": "The full-EC condition accepted the same single EC retained in the candidate condition. This example demonstrates a context-dependent/run-dependent judgment difference, not omission of that EC. The temporal rule remains unresolved."},
}
dump("case_evidence.json", cases)
dump("original_source_checks.json", original_passages)

numbers = read("paper/analysis/professor_meeting_2026-10-08/verified_results.json")
prior = read("paper/analysis/professor_meeting_2026-10-08/provenance.json")
for path, expected_hash in prior["inputs_sha256"].items():
    if path.endswith(".csv") or path.endswith("status.json") or path.endswith(".xlsx"):
        tracked(path)
        assert INPUTS[path] == expected_hash
dump("numeric_ledger.json", numbers)
for path in ["BACE/PROTOCOL.md", "BACE/analysis/ANALYSIS_SPEC.md",
             "BACE/experiments/prompt_sensitivity_v1/PROTOCOL.md",
             "BACE/experiments/evidence_chain_sample_v1/PROTOCOL.md",
             "BACE/analysis/outputs/evaluator_gap/evidence_chain_sample/review/status.json"]:
    tracked(path)

outline = """# Report outline

Audience: the author and professor. Language: English. Format: concise LaTeX meeting report.

## Part 1. Current main-experiment findings (two pages)

Explain the study population and EC/DC pipeline, then report support, diagnostic composition and native evaluator differences. Use the existing support and comparison figures. Distinguish observed automated judgments from accuracy or factual-error claims.

## Part 2. Five discussion points (one page each)

Use the same sequence for each point: observed result; one real saved case; what the case does and does not show; one decision for discussion.

1. What does the low support rate measure? ASML's original glossary versus its extracted Scope 1 evidence claim.
2. What do dominant automated diagnoses mean? Wartsila's 2019 description used in a 2022 disclosure.
3. How should evaluator disagreement be interpreted? SCA's incident count changed into a worker count.
4. How much do judgment instructions matter? Kinnevik's anti-bribery policy claim under the three fixed-input prompt conditions.
5. How much does evidence selection matter? DiaSorin's training claim: all ECs accept the very EC that is retained, but rejected, in the candidate condition.

Use simple flow diagrams for evidence processing, temporal interpretation and the three evidence conditions. Use existing plots for quantitative effects; a small table and flow diagram suffice for the sampled evidence-chain result.

## Part 3. Decisions and source notes (one page)

Prioritize independent source review, temporal/inference rules and manuscript integration. Record incomplete human validation and the different analysis cohorts. Provide short case identifiers and source-file pointers; keep full machine identifiers and input hashes in the companion evidence ledger.

Target: eight pages, including figures; no separate title page, literature review or long appendix. Cases are illustrative, assistant-inspected examples, not a representative validation sample.
"""
(OUT / "REPORT_PLAN.md").write_text(outline)
dump("provenance.json", {
    "checked_at": datetime.now(ZoneInfo("Europe/Zurich")).isoformat(),
    "command": "python paper/reports/results_discussion_2026-10-08/prepare_evidence.py",
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "input_sha256": INPUTS, "status": "PASS", "model_calls": 0,
    "independent_human_validation": False,
    "case_selection": "Four existing illustrative cases; DiaSorin selected after screening the prepared true/true/false review pattern for a concise interpretable case. No prevalence inference.",
    "numerical_scope": "Reused verified means and counts after checking saved inputs. Saved bootstrap intervals were not rerun.",
})
print("PASS: five real cases, source passages, numeric inputs and report assets verified.")
