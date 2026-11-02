# Introduction drafting and integration

Prepared 2 October 2026 for Nature Sustainability, Article. The active prose is
in [main.tex](../../manuscript/main.tex), between `BEGIN_INTRODUCTION` and
`END_INTRODUCTION`. This folder records evidence rather than a second editable
copy of the manuscript.

## Argument

| Paragraph | Purpose | Evidence or interpretation boundary |
|---|---|---|
| I01 | Connect reporting purpose to faithful representation and verifiability. | Original 2023 ESRS, not a claim about current legal applicability. Final sentences motivate the study. |
| I02 | Establish AI-assisted analysis and drafting as the setting. | ChatReport and SusGen; no claim of widespread corporate adoption. |
| I03 | Explain entity, time, metric and other factual boundaries. | Conceptual examples, not estimates of observed error frequency. |
| I04 | Acknowledge established evaluation principles. | Atomic support, context preservation and joint evidence are prior work. |
| I05 | Connect domain precedents to the measurement question. | Human ESG support evaluation already exists; no exclusive-priority claim. |
| I06 | State the aim, approach, analysed scope and bounded contribution. | Planned and completed samples differ; automated judgments require independent validation. |

The Introduction organizes the completed descriptive study. It does not introduce
preregistered hypotheses, claim comparative accuracy or present human validation
as complete. RQ1–RQ3 map to support patterns, diagnosis and evaluator comparison;
the human-assessment question remains conditional on completed annotations.

## Verification records

- [Citation occurrences](citation_occurrences.json): eleven Introduction occurrences across ten original sources, with exact claims, identifiers, versions, locators, retrieval dates, excerpts, limitations and hashes. The two existing Methods occurrences remain in the separate LaTeX migration record.
- [Numerical ledger](numeric_ledger.json): counts and design values linked to saved calculations, cohort, units, missingness and upstream provenance.
- [Argument map](argument_map.json): distinguishes literature assertions, conceptual reasoning and study-specific claims.
- [Draft record](draft_record.json): reviewed Introduction and paragraph hashes.
- [Integration baseline](baseline.json): pre-edit Results, Methods and figure hashes; these scientific blocks and figure environments are preserved.
- [Verification script](verify_introduction.py): checks source identity, claims and citations, numerical records, rendered prose, figure preservation and bibliography coverage; writes `provenance.json` and `word_counts.json`.
- [Evidence preparation script](prepare_evidence.py): records the manually reviewed assertions. Re-running it does not replace original-source review when prose changes.

L1 is resolved for the actual Introduction wording through ESRS 1 paragraph 2
and Appendix B QC 5 and QC 13–14. The official PDF was retrieved at the UTC time
in its [retrieval record](../../literature/sources/esrs2023/retrieval.json), on
2 October in the author's Europe/Zurich timezone. The unused Christensen et al.
lead was not verified. Earlier planning records remain dated historical documents.
The two inaccessible close comparisons in the gap report remain unresolved;
neither is used to support an assertion here.

## Reproduce local checks

From the repository root, after any reviewed manuscript edit:

```bash
(cd paper/manuscript && /home/muwang/.local/share/bace-writing-skills/venv/bin/python build.py)
/home/muwang/.local/share/bace-writing-skills/venv/bin/python paper/analysis/methods_draft/verify_methods.py
/home/muwang/.local/share/bace-writing-skills/venv/bin/python paper/analysis/introduction_draft/verify_introduction.py
/home/muwang/.local/share/bace-writing-skills/venv/bin/python paper/analysis/latex_draft/verify_latex.py
```

The last check compiles the source ZIP in an isolated local directory. This
does not upload the unpublished manuscript or establish that it is ready for
submission. Discussion, Abstract, declarations and outstanding validation remain
separate tasks. Figure-specific earlier QA records describe their dated PDFs;
the current integration record checks unchanged artwork in the updated manuscript.
