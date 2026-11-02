# BACE main-experiment workflow report

Evidence checked: 2 November 2026. Scope: the frozen `main_v1` experiment only.

Terminology correction, 2 November 2026: the author confirms that BACE expands
to **Bidirectional Atomic Claim Evaluation**. The report uses this full name;
the frozen experiment documentation is left unchanged. No methods or results
change with this correction.

Concept-definition revision, 2 November 2026: expanded the operational claim,
context, deduplication, candidate, support, diagnosis and metric definitions
from the frozen prompts/configurations. Added Appendix C and a hash-checked
definition-source record. Removed the separate review-status discussion and
associated report-only workbook checks. Hypothetical illustrations are clearly
separated from observations; no generation or evaluation is rerun.

## Reading

- `BACE_main_experiment_report.pdf`: formatted English report with an end-to-end workflow figure, principal-result figure, detailed method description and source map.
- `REPORT.md`: editable English report containing the same prose and tables.
- `numeric_ledger.json`: unrounded recalculated values, estimands, denominators, cohort and bootstrap parameters.
- `method_results.csv`, `task_results.csv`, `diagnoses.csv`, `paired_differences.csv`: principal-result tables.
- `selected_companies.csv`, `stage_completeness.csv`: sample and completion inventories.
- `provenance.json`: hashes, execution identity, verification scope and limits.
- `concept_provenance.json`: exact prompt/schema/config paths, hashes, versions, source-section locators and report uses for the operational definitions.
- `upstream_README.md`, `upstream_source.json`: a pinned public upstream description and its source locator; not proof of local/remote dataset identity.
- `render_manifest.json`, `validation_report.json`, `review/concept_definitions_final/`: current rendering hashes, validation record and PDF inspection artifacts. Earlier preview folders retain draft renders.

## Reproduction

From `/home/muwang/master_thesis`:

```bash
python -B paper/reports/main_experiment_2026-11-02/prepare_report.py
python -B paper/reports/main_experiment_2026-11-02/render_report.py
mkdir -p paper/reports/main_experiment_2026-11-02/review/concept_definitions_final
pdftoppm -scale-to 1100 -png paper/reports/main_experiment_2026-11-02/BACE_main_experiment_report.pdf paper/reports/main_experiment_2026-11-02/review/concept_definitions_final/page
pdftotext -bbox paper/reports/main_experiment_2026-11-02/BACE_main_experiment_report.pdf paper/reports/main_experiment_2026-11-02/review/concept_definitions_final/text_boxes.html
pdftotext -layout paper/reports/main_experiment_2026-11-02/BACE_main_experiment_report.pdf paper/reports/main_experiment_2026-11-02/review/concept_definitions_final/report_extracted.txt
python -B paper/reports/main_experiment_2026-11-02/validate_report.py
```

The preparation script uses standard-library readers and the locally available
NumPy package. The renderer uses locally available Matplotlib, ReportLab and
Matplotlib's bundled DejaVu fonts. No packages are installed, no credential
files are sourced, and no generation/evaluation requests are sent. All newly
computed and rendered outputs stay in this directory. `REPORT.template.md` is
the authoritative editable prose source: numerical placeholders are populated
from verified calculations, and `REPORT.md` is regenerated from it.

Inspect the regenerated page previews before running the validation script:
its saved validation record includes a manual visual-review statement as well
as automated hash, definition-order, numeric and text-boundary checks. Start
with a fresh preview directory if a later revision changes the page count.

Reproduction requires the consumed saved artifacts to retain their recorded
hashes. A changed source fails verification rather than silently reusing stale
results. The script rechecks both comparator mappings for all 1,800 cases and
recalculates BACE metrics for the 1,798 complete cases. It preserves the full
planned inventory and excludes the two BACE-missing cases from paired results.

## Interpretation

Scores are automated support measurements within supplied evidence, not factual
truth, legal compliance or independently established evaluator accuracy.
This report does not merge subsequent evidence-chain or
prompt-sensitivity experiments into the main cohort.
