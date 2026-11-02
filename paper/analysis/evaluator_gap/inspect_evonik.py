"""Preserve the exact input boundary for a previously discussed counterexample."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CID = "w2__text_embedding_3_large__stratified_by_evidence_type_n10__evonik_industries__2023__e1_4_targets"
DID = "dc_a9b573fded182db3e02b3ee78bd28e1a"
BASE = ROOT / "BACE/results/main_v1/cases" / CID
SOURCES = {}
ledger_path = ROOT / "BACE/analysis/outputs/snapshot/sources.json"
ledger_bytes = ledger_path.read_bytes()
expected = json.loads(ledger_bytes)


def read(name):
    path = BASE / name
    data = path.read_bytes()
    key = str(path.relative_to(ROOT))
    digest = hashlib.sha256(data).hexdigest()
    assert digest == expected[key], key
    SOURCES[key] = {"sha256": digest, "bytes": len(data)}
    return [json.loads(line) for line in data.decode().splitlines() if line.strip()]


inputs = read("inputs/generation_cases.jsonl")[0]
response = read("generation/generated_disclosures.jsonl")[0]
dc = next(r for r in read("bace/dedup/dc_claims.jsonl") if r["dc_id"] == DID)
ecs = read("bace/dedup/ec_claims.jsonl")
selected = next(r for r in read("bace/candidates/dc_candidate_ecs.jsonl") if r["dc_claim_id"] == DID)
support = next(r for r in read("bace/support/dc_support_sets.jsonl") if r["dc_claim_id"] == DID)
diagnosis = next(r for r in read("bace/diagnosis/dc_unsupported_diagnoses.jsonl") if r["dc_claim_id"] == DID)
native = {}
for framework, index in (("ragchecker", 30), ("ragas", 23)):
    record = read(f"evaluation/{framework}/results.jsonl")[-1]
    native[framework] = next(r for r in record["claims"] if r["claim_index"] == index)
key_card = next(r for r in inputs["prompt_evidence"] if r["prompt_label"] == "Evidence 18")
assert "9,519 5,468 2008 2021" in key_card["retrieval_text"]
record = {
    "review_date": "2026-09-30",
    "review_status": "ANALYST_REVIEW_NOT_ADJUDICATED",
    "generation_case_id": CID,
    "target_dc": dc,
    "generated_text": response["generated_text"],
    "key_supplied_card": key_card,
    "all_supplied_cards": inputs["prompt_evidence"],
    "all_ecs": ecs,
    "candidate_ecs": [r for r in ecs if r["ec_id"] in selected["candidate_ec_ids"]],
    "ecs_derived_from_key_card": [r for r in ecs if any(p["prompt_label"] == "Evidence 18" for p in r["ec_provenance"])],
    "support": support,
    "diagnosis": diagnosis,
    "native_claims": native,
    "interpretation": {
        "correction": "The previous discussion and alternative-review note overstated full support from the supplied table. Its exact text contains 5,468 but does not explicitly supply the thousand-tonne unit or intact column headings for this value. The original PDF was not rechecked in this review and cannot silently supplement the prompt-visible evidence.",
        "source_to_ec": "The EC derived from Evidence 18 retains the previous target but not the numerical emissions levels. Omission alone is not established as an extraction error: the input table is incomplete.",
        "candidate_set": "The candidate set contains only the separately reported Scope 1 and Scope 2 values. The support stage did not receive the supplied table row itself.",
        "diagnosis_limit": "The contradiction rationale adds coarsely reported component values and treats the resulting total as incompatible with the more precise generated total. That argument does not establish a contradiction without resolving reporting precision and accounting basis. This does not independently prove the binary unsupported judgment wrong.",
        "conclusion": "Retain as an ambiguous pipeline and diagnosis example, not a confirmed BACE false rejection or a confirmed comparator error. A diagnosis rationale is produced after the support decision and is not a causal trace of that earlier decision."
    },
    "source_hashes": SOURCES,
    "snapshot_source_ledger_sha256": hashlib.sha256(ledger_bytes).hexdigest(),
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "model_calls": 0,
}
(OUT / "evonik_boundary_recheck.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(record["interpretation"], indent=2))
