# Main-experiment analysis

Four independently executable notebooks explain the data landscape, evidence support,
automated failure patterns and native evaluator differences. All analyses are
post-experiment, descriptive, and based on the frozen main run. They are not a
preregistered analysis plan or a human-validated evaluator benchmark.

## Reading order

1. `00_data_landscape.ipynb`: sources, selection, geography, coverage, and visible evidence.
2. `01_evidence_support.ipynb`: support distributions and heterogeneity.
3. `02_failure_patterns.ipynb`: diagnostic composition and traceable examples.
4. `03_evaluator_comparison.ipynb`: paired native scores, segmentation, and disagreements.

## Reproduction

Use the existing independent environment inside this directory; do not recreate
or install packages into either frozen environment for this analysis. Source files are read only.
Generated tables, source manifests, figure exports and QA records live in `outputs/`.
A cached analysis snapshot is reused only after checking its input hashes.
Missing results remain missing. Comparison uses the common completed cohort.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/execute_notebooks.py 00_data_landscape.ipynb 01_evidence_support.ipynb 02_failure_patterns.ipynb 03_evaluator_comparison.ipynb
```

Git includes the existing main-run snapshot, source hashes, HTML reading copies,
figure exports, source tables, selected case bundles and QA records. Follow-up
evaluator-gap, evidence-chain and prompt-sensitivity studies are outside this
repository scope and remain local.

The main sampling record is also tracked at `../evidence/sample/sample.json`;
full evidence payloads are not included.

A fresh clone can inspect the saved results, but rebuilding the snapshot and
executing notebooks still require the original consumed artifacts. The loader
checks their hashes before reusing a snapshot; Git does not include all raw
per-case calls, source datasets or frozen evidence inputs. See
[repository scope](../../docs/REPOSITORY.md).

Figures use Python/Matplotlib with consistent candy blue, green and orange accents,
editable vector text, and explicit units and denominators. Nature-inspired design
does not establish compliance with a particular journal's submission rules.

## Reading exports and checks

For notebooks 00–03, code-hidden reading copies are written as `outputs/00_data_landscape.html` through
`outputs/03_evaluator_comparison.html`. Notebook figures link to their PDF, SVG,
PNG and source CSV files; case plates also link to complete evidence bundles.

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

For a complete QA refresh, run `scripts/verify_integrity.py` and
`scripts/review_previews.py`, inspect any changed figure layouts, then update the
review records with `scripts/write_review_report.py` and the final inventory with
`scripts/write_analysis_manifest.py` using the same analysis Python interpreter.
The layout review recorded for this prose revision is carried forward only when
the baseline PNG comparison remains exact.

The renderer requires the installed `nature-figure` skill (version 2.8.0 used here).
Its default location is `~/.codex/skills/nature-figure`; set `NATURE_FIGURE_SKILL`
when installed elsewhere. The basemap is bundled under `assets/` with its public-
domain attribution and source hash, so reproduction needs no map download.

```bash
.venv/bin/python scripts/verify_integrity.py
.venv/bin/python scripts/validate_analysis.py
```

`ANALYSIS_SPEC.md` defines the analysis and figure contracts. `QA_REVIEW.md`
records the final visual/statistical review. Machine-readable acceptance,
source-validation and numeric-repeat evidence is under `outputs/qa/`.
The exact analysis dependency versions are pinned in `requirements.lock.txt`.

The examples are diagnostic illustrations, not a substitute for blinded human
validation. Source inspection found both questionable generated interpretations
and evaluator/extraction problems; neither is hidden or relabelled in aggregate
results. The experiment's official summarizer is left unchanged and still requires
all cases to complete before it can finalize its own main-run outputs.
