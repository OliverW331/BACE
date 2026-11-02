# BACE writing rules

Established: 29 September 2026. Target: Nature Sustainability, Article.
These are project integrity rules, distinct from publisher requirements.

## Citation evidence

For each citation occurrence, verify existence and bibliographic metadata, then
read the original full-text passage, table, figure or supplement supporting the
exact assertion. Read its qualifications and methods where these change the
interpretation. A DOI response or an abstract is discovery evidence only.

Record the cite key, manuscript location, asserted claim, canonical identifier,
source version, source URL/local file, page/section/table locator, access date,
support verdict and limitations. Keep quotations short and faithful. A source
can support one occurrence but not another. Retractions, corrections, preprints
and published versions must be distinguished. Relevant contrary evidence must
be discussed honestly rather than silently removed.

If full text is unavailable, retain the candidate as `UNVERIFIED_FULL_TEXT` in
working notes and remove or qualify the unsupported manuscript assertion.
Failure to retrieve a source is not proof that the source is fabricated.
Use lawful access; never infer a DOI, author list or quotation from memory.

## Numerical provenance

Every manuscript number needs a saved result, including numbers copied from a
previous draft. For calculated results record:

- Input artifact paths and hashes, run/version and cohort selection.
- Script or notebook and the relevant cell/function, command and environment.
- Result file and row/column or JSON key, numerator, denominator and units.
- Macro/micro aggregation, missingness, exclusions, rounding and uncertainty.
- Seeds, resampling unit, interval definition and executed test when applicable.

Classify values as `SOURCE_REPORTED`, `COMPUTED_VERIFIED`,
`COMPUTATION_PENDING` or `UNVERIFIED`. Only the first two belong in final claims;
external reported values also require original-source verification. Refresh all
dependent numbers together when the source cohort or computation changes.
Search equivalent units and rounding variants before concluding a value lacks
support. Do not replace an unsupported number with an unsupported adjective.

Paired comparisons require matched observations or sufficient paired summary
statistics for the stated method. Separate model confusion matrices do not
recover their joint disagreements. McNemar's test can use verified discordant
pair counts, but does not establish evaluator accuracy without suitable labels.
Sampling uncertainty does not measure model-run or seed variability. Do not
infer significance from overlapping intervals, interval width or a large-looking
point difference. Preserve exploratory status and correct relevant test families.

## BACE evidence boundaries

Start from `01_paper_blueprint.md`, `02_evidence_map.md`,
`03_research_foundation.md`, `../BACE/PROTOCOL.md`,
`../BACE/analysis/ANALYSIS_SPEC.md` and the relevant saved results.
Working notes are maps to evidence, not a replacement for result files.

Distinguish case, claim, company-year and company. Repeated tasks and years can
be dependent within companies. Distinguish evidence claim coverage, all-DC
support and the separately labelled sensitivity support metric. Different
evaluators' native inventories and denominators cannot establish comparative
accuracy by themselves. The available evidence boundary does not establish
external truth, overall sustainability performance or ESRS compliance.

Report current saved run status and paired-cohort availability rather than
carrying forward a planned sample size. Check completed annotations and
adjudication before claiming human validation; conditional judgment validation
does not validate extraction, candidate recall or the entire pipeline.

## Missing information and author accountability

Use `AUTHOR_INPUT_NEEDED` for unknown affiliations, contributions, funding,
competing interests, ethics/consent, licences, data-access conditions and
submission decisions. Preserve stated facts; never manufacture negative
declarations such as "no competing interests". Describe planned work in future
tense and completed work only after inspecting its artifact.

Prepare requested text and reversible edits within the established scope.
Ask only for missing facts that affect the work. Disclosure of material AI use
must follow the current official policy; authors retain scientific judgment and
accountability. An internal AI critique is not journal peer review or acceptance.

## Journal and tool precedence

Use `NATURE_SUSTAINABILITY_GUIDELINES.md` for dated official requirements and
recheck at submission. Corpus-derived writing advice and upstream skill defaults
are not publisher mandates. Do not impose speech-conference structure, Elsevier
highlights, Harvard citations, flagship Nature limits or an arbitrary citation quota.

Use the independent writing-tools environment documented in the skill audit.
New calculations belong under `paper/` with saved inputs and provenance.
For standalone LaTeX work use the Codex editor and native compilation when
available; do not install TeX or run an upstream cleanup/compile script merely
because a skill mentions one. Publication, deposits and messages require the
author's instruction; preparing submission files does not imply submission.
