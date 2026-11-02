# BACE paper workspace

Target: **Nature Sustainability, Article**  
Initialized: **29 September 2026**  
Status: **The LaTeX manuscript includes Introduction, Results, Methods and all four current main figures with full legends, updated on 2 October 2026. The Introduction has original-source citations and recorded evidence checks. Abstract, Discussion, author details and declarations remain incomplete. Human validation remains pending locally.**

This directory holds the preparation and writing materials for the BACE paper.
All paper materials are written in English.

## Start here

1. Read [Paper blueprint](01_paper_blueprint.md) for the agreed positioning, proposed questions and contributions. Revision 5 links the selected Results storyline.
2. Read [Evidence map](02_evidence_map.md) to see which findings have supporting data and which conclusions need further evidence.
3. Read [Research foundation](03_research_foundation.md) for the English background, problem, gap, purpose and research questions, with explicit citation tasks.
4. Read [Research gap verification](04_research_gap_verification.md) for the defensible contribution, direct precedents and remaining access limits.
5. Use [References](references.bib), the [source index](literature/SOURCE_INDEX.md) and [citation ledger](literature/citation_ledger.md) to trace literature claims.
6. Read [Results storyline and main-figure plan](05_results_storyline.md) for the three principal findings, exact source tables, interpretation limits and proposed display composition.
7. Use the [numeric ledger](analysis/storyline/numeric_ledger.json) and [verification provenance](analysis/storyline/provenance.json) when drafting Results and Methods from this snapshot.
8. Read [Expanded disagreement examples](07_expanded_disagreement_examples.md) for the current five-case selection, including incident-versus-worker counts and an original-PDF check of an emissions outcome misread as a target. The [initial report](06_verified_disagreement_examples.md) preserves the first two cases. These are qualified source-inspected illustrations, not independent human validation.
9. Review the [Results draft](08_results_draft.md), with four manuscript subsections and a paragraph-level evidence ledger, alongside the [full Methods draft](10_methods_draft.md) and its Results–Methods crosswalk. The [Methods outline](09_methods_evidence_outline.md) remains the earlier planning record.
10. Use [Results verification](analysis/results_draft/provenance.json) for arithmetic, cohorts and local annotation status, and [Methods verification](analysis/methods_draft/provenance.json) for source/configuration checks and complete paragraph correspondence. [Methods citation occurrences](analysis/methods_draft/citation_occurrences.json) identify original full-text support for the two methodological citations.
11. Open the [compiled manuscript PDF](manuscript/main.pdf) or edit [main.tex](manuscript/main.tex). The [Overleaf source ZIP](manuscript/bace_overleaf.zip) is ready for upload; [project instructions](manuscript/README.md) describe compilation and editing. The [migration record](analysis/latex_draft/migration.json) retains the mapping from the 39 source paragraphs to LaTeX.
12. Review [Figure 1](manuscript/figures/fig1_study_design.pdf), its [legend and source notes](analysis/fig1/legend.md), [figure contract](analysis/fig1/FIGURE_CONTRACT.md) and [numerical source ledger](analysis/fig1/source_data.csv). The figure distinguishes the completed automated workflow from the prepared human-review branch.
13. Review [Figure 2](manuscript/figures/fig2_support.pdf), its [legend and source notes](analysis/fig2/legend.md), [figure contract](analysis/fig2/FIGURE_CONTRACT.md), [per-disclosure source data](analysis/fig2/disclosures.csv), [claim composition](analysis/fig2/claim_composition.csv) and [task estimates](analysis/fig2/task_estimates.csv). The figure distinguishes equal disclosure weighting from pooled claim weighting and preserves the saved company-cluster intervals.
14. Review [Figure 3](manuscript/figures/fig3_diagnoses_cases.pdf), its [legend and source notes](analysis/fig3/legend.md), [figure contract](analysis/fig3/FIGURE_CONTRACT.md), [diagnostic composition](analysis/fig3/diagnosis_composition.csv), [complete selected-case evidence](analysis/fig3/case_evidence.json) and [original-report checks](analysis/fig3/original_source_checks.json). The two fixed cases explain an automated temporal diagnosis and expose a source-extraction limitation; they are not a representative validation sample.
15. Review [Figure 4](manuscript/figures/fig4_native_comparison.pdf), its [legend and source notes](analysis/fig4/legend.md), [figure contract](analysis/fig4/FIGURE_CONTRACT.md), [paired source rows](analysis/fig4/paired_disclosures.csv), [paired mean differences](analysis/fig4/paired_differences.csv) and [exact distribution coordinates](analysis/fig4/ecdf_coordinates.csv). All panels share the same 1,798 disclosures; native score gaps and inventory differences do not establish comparative accuracy.

16. Read the six-paragraph Introduction in [the active manuscript](manuscript/main.tex), with its [argument and evidence guide](analysis/introduction_draft/README.md), [citation occurrences](analysis/introduction_draft/citation_occurrences.json) and [numerical ledger](analysis/introduction_draft/numeric_ledger.json). The original 2023 ESRS passage now supports the actual reporting-background wording. Earlier foundation and gap-review documents retain their dated status.

From this migration onward, `manuscript/main.tex` is the active manuscript. The
Markdown Results and Methods remain dated source drafts with evidence ledgers.
Track subsequent scientific revisions in the LaTeX manuscript and their evidence;
do not maintain independently edited copies without an explicit synchronization.
The build command compiles the current TeX and never overwrites it from Markdown.

The author confirmed the paper's main positioning on 29 September 2026.
The title, exact question wording, section allocation and figure plan remain proposals.
The evidence map records observations from the current saved analysis; it does not certify evaluator validity.

## Writing sequence

| Step | Deliverable | Completion criterion |
|---|---|---|
| 1. Establish the argument | Revised blueprint | The problem, gap, questions and intended contributions form a consistent chain. |
| 2. Connect findings to evidence | Claim-to-source and figure plan | Each principal result has an identifiable source, denominator, interpretation and limitation. |
| 3. Settle the analytical scope | Documented case cohort and validation status | Planned and analyzed samples are distinguished; human-validation claims match completed work. |
| 4. Draft Results and Methods | First substantive manuscript sections | Results answer the research questions; Methods describe the procedures actually used. |
| 5. Draft Introduction and Discussion | Complete main-text argument | Literature supports the gap; implications remain within the evidence. |
| 6. Write Abstract and finalize Title | Concise summary of the completed argument | Every abstract result is supported in the main text. |
| 7. Prepare submission materials | References, statements, supplementary material and cover letter | Sources, declarations, figures and journal requirements have been checked. |

Steps 1, 2 and the existing Methods can progress while outstanding validation is completed.
The Introduction, Results and connected Methods drafts have been incorporated into the LaTeX manuscript for author review. Methods describes completed procedures and the prepared human-assessment design separately; its crosswalk covers every Results paragraph. All four current main figures and their full legends are included. The next deliverable is Discussion, followed by Abstract. Human-assessment results remain pending completed annotations and analysis. Source-access details and author declarations remain explicitly unresolved.

## Journal constraints

The [official content-type guidance](https://www.nature.com/natsustain/content), checked on 29 September 2026, specifies:

- Title: up to 10 words or 90 characters.
- Abstract: up to 150 words, without references.
- Main text: up to 3,500 words, excluding the abstract, Methods, references and figure legends.
- Order: Introduction without a heading, then Results, Discussion and Methods.
- Results, Discussion and Methods: topical subheadings.
- Main display items: up to six figures and tables combined.
- References: typically up to 50, as a guideline.

Recheck the guidance when preparing the submission.
The proposed framing also considers the journal's [aims and scope](https://www.nature.com/natsustain/aims).

## Source materials and status

- [Experiment overview](../BACE/README.md) and [frozen protocol](../BACE/PROTOCOL.md).
- [BACE method definition](../docs/generation_evaluation.md).
- [Analysis guide](../BACE/analysis/README.md) and [analysis contract](../BACE/analysis/ANALYSIS_SPEC.md).
- [Existing Introduction evidence map](../docs/main/introduction/introduction_logic_chain_and_evidence.md).
- [Formal human-validation guide](../BACE/analysis/validation/README.md).

The inspected saved run and analysis contain 1,798 completed BACE cases out of 1,800 planned cases; the saved run status is `incomplete`.
The current paired comparison also contains 1,798 cases.
Record any later completion and refresh affected manuscript numbers from a consistent analysis version.

The local formal reviewer workbooks each contain 600 unique sample rows; direct inspection found their support and diagnosis cells blank. See the [workbook status check](analysis/storyline/validation_status.json). This check does not establish whether annotated copies exist elsewhere.
The guide defines conditional judgment validation, not independent validation of the entire pipeline.

Keep experiment artifacts and analysis exports in their existing locations and reference them from this directory.
Record future writing decisions separately from the frozen experimental protocol.
The research questions below organize a post-experiment paper and must not be represented as preregistered hypotheses.
