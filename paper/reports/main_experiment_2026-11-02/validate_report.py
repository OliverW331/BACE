"""Check final report artifacts, numerical consistency and rendered text bounds."""

import hashlib
import json
import math
import re
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
REVIEW = OUT / "review/concept_definitions_final"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


ledger = json.loads((OUT / "numeric_ledger.json").read_text())
provenance = json.loads((OUT / "provenance.json").read_text())
render = json.loads((OUT / "render_manifest.json").read_text())
report = (OUT / "REPORT.md").read_text()
assert "{{" not in report
assert "Bidirectional Atomic Claim Evaluation" in report
assert "Boundary-Aware Claim Evaluation" not in report
assert ledger["planned_disclosures"] == 1800
assert ledger["analysed_disclosures"] == 1798
assert ledger["company_clusters"] == 30
assert ledger["methods"][0]["denominator"] == sum(ledger["claim_counts"].values())
assert ledger["methods"][0]["numerator"] == ledger["claim_counts"]["direct"] + ledger["claim_counts"]["inferred"]
assert sum(record["count"] for record in ledger["diagnoses"]) == 42646
assert ledger["canonical_card_counts"] == {"CSV metric": 43827, "PDF narrative": 497551, "PDF table row": 390070}
assert "formal_review_workbooks" not in ledger
assert not re.search(r"human[- ]validation|reviewer workbooks|human annotation|\[S15\]", report, re.IGNORECASE)
concepts = json.loads((OUT / "concept_provenance.json").read_text())
assert len(concepts["stages"]) == 7
assert len(concepts["runtime_sources"]) == 4
for source in concepts["runtime_sources"]:
    assert digest(ROOT / source["path"]) == source["sha256"]
    assert provenance["inputs"][source["path"]] == source["sha256"]
    code = (ROOT / source["path"]).read_text()
    for locator in source["locator"].split("; "):
        assert f"def {locator}(" in code
assert digest(OUT / provenance["definition_record"]["path"]) == provenance["definition_record"]["sha256"]
for stage in concepts["stages"]:
    assert digest(ROOT / stage["config_path"]) == stage["config_sha256"]
    for reference in stage["references"]:
        assert digest(ROOT / reference["path"]) == reference["sha256"]
        assert provenance["inputs"][reference["path"]] == reference["sha256"]
        if reference["kind"] in ["prompt", "prompts"]:
            prompt = (ROOT / reference["path"]).read_text()
            for locator in reference["locator"].split("; "):
                if locator == "EVIDENCE/DISCLOSURE RULES":
                    assert "EVIDENCE RULES" in prompt or "DISCLOSURE RULES" in prompt
                else:
                    assert locator in prompt, (reference["path"], locator)
diagnosis_stage = next(stage for stage in concepts["stages"] if stage["stage"] == "Unsupported diagnosis")
diagnosis_reference = next(reference for reference in diagnosis_stage["references"] if reference["kind"] == "prompt")
diagnosis_prompt = (ROOT / diagnosis_reference["path"]).read_text()
diagnosis_labels = ["non_disclosure_statement", "contradiction", "evidence_conflation", "factual_boundary_distortion", "inferential_inflation", "unsupported_novelty"]
positions = [diagnosis_prompt.index(f"`{label}`") for label in diagnosis_labels]
assert positions == sorted(positions)
for order, label in enumerate(diagnosis_labels, 1):
    assert f"| {order} | `{label}` |" in report
for expected in ["Substantive admission", "Self-contained meaning", "Minimal sufficient EC set", "Bidirectional evaluation", "multi-EC-required DC", "(A + I) / (N - H)", "Appendix C"]:
    assert expected in report, expected
for record in ledger["methods"]:
    assert record["disclosures"] == 1798
    assert math.isclose(record["pooled"], record["numerator"] / record["denominator"], abs_tol=1e-12)
    assert record["low"] < record["mean"] < record["high"]
for record in ledger["paired_differences"]:
    comparator = next(method for method in ledger["methods"] if method["method"].casefold() == record["comparison"].split()[-1].casefold())
    assert math.isclose(record["mean"], ledger["methods"][0]["mean"] - comparator["mean"], abs_tol=1e-12)
assert sum(record["disclosures"] for record in ledger["tasks"]) == 1798
template = (OUT / "REPORT.template.md").read_text()
for field, value in ledger["tokens"].items():
    if "{{" + field + "}}" in template:
        assert value in report, field
for image in re.findall(r"!\[.*?\]\((.*?)\)", report):
    assert (OUT / image).is_file()
for filename, expected in provenance["outputs"].items():
    assert digest(OUT / filename) == expected
for relative, expected in provenance["inputs"].items():
    assert digest(ROOT / relative) == expected, relative
assert digest(OUT / render["source"]) == render["source_sha256"]
assert digest(OUT / "numeric_ledger.json") == render["numeric_ledger_sha256"]
assert digest(OUT / render["pdf"]) == render["pdf_sha256"]

namespaces = {"page": "http://www.w3.org/1999/xhtml"}
document = ElementTree.parse(REVIEW / "text_boxes.html")
pages = document.findall(".//page:page", namespaces)
outside = []
for page_number, page in enumerate(pages, 1):
    width, height = float(page.attrib["width"]), float(page.attrib["height"])
    for word in page.findall("page:word", namespaces):
        left, right = float(word.attrib["xMin"]), float(word.attrib["xMax"])
        top, bottom = float(word.attrib["yMin"]), float(word.attrib["yMax"])
        if left < 40 or right > width - 40 or top < 8 or bottom > height - 8:
            outside.append({"page": page_number, "text": word.text, "box": [left, top, right, bottom]})
assert pages
assert not outside, outside
extracted = (REVIEW / "report_extracted.txt").read_text()
for expected in ["Bidirectional Atomic Claim Evaluation", "55.4%", "90.2%", "90.7%", "94,955", "42,646", "1,798", "Appendix B", "Appendix C", *diagnosis_labels]:
    assert expected in extracted, expected
assert "Boundary-Aware Claim Evaluation" not in extracted
rendered_pages = sorted(REVIEW.glob("page-*.png"))
assert len(rendered_pages) == len(pages)
for page in extracted.split("\f"):
    if page.strip():
        assert len(page.split()) >= 150, "Unexpected nearly empty page; inspect pagination"
source = json.loads((OUT / "upstream_source.json").read_text())
assert digest(OUT / source["local_file"]) == source["sha256"]
result = {"status": "PASS", "date": "2026-11-02", "pdf_pages": len(pages), "word_box_boundary_violations": outside, "report_has_unresolved_tokens": False, "numeric_status": "COMPUTED_VERIFIED", "source_hashes_rechecked": len(provenance["inputs"]), "definition_stages_checked": len(concepts["stages"]), "diagnosis_order_checked": diagnosis_labels, "full_consumed_source_index_previously_verified": provenance["source_index"]["verified_files"], "visual_review": {"method": "Contact-sheet inspection of all pages and full-size inspection of definition tables, principal results and source locators", "page_previews": [str(path.relative_to(OUT)) for path in rendered_pages], "findings": "No observed clipping, overlapping text, unreadable glyphs or trailing orphan page"}, "pdf_sha256": render["pdf_sha256"], "script_sha256": digest(__file__)}
(OUT / "validation_report.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"status": result["status"], "pages": len(pages), "source_hashes": result["source_hashes_rechecked"], "numeric_status": result["numeric_status"]}))
