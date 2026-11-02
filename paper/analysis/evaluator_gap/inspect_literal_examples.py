"""Export fixed illustrative literal matches with original evidence and judgments."""
import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SELECTED_TEXTS = [
    "KLM subsidiaries recorded 53 workplace accidents in 2017.",
    "Air France-KLM incorporates environmental obligations into relevant product or service specifications.",
    "Social reporting covers HOP!.",
    "Air France broadened access to training through Manager Cafés.",
    "Air France-KLM manages fleet capital expenditure under strict capital discipline.",
]
pair_bytes = (OUT / "literal_pairs.csv").read_bytes()
provenance = json.loads((OUT / "provenance.json").read_text())
assert hashlib.sha256(pair_bytes).hexdigest() == provenance["output_sha256"]["literal_pairs.csv"]
pairs = list(csv.DictReader(io.StringIO(pair_bytes.decode())))
ledger_path = ROOT / "BACE/analysis/outputs/snapshot/sources.json"
ledger_bytes = ledger_path.read_bytes()
ledger = json.loads(ledger_bytes)
source_hashes = {}


def read(base, relative):
    path = base / relative
    data = path.read_bytes()
    name = str(path.relative_to(ROOT))
    digest = hashlib.sha256(data).hexdigest()
    assert digest == ledger[name], name
    source_hashes[name] = digest
    return [json.loads(line) for line in data.decode().splitlines() if line.strip()]


examples = []
for text in SELECTED_TEXTS:
    # The first sorted matching case is fixed; this is an illustrative selection.
    p = next(row for row in pairs if row["bace_dc_text"] == text)
    assert " ".join(p["bace_dc_text"].casefold().split()) == " ".join(p["external_claim_text"].casefold().split())
    base = ROOT / "BACE/results/main_v1/cases" / p["generation_case_id"]
    inputs = read(base, "inputs/generation_cases.jsonl")[0]
    response = read(base, "generation/generated_disclosures.jsonl")[0]
    dc = next(r for r in read(base, "bace/dedup/dc_claims.jsonl") if r["dc_id"] == p["bace_dc_id"])
    ecs = read(base, "bace/dedup/ec_claims.jsonl")
    candidates = next(r for r in read(base, "bace/candidates/dc_candidate_ecs.jsonl") if r["dc_claim_id"] == p["bace_dc_id"])
    support = next(r for r in read(base, "bace/support/dc_support_sets.jsonl") if r["dc_claim_id"] == p["bace_dc_id"])
    diagnosis = next((r for r in read(base, "bace/diagnosis/dc_unsupported_diagnoses.jsonl") if r["dc_claim_id"] == p["bace_dc_id"]), None)
    record = read(base, "evaluation/ragas/results.jsonl")[-1]
    native = next(r for r in record["claims"] if r["claim_index"] == int(p["external_claim_index"]))
    assert dc["dc_text"] == p["bace_dc_text"]
    assert native["claim"] == p["external_claim_text"]
    assert native["supported"] == (p["external_supported"] == "True")
    examples.append({"pair": p, "target_dc": dc, "generated_text": response["generated_text"],
                     "all_prompt_evidence": inputs["prompt_evidence"], "all_ecs": ecs,
                     "candidate_ecs": [r for r in ecs if r["ec_id"] in candidates["candidate_ec_ids"]],
                     "bace_support": support, "bace_diagnosis": diagnosis, "ragas_claim": native})

counts = {
    "pairs": len(pairs),
    "ragas_supported": sum(p["external_supported"] == "True" for p in pairs),
    "bace_supported": sum(p["bace_supported"] == "True" for p in pairs),
    "both_supported": sum(p["bace_supported"] == p["external_supported"] == "True" for p in pairs),
    "both_unsupported": sum(p["bace_supported"] == p["external_supported"] == "False" for p in pairs),
    "bace_unsupported_ragas_supported": sum(p["bace_supported"] == "False" and p["external_supported"] == "True" for p in pairs),
    "bace_supported_ragas_unsupported": sum(p["bace_supported"] == "True" and p["external_supported"] == "False" for p in pairs),
}
output = {"review_date": "2026-09-30", "counts": counts,
          "selection": "Five editorially selected examples from the first company in the sorted literal-pair file; first matching case for each exact target text. Not a representative sample or human validation.",
          "literal_pairs_sha256": hashlib.sha256(pair_bytes).hexdigest(),
          "source_ledger_sha256": hashlib.sha256(ledger_bytes).hexdigest(),
          "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "command": "/home/muwang/.local/share/bace-writing-skills/venv/bin/python paper/analysis/evaluator_gap/inspect_literal_examples.py",
          "source_hashes": source_hashes, "examples": examples,
          "model_calls": 0, "experiment_changes": "None"}
(OUT / "literal_examples.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(counts, indent=2))
