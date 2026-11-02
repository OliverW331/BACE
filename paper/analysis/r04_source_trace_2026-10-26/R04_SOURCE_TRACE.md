# R04: source-to-EC mapping and missing table context

Access date: 26 October 2026. Case: OMV, target year 2023, G1-2. This document clarifies saved records; it does not replace frozen evidence, claims, scores or workbooks.

## Correct mapping

| Displayed item | Actual source | Saved extraction / selection status |
| --- | --- | --- |
| Evidence 5: suppliers and contractors; on-time payment | OMV Sustainability Report 2019, PDF page 159; narrative card spanning pages 159-160 | Zero claims in direct extraction, integrated review, atomicity output and final deduplicated inventory |
| EC01: average invoice-payment period of 60.0 days | Evidence 14, Corporate Sustainability Tracker, reporting year 2023 | The sole EC selected as a candidate for the target DC |

**EC01 is a local candidate-list alias, not a source-card identifier. It is not an EC extracted from Evidence 5.**

Stable identifiers:

- Evidence 5: `pdf_narrative::4a868d73-3310-4e93-a8dc-a6b88b252509::sustainability_report::2019::p159::c0901`.
- Evidence 14: `csv::4a868d73-3310-4e93-a8dc-a6b88b252509::2023::7c966679-3964-4ebe-bc33-0e96343dca51`.
- EC01: `ec_0dad29aff963f685f6c084e94770eee8`.
- Target DC: `dc_c34e88b73a00b1cf0682594cb512f84d`.

## What the original PDF says

Visual inspection of page 159 confirms the following row/column relationship:

| Table role | Original text |
| --- | --- |
| Stakeholder group | Suppliers and contractors |
| Column heading | Key topics and concerns raised by stakeholders |
| Listed item | On-time payment |

The same column lists procurement regulations, stipulations of the Code of Conduct, fair contract and adequate working conditions. Supplier audits, field visits, supplier events and contractor management meetings belong to a different column, headed `Type of OMV engagement`.

The supplied narrative card flattens these different columns together and omits the table headings. None of the 22 supplied cards contains the searched headings `Key topics and concerns`, `Stakeholder groups`, or `Type of OMV engagement`. Only Evidence 5 contains `On-time payment`.

Based on the original PDF layout, a possible source-faithful historical proposition is:

> OMV's 2019 sustainability report lists on-time payment among the key topics and concerns raised by suppliers and contractors.

This is an audit interpretation of the original PDF, **not a saved model EC**. The missing table heading must not be treated retrospectively as text that the original extractor received. Whether this historical statement supports an unqualified claim in a 2023 disclosure remains a separate temporal-applicability question.

## Where the information disappears

The direct extraction call `ecx_ded17c940b4c124ac8ceb8258dc1e896` returned the following for Evidence 5:

```json
{
  "claims": [],
  "unextracted_spans": [{
    "reason": "document_structure",
    "explanation": "Navigation text and predicate-free list items."
  }]
}
```

The full excluded quotation is retained in `trace.json`. Both later review stages returned an empty patch for this card. The atomicity prompt expressly says `An empty source unit must stay empty`, so that stage could not restore the missing relation. There are no Evidence 5 occurrences in the final inventory of 85 ECs.

Candidate selection receives the final EC inventory, not the original PDF table. It selects the payment-duration EC from Evidence 14. The support judge then receives just that one EC with the target DC. This establishes an upstream evidence-retention problem; it is not a case where a correctly extracted Evidence 5 EC was merely overlooked during candidate selection.

## Why the reader makes the pairing look wrong

The [reader builder](/home/muwang/master_thesis/paper/analysis/reader_layout_2026-10-22/build_minimal_readers.py:75) assigns `EC01`, `EC02`, etc. by position in the DC's candidate list. It selects source excerpts independently, and explicitly selects the Evidence 5 supplier-list passage for R04 at lines 92-94.

The [rendering code](/home/muwang/master_thesis/paper/analysis/reader_layout_2026-10-22/build_minimal_readers.py:234) prints the selected evidence excerpts followed by the selected candidate ECs. It labels ECs only with their local alias and text; it omits their source evidence number and does not display the extraction status of the preceding evidence. Thus the two independent selections appear to form a source/extraction pair.

The saved EC provenance is correct: it points to Evidence 14. The presentation hides that relationship. `1 of 1 shown` means one of the target DC's one candidate EC is displayed; it does not mean Evidence 5 produced one EC.

An unambiguous reader should display:

```text
Selected source passage
2019 | Evidence 5 | OMV sustainability report, page 159
[Supplier stakeholder-list excerpt]
Saved ECs from Evidence 5: 0
Direct-extraction reason: document_structure / predicate-free list items.

Candidate EC actually supplied to the BACE support judge
EC01 | Source: Evidence 14 | 2023 | Corporate Sustainability Tracker
[Saved average-payment-period EC, unchanged]
```

This panel is a proposed clarification, not a claim that the existing XLSX files have been rebuilt.

## Interpreting the saved results

- Original BACE: unsupported, diagnosed as inferential inflation, using only the 2023 payment-duration EC at the support stage.
- RAGAS-style and RAGChecker-style BACE variants: unsupported, using the same candidate EC input; these are not runs on the original evidence cards.
- Native RAGAS: supported, with the saved reason `The supplier and contractor relationship list includes on-time payment.`
- Native RAGChecker: supported; its per-card result for Evidence 5 is `Entailment`, while Evidence 14 is `Neutral`.

The input representation differs at the judgment stage. This example therefore cannot establish that BACE's support prompt is simply more conservative than the native prompts. It also does not, by itself, resolve the 2019-to-2023 temporal question or prove either evaluator correct.

## Verification and artifacts

`audit_r04.py` reconstructs the mapping from the original saved files, verifies the packet's final EC inventory and candidate EC against those files, and checks 14 read artifacts against their execution-receipt hashes. `trace.json` preserves the relevant raw extraction output, source cards, candidate/support input, comparator results and prompt-variant records. `provenance.json` records input hashes and the access date. No model calls or frozen-artifact edits were made.

```bash
python paper/analysis/r04_source_trace_2026-10-26/audit_r04.py
```

Original page rendering:

![OMV 2019 sustainability report, page 159](/home/muwang/master_thesis/paper/analysis/r04_source_trace_2026-10-26/omv_2019_page_159.png)
