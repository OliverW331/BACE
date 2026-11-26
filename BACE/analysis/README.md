# Main-experiment analysis

This directory holds the analysis code for the main run. The article's figures and additional analyses are produced by `figures_v3/` and `revision_2026-11/` (see [below](#article-figures-and-additional-analyses)). The derived-data release is written by `release_v1/export_release.py`.

## Descriptive notebooks

Four independently executable notebooks explain the data landscape, evidence support,
automated failure patterns and native evaluator differences. All analyses are
post-experiment, descriptive, and based on the frozen main run. They are not a
preregistered analysis plan or a human-validated evaluator benchmark.

### Reading order

1. `00_data_landscape.ipynb`: sources, selection, geography, coverage, and visible evidence.
2. `01_evidence_support.ipynb`: support distributions and heterogeneity.
3. `02_failure_patterns.ipynb`: diagnostic composition and traceable examples.
4. `03_evaluator_comparison.ipynb`: paired native scores, segmentation, and disagreements.

### Reproduction

Use a separate analysis environment in this directory (`.venv`, pinned in
`requirements.lock.txt`); do not install analysis packages into the experiment
environment. Source files are read only.
Generated tables and source manifests live in `outputs/`.
A cached analysis snapshot is reused only after checking its input hashes.
Missing results remain missing. Comparison uses the common completed cohort.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/execute_notebooks.py 00_data_landscape.ipynb 01_evidence_support.ipynb 02_failure_patterns.ipynb 03_evaluator_comparison.ipynb
```

Git includes the main-run snapshot, source hashes and HTML reading copies.
Figure exports and case bundles that quote source reports are not included.

The main sampling record is also tracked at `../evidence/sample/sample.json`;
full evidence payloads are not included.

A fresh clone can inspect the saved results, but rebuilding the snapshot and
executing notebooks still require the original consumed artifacts. The loader
checks their hashes before reusing a snapshot; Git does not include all raw
per-case calls, source datasets or frozen evidence inputs. See
[repository scope](../../docs/REPOSITORY.md).

### Reading copies and checks

For notebooks 00–03, code-hidden reading copies are written as `outputs/00_data_landscape.html` through
`outputs/03_evaluator_comparison.html`. Notebook figures link to their PDF, SVG,
PNG and source CSV files, which are regenerated locally when the notebooks are executed.

Each figure has its own question, reading caption, data-shape analysis,
interpretation and limits. The prose is included in the saved notebook outputs
and remains visible with code hidden. Quantitative descriptions are recomputed
from the plotted data; fixed case readings retain their source-based qualifications.
For notebooks 00–03, `figure_narrative.py` is the editable source of these reading units, and
`scripts/build_notebooks.py` defines notebook organisation and plotting cells.
After changing either source, rebuild and execute to refresh saved content:

```bash
.venv/bin/python scripts/build_notebooks.py
.venv/bin/python scripts/execute_notebooks.py 00_data_landscape.ipynb 01_evidence_support.ipynb 02_failure_patterns.ipynb 03_evaluator_comparison.ipynb
.venv/bin/python scripts/validate_analysis.py
.venv/bin/python scripts/validate_readings.py
```

The notebook renderer uses a local figure-style module (`NATURE_FIGURE_SKILL`, default
`~/.codex/skills/nature-figure`, version 2.8.0) that is not distributed with this
repository. The saved HTML reading copies show the rendered output. The basemap
is bundled under `assets/` with its public-domain attribution and source hash.

`ANALYSIS_SPEC.md` defines the analysis and figure contracts.
The exact analysis dependency versions are pinned in `requirements.lock.txt`.

The experiment's official summarizer is left unchanged and still requires all
cases to complete before it can finalize its own main-run outputs.

## Article figures and additional analyses

All scripts read saved outputs only and make no model calls. Run them from the
repository root with the experiment environment (`BACE/.venv`) and R (4.2.2 used) with
`ggplot2`, `patchwork`, `ggtext`, `ggdist`, `dplyr`, `readr`, `scales` and
`forcats`. Fig. 1 is exported to PDF and PNG with Inkscape.

1. `revision_2026-11/run_revision_analyses.py` computes the additional analyses
   reported in the article (exact-claim agreement with comparators, reporting-year
   mentions, diagnoses by candidate count, boundary types, claim strata and
   company-cluster bootstrap intervals). Boundary-type and quantity rules are read
   from `coding_rules_v1.json`, whose hash is recorded in `coding_rules_v1.sha256`.
   Results are written to `outputs/revision_2026-11/`.
2. `figures_v3/prep_fig2.py`, `prep_fig3.py`, `prep_fig4.py` and `prep_ed.py`
   write the tidy source data of each figure panel to `outputs/figures_v3/*_data/`.
3. `figures_v3/fig2.R`, `fig3.R`, `fig4.R` and `ed_figs.R` draw Figs 2–4 and
   Extended Data Figs 1–3. `figures_v3/fig1_svg.py` draws Fig. 1.

```bash
BACE/.venv/bin/python -B BACE/analysis/revision_2026-11/run_revision_analyses.py
BACE/.venv/bin/python -B BACE/analysis/figures_v3/prep_fig2.py
Rscript BACE/analysis/figures_v3/fig2.R
```

The other figures follow the same two-step pattern. Step 1 and the Fig. 1 and
Fig. 4 case panels read the per-case outputs under `BACE/results/main_v1/cases/`,
which are not tracked; the source data of every figure accompany the article.
`figures_v3/COLOURS.md` documents the colour scheme shared by all figures.
