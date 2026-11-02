# BACE results and discussion report

Prepared on 8 October 2026. All report text is English.

Open `bace_results_discussion.pdf` for the eight-page meeting report. The editable source is `bace_results_discussion.tex`; `REPORT_PLAN.md` preserves the outline. Each of the five discussion points uses one real saved case. These are illustrative assistant source inspections, not independent human validation.

## Contents

- Pages 1–2: current main-experiment findings and existing figures.
- Pages 3–7: five discussion points, each with a real case and a question for the meeting.
- Page 8: decisions, validation status and source guide.

`case_evidence.json` retains complete case IDs, evidence and judgments. For the DiaSorin example, it also retains the three verified source-call locations and support sets. `original_source_checks.json`, `numeric_ledger.json` and `provenance.json` document source passages, numerical inputs and hashes. Raw experiment artifacts remain unchanged.

## Compilation

The source was opened with the Codex LaTeX editor. Its standalone compiler cannot load the external figure assets and reports `assets/main_support.pdf` as unavailable. Keep the source editable there; use the saved PDF for the complete illustrated version.

The delivered PDF was successfully compiled using the system's existing TeX Live installation, with no new packages or environment changes:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build bace_results_discussion.tex
```

Run this from this directory. The generated file is `build/bace_results_discussion.pdf`; the delivered copy is at the directory root. `assets/` must remain beside the source. The source ZIP includes the source, figures, PDF, plan and evidence records.

`qa/final_review.json` records the final compilation, pagination and visual review. Source intervals are reused from saved company-cluster bootstrap outputs; no experiments, model calls or new human annotations were performed.
