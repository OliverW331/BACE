"""Source-grounded reading units displayed around every notebook figure.

Quantitative descriptions are recomputed from the figure's own source frames.
Qualitative readings refer to the fixed, inspected excerpts and case bundles.
The rendering layer saves these units beside the plotted data for review.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from analysis_data import company_bootstrap, METHODS, OUT, read


def unit(question, pattern, meaning, limits, panels=1):
    return dict(question=question, pattern=pattern, meaning=meaning, limits=limits, panels=panels)


def pct(x):
    return f'{100*x:.1f}%'


def pp(x):
    return f'{100*x:.1f}'


def span(x):
    return f'{pct(x.quantile(.25))}–{pct(x.quantile(.75))}'


def explain_figure(name, frames):
    """Fail on missing editorial coverage instead of silently omitting analysis."""
    d = frames.get('data')
    if name.startswith('00_'):
        return landscape(name, d, frames)
    if name.startswith('01_'):
        return support(name, d, frames)
    if name.startswith('02_example_'):
        return example(name, d)
    if name.startswith('02_'):
        return diagnosis(name, d)
    if name.startswith('03_'):
        return comparison(name, d, frames)
    raise KeyError(name)


def landscape(name, d, frames):
    if name == '00_selection':
        n, eligible, selected = d.companies
        return unit(
            'How much of the source register survives availability screening and final selection?',
            f'The bars contract from {n:,} to {eligible:,} to {selected:,} companies: '
            f'{pct(eligible/n)} are eligible, and {pct(selected/eligible)} of that eligible pool is selected '
            f'({pct(selected/n)} of the register). Most of the initial reduction therefore happens before sampling.',
            'Subsequent results describe a small subset with sustained historical source availability. '
            'The sharp narrowing makes the selection rule part of the interpretation of every later score.',
            'These are exact counts for this register, without sampling-error bars. Availability screening '
            'does not establish report quality, accurate extraction, or representativeness of the wider company population.')
    if name == '00_geography':
        ranked = d.sort_values(['companies', 'country'], ascending=[False, True])
        top = ranked.iloc[:2]
        return unit(
            'After selection, where are the companies registered, and is geographical coverage evenly spread?',
            f'The map covers {len(d)} European register countries. The darkest countries are '
            + ' and '.join(f'{r.country} ({r.companies})' for r in top.itertuples())
            + f'; together they account for {int(top.companies.sum())}/{int(d.companies.sum())} companies '
            f'({pct(top.companies.sum()/d.companies.sum())}). '
            f'{int((d.companies==1).sum())} countries contribute only one company each. '
            'The concentration is in selected company counts, not in country land area.',
            'This uneven coverage identifies where the sample has more observations and where a country-specific '
            'reading would depend on a single company. The country field locates the register entry; multinational operations can extend far beyond it.',
            'Colour represents counts, not companies per capita, market share or environmental impact. '
            'Large polygons draw more visual attention without receiving greater statistical weight. '
            'Uncoloured countries have no selected companies; they do not have zero ESG activity.')
    if name == '00_sector_selection':
        p = d.pivot(index='sector', columns='cohort', values='percent').fillna(0)
        selected = d[d.cohort=='Selected'].sort_values(['companies','sector'], ascending=[False,True])
        small = selected.loc[selected.companies.idxmin()]
        leaders = selected[selected.companies == selected.companies.max()]
        shifts = p.Selected-p.Eligible
        return unit(
            'Does the geographical sample also preserve the sector mix, or does stratification change it?',
            f'The selected markers cover {len(selected)} sectors. '
            + ' and '.join(f'{r.sector} ({r.companies}/30; {r.percent:.1f}%)' for r in leaders.itertuples())
            + f' are the largest groups. {small.sector} rises from '
            f'{p.loc[small.sector,"Eligible"]:.1f}% of eligible companies to {small.percent:.1f}% '
            f'of selected companies, but still contains only {small.companies} company. '
            f'Selected-minus-eligible shifts span {shifts.min():+.1f} to {shifts.max():+.1f} percentage points.',
            'The minimum allocation of one company per eligible sector raises the relative weight of a small sector '
            'and reduces that of larger sectors. Marker separation is therefore an expected consequence of allocation, '
            'not evidence that some sectors perform better.',
            'Each cohort has its own denominator (600, 250 or 30). A selected share of 3.3% is one company; '
            'its many repeated disclosures cannot substitute for multiple independent companies in that sector.')
    if name == '00_source_coverage':
        csv = d.csv_valid_metrics
        pdf = d.pdf_valid_headers.dropna()
        years = d.groupby('year').csv_valid_metrics.median()
        companies = d.groupby('company_name').csv_valid_metrics.mean().sort_values()
        return unit(
            'Within the selected sample, does complete annual availability also mean equal amounts of source material?',
            f'Panel a has no empty required company-year cells, but CSV counts range from {int(csv.min())} '
            f'to {int(csv.max())} (median {csv.median():.0f}; middle half {csv.quantile(.25):.0f}–{csv.quantile(.75):.0f}). '
            f'The across-company median increases from {years.iloc[0]:.1f} in {years.index[0]} to '
            f'{years.iloc[-1]:.1f} in {years.index[-1]}. Row averages also differ: '
            f'{companies.index[0]} has {companies.iloc[0]:.1f} metrics versus '
            f'{companies.index[-1]} with {companies.iloc[-1]:.1f}. '
            f'Panel b is much more discrete: {int((pdf==1).sum())} of {len(pdf)} required cells have one PDF '
            f'and {int((pdf==2).sum())} have two; {int(d.pdf_valid_headers.isna().sum())} grey cells are outside the PDF window.',
            'Together, the panels separate a binary entry requirement from uneven evidence volume. '
            'The CSV columns become richer in later years at the sample-median level, while the PDF view mostly distinguishes one versus two reports. '
            'These features can change what is available for retrieval even though every selected company passes screening.',
            'The two colour scales have different units and ranges: equally dark cells do not contain equal evidence. '
            'More extracted metrics could reflect reporting, extraction coverage or both; it does not establish improving ESG performance. '
            'The annual pattern is descriptive for selected companies, not an independent time-series experiment.', 2)
    if name == '00_screening_gaps':
        complete = int(d.loc[(d.missing_csv_year_count==0)&(d.missing_pdf_year_count==0),'companies'].sum())
        pdf_only = int(d.loc[(d.missing_csv_year_count==0)&(d.missing_pdf_year_count==8),'companies'].sum())
        any_csv = int(d.loc[d.missing_csv_year_count>0,'companies'].sum())
        any_pdf = int(d.loc[d.missing_pdf_year_count>0,'companies'].sum())
        return unit(
            'The selected heatmaps hide excluded companies; which availability gaps dominate the full register?',
            f'Two bubbles dominate: {complete} companies at (0, 0), and {pdf_only} at (0, 8). '
            f'The latter have all nine required CSV years but no qualifying PDF year. '
            f'Together these two locations contain {pct((complete+pdf_only)/d.companies.sum())} of the register. '
            f'At least one CSV year is missing for {any_csv} companies and at least one PDF year for {any_pdf}; these groups overlap.',
            'The large vertical separation at zero missing CSV years shows that PDF availability is a major screening constraint. '
            'The smaller points elsewhere describe joint gaps rather than a smooth continuum of equally populated coverage levels.',
            'A missing qualifying PDF is a gap in this collected and screened corpus, not proof that the company published no report. '
            'Bubble area has a small visibility offset, so count ratios should be read from the source table, not inferred precisely from diameter. '
            'Known sector classification is an additional eligibility condition.')
    if name == '00_evidence_scale':
        counts = frames['counts'].set_index('type').cards
        lengths = frames['length_frequencies']
        statements = []
        for kind in counts.index:
            v = lengths[lengths.type==kind].sort_values('characters')
            c = v['count'].cumsum()/v['count'].sum()
            q = lambda p: int(v.loc[c>=p,'characters'].iloc[0])
            statements.append(f'{kind}: median {q(.5):,}, middle half {q(.25):,}–{q(.75):,}, '
                              f'99th percentile {q(.99):,}, maximum {q(1):,} characters')
        return unit(
            'How unequal are the sizes and text lengths of the three stored evidence representations?',
            'Panel a contains ' + '; '.join(f'{kind}: {n:,} cards ({pct(n/counts.sum())})' for kind,n in counts.items())
            + '. PDF-derived cards dominate stored volume. In panel b, the steep part of each ECDF marks a densely populated length range: '
            + '; '.join(statements) + '. CSV cards occupy a narrow band; narrative cards are typically longer. '
            'Table rows have a short median but a long sparse upper tail, so their maximum does not describe a typical row.',
            'The panels jointly distinguish how many units exist from how much text each unit contains. '
            'A type can be numerous without having the longest individual records, and text length affects the size of the material retrieval must handle.',
            'Both horizontal axes are logarithmic: equal spacing means a multiplicative change, not an equal count or character increment. '
            'Long extracted rows may reflect complex tables or extraction artefacts; length alone cannot diagnose either. '
            'Cards are representations that may share a source report, not independent factual observations.', 2)
    if name == '00_visible_evidence':
        kinds = ['PDF narrative','PDF table row','CSV metric']
        total = d[kinds].sum(axis=1)
        return unit(
            'How does the large canonical library translate into the much smaller evidence context seen by each generator call?',
            'All three series peak at the cap of ten cards: '
            + '; '.join(f'{kind}: {int((d[kind]==10).sum()):,}/{len(d):,} disclosures '
                         f'({pct((d[kind]==10).mean())})' for kind in kinds)
            + f'. Zero-card strata occur for {int((d[kinds[0]]==0).sum())} narrative and '
            f'{int((d[kinds[1]]==0).sum())} table-row contexts. Total visible cards range from '
            f'{int(total.min())} to {int(total.max())}, with median {total.median():.0f}.',
            'The peak is a retrieval-design ceiling. CSV reaches it for every disclosure, while PDF strata sometimes fall short. '
            'Consequently, representation balance at the prompt is very different from the proportions in canonical storage.',
            'Connecting lines join frequencies at discrete counts; they are not a time trend or a continuous density. '
            'Unused slots are not reassigned to other types. Hitting the cap says nothing about topical relevance, '
            'and failing to fill it does not establish that relevant material is absent from all original reports.')
    if name == '00_time_windows':
        return unit(
            'Which temporal boundary governs the evidence just counted, and how much do neighbouring target years share?',
            'Both panels form diagonal bands that move one column right with each target year. '
            'Panel a permits four PDF report years per target and ends one year before it; '
            'panel b permits five CSV years and includes the target year. For 2019 these are 2015–2018 '
            'and 2015–2019; for 2023 they are 2019–2022 and 2019–2023.',
            'The one-column difference explains why target-year numerical metrics may be available alongside older narrative descriptions. '
            'Adjacent target years share three permitted PDF years and four CSV years, so their source pools overlap substantially. '
            'Later changes in scores therefore occur within moving, overlapping windows.',
            'These cells encode a rule, not observed availability, score magnitude or publication dates. '
            'The band shape is imposed by design and is not an empirical trend. It cannot establish what a user could have known at a historical date.', 2)
    if name == '00_provenance_example':
        text = '\n'.join(d.text)
        assert '2015_SR.pdf' in text and 'compensation' in text and 'E1-1_transition_plan' in text
        return unit(
            'What survives the transformation from an original report into one specific prompt input?',
            'Read downward through four stages: the 2015 sustainability report and page 4, the narrative-card identifier, '
            'the first 620 characters of the frozen card, and its use as Evidence 1 for Genmab’s 2019 E1-1 task. '
            'The displayed text concerns compensation, employee development and an internal roadmap; it does not itself provide '
            'an explicit climate-transition-plan statement. The excerpt boundary also cuts off the final sentence.',
            'The identifiers make the representation traceable, while the content shows why provenance and relevance are separate questions. '
            'An exact card-to-prompt match confirms which extracted text was shown; it does not establish that the card answers the target task.',
            'This is the first case and first visible narrative card, not a representative random relevance audit. '
            'The displayed excerpt is truncated; no claim about the entire card or report follows from that truncation. '
            'Matching extracted text cannot verify the preservation of the original PDF layout.')
    raise KeyError(name)


def support(name, d, frames):
    if name == '01_completion':
        row = d.set_index('stage').loc['BACE']
        return unit(
            'Before interpreting support scores, which planned cases actually have completed results?',
            f'Generation, RAGChecker and RAGAS each reach 1,800/1,800. BACE reaches '
            f'{row.complete:,}/1,800 ({pct(row.complete/1800)}), leaving {row.missing} cases. '
            'At this scale the missing segment is almost invisible, so the printed counts carry essential information.',
            'The generation stage has finished, but the full evaluation run is incomplete. All BACE summaries '
            'use observed completed branches, and paired comparisons require completion of all three evaluators.',
            'A 99.9% completion rate does not establish ignorable missingness. The two failures are not zero support '
            'and are not evidence of false content. Their exclusion remains visible in the affected company, year and task denominators.')
    if name == '01_support_distribution':
        x = frames['disclosures'].bace_support_rate_all_dc
        counts = frames['claim_counts'].set_index('status')['count']
        hist, edges = np.histogram(x,bins=np.linspace(0,1,21))
        peak = int(hist.argmax())
        ci = company_bootstrap(frames['disclosures'],'bace_support_rate_all_dc')
        pooled = (counts.Direct+counts.Inferred)/counts.sum()
        return unit(
            'Among completed cases, is the average score typical, or does it conceal a broad distribution?',
            f'Panel a contains {len(x):,} completed disclosures and has its tallest displayed bin at {pct(edges[peak])}–{pct(edges[peak+1])} '
            f'({hist[peak]} disclosures). The median is {pct(x.median())}, the middle half spans {span(x)}, '
            f'and the 10th–90th percentiles span {pct(x.quantile(.1))}–{pct(x.quantile(.9))}. '
            f'The mean ({pct(x.mean())}; company-cluster 95% interval {pct(ci["low"])}–{pct(ci["high"])}) '
            f'is close to the median, giving no reason to describe pronounced skew. '
            f'Only {int((x<=.25).sum())} disclosures score at most 25%, while {int((x>=.75).sum())} reach at least 75%. '
            'Panel b partitions all DCs: '
            + '; '.join(f'{status.lower()}: {int(n):,} ({pct(n/counts.sum())})' for status,n in counts.items()) + '.',
            f'The broad centre means that a mean near one-half is not a universal score for every disclosure. '
            f'Direct support supplies the larger supported component, but inferred support contributes materially. '
            f'The pooled support rate is {pct(pooled)}, {abs(100*(pooled-x.mean())):.1f} '
            'percentage points from the macro mean: similar overall summaries here despite their different weighting.',
            'The modal bin depends on the displayed 0.05 bin width and is not a fitted population mode. '
            'Panel a weights disclosures equally; panel b weights DCs equally and gives longer claim inventories more influence. '
            'Neither panel measures factual accuracy or includes the two missing BACE branches.', 2)
    if name == '01_task_support':
        order = d.sort_values('mean')
        low, high = order.iloc[0], order.iloc[-1]
        middle = d[(d['mean']>=.5)&(d['mean']<=.6)]
        widths = d.high-d.low
        return unit(
            'Does the broad disclosure distribution reflect differences between the twelve fixed tasks?',
            f'{low.task} has the lowest mean ({pct(low["mean"])}); {high.task} has the highest '
            f'({pct(high["mean"])}), a span of {pp(high["mean"]-low["mean"])} percentage points. '
            f'{len(middle)} of {len(d)} task means lie between 50% and 60%. '
            f'Interval widths range from {pp(widths.min())} to {pp(widths.max())} percentage points, '
            'and many neighbouring task intervals overlap. Colours group E1, S1 and G1 tasks; they do not mark statistical significance.',
            'There is a visible low task and a group of higher tasks, but most means occupy a fairly compact middle band. '
            'This suggests examining task-specific evidence and claim types, rather than treating the overall mean as equally applicable to every task.',
            'These are descriptive task summaries from the same 30 companies. Overlap or non-overlap of marginal intervals '
            'is not a paired, multiplicity-adjusted test of task differences. S1-1 and S1-5 have 149 disclosures; the others have 150. '
            'Source availability, generated wording and evaluator behaviour can all contribute to the ordering.')
    if name == '01_company_year':
        low, high = d.loc[d['mean'].idxmin()],d.loc[d['mean'].idxmax()]
        rowmeans=d.groupby('company_name')['mean'].mean().sort_values()
        widths=d.groupby('company_name')['mean'].agg(lambda x:x.max()-x.min())
        return unit(
            'Do the task-level averages conceal persistent company differences or local company-year variation?',
            f'The middle half of cell values spans {span(d["mean"])}. The lightest cell is '
            f'{low.company_name}, {low.year} ({pct(low["mean"])}), and the darkest is '
            f'{high.company_name}, {high.year} ({pct(high["mean"])}), a {pp(high["mean"]-low["mean"])}-point span. '
            f'Equal-year row means range from {rowmeans.index[0]} ({pct(rowmeans.iloc[0])}) to '
            f'{rowmeans.index[-1]} ({pct(rowmeans.iloc[-1])}); the median within-row five-year range is '
            f'{pp(widths.median())} points. Thus both row differences and within-row changes contribute to the pattern.',
            'Some companies have generally darker rows, but changing cells within rows prevent a single stable company ranking from describing everything. '
            'The next figure pools completed disclosures within each year to show how much of that local variation survives aggregation.',
            f'All {len(d)} company-years are present; {int((d.disclosures==11).sum())} cells average 11 tasks '
            'and the rest average 12. The fixed 0–1 scale and alphabetical row order avoid artificial contrast from row scaling or clustering. '
            'These are support-of-generated-text summaries, not rankings of company ESG quality.')
    if name == '01_year_support':
        values = '; '.join(f'{r.year}: {pct(r.mean)} (n={r.disclosures})' for r in d.itertuples())
        delta = d['mean'].diff()
        return unit(
            'When companies and tasks are aggregated, is there a consistent temporal movement in support?',
            f'The connected means are {values}, with n denoting completed disclosures from 30 recurring companies. The end-to-start difference is '
            f'{pp(d["mean"].iloc[-1]-d["mean"].iloc[0])} percentage points, but '
            f'{int((delta<0).sum())} of the four adjacent changes is downward. '
            f'The full range of annual means is only {pp(d["mean"].max()-d["mean"].min())} points; '
            'the intervals overlap for several years. The trajectory therefore has fluctuations rather than a monotonic rise.',
            'The modest annual spread, compared with the preceding company-year range, shows how aggregation smooths local differences. '
            'A later endpoint can coexist with a mid-period decrease and substantial variation within every year.',
            'Lines guide the eye between five repeated annual observations of the same companies. '
            'The intervals are marginal company-cluster intervals, not a trend test or an interval for the endpoint difference. '
            'Changing evidence windows and two missing task results also constrain temporal interpretation.')
    if name == '01_secondary_metrics':
        e,i=d.bace_eccr,d.bace_inference_rate
        delta=d.bace_support_rate_excluding_non_disclosure_sensitivity-d.bace_support_rate_all_dc
        return unit(
            'Do evidence coverage, inferred support and non-disclosure treatment reveal features hidden by the main score?',
            f'In panel a, ECCR has median {pct(e.median())} and middle half {span(e)}; '
            f'inference rate has median {pct(i.median())} and middle half {span(i)}. '
            'The steep central parts overlap substantially, although their denominators differ. '
            f'Only {int((i==0).sum())} disclosures have zero inference rate; undefined values are '
            f'{e.isna().sum()} for ECCR and {i.isna().sum()} for inference. '
            f'Panel b is strongly right-tailed: {int((delta==0).sum())}/{len(delta)} disclosures have no change, '
            f'the median increase is {pp(delta.median())} points, the 90th percentile is {pp(delta.quantile(.9))}, '
            f'and the maximum is {pp(delta.max())}. '
            f'{int((delta>.1).sum())} increase by more than ten points; {delta.isna().sum()} changes are undefined.',
            'ECCR and inference are numerically similar near their centres but answer different questions: '
            'which ECs appear in accepted sets, and which supported DCs require inference. '
            'The sensitivity tail shows that non-disclosure treatment matters much more for a subset of disclosures than for the typical one. '
            'Removing an unsupported non-disclosure statement shrinks the denominator without adding supported claims, so the nonnegative shift is partly arithmetic.',
            'Curve overlap does not equate the two secondary constructs. ECCR includes alternative accepted sets and is not observed evidence use. '
            'The sensitivity calculation changes the estimand; it does not demonstrate improved generation or identify the preferable denominator.', 2)
    raise KeyError(name)


def diagnosis(name, d):
    if name == '02_label_composition':
        v=d.set_index('label')
        major=v.loc[['factual_boundary_distortion','evidence_conflation']]
        rare=v.loc['contradiction']
        return unit(
            'Which automatic labels account for most unsupported DCs, and are they confined to a few disclosures?',
            f'Panel a partitions {int(d["count"].sum()):,} unsupported DCs and is dominated by boundary distortion ({major.percent_unsupported.iloc[0]:.1f}%) '
            f'and conflation ({major.percent_unsupported.iloc[1]:.1f}%); together they comprise '
            f'{major.percent_unsupported.sum():.1f}% of unsupported DCs. '
            f'Contradiction is a very small bar: {int(rare["count"])} claims '
            f'({rare.percent_unsupported:.2f}% of unsupported DCs). '
            f'Panel b uses {round(100*major.disclosures.iloc[0]/major.percent_disclosures.iloc[0]):,} completed disclosures and shows that the two dominant labels also occur broadly, in '
            f'{major.percent_disclosures.iloc[0]:.1f}% and {major.percent_disclosures.iloc[1]:.1f}% '
            'of completed disclosures. Non-disclosure statements are '
            f'{v.loc["non_disclosure_statement","percent_unsupported"]:.1f}% of unsupported DCs '
            f'but appear in {v.loc["non_disclosure_statement","percent_disclosures"]:.1f}% of disclosures.',
            'The main diagnostic burden is distributed across many disclosures, rather than being generated by only a few large claim inventories. '
            'The differing bar lengths across panels show why frequency per claim and prevalence per disclosure answer different questions. '
            'A category can be a modest share of DCs while appearing in most disclosures.',
            'Panel a categories are mutually exclusive for each DC; panel b categories can co-occur within one disclosure. '
            'These are frequencies of automated labels, not validated frequencies of error. '
            'The rare contradiction category is especially unsuitable for broad conclusions from one illustrative case.', 2)
    if name == '02_task_patterns':
        grid=d.pivot(index='task',columns='label',values='percent_all_dc')
        boundary=grid.factual_boundary_distortion
        nd=grid.non_disclosure_statement
        total=grid.sum(axis=1)
        return unit(
            'Does the overall diagnostic composition recur in every task, or do some tasks show distinctive concentrations?',
            f'Boundary distortion is the largest of the six label shares in '
            f'{int((grid.idxmax(axis=1)=="factual_boundary_distortion").sum())}/{len(grid)} task rows, '
            f'ranging from {boundary.min():.1f}% to {boundary.max():.1f}% of all task DCs. '
            f'Non-disclosure forms local dark cells: {nd.idxmax()} reaches {nd.max():.1f}%, '
            f'whereas {nd.idxmin()} is {nd.min():.2f}%. The contradiction column remains almost white '
            f'(maximum {grid.contradiction.max():.2f}%). Summing the six shares gives an unsupported '
            f'claim fraction from {total.min():.1f}% ({total.idxmin()}) to {total.max():.1f}% ({total.idxmax()}).',
            'The broad boundary column supports a cross-task inspection priority, while the non-disclosure hotspots suggest '
            'that the treatment of missing target-year metrics matters unevenly across tasks. '
            'The nearly empty contradiction column reflects its rarity in this output taxonomy, not absence of every possible factual problem.',
            'Colours share a common percentage scale and use all DCs within each task, without row normalisation. '
            'These pooled fractions give larger claim inventories more weight, so they need not equal one minus notebook 01’s macro support. '
            'The grid cannot separate source insufficiency, generated assertions, segmentation or diagnostic behaviour as causes.')
    if name == '02_pipeline_checks':
        v=d.set_index('label')
        novelty=v.loc['unsupported_novelty']; nd=v.loc['non_disclosure_statement']
        return unit(
            'Before reading cases, do candidate availability and quote localisation reveal different diagnostic paths?',
            f'The blue markers separate into two nonzero rows and four at zero. '
            f'Unsupported novelty has {int(novelty.zero_candidates)}/{int(novelty.claims)} DCs without candidates '
            f'({novelty.zero_candidate_percent:.1f}%), compared with '
            f'{int(nd.zero_candidates)}/{int(nd.claims)} non-disclosure DCs ({nd.zero_candidate_percent:.1f}%). '
            f'All orange markers sit near zero: only {int(d.no_exact_quote.sum())}/{int(d.claims.sum()):,} '
            f'unsupported DCs lack a contiguous generated-text quote; the largest within-label fraction is '
            f'{d.no_exact_quote_percent.max():.2f}%.',
            'Candidate absence is concentrated in particular categories, whereas literal quote localisation succeeds almost everywhere. '
            'This makes candidate/extraction inspection relevant to novelty cases, but the near-zero orange markers only say '
            'that a quoted span can be found in the generated response. They do not validate its meaning or its evidence support.',
            'The 0–100% axis visually compresses tiny quote-localisation differences. A candidate can exist and still be irrelevant, '
            'and an empty candidate list can result from information loss earlier in the pipeline. '
            'The label and candidate route belong to the same automated process, so their association is not independent validation.')
    if name == '02_asml_source_layout':
        r=d.iloc[0]
        return unit(
            'Can the source page resolve the apparent Scope 1 contradiction raised in the ASML example?',
            f'On PDF page {r.pdf_page} (printed page {r.printed_page}), the two glossary rows align '
            'direct Scope 1 with combustion of natural gas and purchased CO₂, and indirect Scope 2 with '
            'electricity consumption multiplied by local conversion factors. The key pattern is horizontal row association: '
            'the electricity text belongs to the second definition, although the flattened card places it after the Scope 1 label.',
            'Preserving two-dimensional layout changes the reading. The original row association supports the historical '
            'Scope 1 wording shown earlier and contradicts the specific electricity-based premise of the automatic rationale. '
            'This is concrete evidence that source representation or EC extraction can produce a misleading diagnostic example.',
            'This is one inspected page, and the generator received the flattened card rather than this crop. '
            'The check establishes a local association error; it does not establish the overall reliability of BACE, '
            'the frequency of PDF-layout failures, or the correctness of every statement in that disclosure.')
    raise KeyError(name)


def example(name, d):
    label=name.removeprefix('02_example_')
    readings={
        'non_disclosure_statement': (
            'Why can an explicitly cautious statement about missing data receive an unsupported label?',
            'The generated sentence withholds a quantified 2021 total and explicitly rejects treating absence as zero. '
            'The extracted DC isolates fines in 2021, whereas the displayed CSV card records zero confirmed corruption '
            'or bribery incidents in 2017. Both the year and the measure differ: incidents are not fines.',
            'Reading the four blocks together reveals a statement about a reporting gap, not a fabricated numerical total. '
            'The older zero-incident metric cannot settle whether a 2021 fines total was supplied. This is why the category '
            'must remain distinguishable from an affirmative unsupported factual assertion.',
            'A single card cannot prove that a metric is absent from all company publications, and this case does not establish '
            'company withholding. The label describes the frozen evidence-bound evaluation; its inclusion in the main denominator '
            'is a measurement choice examined in notebook 01.'),
        'contradiction': (
            'Is the ASML contradiction between the generated claim and the source, or between two readings of extracted text?',
            'The top block says historical Scope 1 includes natural gas and purchased CO₂; the DC retains the purchased-CO₂ component. '
            'The source block runs glossary terms and definitions together. The automatic rationale then attributes '
            'electricity-conversion factors to Scope 1. The apparent conflict turns on which glossary label belongs to which definition.',
            'The plate exposes a source-association question that a flat text reading cannot reliably resolve. '
            'The original-page crop later in this notebook resolves it in favour of the gas/purchased-CO₂ Scope 1 row. '
            'Accordingly, this example challenges the automatic contradiction rationale rather than supplying a clean generation error.',
            'The original layout must be checked to establish the row relationship; proximity in the flattened text is insufficient. '
            'This one inspected case cannot estimate the error rate of the 42 automatically labelled contradiction DCs.'),
        'evidence_conflation': (
            'What relationship does the Nestlé sentence add when it connects historical assessments to an ongoing priority?',
            'The generated wording is “Our development priority remains moving beyond individual site assessments”. '
            'The 2021 visible source supports a “more comprehensive and systematic approach” to risks, including animal welfare. '
            'The diagnostic rationale disputes the link to earlier site assessments and its status as a continuing priority in target year 2022.',
            'The distinctive change is relational and temporal: individually sourced ideas are joined into one continuing-development narrative. '
            'The source does contain a forward-looking expansion in approach, so this is subtler than inventing an unrelated topic. '
            'The blocks identify exactly which continuity claim needs review.',
            'The displayed card does not include all earlier assessment material; the complete bundle contains that context. '
            'The automatic conflation label is not independently established by this plate, and one case does not quantify how often such linking is unjustified.'),
        'factual_boundary_distortion': (
            'What changes when an accurately quoted historical activity is expressed as current practice?',
            'The visible 2019 text explicitly describes Wärtsilä’s online supply-chain risk solution and more than 2,000 suppliers. '
            'The generated sentence uses present-tense “uses” in a 2022 disclosure; the extracted DC focuses on the online solution. '
            'The rationale accepts the 2019 activity but questions whether it is established for 2022.',
            'Most substantive wording matches; the three-year temporal carry-forward is the disputed boundary. '
            'The source’s “have been, and continue to be” wording expresses continuity at the time of the 2019 report, '
            'which explains why reuse may sound plausible while still leaving a target-year evidence gap.',
            'Lack of a 2022 confirmation does not show that the activity stopped. Neither a historical exact match nor '
            'an automatic boundary label settles the real-world 2022 practice. This is a temporal-support illustration, not a company performance finding.'),
        'inferential_inflation': (
            'How much of the Pennon disagreement rests on strengthening an obligation word?',
            'The generated disclosure and DC use “require”, while the 2018 visible passage says “We expect them to” '
            'uphold standards and protect human rights. The excerpt also interleaves water-service and management text '
            'from neighbouring table columns. The rationale identifies the change from expectation to requirement.',
            'The pattern is a shift in modal strength, rather than a new supplier or a different human-rights topic. '
            'That distinction matters because an expectation can be weaker than a binding obligation. The interleaved text '
            'also shows why the excerpt must be read as an extracted representation with layout limitations.',
            'Other visible cards discuss supplier codes and strict procurement policies; they may affect the reading of the complete obligation. '
            'This excerpt alone does not establish the legal force of Pennon’s policy or independently verify the inflation label.'),
        'unsupported_novelty': (
            'Is the accident-severity indicator absent from the visible evidence, or lost before the support judgement?',
            'The generated sentence lists workplace-accident severity among monitoring indicators. The 2018 visible card '
            'explicitly includes “Severity rate of workplace accident”, yet the rationale discusses health-and-safety coverage '
            'and fatalities without recognising that indicator. In the full bundle, the card’s three retained ECs concern '
            'risk identification, prioritisation and validation; the indicator list is omitted.',
            'The top and source blocks share the disputed indicator, while the extracted representation does not preserve it. '
            'That supplies a concrete reason to question a simple absence-of-evidence reading of the novelty label. '
            'Inspecting only candidate ECs would miss information actually available in the prompt.',
            'The source lists social indicators in an assurance context. Presence of the phrase does not, by itself, '
            'establish the stronger interpretation that it monitored workforce-policy performance in target year 2019. '
            'The extraction omission is observable; the full target-year support judgement still requires review.')
    }
    if label not in readings:
        raise KeyError(name)
    assert len(d)==4 and list(d.columns)==['role','text']
    return unit(*readings[label])


def comparison(name, d, frames):
    if name == '03_native_comparison':
        x=frames['scores']; diff=frames['paired_differences']
        details=[]
        for method,col in METHODS.items():
            details.append(f'{method}: median {pct(x[col].median())}, middle half {span(x[col])}, '
                           f'{int((x[col]>=.9).sum()):,}/{len(x):,} at or above 0.90 and '
                           f'{int((x[col]==1).sum())} exactly 1.00')
        return unit(
            'On the identical completed disclosures, how far apart are native score distributions and paired means?',
            'Panel a rises mainly in the middle of the score axis for BACE and near its upper end for both comparators: '
            + '; '.join(details) + '. The two comparator curves overlap extensively, including their central ranges. '
            'Panel b puts both paired mean differences well left of zero: '
            + '; '.join(f'{r.contrast}: {pp(r.mean)} percentage points '
                         f'(95% company-cluster interval {pp(r.low)} to {pp(r.high)})' for r in diff.itertuples()) + '.',
            'The broad curve separation and the negative paired differences jointly show that the score gap is not just an artefact '
            'of comparing different case cohorts. High-end concentration also gives the comparators less room to distinguish '
            'already high-scoring disclosures. Similar comparator distributions do not imply matching judgements on each case.',
            'An ECDF higher at a given threshold means more observations at or below that score, not better performance. '
            'The denominator is each pipeline’s own claim inventory. A lower native score cannot identify stricter judgement '
            'as the sole mechanism or prove greater accuracy. Intervals resample 30 company clusters and do not measure judge randomness.', 2)
    if name == '03_rank_agreement':
        x=frames['scores']; ranks=frames['rank_associations']; statements=[]
        for panel,r in zip('abc',ranks.itertuples()):
            a,b=x[METHODS[r.method_a]],x[METHODS[r.method_b]]
            statements.append(f'Panel {panel} ({r.method_a} versus {r.method_b}): '
                              f'ρ={r.spearman_rho:.3f}; {int((b>a).sum()):,} points above the equality line, '
                              f'{int((b<a).sum()):,} below and {int((b==a).sum())} tied; '
                              f'{pct((abs(b-a)<=.05).mean())} differ by at most 0.05')
        rc,ra=x[METHODS['RAGChecker']],x[METHODS['RAGAS']]
        return unit(
            'Does the distributional gap also mean that evaluators order the same disclosures differently?',
            '. '.join(statements) + '. In panels a and b the cloud lies overwhelmingly above the diagonal, '
            'with wide horizontal spread under high comparator scores. Panel c has points on both sides, '
            f'with {int(((rc>=.9)&(ra>=.9)).sum())}/{len(x)} in the upper-right square where both scores are at least 0.90.',
            'All three rank associations are positive, but the dispersion shows that agreement is partial. '
            'Panels a and b combine a large level offset with only modest shared ordering; panel c has closer score levels '
            'and stronger rank association, yet substantial case-level disagreement remains. The ceiling creates ties and crowded top-edge bands.',
            'The diagonal is equality, not a fitted trend, and darkness reflects overplotting as well as density. '
            'Each panel retains all common disclosures, which are dependent within companies. '
            'Descriptive correlations and shared judge deployment cannot establish an independent accuracy ranking.', 3)
    if name == '03_claim_inventories':
        columns={'BACE':'bace_dc_count','RAGChecker':'ragchecker_claim_count','RAGAS':'ragas_claim_count'}
        x=d.bace_dc_count-d.ragchecker_claim_count
        y=d.bace_support_rate_all_dc-d.ragchecker_faithfulness
        rho=x.corr(y,method='spearman')
        return unit(
            'Could different claim segmentation help explain why native rates disagree on the same text?',
            'Panel a places BACE’s central claim-count range to the right: '
            + '; '.join(f'{m} median {d[c].median():.0f}, middle half '
                         f'{d[c].quantile(.25):.0f}–{d[c].quantile(.75):.0f}' for m,c in columns.items())
            + f'. In panel b, the count difference has median {x.median():.0f} '
            f'(middle half {x.quantile(.25):.0f}–{x.quantile(.75):.0f}; range {x.min():.0f} to {x.max():.0f}). '
            f'{int(((x>0)&(y<0)).sum()):,}/{len(d):,} points combine more BACE claims with a lower BACE score. '
            f'The count-gap/score-gap rank association is weakly negative (ρ={rho:.3f}); the cloud is not a tight descending relation.',
            'BACE usually produces a larger native inventory, so the score denominators differ systematically. '
            'The loose scatter means that the number of additional claims alone is an inadequate explanation of each score gap. '
            'Content selection, splits and merges, and support decisions all remain relevant.',
            'The two axes are outcomes of the same pipelines, not independently manipulated variables. '
            'A negative association cannot assign a causal fraction of the score gap to segmentation. '
            'More claims do not necessarily mean more complete or more accurate extraction; one proposition can be split differently.', 2)
    if name == '03_task_disagreement':
        summaries=[]
        for comp,v in d.groupby('comparison',sort=False):
            a,b=v.loc[v['mean'].idxmin()],v.loc[v['mean'].idxmax()]
            summaries.append(f'against {comp}, from {pp(a["mean"])} points ({a.task}) '
                             f'to {pp(b["mean"])} ({b.task})')
        g=d.pivot(index='task',columns='comparison',values='mean')
        separation=(g.RAGChecker-g.RAGAS).abs()
        task=separation.idxmax()
        return unit(
            'Is the global score offset spread across all tasks, and do both comparators show the same task profile?',
            f'All {len(d)} task-by-comparator mean gaps are negative: ' + '; '.join(summaries)
            + f'. All displayed upper interval bounds also remain below zero. The largest separation between '
            f'the two comparator gaps occurs at {task}: {pp(g.loc[task,"RAGChecker"])} versus '
            f'{pp(g.loc[task,"RAGAS"])} points, a {pp(separation.loc[task])}-point difference.',
            'The overall offset is distributed across tasks rather than arising from one isolated row. '
            'The different gap sizes, especially for E1-6, show that similar global comparator means can conceal '
            'task-specific differences in segmentation or evidence judgement.',
            'The intervals describe within-task paired gaps under company resampling. Their position is not an evaluator-accuracy test, '
            'and no multiplicity-adjusted comparison of tasks is claimed. The same companies appear in all rows; '
            'task evidence, generated claims and native inventories all vary together.')
    if name == '03_alignment_coverage':
        rc=d.set_index('framework').loc['ragchecker'];ra=d.set_index('framework').loc['ragas']
        return unit(
            'After seeing different native inventories, how much can a strict literal-text match actually align?',
            f'One bar is zero: RAGChecker has {rc.matched_pairs:,} unique exact-text partners. '
            f'RAGAS has {ra.matched_pairs:,}/{ra.bace_claims:,}, covering '
            f'{pct(ra.matched_pairs/ra.bace_claims)} of BACE DCs. Within that restricted RAGAS overlap, '
            f'{ra.agreements:,} pairs ({pct(ra.agreements/ra.matched_pairs)}) share the binary verdict. '
            f'{ra.external_ambiguous_rows} ambiguous RAGAS rows are excluded; no BACE rows have ambiguous keys.',
            'The near-empty coverage exposes the limits of literal alignment. RAGChecker represents claims as joined triples, '
            'whereas BACE uses sentences, so semantically related propositions can fail the exact-string rule. '
            'The nonzero RAGAS overlap supplies a narrow inspectable subset, not a common denominator for the three full evaluations.',
            'Zero literal matches is not zero semantic overlap, and an unmatched claim is not a verdict disagreement. '
            'Matching text is a highly selected subset; its binary agreement cannot be extrapolated to unmatched claims or interpreted as accuracy. '
            'All unmatched claims remain in the native-score analyses.')
    if name in ('03_case_lower','03_case_higher'):
        return extreme(name, d)
    if name == '03_judgement_source_coverage':
        assert 'suppliers' in d.text.iloc[-1]
        return unit(
            'Within the low-BACE Investec case, what visible evidence bears directly on one disagreement?',
            'The BACE DC concerns suppliers as a source of financial-crime and integrity risk. Its rationale says no EC provides an anchor. '
            'RAGChecker’s supported triple includes suppliers among the relevant actors, and the displayed 2017 report text '
            'explicitly lists “staff, clients, suppliers and other stakeholders” in the risk definition.',
            'The four blocks locate the disagreement in the representation used for judgement: the supplier relation is present '
            'in the full visible card even though BACE’s EC-based path reports no anchor. This is a concrete challenge '
            'to the absence-of-anchor rationale and helps explain how a low BACE score can coexist with comparator support.',
            'The card predates target year 2021, so this local textual match does not establish every temporal element of the generated claim. '
            'The native propositions are related but not a formally adjudicated one-to-one mapping. '
            'One inspected disagreement cannot show that RAGChecker is globally more accurate.')
    if name == '03_judgement_combined_evidence':
        assert '35103.0' in d.text.iloc[-1] and '4638.0' in d.text.iloc[-1]
        return unit(
            'Within the higher-BACE Banco BPM case, why does comparing several cards change the support path?',
            'The visible data contain two matching pairs: own-operations and consolidated-group location-based '
            'Scope 2 values are each 35,103 tCO₂e, and their market-based values are each 4,638 tCO₂e. '
            'BACE accepts the equality statement with one inferred four-EC set; RAGChecker marks its equality claim '
            'unsupported after neutral decisions on individual contexts; RAGAS explicitly accepts the cross-value comparison.',
            'The equality relation is obtained by comparing records rather than merely repeating one scalar value. '
            'The text blocks therefore connect two pairs of equal numbers to different '
            'evidence-combination paths. This gives a mechanism for this particular disagreement without assuming that a higher score is preferable.',
            'Matching extracted values establishes equality within these visible records, not independently verified emissions '
            'or equivalence of every organisational boundary. The example is deliberately explanatory and cannot measure '
            'how frequently each evaluator succeeds at combining evidence.')
    raise KeyError(name)


def extreme(name, d):
    assert len(d)==4
    lower=name.endswith('lower')
    direction='lower' if lower else 'higher'
    bundle=read(OUT/'examples'/f'03_bace_{direction}_than_ragchecker.json')
    gap=bundle['gap']
    if lower:
        return unit(
            'What does the most negative BACE-minus-RAGChecker case look like beneath its aggregate scores?',
            f'Investec 2021 G1-4 has a {pp(gap)}-point gap: BACE supports 9/46 DCs (19.6%), '
            'RAGChecker supports 29/29 native claims (100.0%), and RAGAS supports 29/34 (85.3%). '
            'The BACE inventory includes 14 conflation, 12 boundary and 9 non-disclosure DCs, plus one inflation '
            'and one novelty DC. Thus the gap combines a larger inventory with a very different allocation of unsupported labels.',
            'The opening passage sounds coherent and describes controls, but prose fluency alone does not settle its source support. '
            'The inventory points to temporal and relational reading as useful inspection targets. The supplier example below '
            'then checks one specific source-coverage disagreement within this same case.',
            'This is the minimum paired gap selected from the common cohort, so its magnitude is intentionally extreme. '
            'The displayed opening is only the first 700 characters and cannot explain every verdict. '
            'Neither the perfect comparator score nor the low BACE score is a human accuracy label.')
    return unit(
        'Can the score ordering reverse, and what evidence structure appears in the most positive case?',
        f'Banco BPM 2021 E1-6 has a {pp(gap)}-point BACE-minus-RAGChecker gap. '
        'BACE supports 20/28 DCs (71.4%): ten direct and ten inferred. RAGChecker supports 12/24 claims (50.0%), '
        'while RAGAS supports 27/29 (93.1%). The eight unsupported BACE DCs comprise six non-disclosure '
        'statements and two conflation labels. The generated opening contains several emissions quantities and an equality relation.',
        'The reversal rules out a universal case-by-case ordering in which BACE always scores lowest. '
        'The sizeable inferred component makes cross-card numerical relationships worth inspecting; '
        'the four-value equality example below provides one such traceable path. RAGAS still scores higher, '
        'so this case does not reverse every pairwise ordering.',
        'This is the maximum BACE-minus-RAGChecker gap, not a representative emissions task. '
        'Different inventories prevent attributing the entire gap to one equality claim or to inference alone. '
        'Numerical consistency among extracted cards is not external verification of the underlying emissions data.')
