"""Check saved example records, local document links and source immutability.

These are artifact checks, not tests of the scientific interpretation.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(2**20):
            h.update(block)
    return h.hexdigest()


def main():
    provenance = json.loads((OUT / "bundle_provenance.json").read_text())
    reviews = json.loads((OUT / "expansion_review_notes.json").read_text())
    changed = [p for p, entry in provenance["input_files"].items() if sha256(ROOT / p) != entry["sha256"]]
    changed += [p for p, digest in reviews["input_sha256"].items() if sha256(ROOT / p) != digest]
    assert not changed, changed
    assert sha256(OUT / "build_case_bundles.py") == provenance["script_sha256"]
    assert sha256(OUT / "record_expansion_review.py") == reviews["script_sha256"]
    docs = [ROOT / "paper" / name for name in ["README.md", "05_results_storyline.md",
        "06_verified_disagreement_examples.md", "07_expanded_disagreement_examples.md"]]
    counts = {}
    expected_entailments = {"sca_incidents_workers": ["Evidence 23"],
        "deutsche_bank_employee_population": ["Evidence 18", "Evidence 20"],
        "banco_bpm_actual_as_target": ["Evidence 19"]}
    for selection in provenance["selected_cases"]:
        name = selection["name"]
        bundle = json.loads((OUT / (name + ".json")).read_text())
        assert bundle["selection"] == selection
        assert bundle["bace_support"]["support_sets"] == []
        assert all(c["supported"] is True for c in bundle["native_claims"].values())
        assert all(bundle["checks"].values())
        for quote in bundle["original_generated_quotations"]:
            assert quote in bundle["generated_text"]
        for label in expected_entailments.get(name, []):
            card = next(c for c in bundle["full_prompt_evidence"] if c["prompt_label"] == label)
            assert bundle["native_claims"]["ragchecker"]["evidence_verdicts"][card["evidence_id"]] == "Entailment"
        counts[name] = len(bundle["full_prompt_evidence"])
        docs += [OUT / (name + "_full_evidence.md")]
    broken = []
    for doc in docs:
        for target in re.findall(r"\]\(([^)]+)\)", doc.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            if not (doc.parent / target).resolve().exists():
                broken.append({"document": str(doc.relative_to(ROOT)), "target": target})
    assert not broken, broken
    rows = json.loads((OUT / "verified_source_rows.json").read_text())
    assert len(rows) == 7
    assert len(counts) == 5
    assert counts["deutsche_bank_employee_population"] == 20
    assert all(n == 30 for name, n in counts.items() if name != "deutsche_bank_employee_population")
    output_files = docs + [OUT / "banco_bpm_2022_p15.png", OUT / "banco_bpm_2022_p15.txt",
        OUT / "expansion_review_notes.json", OUT / "verified_source_rows.json"]
    result = dict(status="PASS", checked_at_utc=datetime.now(timezone.utc).isoformat(),
        command="/home/muwang/.local/share/bace-writing-skills/venv/bin/python paper/analysis/disagreement_cases/verify_case_documents.py",
        script_sha256=sha256(Path(__file__)), broken_local_links=broken, changed_input_files=changed,
        verified_bundles=len(counts), selection_counts={"principal_illustrations": 4, "qualified_candidates": 1},
        unique_csv_source_rows=len(rows), native_claim_labels_verified=True,
        full_evidence_card_counts=counts, documents={str(p.relative_to(ROOT)): sha256(p) for p in output_files},
        scope="Artifact consistency only. Scientific interpretation and its qualifications are recorded in the reports; no independent human validation.")
    (OUT / "document_checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "verified_bundles": len(counts), "unique_csv_source_rows": len(rows), "broken_links": len(broken)}))


if __name__ == "__main__":
    main()
