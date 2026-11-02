"""Render completed prompt findings from saved paired calculations; no model calls."""
from datetime import datetime, timezone
from pathlib import Path

from evaluator_gap_analysis import ROOT, sha, save_json
from evaluator_gap_prompt_sensitivity import DEST, LABELS, VARIANTS


CASE_READINGS = [
    ("dc_64e76c6b43635f2b74606edd2b45dea2", "Kinnevik: historical policy wording",
     "All four candidate ECs describe anti-bribery provisions in the Code of Conduct in 2017 or 2018; the target reporting year is 2020. The RAGChecker-style condition accepts this target while the other two conditions reject it. The unresolved question is whether the historical descriptions support the policy's application in the target year."),
    ("dc_212aa288e4c442a26a37725975d29693", "SCA: the opposite direction for a policy claim",
     "The sole candidate EC says that work against corruption was included in SCA's Code of Conduct according to its 2019 report; the target reporting year is 2022. Original BACE accepts it and both adapted conditions reject it. Together with the Kinnevik case, this cautions against assuming that either adapted prompt uniformly relaxes temporal judgments."),
    ("dc_3cad0ec41f9faa366daa1d4f4b0f7ce8", "Mondi: a matching number with an additional relationship",
     "The sole candidate EC gives the 90% inclusiveness ambition but does not name MAP2030. The target attaches that ambition to MAP2030 in a 2021 reporting context, whereas the EC cites the 2020 report. Original BACE accepts the target and both adapted conditions reject it. Candidate-level inspection identifies the plan relationship and time interpretation as questions; it does not establish what the uninspected raw source says."),
    ("dc_6dcd8f61285862c8b866370b13d25f1a", "Covestro: combining separate statements",
     "The RAGAS-style support set combines ECs about real-time positive trends, real-time negative trends, and corresponding short-term corrective measures. All candidates cite the 2017 report, while the reporting context is 2019. Only RAGAS-style accepts the combined target. Interpreting the relationship between these statements and its temporal scope requires a separately specified rule."),
    ("dc_de3cd29c59c26e6d90de7a45f30b0645", "D'Ieteren: an originally accepted combination",
     "The two candidate ECs identify Human Resources as the employee-well-being initiative owner and describe initiative owners' responsibility for deploying actions. Both cite the 2022 report, with a 2023 target reporting context. Original BACE combines them into a support set; both adapted conditions return empty sets. Changing the instructions therefore also removes support that originally involved a combination of ECs."),
]


def write_findings(result):
    """Write a numerical reading and bounded case commentary for notebook 04."""
    assert result['ready'], 'Completed paired results are required'
    scores = result['scores'].set_index('condition')
    effects = result['effects'].set_index('condition')
    repeat = result['repeat_effects'].set_index('condition')
    overlap = result['flip_overlap_by_direction'].set_index('direction')
    original = scores.loc['original']
    failures = result['failed_records']
    excluded = failures.loc[failures.condition.isin(VARIANTS), 'generation_case_id'].nunique()
    lines = [
        '### Reading the completed experiment',
        f"The primary analysis contains **{int(original.disclosures):,} complete paired disclosures and {int(original.claims):,} claims from {int(original.companies_with_observations)} companies**. The {len(failures)} final failed records remain missing; {excluded} affected disclosures are excluded as whole units. All scheduled jobs have recorded outcomes. Sources: `execution_completeness.csv`, `failed_records.csv`, `disclosure_completeness.csv` and `scores.csv` in the table directory.",
        f"Original BACE's disclosure-macro support rate is **{100*original.estimate:.2f}%** (95% company-cluster interval {100*original.low:.2f}–{100*original.high:.2f}%). Each disclosure receives equal weight. Sources: `scores.csv` and `effects.csv`.",
    ]
    for condition in VARIANTS:
        score, effect = scores.loc[condition], effects.loc[condition]
        transitions = result['transitions'].loc[lambda f: f.condition.eq(condition)]
        addition = transitions.loc[lambda f: ~f.original_supported & f.new_supported].iloc[0]
        removal = transitions.loc[lambda f: f.original_supported & ~f.new_supported].iloc[0]
        flips = int(addition.claims + removal.claims)
        company = result['company_effects'].loc[lambda f: f.condition.eq(condition)]
        lines.append(
            f"**{LABELS[condition]}:** support is {100*score.estimate:.2f}% (95% CI {100*score.low:.2f}–{100*score.high:.2f}%), a change of **{100*effect.estimate:+.2f} percentage points** (95% CI {100*effect.low:+.2f} to {100*effect.high:+.2f}). It changes {int(addition.claims):,} originally unsupported claims to supported ({100*addition.fraction_original_status:.2f}% of {int(addition.original_status_denominator):,}) and {int(removal.claims):,} originally supported claims to unsupported ({100*removal.fraction_original_status:.2f}% of {int(removal.original_status_denominator):,}). In total, {flips:,}/{int(original.claims):,} claims change ({100*flips/original.claims:.2f}%). The average effect is positive in {int(company.delta.gt(0).sum())}/{len(company)} companies. Leaving out one company at a time gives {100*effect.leave_one_company_out_min:.2f}–{100*effect.leave_one_company_out_max:.2f} pp; this range is an influence check, not a confidence interval. Sources: `scores.csv`, `effects.csv`, `transitions.csv` and `company_effects.csv`."
        )
    lines.append(
        'The higher means coexist with substantial changes in both directions. These are not monotonic expansions of the original supported set. The transition counts weight claims equally; their net fraction must not be substituted for the disclosure-macro effect.'
    )
    add, remove = overlap.loc['unsupported_to_supported'], overlap.loc['supported_to_unsupported']
    lines.append(
        f"The two variants share {int(add.both_flips):,} newly supported claims out of {int(add.union_flips):,} supported by at least one variant ({100*add.shared_fraction_of_union:.2f}% of that union). They share {int(remove.both_flips):,} newly rejected claims out of a union of {int(remove.union_flips):,} ({100*remove.shared_fraction_of_union:.2f}%). Their changes overlap only partly. Source: `flip_overlap_by_direction.csv`."
    )
    rep = repeat.loc['original_repeat']
    rt = result['repeat_transitions'].loc[lambda f: f.condition.eq('original_repeat')]
    additions = int(rt.loc[~rt.original_supported & rt.new_supported, 'claims'].sum())
    removals = int(rt.loc[rt.original_supported & ~rt.new_supported, 'claims'].sum())
    lines.append(
        f"On the fixed repeat subset of {int(rep.disclosures)} disclosures and {int(rep.claims):,} claims, rerunning the original prompt changes the macro mean by **{100*rep.estimate:+.2f} pp** (95% CI {100*rep.low:+.2f} to {100*rep.high:+.2f}). This small net change masks {additions} additions and {removals} removals: {additions+removals}/{int(rep.claims):,} claims change ({100*(additions+removals)/rep.claims:.2f}%). On that same subset, RAGAS-style changes the historical mean by {100*repeat.loc['ragas_style','estimate']:+.2f} pp and RAGChecker-style by {100*repeat.loc['ragchecker_style','estimate']:+.2f} pp. Thus individual flips cannot all be assigned to the changed prompt. One repeat cannot separate all sources of run variability, and company bootstrap intervals condition on these observed runs. Sources: `repeat_effects.csv` and `repeat_transitions.csv`."
    )
    lines.extend([
        '### What the selected cases can and cannot explain',
        'The following exploratory readings use five cases from the fixed, hash-selected example bundle displayed above. The choice of cases to discuss is interpretive, not a prevalence sample. These are assistant readings of saved candidate ECs and support sets, not independent human validation or raw-source adjudication. The support-stage outputs do not provide judge rationales; possible interpretive questions below are not established causes of the verdicts.',
    ])
    examples = {x['dc_id']: x for x in result['examples']['examples']}
    for dc_id, title, reading in CASE_READINGS:
        example = examples[dc_id]
        verdicts = '; '.join(f"{LABELS[c]}: {'supported' if example[c+'_support_sets'] else 'unsupported'}"
                             for c in ['original', *VARIANTS])
        lines.append(f"**{title}.** {example['dynamic_input']['dc_claim']['dc_text']}\n\n{reading}\n\n{verdicts}. Locator: `{example['generation_case_id']}` / `{dc_id}` in `examples.json`; the full candidate set and all three support sets are preserved there.")
    lines.extend([
        '### Scope of the conclusion',
        'The observed support rates and individual judgments are sensitive to the bundled judgment instructions under fixed BACE claims, candidate ECs, model settings and output requirements. The experiment does not validate the newly accepted or newly rejected claims, repair losses during evidence processing, or identify evaluator accuracy. It does not allocate any percentage of the native RAGAS/RAGChecker–BACE gap to prompts: native inventories, evidence presentation and other framework operations differ. Independent source review and explicit temporal and inference rules remain necessary.',
    ])
    text = '\n\n'.join(lines) + '\n'
    path = DEST/'findings.md'
    path.write_text(text)
    sources = list((DEST/'tables').glob('*.csv')) + [DEST/'examples.json', Path(__file__)]
    save_json(DEST/'findings_provenance.json', {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'findings_sha256': sha(path),
        'sources': {str(p.relative_to(ROOT)): sha(p) for p in sorted(sources)},
        'case_dc_ids': [x[0] for x in CASE_READINGS],
        'reading_scope': 'Saved candidate evidence and automated support sets only.',
        'independent_human_validation': False,
    })
    return text
