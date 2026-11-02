"""Freeze a deterministic source-review sample and verify original saved artifacts."""
import csv
import hashlib
import io
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
GAP = ROOT / "paper/analysis/support_gap_composition_2026-10-20"
SNAPSHOT = ROOT / "BACE/analysis/outputs/snapshot"
HASHES = {}


def read(path):
    data = path.read_bytes()
    HASHES[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    return data


pairs = list(csv.DictReader(io.StringIO(read(GAP / "matched_pairs.csv").decode())))
prov = json.loads(read(GAP / "provenance.json"))
assert HASHES[str((GAP / "matched_pairs.csv").relative_to(ROOT))] == prov["output_sha256"]["matched_pairs.csv"]
ledger = json.loads(read(SNAPSHOT / "sources.json"))


def rank(p):
    return hashlib.sha256(("20261020-review-v1|" + p["framework"] + "|" +
                           p["generation_case_id"] + "|" + p["bace_dc_id"]).encode()).hexdigest()


selected = []
cats = ("evidence_conflation", "inferential_inflation", "unsupported_novelty", "non_disclosure_statement")
for cat in cats:
    for f, quota in (("ragas", 2), ("ragchecker", 1)):
        pool = sorted((p for p in pairs if p["framework"] == f and p["bace_label"] == cat and p["external_supported"] == "True"), key=rank)
        companies = set()
        for p in pool:
            if p["company_id"] in companies:
                continue
            selected.append({**p, "selection_stratum": cat, "selection_rank": rank(p)})
            companies.add(p["company_id"])
            if len(companies) == quota:
                break
for kind, quota in (("reverse_disagreement", 2), ("both_supported_control", 1)):
    for f in ("ragas", "ragchecker"):
        pool = sorted((p for p in pairs if p["framework"] == f and p["bace_supported"] == "True" and
                       p["external_supported"] == ("False" if kind == "reverse_disagreement" else "True")), key=rank)
        selected.extend({**p, "selection_stratum": kind, "selection_rank": rank(p)} for p in pool[:quota])
assert len(selected) == 18


def raw(base, relative):
    path = base / relative
    content = read(path)
    assert HASHES[str(path.relative_to(ROOT))] == ledger[str(path.relative_to(ROOT))]
    return [json.loads(line) for line in content.decode().splitlines() if line.strip()]


packets = []
(OUT / "packets").mkdir(exist_ok=True)
for idx, pair in enumerate(selected, 1):
    rid = f"R{idx:02d}"
    pair["review_id"] = rid
    base = ROOT / "BACE/results/main_v1/cases" / pair["generation_case_id"]
    inputs = raw(base, "inputs/generation_cases.jsonl")[0]
    response = raw(base, "generation/generated_disclosures.jsonl")[0]
    dc = next(r for r in raw(base, "bace/dedup/dc_claims.jsonl") if r["dc_id"] == pair["bace_dc_id"])
    ecs = raw(base, "bace/dedup/ec_claims.jsonl")
    candidate = next(r for r in raw(base, "bace/candidates/dc_candidate_ecs.jsonl") if r["dc_claim_id"] == pair["bace_dc_id"])
    support = next(r for r in raw(base, "bace/support/dc_support_sets.jsonl") if r["dc_claim_id"] == pair["bace_dc_id"])
    diagnosis = next((r for r in raw(base, "bace/diagnosis/dc_unsupported_diagnoses.jsonl") if r["dc_claim_id"] == pair["bace_dc_id"]), None)
    native = raw(base, f"evaluation/{pair['framework']}/results.jsonl")[-1]
    claim = next(r for r in native["claims"] if r["claim_index"] == int(pair["external_claim_index"]))
    text = " ".join(claim["claim"]) if isinstance(claim["claim"], list) else claim["claim"]
    assert text == pair["external_claim_text"] and dc["dc_text"] == pair["bace_dc_text"]
    assert claim["supported"] == (pair["external_supported"] == "True")
    assert bool(support["support_sets"]) == (pair["bace_supported"] == "True")
    if diagnosis:
        assert diagnosis["unsupported_label"] == pair["bace_label"]
    packet = {"review_id": rid, "selection": pair, "generated_text": response["generated_text"],
              "target_dc": dc, "evidence_cards": inputs["prompt_evidence"], "all_ecs": ecs,
              "candidate_ecs": [r for r in ecs if r["ec_id"] in candidate["candidate_ec_ids"]],
              "support": support, "diagnosis": diagnosis, "comparator_claim": claim}
    packets.append(packet)
    (OUT / "packets" / f"{rid}.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
    lines = [f"# {rid}: {pair['company_name']} / {pair['year']} / {pair['task']}",
             "", "## Target", "", dc["dc_text"], "", "## Full generated disclosure", "", response["generated_text"],
             "", "## All supplied evidence cards", ""]
    for c in inputs["prompt_evidence"]:
        lines += [f"### {c['prompt_label']} | Source year {c.get('source_year')} | {c.get('source_label')} | Pages {c.get('page_start')}-{c.get('page_end')}",
                  f"ID: {c['evidence_id']}", c["retrieval_text"], ""]
    (OUT / "packets" / f"{rid}_sources.md").write_text("\n".join(lines) + "\n")
    lines = [f"# {rid}: Saved judgments", "", json.dumps(pair, indent=2, ensure_ascii=False),
             "", "## BACE diagnosis", json.dumps(diagnosis, indent=2, ensure_ascii=False),
             "", "## BACE candidate ECs"]
    lines += [r["ec_id"] + ": " + r["ec_text"] for r in packet["candidate_ecs"]]
    lines += ["", "## BACE support sets", json.dumps(support, indent=2, ensure_ascii=False),
              "", "## Comparator judgment", json.dumps(claim, indent=2, ensure_ascii=False)]
    (OUT / "packets" / f"{rid}_judgments.md").write_text("\n".join(lines) + "\n")
with (OUT / "selection.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(selected[0]))
    writer.writeheader(); writer.writerows(selected)
residual = {f: Counter(p["bace_label"] for p in pairs if p["framework"] == f and p["bace_supported"] == "False" and p["external_supported"] == "True" and p["bace_label"] != "factual_boundary_distortion") for f in ("ragas", "ragchecker")}
(OUT / "selection_provenance.json").write_text(json.dumps({
    "prepared_at_utc": datetime.now(timezone.utc).isoformat(), "analysis_status": "Exploratory AI internal source review",
    "selection_rule": "REVIEW_PLAN.md", "selected_pairs": len(selected),
    "positive_disagreement_frame_excluding_boundary": residual, "inputs_sha256": HASHES,
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "command": "python paper/analysis/residual_gap_review_2026-10-20/prepare_review.py",
    "external_model_calls": 0, "experiment_changes": [],
    "output_sha256": {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((OUT / "packets").glob("*"))}
}, indent=2) + "\n")
for p in packets:
    s = p["selection"]
    print(p["review_id"], s["framework"], s["selection_stratum"], s["company_name"], s["year"], s["bace_dc_text"], "source_chars=", len((OUT / "packets" / f"{p['review_id']}_sources.md").read_text()))
