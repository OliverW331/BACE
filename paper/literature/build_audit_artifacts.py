"""Assemble the reviewed bibliography, source index and occurrence-level ledger.

The semantic readings are authored in source_evidence.json. This script checks
provenance and citation coverage; it does not automate scientific verification.
"""
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAPER = ROOT.parent
PROJECT = PAPER.parent
sys.path.insert(0, str(PROJECT / ".agents/skills/citation-management/scripts"))
from _common import parse_bibtex


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence = json.loads((ROOT / "source_evidence.json").read_text())
    by_key = {x["key"]: x for x in evidence}
    mapping = {k.lower(): v for k, v in json.loads((ROOT / "doi_key_map.json").read_text()).items()}
    mapping["10.48550/arxiv.2405.14486"] = "refchecker2024_arxiv"
    raw = (ROOT / "doi_metadata_raw.bib").read_text() + "\n" + (ROOT / "additional_metadata_raw.bib").read_text()
    entries = parse_bibtex(raw)
    bib = {}
    corrections = []
    for entry in entries:
        fields = dict(entry["fields"])
        doi = fields.get("doi", "").lower()
        if doi not in mapping:
            continue
        key = mapping[doi]
        old_key = entry["key"]
        if key in bib:
            raise ValueError(f"Duplicate bibliography entry: {key}")
        fields["url"] = "https://doi.org/" + fields["doi"]
        fields["title"] = "{" + fields["title"] + "}"
        if fields.get("pages"):
            fields["pages"] = fields["pages"].replace("–", "--")
        if key == "dndscore2025":
            old = fields["pages"]
            fields["pages"] = "23609--23626"
            corrections.append({"key": key, "field": "pages", "before": old, "after": fields["pages"], "basis": "ACL publisher citation_firstpage/citation_lastpage and the printed page numbers in the original PDF agree; DOI metadata differs."})
        if key == "factscore2023":
            old = fields["author"]
            fields["author"] = old.replace("Koh, Pang and", "Koh, Pang Wei and")
            corrections.append({"key": key, "field": "author", "before": "Koh, Pang", "after": "Koh, Pang Wei", "basis": "Original PDF page 1 spells Pang Wei Koh; publisher/DOI metadata omits Wei. Author position is unchanged."})
        if key == "susgen2025":
            fields["author"] = fields["author"].replace("Hejia, Huang", "Huang, Hejia").replace("Wei Jie, Yeo", "{Yeo Wei Jie}")
            corrections.append({"key": key, "field": "author", "before": "Hejia, Huang; Wei Jie, Yeo", "after": "Huang, Hejia; {Yeo Wei Jie}", "basis": "Original PDF page 1 spells Hejia Huang and Yeo Wei Jie. The latter is retained as a literal full name to avoid imposing an unverified family-name split; author order is unchanged."})
        if key == "ragchecker2024":
            fields["author"] = fields["author"].replace("Jiayang, Cheng", "{Cheng Jiayang}")
            corrections.append({"key": key, "field": "author", "before": "Jiayang, Cheng", "after": "{Cheng Jiayang}", "basis": "The printed original spells Cheng Jiayang. Retain the literal full name rather than imposing a family-name split; author position is unchanged."})
        if key == "refchecker2024_arxiv":
            fields["eprint"] = "2405.14486v1"
            fields["archiveprefix"] = "arXiv"
            fields["note"] = "Preprint, version 1, submitted 23 May 2024"
        if key == "esghrag2025":
            fields["eid"] = "1103"
        if key == "europe2026":
            fields["eid"] = "5940"
        bib[key] = {"type": entry["type"], "fields": fields, "retrieved_key": old_key}
    assert set(bib) == set(by_key), (set(by_key) - set(bib))
    rendered = []
    for key, e in bib.items():
        lines = [f"@{e['type']}{{{key},"]
        lines.extend(f"  {name} = {{{value}}}," for name, value in e["fields"].items())
        lines.append("}")
        rendered.append("\n".join(lines))
    # Later original-source verifications are separate from this dated review.
    # Retain their registered entries when rebuilding the shared library.
    additions = ROOT / "additional_references.bib"
    if additions.exists():
        extra = additions.read_text().strip()
        extra_keys = re.findall(r"@\w+\{([^,]+),", extra)
        assert len(extra_keys) == len(set(extra_keys))
        assert not set(extra_keys).intersection(bib), "Duplicate bibliography key"
        if extra:
            rendered.append(extra)
    (PAPER / "references.bib").write_text("\n\n".join(rendered) + "\n")
    save(ROOT / "metadata_corrections.json", corrections)
    save(ROOT / "citation_key_mapping.json", {k: {"retrieved_key": v["retrieved_key"], "doi": v["fields"]["doi"]} for k, v in bib.items()})

    catalog = []
    index = ["# Verified source index", "", "Checked on 29 September 2026. Entries describe the specific inspected passages, not whole-paper endorsements.", "", "Citation keys match `../references.bib`. Pending-access candidates are recorded separately in the gap report.", ""]
    for e in evidence:
        key = e["key"]
        folder = ROOT / "sources" / key
        r = json.loads((folder / "retrieval.json").read_text())
        pdf, txt = folder / "original.pdf", folder / "fulltext.txt"
        assert pdf.exists() and txt.exists() and r.get("fulltext_extracted"), key
        assert sha(pdf) == r["pdf_sha256"] and sha(txt) == r["text_sha256"], key
        fulltext = txt.read_text()
        assert all(f"=== PDF page {p} ===" in fulltext for p in e["pages"]), key
        version = "arXiv:2405.14486v1, submitted 23 May 2024" if key == "refchecker2024_arxiv" else "Publisher/conference version of record retrieved 29 September 2026"
        rec = dict(e, title=bib[key]["fields"]["title"].strip("{}"), authors=bib[key]["fields"].get("author"), canonical_identifier=bib[key]["fields"]["doi"], source_version=version, source_url=r.get("pdf_url", r["url"]), original_pdf=str(pdf.relative_to(PAPER)), fulltext=str(txt.relative_to(PAPER)), pdf_sha256=sha(pdf), fulltext_sha256=sha(txt), checked_date="2026-09-29", metadata_status="Checked against source landing metadata and original author/title pages; documented corrections retained")
        catalog.append(rec)
        index += [f"## {key}", "", rec["title"], "", f"[Original PDF](sources/{key}/original.pdf) · [Extracted text](sources/{key}/fulltext.txt) · [Canonical identifier](https://doi.org/{rec['canonical_identifier']})", "", f"Version: {version}.", "", f"Locator: {e['locator']}.", "", f"Verified statement: {e['claim']}", "", f"Evidence paraphrase: {e['paraphrase']}", "", f"Limits: {e['limits']}", ""]
    save(ROOT / "source_catalog.json", catalog)
    (ROOT / "SOURCE_INDEX.md").write_text("\n".join(index))
    catalog_map = {x["key"]: x for x in catalog}

    ledger = []
    docs = [PAPER / "03_research_foundation.md", PAPER / "04_research_gap_verification.md"]
    for doc in docs:
        section = ""
        for line_no, line in enumerate(doc.read_text().splitlines(), 1):
            if line.startswith("## "):
                section = line[3:]
            groups = re.findall(r"\[((?:@[^\]]+))\]", line)
            for group in groups:
                keys = re.findall(r"@([A-Za-z0-9_]+)", group)
                for key in keys:
                    src = catalog_map[key]
                    assertion = line.split("|")[2].strip() if line.startswith("|") else line
                    assertion = re.sub(r"\[\@[^\]]+\]", "", assertion).strip()
                    rec = {
                        "id": f"CIT-{len(ledger)+1:03d}", "cite_key": key,
                        "manuscript_location": str(doc.relative_to(PAPER)), "line": line_no, "section": section,
                        "asserted_claim": assertion, "canonical_identifier": src["canonical_identifier"],
                        "source_version": src["source_version"], "source_url": src["source_url"],
                        "local_source": src["original_pdf"], "source_locator": src["locator"], "access_date": "2026-09-29",
                        "evidence_type": "faithful paraphrase of original full text", "evidence_paraphrase": src["paraphrase"],
                        "source_supported_component": src["claim"], "support_verdict": "QUALIFIED" if len(keys)>1 else "DIRECT",
                        "limitations": src["limits"] + (" Grouped citation: this source supports its stated component, not every component of the combined sentence." if len(keys)>1 else ""),
                        "source_pdf_sha256": src["pdf_sha256"], "manuscript_sha256": sha(doc)
                    }
                    ledger.append(rec)
    save(ROOT / "citation_ledger.json", ledger)
    with (ROOT / "citation_ledger.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ledger[0])); w.writeheader(); w.writerows(ledger)
    md = ["# Citation occurrence ledger", "", "Each occurrence records the exact local claim and original-source evidence. DIRECT means that the inspected passage supports the stated source-specific claim. QUALIFIED marks a grouped claim for which this source supports only its identified component.", "", "These are source-specific literature judgments, not validation of BACE. Full machine-readable records are in [JSON](citation_ledger.json) and [CSV](citation_ledger.csv).", ""]
    for x in ledger:
        md += [f"## {x['id']}: {x['cite_key']}", "", f"Occurrence: `{x['manuscript_location']}:{x['line']}`, {x['section']}.", "", x["asserted_claim"], "", f"Verdict: {x['support_verdict']}. Source: [PDF]({x['local_source'].removeprefix('literature/')}), {x['source_locator']}.", "", f"Evidence: {x['evidence_paraphrase']}", "", f"Limits: {x['limitations']}", ""]
    (ROOT / "citation_ledger.md").write_text("\n".join(md))

    log = ["# Search record", "", "Targeted discovery conducted 29 September 2026. Exact raw responses are retained. Result totals are provider-reported; returned hit sets are bounded and are not an exhaustive screened corpus. A failed request is not zero matches. Queries with Boolean-looking syntax returned broad ranked sets and are not treated as strict intersections.", "", "| ID | Provider | Exact query | HTTP status | Returned records | Record |", "|---|---|---|---|---|---|"]
    hit_rows = []
    canonical_dois = {x["canonical_identifier"].lower(): x["key"] for x in catalog}
    aliases = {"10.48550/arxiv.2502.10855":"claimify2025", "10.48550/arxiv.2408.08067":"ragchecker2024"}
    canonical_dois.update(aliases)
    for path in sorted((ROOT / "searches").glob("s[0-9][0-9].json")):
        s = json.loads(path.read_text())
        results = s.get("results", [])
        log.append(f"| {s['id']} | {s['backend']} | {s['query']} | {s.get('http_status', 'failed')} | {len(results)} | [record](searches/{path.name}) |")
        for rank, hit in enumerate(results, 1):
            doi = (hit.get("doi") or "").lower().removeprefix("https://doi.org/")
            key = canonical_dois.get(doi)
            disposition = "SELECTED_ORIGINAL_SOURCE_REVIEW" if key else "NOT_ASSESSED_IN_THIS_TARGETED_REVIEW"
            if doi in {"10.1051/epjconf/202637001014", "10.1051/epjconf/202637001014/pdf", "10.1109/ecbios61468.2024.10885500"}:
                disposition = "SELECTED_UNVERIFIED_FULL_TEXT"
            hit_rows.append({"query_id":s["id"], "rank":rank, "title":hit.get("title"), "doi":doi, "source_key":key, "disposition":disposition})
    log += ["", "Consensus attempts failed because the connector was not connected: [attempt record](consensus_attempts.json).", "", "The initial connectivity/routing probes preceded the logged query batches and are not treated as a reproducible search corpus. The recorded NeurIPS index lookup resolved RAGChecker to the official published paper.", "", "Selection dispositions identify the works examined for this bounded comparison. Unassessed records are not scientific exclusions. See [search hit dispositions](search_hit_dispositions.json)."]
    (ROOT / "SEARCH_LOG.md").write_text("\n".join(log)+"\n")
    save(ROOT / "search_hit_dispositions.json", hit_rows)

    rejected = [
        {"claim":"Earlier factuality methods do not preserve material qualifiers.","verdict":"CONTRADICTED","sources":["veriscore2024","claimify2025","dndscore2025"]},
        {"claim":"BACE is the first approach to assess support from multiple evidence items.","verdict":"CONTRADICTED","sources":["alce2023"]},
        {"claim":"Human support or hallucination evaluation is absent in sustainability applications.","verdict":"CONTRADICTED","sources":["chatreport2023","esgbench2026"]},
        {"claim":"Erroneous synthesis of retrieved sustainability evidence has not previously been documented.","verdict":"CONTRADICTED","sources":["chatreport2023"]}
    ]
    save(ROOT / "rejected_claims.json", rejected)
    manifest = {"checked_date":"2026-09-29", "review_type":"targeted original-source comparison", "canonical_fulltext_sources":len(catalog), "citation_occurrences":len(ledger), "inaccessible_candidates":["ecosmart2024","selfeval2026"], "rendered_pages_inspected":["previews/veriscore_page3.png","previews/esgbench_page4.png"], "command":"/home/muwang/.local/share/bace-writing-skills/venv/bin/python paper/literature/build_audit_artifacts.py", "python":sys.version, "input_hashes":{str(p.relative_to(PAPER)):sha(p) for p in [ROOT/"source_evidence.json",ROOT/"doi_metadata_raw.bib",ROOT/"additional_metadata_raw.bib",*docs]}, "script_sha256":sha(Path(__file__)), "numerical_results":"No experiment metrics recalculated or changed; counts here describe the audit artifacts only."}
    save(ROOT / "audit_manifest.json", manifest)
    print(json.dumps({"sources":len(catalog),"citation_occurrences":len(ledger),"metadata_corrections":len(corrections)},indent=2))


if __name__ == "__main__":
    main()
