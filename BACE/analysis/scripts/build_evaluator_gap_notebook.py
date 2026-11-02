"""Build only notebook 04 from the standard experiment scaffold."""
from pathlib import Path
import subprocess
import sys
import textwrap

import nbformat as nbf

HERE = Path(__file__).resolve().parents[1]
PATH = HERE / "04_evaluator_gap_diagnostics.ipynb"
SCAFFOLD = Path.home() / ".codex/skills/jupyter-notebook/scripts/new_notebook.py"
subprocess.run([sys.executable, str(SCAFFOLD), "--kind", "experiment", "--title",
                "Evaluator gap diagnostics", "--out", str(PATH), "--force"], check=True, capture_output=True)
nb = nbf.read(PATH, as_version=4)
cells = []


def md(text):
    cells.append(nbf.v4.new_markdown_cell(textwrap.dedent(text).strip()))


def code(text):
    cell = nbf.v4.new_code_cell(textwrap.dedent(text).strip())
    cell.metadata = {"jupyter": {"source_hidden": True}}
    cells.append(cell)


md("""
# 04 · Why do the evaluators report different support levels?

**Objective.** Investigate whether BACE's lower native scores reflect loss or
alteration of evidence, construction of target claims, or support-judgment
rules. No evaluator is assumed to be correct. Support is relative to the
supplied evidence, not external truth, legal compliance or disclosure completeness.

**Reading route:** verified cohort → arithmetic sensitivities → candidate sets
→ claim-count controls → identical-wording judgments → source-linked examples
→ independent-review requirements → controlled prompt sensitivity.

This notebook executes the diagnostics supported by saved artifacts and adds
company-aware uncertainty. Independent evidence-loss rates, semantic coverage,
and independently validated temporal-rule effects remain **COMPUTATION_PENDING**.
Section 9 reads the separately executed support-prompt experiment and reports
its actual readiness. This notebook makes no model/API calls and creates no
human labels. These analyses were designed after the main experiment and are
not preregistered.

Each figure includes its question, source data, interpretation and specific
limits. A code-hidden HTML reading copy accompanies the executed notebook.
""")
code("""
from pathlib import Path
import os, sys
analysis_dir = Path.cwd()
if not (analysis_dir / 'evaluator_gap_analysis.py').exists():
    analysis_dir = analysis_dir / 'BACE' / 'analysis'
assert (analysis_dir / 'evaluator_gap_analysis.py').exists(), 'Run from the repository root or BACE/analysis.'
sys.dont_write_bytecode = True
sys.path.insert(0, str(analysis_dir))
runtime = analysis_dir / 'outputs' / 'evaluator_gap' / '.runtime'
os.environ['MPLCONFIGDIR'] = str(runtime / 'matplotlib')
import pandas as pd
from IPython.display import display, Markdown
from evaluator_gap_analysis import (load_inputs, compute_statistics, create_review_templates,
    finalize_provenance, OUT, ROOT, PAPER, SEED, DRAWS, sha, save_json)
from evaluator_gap_figures import (plot_sensitivity, plot_candidates, plot_inventory, plot_literal, note)
pd.set_option('display.max_colwidth', 100)

def estimates(frame, label):
    result = frame[[label, 'estimate', 'low', 'high', 'companies_with_observations', 'denominator']].copy()
    for column in ['estimate', 'low', 'high']:
        result[column] = (100 * result[column]).round(2)
    return result.rename(columns={'estimate':'Estimate (%) or difference (pp)', 'low':'95% interval: lower',
        'high':'95% interval: upper', 'companies_with_observations':'Companies', 'denominator':'Units'})
""")
md("""
## 1. Which records are compared, and what has been verified?

The original analysis snapshot is read without regeneration. The earlier
paper-level diagnostic tables are reused as hash-verified derived inputs and
reconciled against claim-level records. New results have a separate output
directory; no earlier notebooks or outputs are overwritten.

An incomplete BACE result remains missing. A literal match belongs to the same
disclosure and requires a unique complete string after casefolding and whitespace
normalization. It is not a human semantic alignment or a reference label.
""")
code("""
data = load_inputs()
display(data['cohorts'])
case, claims, pairs = data['case'], data['claims'], data['pairs']
note(f"**Verified data:** {len(case):,} paired disclosures, {case.company_id.nunique()} companies, "
     f"{len(claims):,} BACE target claims, and {len(pairs):,} unique literal BACE–RAGAS pairs. "
     f"The literal pairs cover {100 * len(pairs) / len(claims):.2f}% of BACE DCs. "
     "Snapshot hashes, native arithmetic and consumed example source hashes passed. "
     "The entire raw-call history and extraction lineage were not re-audited.")
display(pd.read_csv(OUT / 'tables' / 'excluded_cases.csv'))
""")
md("""
### Statistical definitions

The primary native score gives each disclosure equal weight. Literal-pair
pooled rates give each matched target equal weight; an accompanying case-macro
sensitivity gives each disclosure with a match equal weight. These estimands
are never interchanged.

Where shown, 95% percentile intervals resample complete company clusters with
replacement, retaining every record and method pairing in each selected
company. There are 2,000 draws with seed 20260921. The same resamples are used
for all conditions. Subgroup ratios include the full common-cohort company
universe, with zero contributions from companies outside that subgroup.

These intervals describe resampling of the observed companies. They are not
design-adjusted estimates for all companies in the source register and do not
include model-run, annotation or missing-case uncertainty. No significance
tests, p-values or causal attribution are reported. Leave-one-company-out
ranges provide an additional descriptive influence check.
""")
code("""
tables = compute_statistics(data)
display(tables['analysis_readiness'])
""")
md("""
## 2. Can denominator treatment or completely empty candidate sets explain the gap?

Two precisely defined arithmetic sensitivities are evaluated. The first
removes only BACE-unsupported DCs diagnosed as `non_disclosure_statement`.
The second hypothetically changes every zero-candidate DC to supported.
Neither is a model rerun, independently justified correction, or proposed
replacement for the primary score. Their subsets overlap.
""")
code("""
plot_sensitivity(tables)
display(estimates(tables['paired_effects'], 'contrast'))
""")
md("""
## 3. What do candidate sets reveal about possible evidence loss?

Candidate counts can identify an empty-set bottleneck. They cannot establish
whether a nonempty set contains the required premise or preserves its scope.
The distribution below therefore diagnoses pipeline structure rather than
candidate recall or evaluator correctness.
""")
code("""
plot_candidates(tables)
candidate_summary = tables['candidate_sets'].copy()
candidate_summary['zero_candidate_percent'] = (100 * candidate_summary.pop('zero_candidate_fraction')).round(2)
display(candidate_summary)
""")
md("""
## 4. Is a larger BACE claim count necessary for lower scores?

We condition on whether BACE's native inventory is larger, equal, or no larger
than the comparator's. This is a descriptive control for claim count, not a
semantic control for which propositions were extracted. Equal-count cases
are part of the no-greater group and are shown as a nested sensitivity.
""")
code("""
plot_inventory(tables)
inventory_intervals = estimates(tables['inventory_groups'].assign(
    comparison=lambda d: d.method + ' / ' + d.group), 'comparison')
display(inventory_intervals)
""")
md("""
## 5. Do identical target words receive identical judgments?

Each matched row is a target assertion extracted from the generated disclosure.
Evidence is supposed to support that target. The pairing was performed after
native evaluation; the evaluators were not rerun on a newly standardized
input. BACE still used selected ECs while RAGAS used all supplied cards.

No unique literal RAGChecker partners were found by the existing matching
rule. Its joined-triplet representation requires semantic mapping for a
meaningful shared-proposition comparison. Zero string matches do not imply
zero semantic overlap.
""")
code("""
plot_literal(tables)
display(estimates(tables['literal_pooled_estimates'], 'quantity'))
""")
md("""
### Does changing the weighting or removing one company change the reading?

The first table below averages scores within each matched disclosure before
averaging across disclosures. It includes only disclosures with at least one
literal pair. It does not recover the native full-inventory macro score.

The second table removes each company in turn. These are influence ranges,
not confidence intervals and not independent replication. A stable range
does not repair the selection bias of literal matching.
""")
code("""
display(estimates(tables['literal_case_estimates'], 'quantity'))
influence = pd.concat([
    tables['paired_effects'].loc[tables['paired_effects'].contrast.isin(['BACE minus RAGChecker', 'BACE minus RAGAS'])]
        .rename(columns={'contrast':'quantity'}),
    tables['literal_pooled_estimates'].loc[tables['literal_pooled_estimates'].quantity.eq('BACE minus RAGAS')]
        .assign(quantity='Literal pairs: BACE minus RAGAS')], ignore_index=True)
influence = influence[['quantity','estimate','leave_one_company_out_min','leave_one_company_out_max']].copy()
influence.iloc[:,1:] = (100 * influence.iloc[:,1:]).round(2)
display(influence.rename(columns={'estimate':'Paired difference (pp)',
    'leave_one_company_out_min':'Leave-one-company-out minimum (pp)',
    'leave_one_company_out_max':'Leave-one-company-out maximum (pp)'}))
""")
md("""
### What are BACE's own diagnoses within the selected disagreements?

The next counts are saved automated diagnoses among BACE-unsupported /
RAGAS-supported literal pairs. They identify records to inspect. They do not
establish the prevalence of independently confirmed failure mechanisms.
In particular, `factual_boundary_distortion` is not an independently measured
temporal category.
""")
code("""
diagnoses = tables['literal_disagreement_diagnoses'].copy()
diagnoses['percent_of_selected_disagreements'] = (100 * diagnoses.pop('fraction_of_selected_disagreements')).round(2)
display(diagnoses)
""")
md("""
## 6. What evidence does RAGAS accept in concrete matched claims?

These fixed illustrations were selected for the earlier discussion from the
first company in the sorted literal-pair file. They are neither random nor
representative, and they do not estimate mechanism frequencies. Both
agreement and disagreement examples are retained. Original generated passages,
all input cards, full EC inventories and selected ECs are preserved in the
[source bundle](../../paper/analysis/evaluator_gap/literal_examples.json).

A later BACE diagnosis is not an independent account of why the earlier
support stage made its decision.
""")
code("""
qualifications = [
    'The supplied table gives the 2017 count and BACE also supports it. Reporting coverage remains a separate qualifier.',
    'RAGAS cites the environmental-obligation wording; BACE questions extension of a 2016 report statement to the 2019 context. The continuity rule needs independent review.',
    'The supplied 2018 social-scope footnote names HOP!, whereas BACE has no candidate ECs. This establishes an information-path difference; source scope and target-year applicability remain unresolved.',
    'RAGAS reads new training-access methods as broadened access. Candidate ECs retain the new methods, but BACE questions the stronger characterization. This is a proposed rule-sensitive example, not an adjudicated error.',
    'The source describes prospective expenditure under a discipline framework in 2015. BACE questions both the temporal extension and the claim of actual management in the 2019 context.'
]
for example, qualification in zip(data['examples']['examples'], qualifications):
    native = example['ragas_claim']
    diagnosis = example['bace_diagnosis']
    bace_text = diagnosis['rationale'] if diagnosis else 'Saved supported judgment; no unsupported diagnosis.'
    note('**Target:** ' + example['pair']['bace_dc_text'] + '\\n\\n'
         '**RAGAS saved reason:** ' + native['reason'] + '\\n\\n'
         '**BACE candidate ECs:** ' + str(len(example['candidate_ecs'])) + '. **Later diagnosis:** ' + bace_text + '\\n\\n'
         '**Source-inspection limit:** ' + qualification)
""")
md("""
**Evonik correction.** The previously discussed emissions-total example is
not a confirmed BACE false rejection. The actual supplied table contains the
number but omits complete unit/column context. The later contradiction
rationale remains questionable, but this does not establish that the binary
unsupported decision was wrong. See the
[input-boundary recheck](../../paper/analysis/evaluator_gap/evonik_boundary_recheck.json).

## 7. Independent evidence-chain analysis — COMPUTATION_PENDING

For each sampled target, first verify its fidelity to the generated passage.
Then independently judge sufficiency against (R) all original prompt-visible
cards, (E) the full EC inventory, and (C) the candidate ECs. Add pre-dedup ECs
if extraction and deduplication losses need separate estimates. Preserve
source locators, sufficient premise sets, ambiguity and initial reviewer labels.

The principal quantity is the fraction of BACE rejections that full-source
review supports: `count(B = unsupported and R = supported) / count(B = unsupported)`,
using design weights when sampled. Stage-specific loss rates condition on
sufficient support at the preceding stage; their denominators differ and
they cannot be added. Audit accepted claims too, to detect spurious support
and estimate any net reassessment of the score.

The existing candidate-only reviewer packets supply neither R nor E. Their
400 primary and 200 enriched supplementary units must not be pooled
unweighted. Full-source review added to the primary sample could address
BACE-inventory questions, but would still not validate extraction coverage.

No empty plot or zero-valued loss estimate is displayed for these missing data.
""")
md("""
## 8. Claim construction and inference rules — COMPUTATION_PENDING

Build a neutral proposition inventory from probability-sampled generated
passages. Map each native inventory to it, preserving one-to-one and
split/merged relations, omissions and added qualifiers. Do not propagate an
unsupported conjunction to every component.

With fixed evidence, a common judgment procedure applied to different target
inventories can describe construction effects. With fixed targets and
evidence, different explicitly adapted judgment procedures can describe
procedure effects. A crossed design additionally estimates their interaction.
Such conditions are additional experiments, not unchanged native scores;
none is run by this notebook.

Independently annotate whether the target requires temporal carry-forward,
its asserted period and relevant evidence period. Do not infer this solely
from BACE diagnoses or the oldest card in the prompt. Paired method gaps can
then be compared between temporal and non-temporal targets. Strict-period
and explicitly defined continuity rules can be assessed on the same claims;
relaxing a rule changes the support construct and does not prove a prior
error. Ordinary independent-claim tests would ignore company dependence.

The complete estimands, sampling limits and controlled-condition design are in
the [statistical analysis plan](../../paper/analysis/evaluator_gap/statistical_analysis_plan.md).
""")
code("""
review_templates = create_review_templates()
display(review_templates)
note('**These are header-only schemas.** They are not sampled reviewer packets or completed human annotations. '
     'Existing files are never overwritten, and no template data are treated as a reference automatically. '
     '[Review schema guide](outputs/evaluator_gap/review_templates/README.md).')
""")
md("""
## 9. How sensitive is BACE to its support-judgment instructions?

The author-authorized experiment fixes every BACE DC, its ordered candidate
ECs, company and reporting year, model request settings, message roles, JSON
schema and native parser. It changes only the support-judgment instructions
and criteria. **BACE–RAGAS-style** and **BACE–RAGChecker-style** retain BACE's
support-set output task and are not native baseline evaluations.

The [frozen protocol](../experiments/prompt_sensitivity_v1/PROTOCOL.md),
[input and sampling plan](../experiments/prompt_sensitivity_v1/plan.json),
[RAGAS-style prompt](../experiments/prompt_sensitivity_v1/prompts/ragas_style_v1.txt)
and [RAGChecker-style prompt](../experiments/prompt_sensitivity_v1/prompts/ragchecker_style_v1.txt)
were saved before the first new model call. The original-to-adapted diffs
record both the native criterion and the changes needed for BACE compatibility.

Both new conditions keep the same output contract and minimality section, and
share descriptive direct/inferred labels. The original strict necessary-inference
restrictions are part of the replaced judgment instructions. The primary
endpoint is whether support_sets is nonempty; inferred-label proportions do
not establish a common strict-inference construct or reasoning ability.

All original claims, including originally supported claims, are replayed.
Empty-candidate jobs remain deterministic unsupported and in the denominator.
Runtime or parsing failures remain missing. Final scores use only disclosures
with every claim complete in all three conditions; the original score is
recomputed on that identical cohort. No final primary estimate is shown while
the full scheduled run is incomplete.
""")
code("""
from evaluator_gap_prompt_sensitivity import load_analysis, LABELS as PROMPT_LABELS, DEST as PROMPT_OUT
from evaluator_gap_prompt_figures import plot_prompt_effects, plot_prompt_transitions

def prompt_effect_display(frame):
    if frame.empty:
        return frame
    shown = frame[['condition','disclosures','claims']].copy()
    shown['condition'] = shown.condition.map(PROMPT_LABELS)
    shown['Change (pp, 95% CI)'] = frame.apply(
        lambda r: f'{100*r.estimate:+.2f} [{100*r.low:+.2f}, {100*r.high:+.2f}]', axis=1)
    return shown

prompt_results = load_analysis()
display(prompt_results['completeness'])
if not prompt_results['ready']:
    note('**COMPUTATION_PENDING — prompt sensitivity.** Current saved run status: '
         + prompt_results['status'] + '. Full-cohort support estimates and figures are withheld. '
         'The notebook reads saved results only; it does not launch or resume model calls.')
else:
    note('**COMPUTED_VERIFIED — paired prompt sensitivity.** All scheduled jobs have a recorded outcome. '
         'Failed jobs remain missing and incomplete disclosures are excluded as whole units. '
         'Counts below identify the exact analyzed cohort.')
""")
md("""
### Support-rate changes and individual transitions

The main table averages support rates over complete paired disclosures.
Intervals resample company clusters using the same 2,000 draws and seed as
the earlier sections. Effect units are percentage points, not relative percent
changes. The two transition panels instead pool claim counts and display
percentages conditional on the original judgment in each row.

Company bootstrap intervals condition on the observed runs. They do not
measure independent model-run variance or establish correctness. Native RAGAS
and RAGChecker scores are background comparisons with different inventories;
they are not additional rows in this controlled experiment.
""")
code("""
if prompt_results['ready']:
    display(prompt_results['disclosure_completeness'])
    if not prompt_results['failed_records'].empty:
        note('**Recorded failures remain missing.** A failed full-condition claim excludes its entire disclosure from the primary paired analysis. '
             'A failed repeat-control claim excludes its disclosure from the repeat comparison. '
             '[Failure details and record hashes](outputs/evaluator_gap/prompt_sensitivity/tables/failed_records.csv).')
        display(prompt_results['failed_records'][['condition','generation_case_id','dc_id',
            'call_status','output_attempts','validation_error','error_type']])
    score_table = prompt_results['scores'].copy()
    effect_index = prompt_results['effects'].set_index('condition')
    score_table['Mean support (%, 95% CI)'] = score_table.apply(
        lambda r: f'{100*r.estimate:.2f} [{100*r.low:.2f}, {100*r.high:.2f}]', axis=1)
    score_table['Change (pp, 95% CI)'] = score_table.condition.map(lambda c: 'Reference' if c == 'original' else
        f'{100*effect_index.loc[c,"estimate"]:+.2f} [{100*effect_index.loc[c,"low"]:+.2f}, {100*effect_index.loc[c,"high"]:+.2f}]')
    display(score_table[['label','disclosures','claims','Mean support (%, 95% CI)','Change (pp, 95% CI)']])
    plot_prompt_effects(prompt_results)
    plot_prompt_transitions(prompt_results)
    display(prompt_results['transitions'])
    note('**Separate pooled estimand:** the following table weights each claim equally. It is not the disclosure-macro primary score.')
    pooled_display = prompt_results['pooled'].copy()
    pooled_display['support_rate_percent'] = (100 * pooled_display.pop('support_rate')).round(2)
    pooled_display['condition'] = pooled_display.condition.map(PROMPT_LABELS)
    display(pooled_display)
""")
md("""
### Company influence, overlapping flips and a contemporaneous repeat control

Two disclosures per company were selected by a fixed hash rule before new
outputs were inspected. All their claims are rerun with the original BACE
prompt during the new experiment. This 60-disclosure control compares one
current run with historical BACE; it is not a replicated variance decomposition.
The next table compares all three current conditions with historical BACE
on the same complete repeat subset.

Company-specific effects and leave-one-company-out ranges show concentration
and influence. Ranges are not confidence intervals. The overlap table reports
whether each variant flips the original binary label; if both flip a label,
their new binary direction is necessarily the same.

The directional table separates shared additions to support from shared
removals. Its shared fraction divides the intersection by the union of the
two variants' flipped claims in that direction. It is undefined when neither
variant flips any claim in that direction.
""")
code("""
if prompt_results['ready']:
    display(prompt_effect_display(prompt_results['repeat_effects']))
    display(prompt_results['repeat_transitions'])
    display(prompt_results['flip_overlap'])
    directional_display = prompt_results['flip_overlap_by_direction'][['direction',
        'original_status_denominator','ragas_flips','ragchecker_flips','both_flips',
        'union_flips','shared_fraction_of_union']].copy()
    directional_display['Shared fraction of union (%)'] = (100 * directional_display.pop('shared_fraction_of_union')).round(2)
    display(directional_display)
    company_display = prompt_results['company_effects'].copy()
    for column in ['original_rate','new_rate','delta']:
        company_display[column] = (100 * company_display[column]).round(2)
    display(company_display.rename(columns={'original_rate':'Original support (%)',
        'new_rate':'New support (%)','delta':'Change (pp)'}))
    influence_display = prompt_results['effects'][['label','leave_one_company_out_min','leave_one_company_out_max']].copy()
    influence_display.iloc[:,1:] = (100 * influence_display.iloc[:,1:]).round(2)
    display(influence_display.rename(columns={'leave_one_company_out_min':'Leave-one-company-out minimum (pp)',
        'leave_one_company_out_max':'Leave-one-company-out maximum (pp)'}))
    note('Full source tables, including excluded disclosures and individual paired claims, are saved in '
         '[the prompt-sensitivity table directory](outputs/evaluator_gap/prompt_sensitivity/tables).')
""")
md("""
### Source-linked examples from both flip directions

Examples are selected by a fixed hash ranking, up to three per variant and
direction, preferring distinct companies. They are illustrations of automated
disagreement, not completed human review. Expand an example to inspect the
entire target, every candidate EC and all three support-set outputs. Original
EC identifiers in the support sets are linked to the input aliases in the
display. Original diagnoses are not used as truth labels.
""")
code("""
if prompt_results['ready']:
    import html, json
    from IPython.display import HTML
    for example in prompt_results['examples']['examples']:
        payload = {'context_metadata': example['dynamic_input']['context_metadata'],
                   'dc_claim': example['dynamic_input']['dc_claim'],
                   'candidate_ecs': [dict(ec, original_ec_id=example['ec_original_by_alias'][ec['ec_claim_id']])
                                     for ec in example['dynamic_input']['ec_claims']],
                   'original_support_sets': example['original_support_sets'],
                   'ragas_style_support_sets': example['ragas_style_support_sets'],
                   'ragchecker_style_support_sets': example['ragchecker_style_support_sets']}
        label = ' / '.join(example['selection_reasons']) + ': ' + example['dynamic_input']['dc_claim']['dc_text']
        display(HTML('<details><summary>' + html.escape(label) + '</summary><pre>' +
                     html.escape(json.dumps(payload, ensure_ascii=False, indent=2)) + '</pre></details>'))
    note('[Complete example bundle](outputs/evaluator_gap/prompt_sensitivity/examples.json) · '
         '[Prompt-analysis provenance](outputs/evaluator_gap/prompt_sensitivity/provenance.json)')
    from evaluator_gap_prompt_findings import write_findings
    display(Markdown(write_findings(prompt_results)))
""")
md("""
## 10. What can this notebook conclude now?

The two specified arithmetic changes leave large native differences. A larger
BACE claim count is not necessary for lower scores. Identical target wording
also leaves a substantial selected disagreement, so evidence representation
and judgments need inspection. Concrete records exhibit several plausible
paths, including historical-policy interpretation and absent candidate anchors.

These findings do not quantify validated evidence loss, establish native
evaluator accuracy, or allocate the total score gap to mechanisms. The next
evidence needed is independent source/EC/candidate review, neutral proposition
mapping and independently defined temporal/inference rules. Section 9 reports
the readiness and results of the separate controlled support-prompt experiment.
A change there measures instruction sensitivity under fixed BACE candidate
evidence; it does not establish a prior error, repair evidence losses or
allocate the native evaluator gap to prompt effects.

## Reproducibility and artifact boundaries

This notebook writes only its own tables, figures, provenance and empty
schemas under `outputs/evaluator_gap/`. It does not install packages, rebuild
the shared snapshot or invoke evaluators. Statistical code and rendering are
in `evaluator_gap_analysis.py` and `evaluator_gap_figures.py`; the prompt extension
uses `evaluator_gap_prompt_sensitivity.py`, `evaluator_gap_prompt_figures.py`
and `evaluator_gap_prompt_findings.py`. The dedicated runner records kernel
execution, protected-file checks and HTML export.
""")
code("""
finalize_provenance()
assert all(frame['undefined_draws'].eq(0).all() for frame in
    [tables['score_conditions'], tables['paired_effects'], tables['inventory_groups'],
     tables['literal_pooled_estimates'], tables['literal_case_estimates']])
note('**Completed:** saved-artifact diagnostics, company-cluster intervals, influence checks and source-linked readings. '
     '**Pending:** independent loss/accuracy estimates, semantic coverage and validated temporal-rule effects. '
     'The controlled prompt experiment has its own explicit readiness in Section 9. '
     '[Provenance](outputs/evaluator_gap/provenance.json) · '
     '[Analysis readiness](outputs/evaluator_gap/tables/analysis_readiness.csv).')
""")
nb.cells = cells
nb.metadata.kernelspec = {"display_name": "BACE evaluator gap (Python)", "language": "python", "name": "bace-evaluator-gap"}
nb.metadata.language_info = {"name": "python", "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"}
nb.metadata["analysis_status"] = "Post-experiment exploratory; independent validation pending"
nbf.validate(nb)
nbf.write(nb, PATH)
print(f"Built {PATH.name}: {len(cells)} cells; {sum(c.cell_type == 'code' for c in cells)} code cells.")
