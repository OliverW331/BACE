# BACE results for the professor meeting

Snapshot checked: 8 October 2026 (Europe/Zurich).

The project now has a main descriptive study, native evaluator comparisons, diagnostic analyses, a completed support-prompt sensitivity experiment, and completed statistics for a sampled evidence-chain experiment. The two sensitivity experiments extend the results currently presented in the manuscript. Independent human validation remains pending in the inspected local materials.

## Suggested opening

“We observe a large difference between BACE and two native faithfulness evaluators. Controlled sensitivity experiments show that both judgment instructions and the evidence supplied to the judge affect BACE's support rates. Our next question is which disagreements reflect inadequate evidence, losses during processing, or different interpretation rules. Current automated scores alone cannot establish which evaluator is more accurate.”

## Completed results and their interpretation

### 1. Main study: support within supplied evidence

The planned design is 30 companies × 5 reporting years (2019–2023) × 12 ESRS tasks. The analysed and native paired cohort contains 1,798 disclosures; 2 BACE cases remain incomplete. These are generated company–year–task sections, not 1,798 independent companies. The main run's saved status remains `incomplete`.

The disclosure-macro support rate is **55.4%** (saved 95% company-cluster interval, **53.9–56.8%**). Across **94,955 DCs**, the claim-pooled composition is **34,430 direct (36.3%)**, **17,879 inferred (18.8%)**, and **42,646 unsupported (44.9%)**. Pooled support is 55.1%; it uses a different weighting from the disclosure mean. An unsupported judgment is not an independently verified factual error.

Task means range from **43.9% for workforce targets (S1-5)** to **62.5% for business conduct policies (G1-1)**. Treat these as descriptive heterogeneity, not an established causal task effect.

Show: [Figure 1: study design](/home/muwang/master_thesis/paper/manuscript/figures/fig1_study_design.pdf) and [Figure 2: support and task differences](/home/muwang/master_thesis/paper/manuscript/figures/fig2_support.pdf).

Source: [current case metrics](/home/muwang/master_thesis/BACE/analysis/outputs/snapshot/metrics.csv) and [saved numerical ledger](/home/muwang/master_thesis/paper/analysis/results_draft/verified_numbers.json). Point estimates and counts were reconciled again for this brief.

### 2. Unsupported-claim diagnoses

Of the 42,646 unsupported claims, BACE assigns **19,130 (44.9%)** to factual boundary distortion and **12,205 (28.6%)** to evidence conflation: **73.5% together**. These are outputs of an ordered automated diagnosis procedure. The denominator here is unsupported claims, unlike the all-claim composition above.

[Figure 3](/home/muwang/master_thesis/paper/manuscript/figures/fig3_diagnoses_cases.pdf) includes a historical-to-current policy interpretation and an ASML source-row association problem that challenges BACE's contradiction rationale. Present both the potential reporting problem and the evaluator's own limitation. The examples do not establish error prevalence.

### 3. Native evaluators disagree substantially

On the same 1,798 disclosures, mean native scores are **BACE 55.4%, RAGChecker 90.2%, and RAGAS 90.7%**. BACE-minus-comparator paired differences are **−34.9 pp** (95% interval −36.2 to −33.5) and **−35.3 pp** (−36.5 to −34.1), respectively.

Median claim counts are 52, 40 and 42, respectively. The methods use different inventories, evidence representations and judgment procedures; the difference is not an accuracy ranking.

Show: [Figure 4: native comparisons](/home/muwang/master_thesis/paper/manuscript/figures/fig4_native_comparison.pdf). Source: [paired differences](/home/muwang/master_thesis/BACE/analysis/outputs/figures/03/03_native_comparison__paired_differences.csv).

### 4. Existing diagnostics narrow the explanations

- Removing only unsupported claims diagnosed as non-disclosure statements raises the macro score to **59.7%**, a **4.35 pp** change. A large native gap remains.
- Even hypothetically accepting every zero-candidate DC raises the score by at most **2.05 pp**. This bounds only that subset; nonempty candidate sets can still miss decisive evidence. This scenario overlaps the preceding sensitivity and the effects must not be added.
- In **5,709 uniquely matched BACE–RAGAS claims with identical normalized wording**, the pooled support rates are **59.3% and 94.0%**. The subset covers only **6.01% of BACE claims** and is not representative semantic alignment.

Sources and figures: [diagnostic results](/home/muwang/master_thesis/paper/analysis/evaluator_gap/results.json), [score sensitivity](/home/muwang/master_thesis/BACE/analysis/outputs/evaluator_gap/figures/04_score_sensitivity.pdf), and [identical-wording judgments](/home/muwang/master_thesis/BACE/analysis/outputs/evaluator_gap/figures/04_literal_pairs.pdf). These saved diagnostic values are `SOURCE_REPORTED` here; their original analysis and provenance remain linked in the diagnostic workspace.

### 5. New result: judgment instructions affect support

The completed prompt experiment has **1,796 fully paired disclosures and 94,854 DCs from 30 companies**. Three failed condition-level records affect two disclosures, excluded as whole units. Targets, candidate ECs, model settings and output requirements are fixed; the judgment instructions change. These are adapted prompts within BACE, not native RAGAS or RAGChecker reruns.

| Condition | Mean support | Saved 95% interval |
|---|---:|---:|
| Original BACE | 55.36% | 53.91–56.83% |
| BACE–RAGAS-style | 63.02% | 61.16–64.92% |
| BACE–RAGChecker-style | 60.34% | 58.47–62.22% |

The paired increases are **+7.66 pp** (95% interval **+6.84 to +8.46**) for RAGAS-style and **+4.97 pp** (**+4.14 to +5.79**) for RAGChecker-style. Both additions and removals of support occur. On the fixed 60-disclosure repeat subset, the original prompt's net change is **−0.49 pp**, while **9.95% of claims flip**; small net change does not imply stable individual judgments.

Show: [prompt effects](/home/muwang/master_thesis/BACE/analysis/outputs/evaluator_gap/figures/04_prompt_sensitivity_effects.pdf) and [bidirectional transitions](/home/muwang/master_thesis/BACE/analysis/outputs/evaluator_gap/figures/04_prompt_sensitivity_transitions.pdf). Sources: [scores](/home/muwang/master_thesis/BACE/analysis/outputs/evaluator_gap/prompt_sensitivity/tables/scores.csv), [effects](/home/muwang/master_thesis/BACE/analysis/outputs/evaluator_gap/prompt_sensitivity/tables/effects.csv), and [completed findings](/home/muwang/master_thesis/BACE/analysis/outputs/evaluator_gap/prompt_sensitivity/findings.md).

Interpretation: support is sensitive to the bundled instructions. These changes do not quantify the fraction of the native evaluator gap caused by prompts, nor validate the changed judgments.

### 6. New result: evidence selection and representation affect support

The sampled evidence-chain experiment selected **90 disclosures**, one per company × E/S/G stratum. One failed record excludes one entire disclosure, leaving **89 paired disclosures and 4,746 DCs across 30 companies**. The original full-cohort evidence-chain run was stopped for sampling; it is not a completed full-cohort experiment.

The current three conditions use the same BACE judgment criterion and fixed targets. “Raw cards” means all originally supplied prompt-visible cards, not complete source PDFs. “All ECs” means the full deduplicated evidence-claim pool. “Candidate ECs” means the original selected subset, judged again under the common interface.

| Condition | Mean support | Saved 95% interval |
|---|---:|---:|
| raw_cards | 75.76% | 72.65–78.82% |
| all_ec | 73.39% | 70.42–76.40% |
| candidate_ec | 57.82% | 54.86–60.59% |

Paired differences are **raw cards − all ECs: +2.37 pp** (95% interval **+0.27 to +4.36**); **all ECs − candidates: +15.58 pp** (**+13.72 to +17.50**); and **raw cards − candidates: +17.94 pp** (**+15.81 to +19.92**).

The larger observed contrast is between all ECs and candidates. This makes candidate selection a priority for independent source review. It does not establish a 15.58% evidence-loss rate: changing the input also changes context quantity and may change judge behavior. The sampled-cohort rates must not replace the full-cohort main result. Prompt and evidence-chain effects cannot be added across their different designs.

Sources: [sampled scores](/home/muwang/master_thesis/BACE/analysis/outputs/evaluator_gap/evidence_chain_sample/tables/scores.csv), [paired effects](/home/muwang/master_thesis/BACE/analysis/outputs/evaluator_gap/evidence_chain_sample/tables/effects.csv), and [sample protocol](/home/muwang/master_thesis/BACE/experiments/evidence_chain_sample_v1/PROTOCOL.md). The saved statistical audit passes. A dedicated figure and integration into the inspected Notebook 04 are still absent; use this table for the meeting.

## What needs a decision from the professor

1. **Scientific emphasis:** foreground sensitivity of evidence-grounded evaluation, while treating comparative accuracy as unresolved until independent validation.
2. **Validation priority:** review the same DC against raw cards, all ECs and candidates, especially judgments changed by selection. The existing 600-claim formal workbooks assess judgments conditional on candidate ECs; they cannot by themselves validate upstream extraction or selection.
3. **Temporal and inference rules:** agree how historical policy evidence supports a target-year statement and what combinations of separate facts are admissible. The evidence window makes these questions central.
4. **Presentation:** incorporate the two completed sensitivity experiments into Results and Methods, and create a figure for the sampled evidence-chain comparison before treating the current manuscript as up to date.

Local reviewer A/B workbooks still match the hashes of the inspected blank 600-row versions. The separate evidence-chain packet has **160 review rows and no filled annotation fields**. Annotated copies elsewhere are `AUTHOR_INPUT_NEEDED`; no human agreement or accuracy result is available from these local files. Abstract and Discussion also remain incomplete in the current manuscript.

## Meeting route and backup material

Suggested 15-minute route: study design → main support result → native score gap → prompt sensitivity → sampled evidence-chain table → validation decisions. Use Figure 3 as a concrete illustration if the discussion turns to what a support judgment means.

There are **4 manuscript figure bundles** and **40 analysis figure bundles** across notebooks 00–04. These overlap in content. [Complete figure index](/home/muwang/master_thesis/paper/analysis/professor_meeting_2026-10-08/FIGURE_INDEX.md) lists each PNG/PDF.

- [Notebook 00: data and evidence landscape](/home/muwang/master_thesis/BACE/analysis/outputs/00_data_landscape.html): selection, geography, sectors, source availability and time windows.
- [Notebook 01: support](/home/muwang/master_thesis/BACE/analysis/outputs/01_evidence_support.html): distributions, task/company/year differences and secondary metrics.
- [Notebook 02: failure patterns](/home/muwang/master_thesis/BACE/analysis/outputs/02_failure_patterns.html): diagnosis composition, task patterns, pipeline checks and examples.
- [Notebook 03: evaluator comparison](/home/muwang/master_thesis/BACE/analysis/outputs/03_evaluator_comparison.html): native scores, inventories, rank agreement and source-linked cases.
- [Notebook 04: evaluator-gap diagnostics](/home/muwang/master_thesis/BACE/analysis/outputs/evaluator_gap/04_evaluator_gap_diagnostics.html): arithmetic controls, identical-wording comparisons and the completed prompt experiment; sampled evidence-chain statistics remain separate.

## Verification scope

This brief recomputes main-study counts and means, and both sensitivity experiments' paired means and effects, from saved disclosure-level tables. It checks the prompt tables against their saved hashes and confirms the main metrics and formal workbooks match the prior verification. Saved 95% intervals are `SOURCE_REPORTED`, using 2,000 company-cluster percentile draws and seed 20260921; no bootstrap was rerun. They condition on observed model outputs and do not capture all model-run or annotation uncertainty. Sample intervals are not exact finite-population intervals for the original full cohort.

Input hashes, result values, code, and figure counts are saved alongside this file. Raw model histories, full extraction lineage and every source passage were not re-audited for this meeting inventory. No experiment, frozen environment, manuscript or existing figure was changed.
