# Analysis contract

## Audience and outcome

A reader unfamiliar with the project should be able to explain the data sources,
observed support results, concrete diagnostic patterns, evaluator differences and
limits without reading the code. All notebooks and derived text are in English.
The analysis was designed after the experiment and is not preregistered.

## Notebook and figure contracts

| Notebook | Scientific question | Evidence chain and figure roles |
|---|---|---|
| 00 | What population and evidence are actually represented? | Selection counts establish scope; register geography and sector proportions establish representation; coverage and missing-year counts expose availability filtering; canonical scale and visible-card counts separate storage from exposure; permitted-year matrices establish the time boundary; an exact example establishes provenance. |
| 01 | How much of each disclosure is supported, and where does that vary? | Execution counts define the cohort; the full score distribution establishes typicality and spread; direct/inferred/unsupported counts decompose the score; all twelve task intervals and company-year cells establish heterogeneity; secondary metric distributions and paired sensitivity quantify interpretation boundaries. |
| 02 | What do automated unsupported labels mean in concrete cases? | Composition separates claim burden from disclosure prevalence; task-normalised rates localise patterns; candidate and quote checks expose pipeline dependencies; fixed random examples test label meaning; an original PDF crop challenges a source-layout error. |
| 03 | Why do native evaluator scores differ? | Common-cohort ECDFs and paired differences establish the score gap; all-pair scatter plots distinguish rank and level agreement; native inventories and exact-text overlap expose denominator mismatch; all-task gaps localise differences; opposite-direction cases and source-inspected judgement paths explain specific mechanisms; independent annotation requirements bound conclusions. |

Figures are quantitative grids or source-reading plates, chosen for the question.
Each caption identifies encodings, denominator, units, selection and uncertainty.
Claims in the notebooks are computed from the current snapshot. Qualitative
readings use fixed source identifiers; examples are never silently replaced to
make a preferred interpretation easier.

## Per-figure reading contract

Every figure is a complete analytical unit, in this order:

1. A specific question that connects it to the surrounding investigation.
2. The figure and a reading caption explaining its marks, axes, cohort,
   denominator, units and any uncertainty interval.
3. The actual shape or source relationship, supported by numerical summaries
   or exact source details. Every panel receives its own interpretation.
4. The research meaning of that pattern and the joint reading of multiple panels.
5. Limits and plausible alternative readings specific to that figure.

Quantitative prose is computed from plotted source frames in
`figure_narrative.py`; qualitative prose uses the fixed inspected sources.
The renderer embeds the complete reading unit in saved notebook outputs and
the code-hidden HTML, and writes a companion `.reading.json` with source hashes.
No figure may silently omit its reading unit. Descriptions must not manufacture
a trend, interpret distributional shape as causality, or infer evaluator accuracy
from native score differences. Similar curves and weak trends are reported as such.

The reading audit checks coverage, panel count, question/figure/caption/analysis
order, current source hashes and recomputed prose. An explicit editorial review
must additionally assess whether each description fits the actual figure and
whether its numerical and qualitative evidence supports its interpretation.

## Statistical contract

- Retain the complete planned case inventory; missing scores remain missing.
- Use a common completed cohort for paired method comparisons.
- Primary estimator: unweighted mean of disclosure-level native scores.
- Supplement: pooled native claim rate, explicitly distinguished from the macro mean.
- Bootstrap complete company clusters, with all observed disclosures retained per
  sampled cluster; 2,000 draws, seed 20260921, percentile 95% intervals.
- Do not treat DCs, repeated tasks or years as independent companies.
- Report subgroup results and Spearman associations descriptively; no significance tests.
- Do not equate support with truth, compliance or completeness, or native score
  differences with evaluator accuracy.
- Do not treat exact-text overlap as representative semantic alignment.
- Statistical intervals do not include model randomness, annotation uncertainty,
  missing-case uncertainty or a design-adjusted extrapolation to the register.

## Rendering and integrity contract

Python/Matplotlib is the exclusive plotting backend. Use white backgrounds,
DejaVu Sans, restrained blue (#7AAED6), green (#83C5A3) and orange (#F3B27A),
with neutral grey and labelled categorical extensions. Use marker/line redundancy
where colour alone would be insufficient. Every main figure is 183 mm wide;
text is usually 7–9 pt, with a 5 pt minimum for rendered vector glyphs.
Original PDF crop text is also inspected at final size.

Every figure exports PDF, editable-text SVG, 600 dpi PNG, plotted source CSVs,
caption metadata, final plot-rectangle alignment (1.5 pt tolerance), PDF text and
collision audits. Dynamic source modules are audited as expanded notebook code
plus the shared rendering helper. Final visual and colour-vision reviews are
recorded separately; automatic passes alone do not prove scientific validity.

Analysis inputs are read only. Do not alter frozen scientific configuration,
experiment outputs, input data or the native runtime. Use the isolated analysis
environment, hash-verified snapshots, and local cached public-domain basemap.
No model/API execution is part of notebook reproduction.

## Acceptance

All four named notebooks must run independently from a fresh kernel, contain
actual saved figures and interpretation, and have a useful code-hidden reading
export. Numbers must agree across text, plots and source tables. All sources and
examples must be traceable. Export/QA records must correspond to the final render.
The scientific freeze, source PDF hashes and native runtime package inventory
must remain unchanged. Repeated execution must preserve all numerical source
outputs. Outstanding automatic failures block acceptance.
