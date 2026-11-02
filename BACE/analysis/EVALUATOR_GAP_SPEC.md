# Notebook 04: evaluator-gap analysis contract

Established: 30 September 2026. This extends the four-notebook analysis with a
separate diagnostic notebook and output namespace. The original
`ANALYSIS_SPEC.md` and its prior acceptance records remain unchanged.

Extended: 1 October 2026 with an author-authorized controlled support-prompt
experiment. The separate frozen protocol is
[`../experiments/prompt_sensitivity_v1/PROTOCOL.md`](../experiments/prompt_sensitivity_v1/PROTOCOL.md).
Section 9 reads saved results, presents actual execution completeness and
withholds primary estimates until full scheduling is complete. Two new full
conditions preserve BACE inputs and support-set output; a fixed two-disclosure
per-company original-prompt repeat sample checks historical-to-current drift.
No API call originates in the notebook. This extension does not complete
independent evidence-loss, accuracy or temporal-rule validation.

## Objective

Explain lower BACE support scores without presuming which evaluator is right.
Distinguish evidence-representation loss, target-claim construction, and support
rules. Quantify available operational differences and identify exactly which
independent evidence is missing for error attribution.

## Completed scope

- Verify shared cohort, snapshot hashes, claim counts, native scores and the
  earlier paper diagnostic inputs; consume them without rebuilding the snapshot.
- Compute disclosure-macro arithmetic sensitivities and paired differences,
  with 2,000 company-cluster bootstrap draws, seed 20260921, percentile 95%
  intervals. Preserve pairing and distinguish pooled claim denominators.
- Describe candidate-set distributions and zero-candidate limits, including
  nonempty-set uncertainty.
- Compare paired native scores in named claim-count subsets without treating
  equal counts as equal meaning.
- Analyze unique literal BACE–RAGAS pairs, both disagreement directions,
  macro/micro weighting and leave-one-company-out influence.
- Retain source-linked examples with explicit selection and ambiguity limits,
  including the qualified Evonik interpretation.

## Pending scope

Full-source / full-EC / candidate-EC sufficiency judgments, semantic alignment
against a neutral generated-passage inventory, independently assigned temporal
labels, and controlled evidence/inventory/judgment conditions require additional
evidence. The notebook marks these `COMPUTATION_PENDING` and writes header-only
schemas; it does not fabricate labels or execute model/API calls. Reproduction
never consumes filled template files automatically as a reference benchmark.

The earlier [statistical plan](../../paper/analysis/evaluator_gap/statistical_analysis_plan.md)
defines the proposed estimands, sampling and interpretation limits.

## Boundaries

The evidence boundary is the prompt-visible input. Original PDFs can help
diagnose source preparation but cannot silently provide extra support. Target
fidelity must be checked before assigning evidence-chain errors. Assess false
acceptances as well as false rejections. Source insufficiency, input ambiguity,
and reviewer uncertainty must remain distinguishable.

Native inventories are not a shared denominator. Literal matching is selected,
and native score differences or cluster intervals do not establish accuracy.
No additive causal allocation of the total score gap is attempted. Temporal
mechanisms cannot be independently measured using only BACE's diagnostic labels.

Bootstrap uncertainty is conditional on the observed companies and records;
it omits model-run, annotation and missing-case uncertainty and does not adjust
for the original company-selection design. No significance tests are reported.

## Files and execution

- `04_evaluator_gap_diagnostics.ipynb`: executed English analysis and interpretation.
- `evaluator_gap_analysis.py`: input checks and new diagnostic statistics.
- `evaluator_gap_figures.py`: Python plotting, figure exports and reading units.
- `evaluator_gap_prompt_sensitivity.py`: paired prompt analysis, missingness,
  company effects, flip overlap, repeat control and full-evidence examples.
- `evaluator_gap_prompt_figures.py`: prompt effects and paired transition panels.
- `scripts/build_evaluator_gap_notebook.py`: notebook-specific scaffold builder.
- `scripts/execute_evaluator_gap_notebook.py`: fresh kernel, HTML and preservation checks.
- `scripts/validate_evaluator_gap_notebook.py`: numerical and export acceptance checks.
- `outputs/evaluator_gap/`: all new outputs, including local runtime caches.

Use the existing analysis interpreter with bytecode writes disabled. No package
installation, environment change, frozen protocol change, or alteration of the
first four notebooks is part of this work. The dedicated executor verifies
the scientific freeze, both environment inventories, and protected prior files.

Earlier paper diagnostics remain historical derived inputs. Their original
calculation is not forked into a separately maintained copy. New statistics
reconcile with those inputs and retain hashes and provenance.

## Acceptance and figure contract

The notebook must execute in a fresh kernel with saved outputs and a code-hidden
HTML reading copy. Each figure must have a question, caption, data-based reading,
interpretation and limits. Export 183-mm-wide editable PDF/SVG and 600-dpi PNG,
with source data, text-size audit and collision audit. These are analysis
figures, not a claim of submission readiness for a particular journal.

Verify each figure visually, including labels, uncertainty, color-independent
interpretability, geometry and full data coverage. Record the 5-pt glyph floor
and final dimensions. The current four figures each contain one quantitative
panel, so the alignment gate records `NOT APPLICABLE` rather than a false
multi-panel pass.

Numerical checks cover unbalanced company sizes, preserved pairing, explicit
undefined resampling denominators, reproduction of prior native intervals,
and byte-identical repetition of new source tables. Pending human estimates
must remain visibly pending. Preserve all existing results and environment
inventories. Automated checks and visual review have separate records.
