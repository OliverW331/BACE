"""Preserve selected exclusion checks from the 30 September source review.

The notes are interpretive review entries, not automated adjudications or an
exhaustive record of candidates screened. No experiment artifacts are changed.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PREFIX = "w2__text_embedding_3_large__stratified_by_evidence_type_n10__"
REVIEWS = [
    dict(case="subsea_7__2023__e1_3_actions_resources",
         dc_ids=["dc_5fd5cbf540f43890f37843039d2805bc", "dc_4264a63b381954ff5b0637a9bc214eea", "dc_ed657dca5a2eda5aeb5b74ad85acbd5a"],
         ragchecker=[17, 18, 19], ragas=[17, 18, 19],
         decision="DOES_NOT_MEET_BOTH_SUPPORTED_PATTERN",
         note="The monitoring statement has direct source support. The separate 73% and 66% site-share statements transfer electricity percentages to sites, but RAGChecker rejects both numerical statements."),
    dict(case="investec__2020__s1_4_workforce_actions_resources",
         dc_ids=["dc_e7971d030743389492a47ba3e72bed69"], ragchecker=[39], ragas=[39],
         decision="FULL_PASSAGE_QUALIFIES_POPULATION",
         note="The sentence immediately following the 4,483 figure states that it occurs under both permanent and temporary classifications and is not used to calculate workforce composition. Do not omit this qualification."),
    dict(case="dufry__2019__g1_1_business_conduct_policies",
         dc_ids=["dc_61d4180680dae4d952d553aa5c45b404"], ragchecker=[19, 20], ragas=[29, 30],
         decision="NEAREST_MATCH_OMITS_DISPUTED_RELATIONSHIP",
         note="Nearest numerical matches establish trained at-risk employees, not their relationship to the manager subgroup. Other native statements refer to the general training population; do not equate these with the DC's specific subgroup inclusion."),
    dict(case="cofinimmo__2021__e1_1_transition_plan",
         dc_ids=["dc_46dfca68ed0b8c74250219515544eab1"], ragchecker=[26], ragas=[28],
         decision="EXPLICIT_SUPPORT_IN_SUPPLIED_CARD",
         note="Evidence 12 explicitly lists purchase of 100% renewable electricity for buildings under management. BACE's absence-of-evidence rationale does not establish the alleged unsupported purchase policy; target-year persistence is a separate, weaker issue."),
    dict(case="dufry__2023__e1_1_transition_plan",
         dc_ids=["dc_68f3e970ad0d632d28bf0e13c5ccc464"], ragchecker=[26], ragas=[24],
         decision="EXPLICIT_SUPPORT_IN_SUPPLIED_CARD",
         note="Evidence 6 explicitly gives purchased goods sold to customers as about 90% of total emissions in the 2019 base year. BACE's missing-evidence rationale is insufficient."),
]


def main():
    inputs, records = {}, []
    for review in REVIEWS:
        base = ROOT / "BACE/results/main_v1/cases" / (PREFIX + review["case"])

        def read(relative):
            path = base / relative
            raw = path.read_bytes()
            inputs[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
            return [json.loads(line) for line in raw.splitlines() if line.strip()]

        inp = read("inputs/generation_cases.jsonl")[0]
        response = read("generation/generated_disclosures.jsonl")[0]
        dc = read("bace/dedup/dc_claims.jsonl")
        diagnoses = read("bace/diagnosis/dc_unsupported_diagnoses.jsonl")
        native = {}
        for framework in ["ragchecker", "ragas"]:
            result = read(f"evaluation/{framework}/results.jsonl")[-1]
            native[framework] = [c for c in result["claims"] if c["claim_index"] in review[framework]]
            assert len(native[framework]) == len(review[framework])
        records.append(dict(review=review, generation_case_id=PREFIX + review["case"],
            generated_text=response["generated_text"], full_prompt_evidence=inp["prompt_evidence"],
            disclosure_claims=[c for c in dc if c["dc_id"] in review["dc_ids"]],
            diagnoses=[d for d in diagnoses if d["dc_claim_id"] in review["dc_ids"]],
            native_claims=native,
            scope="Targeted exclusion check. Full context preserved for follow-up; this entry does not certify exhaustive independent adjudication."))
    result = dict(prepared_at_utc=datetime.now(timezone.utc).isoformat(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        command="/home/muwang/.local/share/bace-writing-skills/venv/bin/python paper/analysis/disagreement_cases/record_expansion_review.py",
        input_sha256=inputs, records=records)
    (OUT / "expansion_review_notes.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"saved_review_entries": len(records)}))


if __name__ == "__main__":
    main()
