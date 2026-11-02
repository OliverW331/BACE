# Literature evidence workspace

This directory records the targeted research-gap review completed on 29 September 2026. It supports the [gap report](../04_research_gap_verification.md) and [research foundation](../03_research_foundation.md).

## Read and inspect

- [Source index](SOURCE_INDEX.md): the inspected passages, versions and limitations for 15 original full texts.
- [Citation ledger](citation_ledger.md): 32 source occurrences in the two working documents, with corresponding [JSON](citation_ledger.json) and [CSV](citation_ledger.csv) records.
- [Search log](SEARCH_LOG.md): exact queries and bounded returned hit sets. Failed retrievals and unassessed hits remain explicit.
- [Bibliography](../references.bib): stable citation keys, generated from retrieved DOI metadata with [documented corrections](metadata_corrections.json).
- [Audit manifest](audit_manifest.json): source and occurrence counts, build command and input hashes.

`sources/` contains retrieved originals, extracted text and retrieval records. Source-page locators refer to one-based PDF pages, which can differ from printed pagination. RefChecker is explicitly versioned as an arXiv preprint; the other cited sources use publisher or conference versions.

`source_evidence.json` holds the manually reviewed source statements and faithful paraphrases. `source_catalog.json` adds identifiers, versions and source hashes. `rejected_claims.json` records proposed broad novelty claims contradicted by the inspected literature. Relevant inaccessible sources are described in the gap report, not counted among verified full texts.

The comparison is targeted. It does not establish an exhaustive literature search, exclusive priority or the scientific validity of BACE. The background citation task L1 was pending at the date of that review.

On 2 October 2026, the [Introduction verification](../analysis/introduction_draft/README.md) resolved L1 for the actual manuscript wording using the [original 2023 ESRS regulation](sources/esrs2023/original.pdf), ESRS 1 paragraph 2 and Appendix B QC 5 and QC 13–14. This later review has a separate occurrence ledger and retrieval record. Christensen et al. remains an unused, unverified lead. The original edition is not presented as a current-law consolidation. The ESRS entry is registered in [additional references](additional_references.bib) and included in the shared bibliography; the dated source catalog and gap-review counts above are unchanged.

## Rebuild local audit artifacts

Run from the repository root:

```bash
/home/muwang/.local/share/bace-writing-skills/venv/bin/python paper/literature/build_audit_artifacts.py
```

The script checks stored source hashes and regenerates the working bibliography, source index, citation ledger, search log and manifest. It retains entries registered in `additional_references.bib` when rebuilding the shared bibliography; their later verification remains in its own records. It reads the existing semantic review; it does not perform or replace full-text verification. Review the source statements whenever manuscript claims change, then rebuild to refresh occurrence locations and hashes.

`retrieve_sources.py` and the query/source JSON files preserve the public retrieval procedure. Repeating a network search may return different results; the saved response files document this review's observations. No frozen experiment environment or output is used as a writing-tool installation target.
