import hashlib
import json
from pathlib import Path


OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[2]


def read_json(path):
    return json.loads(path.read_text())


def percent(value):
    return f"{100 * value:.2f}%"


def interval(result):
    return f"{percent(result['mean'])} [{percent(result['low'])}, {percent(result['high'])}]"


def contrast(result):
    return f"{100 * result['mean']:.2f} pp [{100 * result['low']:.2f}, {100 * result['high']:.2f}]"


def main():
    result = read_json(OUTPUT / "results.json")
    integrity = read_json(OUTPUT / "integrity.json")
    metadata = read_json(ROOT / "paper/analysis/ec_metadata_audit_2026-10-26/summary.json")
    followup = read_json(ROOT / "paper/analysis/prompt_gap_review_2026-10-22/results.json")
    cohort = result["cohort"]
    claims = result["claims"]
    rates = result["rates"]
    diagnoses = {row["label"]: row for row in result["diagnoses"]}
    boundary = diagnoses["factual_boundary_distortion"]["claims"]
    conflation = diagnoses["evidence_conflation"]["claims"]
    distribution = result["distribution"]
    alignment = result["literal_alignment"]["ragas"]
    joint = alignment["joint_verdict_counts"]
    sensitivity = result["sensitivity"]
    evidence = result["evidence_use"]
    pairs = result["paired_contrasts"]
    tasks_sensitivity = {row["task"]: row for row in result["tasks_non_disclosure_sensitivity"]}
    task_labels = {row["task"]: row for row in result["task_label_composition"]}
    task_table = "\n".join(f"| {row['task']} | {row['observations']} | {interval(row)} | {percent(tasks_sensitivity[row['task']]['mean'])} | {task_labels[row['task']]['non_disclosure_statement_percent_all_dc']:.2f}% |" for row in sorted(result["tasks"], key=lambda item: item["mean"]))
    diagnosis_table = "\n".join(f"| {row['label']} | {row['claims']:,} | {row['percent_unsupported']:.2f}% | {row['percent_all_dc']:.2f}% | {row['disclosures_with_label']:,} |" for row in sorted(result["diagnoses"], key=lambda item: item["claims"], reverse=True))
    domain_table = "\n".join(f"| {row['standard']} | {interval(row)} | {row['observations']} |" for row in result["domains"])
    year_table = "\n".join(f"| {int(row['year'])} | {row['observations']} | {interval(row)} |" for row in result["years"])
    native_table = "\n".join(f"| {name} | {interval(rates[name])} | {percent(result['native_inventories'][name]['pooled_support'])} | {result['native_inventories'][name]['median_claims']:.0f} |" for name in ("bace", "ragchecker", "ragas"))
    prompt_table = "\n".join(f"| {row['label']} | {100 * float(row['estimate']):.2f} pp | {100 * float(row['low']):.2f} to {100 * float(row['high']):.2f} pp |" for row in followup["saved_prompt_effects"])
    text = f"""# BACE main experiment: meaningful findings and evidence boundaries

Audit date: 29 October 2026. Primary run: `BACE/results/main_v1`.
Status: `COMPUTED_VERIFIED` for the primary numerical reanalysis. Separate saved follow-up and forensic findings are explicitly `SOURCE_REPORTED` and were not rerun.

## Executive interpretation

The strongest result is not that BACE has proved a higher error rate or higher accuracy. It is that the saved disclosures frequently fail BACE's supplied-evidence support contract, predominantly through boundary changes and unsupported combinations rather than unanchored novelty. Large native-score disagreements persist after limited denominator diagnostics, and some survive identical claim wording. Workforce-target tasks are consistently weaker within matched company-years. These observations motivate proposition-level and source-grounded validation; they do not substitute for it.

## 1. Cohort and integrity

- Planned: {cohort['planned']:,} company-year-task cases; complete BACE and common native-comparison cohort: {cohort['bace_complete']:,}; companies: {cohort['companies']}; target years: 2019–2023; tasks: 12.
- Incomplete: Banco BPM / 2019 / S1-5 and Investec / 2023 / S1-1. Exclude these cases from BACE and matched comparisons, not score them as zero. Comparator-only cases remain outside the paired cohort.
- Independently checked {integrity['source_files_checked']:,} consumed source/stage file hashes with zero mismatches, plus all nine saved snapshot table hashes and the snapshot-builder hash.
- Recomputed all complete case-level BACE and native numerators from {claims['all_dc']:,} saved DCs and native verdict inventories. Checked each diagnosis partition, sensitivity denominator, and multi-EC-required count.
- This is not a new extraction, generation, support or diagnosis run. Hash identity does not prove source truth, extraction completeness, or annotation accuracy.

Sources: `integrity.json`; `results.json/cohort`; `provenance.json`; frozen snapshot manifest and stage source-hash map.

## 2. Meaningful primary finding: incomplete supplied-evidence support is pervasive

The disclosure-weighted BACE support mean is **{interval(rates['bace'])}**. The pooled claim-weighted rate is **{percent(claims['pooled_support'])}** ({claims['supported']:,}/{claims['all_dc']:,}); these are distinct estimands.

The median is {percent(distribution['median'])}, with an interquartile range of {percent(distribution['q25'])}–{percent(distribution['q75'])}. There are {distribution['below_half_cases']:,}/{cohort['bace_complete']:,} disclosures ({percent(distribution['below_half_cases']/cohort['bace_complete'])}) below 50% support and {distribution['at_least_80pct_cases']}/{cohort['bace_complete']:,} ({percent(distribution['at_least_80pct_cases']/cohort['bace_complete'])}) at or above 80%. No completed disclosure is automatically classified as fully supported. The observed minimum and maximum are {percent(distribution['minimum'])} and {percent(distribution['maximum'])}.

Leaving out any one company changes the overall mean only to {percent(result['leave_one_company_out']['bace_support_rate_all_dc']['minimum'])}–{percent(result['leave_one_company_out']['bace_support_rate_all_dc']['maximum'])}. The aggregate is therefore not driven by one sampled company. This is cohort robustness, not external validity.

Warranted claim: under this frozen pipeline and its supplied candidate-EC interface, unsupported claims are common across generated disclosures. Do not describe {percent(claims['unsupported']/claims['all_dc'])} as a verified real-world falsehood or hallucination rate.

Numerical locators: `results.json/rates/bace`, `claims`, `distribution`, `leave_one_company_out`.

## 3. Strongest diagnostic finding: scope and relationship errors dominate automated unsupported labels

The following are exclusive automated diagnoses assigned in the frozen rule order, not independent human-confirmed error classes.

| Automated diagnosis | DCs | Share of unsupported DCs | Share of all DCs | Disclosures containing label |
| --- | ---: | ---: | ---: | ---: |
{diagnosis_table}

Boundary distortion and evidence conflation together account for **{boundary + conflation:,}/{claims['unsupported']:,} unsupported DCs ({percent((boundary+conflation)/claims['unsupported'])})**. They concern anchored facts whose time, entity, population, measurement scope or relationship is not supported as stated. Unsupported novelty accounts for only {diagnoses['unsupported_novelty']['percent_unsupported']:.2f}% of unsupported DCs.

Boundary labels occur in {diagnoses['factual_boundary_distortion']['disclosures_with_label']:,}/{cohort['bace_complete']:,} disclosures ({percent(diagnoses['factual_boundary_distortion']['disclosures_with_label']/cohort['bace_complete'])}); conflation labels occur in {diagnoses['evidence_conflation']['disclosures_with_label']:,}/{cohort['bace_complete']:,} ({percent(diagnoses['evidence_conflation']['disclosures_with_label']/cohort['bace_complete'])}). These patterns are distributed broadly, not confined to a few large claim inventories.

Meaning: this study's useful distinction is *preserving evidential boundaries and justified relations*, not merely detecting text with no recognizable anchor. Rare contradiction labels do not establish that almost all disclosures are factually correct. Ordered exclusive diagnosis rules and EC extraction errors can change the apparent composition.

Numerical locators: `results.json/diagnoses`, `claims/label_counts`; `diagnoses.csv`. Rule source: `BACE/config/evaluation/prompts/generation_claim_unsupported_diagnosis_prompt_v1.txt`.

## 4. Native evaluator disagreements are large, but are not an accuracy comparison

All rows below use the same {cohort['bace_complete']:,} complete disclosures. Each evaluator retains its own claim inventory and evidence interface.

| Evaluator | Disclosure-weighted mean [95% interval] | Pooled native claim rate | Median native claim count |
| --- | ---: | ---: | ---: |
{native_table}

The paired native-minus-BACE gaps are {contrast(result['native_minus_bace']['ragchecker'])} for RAGChecker and {contrast(result['native_minus_bace']['ragas'])} for RAGAS. Both company-level mean gaps are positive in all 30 sampled companies. Spearman rank associations with BACE are only {result['spearman_descriptive']['ragchecker']:.3f} and {result['spearman_descriptive']['ragas']:.3f}, respectively: disagreement is not just an overall level offset.

### Same-wording selected overlap

Independent unique casefold/whitespace-normalized matching reproduces {alignment['pairs']:,} BACE–RAGAS literal pairs from {alignment['cases']:,} disclosures, covering {percent(alignment['bace_dc_coverage'])} of BACE DCs. In this selected overlap, BACE support is {percent(alignment['bace_support_rate'])} and RAGAS support is {percent(alignment['native_support_rate'])}.

- Both supported: {joint['bace_1_native_1']:,}.
- Both unsupported: {joint['bace_0_native_0']:,}.
- BACE unsupported / RAGAS supported: {joint['bace_0_native_1']:,}.
- BACE supported / RAGAS unsupported: {joint['bace_1_native_0']:,}.
- Boundary distortion accounts for {alignment['bace_unsupported_native_supported_by_label']['factual_boundary_distortion']:,} of the {joint['bace_0_native_1']:,} first-direction disagreements.

Meaning: differing segmentation cannot be the sole explanation for these selected same-wording disagreements. Evidence representation, candidate access and judgment rules still differ. The overlap is not representative semantic alignment, and neither verdict is ground truth. RAGChecker has no unique literal overlap under this rule; that does not mean no semantic overlap exists.

Numerical locators: `results.json/rates`, `native_minus_bace`, `native_inventories`, `literal_alignment`, `spearman_descriptive`.

## 5. Sensitivities reject two narrow explanations, not all pipeline error

Removing only BACE-unsupported DCs diagnosed as non-disclosure statements removes {sensitivity['non_disclosure_removed']:,} DCs while leaving the supported numerator at {sensitivity['unchanged_supported_numerator']:,}. The disclosure-weighted mean becomes **{percent(rates['non_disclosure_sensitivity']['mean'])}**, a **{sensitivity['macro_increase_pp']:.2f} pp** increase. Native-minus-BACE gaps remain {100*(rates['ragchecker']['mean']-rates['non_disclosure_sensitivity']['mean']):.2f} pp and {100*(rates['ragas']['mean']-rates['non_disclosure_sensitivity']['mean']):.2f} pp. This is a changed estimand, not a corrected support or accuracy score.

There are {sensitivity['zero_candidate_dc']:,} zero-candidate DCs in {sensitivity['zero_candidate_cases']} disclosures, accounting for {percent(sensitivity['zero_candidate_fraction_unsupported'])} of unsupported DCs. Even hypothetically relabeling every such DC as supported raises the macro mean by at most **{sensitivity['zero_candidate_max_macro_increase_pp']:.2f} pp**, to {percent(rates['zero_candidate_upper_bound']['mean'])}.

Meaning: penalizing the diagnosed non-disclosure subset or the empty-candidate subset alone cannot account for the approximately 35 pp native score gap. This does not bound extraction omissions, nonempty-but-incomplete candidate sets, or other sources of bias. The two scenarios overlap and cannot be added.

Numerical locators: `results.json/sensitivity`, `rates/non_disclosure_sensitivity`, `rates/zero_candidate_upper_bound`.

## 6. Newly paired finding: workforce-target tasks are consistently less supported

| Task | Disclosures | All-DC mean [95% interval] | Non-disclosure sensitivity mean | Diagnosed non-disclosure share of all DCs |
| --- | ---: | ---: | ---: | ---: |
{task_table}

On {pairs['G1-1_minus_S1-5']['observations']} matched company-years, G1-1 minus S1-5 is **{contrast(pairs['G1-1_minus_S1-5'])}**, with positive company means in {pairs['G1-1_minus_S1-5']['positive_company_means']}/30 companies. After the non-disclosure sensitivity, the same contrast is {contrast(pairs['G1-1_minus_S1-5_non_disclosure_sensitivity'])}. S1-5 remains the lowest-scoring task after this removal. The exact paired contrast differs slightly from subtracting the two unpaired task means because G1-1 has an additional available case.

E1-4 and E1-6 also exceed S1-5 in matched company-years by {contrast(pairs['E1-4_minus_S1-5'])} and {contrast(pairs['E1-6_minus_S1-5'])}, respectively.

| Task domain | All-DC mean [95% interval] | Disclosures |
| --- | ---: | ---: |
{domain_table}

On the {pairs['E1_minus_S1']['observations']} company-years with all 12 task outputs, within-company-year domain contrasts are E1 minus S1: {contrast(pairs['E1_minus_S1'])}; G1 minus S1: {contrast(pairs['G1_minus_S1'])}. These compare four-task domain means within the same company-year and do not treat tasks as independent companies.

Important qualification: task ranking changes under the sensitivity denominator. For example, E1-6 becomes {percent(tasks_sensitivity['E1-6']['mean'])}, above G1-1 at {percent(tasks_sensitivity['G1-1']['mean'])}. Thus “G1-1 is intrinsically the easiest task” is not established. Task scope, non-disclosure assertions, historical evidence availability, prompt behavior and extraction may all contribute.

Numerical locators: `task_summary.csv`, `task_non_disclosure_sensitivity.csv`, `domain_summary.csv`, `paired_contrasts.csv`, `task_label_composition.csv`.

## 7. Supporting finding: BACE accepts inferred and multi-evidence support

There are {claims['label_counts']['direct']:,} direct-support DCs and {claims['label_counts']['inferred']:,} inferred-support DCs. Inferred-only DCs constitute **{percent(evidence['inferred_fraction_supported'])}** of supported DCs. A DC is classified as direct whenever it has any accepted direct set; inferred-only is therefore not the fraction of all support sets that use inference.

For {int(evidence['multi_ec_required_dc']):,}/{claims['supported']:,} supported DCs (**{percent(evidence['multi_ec_required_dc']/claims['supported'])}**), every saved accepted support set contains more than one EC. This is an operational property of accepted support sets, not proof that a single-EC justification is logically impossible.

The case-level EC inventory contains {int(evidence['case_level_ec']):,} deduplicated ECs, of which {int(evidence['case_level_used_ec']):,} occur in at least one accepted support set. Macro ECCR is {percent(evidence['macro_eccr'])}; pooled ECCR is {percent(evidence['pooled_eccr'])}. Repeated evidence across cases is not independent source replication. Unused ECs may be redundant or task-irrelevant; do not translate this into “the model ignores two thirds of necessary evidence” or a completeness/recall estimate.

Numerical locators: `results.json/claims/label_counts`, `evidence_use`; metric definition: `BACE/script/evaluation/metrics.py`.

## 8. Secondary exploratory pattern: later target years, not monotonic improvement

| Target year | Disclosures | All-DC mean [95% interval] |
| --- | ---: | ---: |
{year_table}

On {pairs['2023_minus_2019']['observations']} matched company-task observations, 2023 minus 2019 is {contrast(pairs['2023_minus_2019'])}; company means are positive in {pairs['2023_minus_2019']['positive_company_means']}/30 companies. Annual means decline between 2020 and 2021, so a monotonic trend is not observed. The generator is fixed; changes in the reporting year and overlapping historical evidence windows do not show model learning, better real-world sustainability or causal improvements in reporting quality.

Descriptive score associations with disclosure word count and EC count are {result['spearman_descriptive']['bace_vs_word_count']:.3f} and {result['spearman_descriptive']['bace_vs_ec_count']:.3f}. These unadjusted associations do not identify mechanisms and are not headline findings.

Numerical locators: `year_summary.csv`, `paired_contrasts.csv`, `results.json/spearman_descriptive`.

## 9. Separate saved follow-up: prompt criteria matter, but do not erase the native gap

`SOURCE_REPORTED`: the saved prompt-sensitivity analysis uses {followup['disclosures']:,} common complete disclosures and {followup['claims']:,} DCs, not the primary {cohort['bace_complete']:,}-disclosure cohort. Adapted prompts judge the same BACE DCs against the same candidate ECs. The original macro mean on that follow-up cohort is {percent(float(followup['saved_prompt_scores'][0]['estimate']))}.

| Saved adapted condition | Increase over original BACE | Saved 95% interval for increase |
| --- | ---: | ---: |
{prompt_table}

Meaning: judgment instructions affect support decisions even when the supplied DC/EC representation is held fixed in the saved comparison. These adapted conditions are not the native frameworks. This is not a causal decomposition of the entire native gap, evidence of evaluator accuracy, or a new computation performed here. Diagnoses were not rerun, and these changes are not additive with the removal sensitivities.

Source locator: `paper/analysis/prompt_gap_review_2026-10-22/results.json/saved_prompt_effects`, `saved_prompt_scores`; this audit's `provenance.json` records the consumed result hash.

## 10. Material validity caveat: evidence metadata enters extracted propositions

`SOURCE_REPORTED`: the 26 October saved forensic audit traces ESRS/disclosure taxonomy in CSV card text into final EC wording. It reports {metadata['downstream']['support_dc_records_with_flagged_ec']:,} DC records with at least one broadly flagged EC in an accepted support set, across {metadata['downstream']['cases_with_flagged_support_ec']:,} cases. The screen includes legitimate standard references and is not an adjudicated extraction-error count. It establishes downstream exposure, not how many decisions would change without those words.

This limits interpretation of the primary outcomes: supplied EC text can already have a disputed boundary or qualifier before support judgment. An original-source audit and a separately versioned sensitivity are needed to estimate effects. Do not silently remove these words from frozen ECs or reviewer packets and call the modified material the original input. The primary score is conditional on the saved pipeline, not a clean source-level error rate.

Sources: `paper/analysis/ec_metadata_audit_2026-10-26/REPORT.md`, `summary.json/downstream`; source-relative counterexamples in `BACE/analysis/NARRATIVE_REVIEW.md`.

## 11. What the main experiment cannot currently establish

The inspected formal A and B workbooks each contain {result['human_review'][0]['sample_rows']} sample rows, **zero completed human support labels and zero completed human diagnosis labels** as of this audit. Preparing reviewer materials is not completed human validation. No new labels or adjudication were produced here.

Consequently, the current record does not establish:

- BACE has higher accuracy, precision, recall or F1 than RAGChecker/RAGAS.
- Every BACE-unsupported claim is false or externally ungrounded.
- Diagnosis percentages are independent human-confirmed error rates.
- Higher or lower scores reflect a company's real sustainability performance or legal compliance.
- ECCR measures complete use of necessary evidence.
- The 30 availability-filtered companies represent all companies or sectors.
- Cluster bootstrap intervals capture model-run randomness, extraction/annotation error or missing-case uncertainty.

Numerical locator: `results.json/human_review`, with workbook hashes. Validation scope: `BACE/analysis/validation/README.md`.

## Recommended results hierarchy

1. Lead with the *type and prevalence of supplied-evidence support failures*, especially boundary distortion and unsupported combinations.
2. Show *large native level and rank disagreements*, then the selected identical-wording comparison and limited alternative-explanation diagnostics. Label all of these disagreements, not accuracy gains.
3. Use *within-company-year task contrasts* to demonstrate where support is weakest, retaining the denominator sensitivity and all tasks.
4. Use *accepted inferred/multi-EC support* to explain the method's analytical value without claiming inference correctness.
5. Put annual patterns, raw EC coverage and weak unadjusted associations in supporting material rather than the headline.
6. Treat the saved prompt comparison as a separate follow-up and the metadata finding as a central validity caveat.

The highest-value next steps are source-grounded review of boundary/conflation disagreements (including cases where BACE is wrong), completion and analysis of the blinded support/diagnosis sample, representative semantic proposition alignment, and a separately versioned extraction sensitivity. These are recommendations, not completed or launched work.

## Reproduction and uncertainty

Run `reanalyse_main.py`, then `render_report.py` with the independent writing-tools Python environment. Only Python's standard library is required. New outputs live in this directory; frozen environments and experiment artifacts are unchanged.

All newly computed intervals use {result['bootstrap']['draws']:,} complete-company cluster draws, seed {result['bootstrap']['seed']}, Python `random.Random`, and linearly interpolated 95% percentile intervals. Within each draw retain all observed records of each sampled company. Paired contrasts match the specific company-year or company-task cells before resampling. Their observations and exclusions are saved explicitly.

This intentionally differs from the original 2,000-draw NumPy bootstrap seed 20260921. Point estimates reproduce the saved results; small interval differences are Monte Carlo implementation differences, not a changed experiment. No hypothesis tests, P values or multiple-testing declarations were generated. Selected contrasts are exploratory, not prespecified confirmation.

Input hashes, code version, runtime and command are in `provenance.json`; primary results and denominators are in `results.json`; component tables are supplied as CSV. Report values are rendered directly from saved results, not copied from manuscript prose.
"""
    (OUTPUT / "REPORT.md").write_text(text)
    inputs = [OUTPUT / "results.json", OUTPUT / "integrity.json", ROOT / "paper/analysis/ec_metadata_audit_2026-10-26/summary.json", ROOT / "paper/analysis/prompt_gap_review_2026-10-22/results.json"]
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    (OUTPUT / "report_manifest.json").write_text(json.dumps({"access_date": "2026-10-29", "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "inputs": hashes, "report_sha256": hashlib.sha256(text.encode()).hexdigest()}, indent=2) + "\n")
    print(f"Wrote {OUTPUT / 'REPORT.md'}")


if __name__ == "__main__":
    main()
