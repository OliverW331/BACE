# Support-gap composition

Read `REPORT.md` for the interpretation and `ANALYSIS_PLAN.md` for scope.
This directory contains new descriptive writing analyses; original experiment
outputs and environments are unchanged.

| File | Purpose |
|---|---|
| `results.json` | Verified native and matched-subset numerical summaries |
| `native_rates.csv` | Complete-cohort native disclosure-macro rates |
| `matched_pairs.csv` | Every retained target pair, verdict and BACE diagnosis |
| `matching_coverage.csv` | Strict/period-normalized counts and exclusions |
| `joint_judgments.csv` | Both agreement and disagreement directions |
| `category_composition.csv` | Positive category shares and conditional denominators |
| `matched_gap_accounting.csv` | Exact pooled and selected-disclosure-macro gap contributions |
| `all_bace_unsupported_categories.csv` | Complete BACE unsupported inventory, not gap composition |
| `raw_comparator_audit.csv` | Original-record verification for every retained pair |
| `sca_source_example.json` | Source-relative incident/worker mismatch, outside matched counts |
| `hop_candidate_example.json` | Matched evidence-path example with unresolved contextual scope |
| `provenance.json` | Analysis inputs, script, command and output hashes |
| `category_composition.pdf`, `.svg`, `.png` | Editable figure and preview |
| `qa/` | Figure provenance, automated checks and visual review |

From the project root:

```bash
python paper/analysis/support_gap_composition_2026-10-20/analyze_gap_composition.py
PYTHONDONTWRITEBYTECODE=1 BACE/analysis/.venv/bin/python paper/analysis/support_gap_composition_2026-10-20/plot_gap_composition.py
```

The analysis uses only the Python standard library. Plotting uses the existing
Matplotlib environment in read-only mode and the installed figure QA helper.
Do not install packages into either frozen BACE environment.
