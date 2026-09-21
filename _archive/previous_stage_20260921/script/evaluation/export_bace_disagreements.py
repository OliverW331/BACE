"""Export 133 source-audit disagreements with manually aligned native claims.

No model calls or new adjudications. The prior expert review is preserved.
External judgments apply to each framework's own extracted claims, not to a
controlled re-evaluation of the BACE DC. Indices below are native, zero-based.
All alignments were inspected against complete case-level claim lists.
"""
from collections import Counter
import csv
import hashlib
import json
import re

from bace_expert_review import CSV, PLAN, ROOT, RUN, CLASSES, bace_class, case, rows
from external_evaluation import adapt_case


OUTPUT = RUN / 'expert_disagreements_133.csv'
EXTERNAL = {
    name: ROOT / f'evidence_pilot/evaluation/{name}/pilot_v1/results.jsonl'
    for name in ('ragchecker', 'ragas')
}


def a(ids, relation='equivalent', note='Same proposition, allowing ordinary paraphrase and resolved company references.'):
    return (ids if isinstance(ids, list) else [ids], relation, note)


def b(ids, note):
    return a(ids, 'broader_native_claim', note)


def p(ids, note):
    return a(ids, 'partial_native_claim', note)


def s(ids, note):
    return a(ids, 'split_native_claims', note)


def d(ids, note):
    return a(ids, 'different_scope', note)


def r(ids, note):
    return a(ids, 'related_not_equivalent', note)


# Explicit per-DC alignment decisions. A split match is not a native verdict on
# the conjunction. A partial match cannot validate the omitted qualifications.
ALIGNMENTS = {
    1: {
        19: (d(11, 'Native subject says 2019 evidence; the DC refers to the supplied evidence packet.'), a(12)),
        21: (d(12, 'Native claim combines Scope 2 and Scope 3 and says 2019 evidence; the DC is packet-scoped Scope 2 absence.'), a(13)),
        22: (d(12, 'Native claim combines Scope 2 and Scope 3 and says 2019 evidence; the DC is packet-scoped Scope 3 absence.'), a(14)),
        24: (r(15, 'Primary reliance applies to mileage, invoices and agent data collectively. The DC assigns primary reliance to mileage alone.'), a(17)),
        25: (r(15, 'The native claim concerns the combined three-source list; it does not make agent data individually primary.'), a(19)),
        26: (r(15, 'The native claim concerns the combined three-source list; it does not make purchase invoices individually primary.'), a(18)),
        33: (d(21, 'Native claim combines mitigation actions and decarbonisation levers and restricts its subject to 2019 evidence.'), p(28, 'Native absence claim omits the explicit link to the reported transition exposure.')),
        34: (d(22, 'Native claim combines implementation expenditure and financing and refers to 2019 evidence.'), p(30, 'Native financing absence omits the explicit transition-exposure link.')),
        35: (d(22, 'Native claim combines implementation expenditure and financing and refers to 2019 evidence.'), p(29, 'Native expenditure absence omits the explicit transition-exposure link.')),
        36: (d(23, 'Native subject says 2019 evidence; DC absence is bounded to the available packet.'), p(31, 'Native locked-in-emissions absence omits the explicit transition-exposure link.')),
        37: (d(21, 'Native claim combines mitigation actions and decarbonisation levers and refers to 2019 evidence.'), a(27)),
        38: (d(24, 'Native subject says 2019 evidence; DC absence is bounded to the available packet.'), a(32)),
        39: (s([25, 26], 'Risk metrics and the CFO/senior-management population are judged in separate native claims; their combination is not separately judged.'), b(33, 'Native claim combines CFO and wider senior management.')),
        40: (s([25, 26], 'Risk metrics and the CFO/senior-management population are judged in separate native claims; their combination is not separately judged.'), b(33, 'Native claim combines CFO and wider senior management.')),
    },
    2: {
        2: (r(0, 'Native predicate is reports with reference to the standard; DC predicate is quantifies in accordance with it.'), a(0)),
        3: (a(1), a(1)),
        4: (a(0, note='The abbreviated GHG Protocol Corporate Standard refers to the full standard named by the DC.'), r(0, 'Native predicate is quantifies; the DC separately asserts the reporting basis.')),
        6: (b(3, 'Native boundary claim combines operations and sites.'), b(3, 'Native boundary claim combines operations and sites.')),
        7: (b(3, 'Native boundary claim combines operations and sites.'), b(3, 'Native boundary claim combines operations and sites.')),
        8: (a(4), a(4)),
        16: (a(13), a(13)),
        21: (a(18), a(19)),
        24: (a(19), a(20)),
        33: (a(30), a(27)),
    },
    3: {
        11: (b(5, 'Native claim combines physical and transition risks across three time horizons.'), b(5, 'Native transition-risk claim combines short-, medium- and long-term horizons.')),
        12: (b(6, 'Native financial-planning claim combines opportunities and risks and both short and medium terms.'), b(7, 'Native claim combines short- and medium-term opportunities.')),
        14: (b(6, 'Native financial-planning claim combines opportunities and risks and both short and medium terms.'), b(7, 'Native claim combines short- and medium-term opportunities.')),
        24: (s([16, 17, 18, 19], 'Target magnitude/deadline, baseline, carbon-backpack focus and the 3% annual correspondence are separately extracted; no single native claim tests the full attachment.'), s([18, 19, 20], 'Target parameters, carbon-backpack focus and annual correspondence are separately judged; their conjunction is not separately judged.')),
        26: (p(23, 'Native 15% Scope 3 target indicator does not attach that metric to the specific 2020-2025 upstream carbon-backpack target.'), p(24, 'Native percentage-of-target indicator lacks the DC attachment to the specific upstream carbon-backpack target.')),
        27: (s([20, 21], 'Category composition and most-significant ranking are separately judged.'), s([21, 22], 'Category composition and most-significant ranking are separately judged.')),
        32: (p(27, 'Native brochure claim says downstream examples, without the DC detail about improving customer CO2 performance.'), p(29, 'Native brochure claim says downstream examples, without explicitly restating the customer-CO2-performance relationship.')),
        34: (p(26, 'Native innovative-product lever claim omits the DC principal-lever characterization.'), d(28, 'Native claim says products are capable of improving carbon performance; the DC describes products that improve it.')),
        36: (a(28), a(30)),
        37: (a(29), a(31)),
        42: (d(33, 'Native claim combines CapEx and OpEx and omits the available-data restriction, extending the absence to company reporting.'), a(36)),
        43: (d(33, 'Native claim combines CapEx and OpEx and omits the available-data restriction, extending the absence to company reporting.'), a(37)),
        44: (a(34), a(38)),
    },
    4: {
        8: (p(17, 'Native claim gives the 2022 absolute reduction only; it does not judge the added 2008 baseline or attachment to the 50%-by-2025 target.'), p(17, 'Native claim omits the 2008 reference year and the specified target attachment.')),
        9: (p(19, 'Native reduction claim omits the 2008 reference year and the specified 50%-by-2025 target attachment.'), p(19, 'Native reduction claim omits the 2008 reference year and the specified target attachment.')),
        10: (p(18, 'Native 25% reduction claim omits the DC 2008 baseline and target attachment; the metric interpretation itself is still disputed.'), p(18, 'Native 25% reduction claim omits the DC 2008 baseline and target attachment.')),
        11: (p(20, 'Native 25% location-based Scope 2 reduction claim omits the 2008 baseline and target attachment.'), p(20, 'Native 25% location-based Scope 2 reduction claim omits the 2008 baseline and target attachment.')),
        20: (p(22, 'Native Scope 3 amount omits upstream-only scope, the 2020 baseline and attachment to the 15%-by-2025 target.'), p(22, 'Native Scope 3 amount omits upstream-only scope, the 2020 baseline and target attachment.')),
        21: (p(23, 'Native base-year-relative Scope 3 percentage does not name 2020, upstream-only scope or the specific target.'), p(23, 'Native base-year-relative Scope 3 percentage omits the specified upstream scope, 2020 baseline and target attachment.')),
        25: (b(14, 'Native Category 1 claim combines packaging, chemicals and indirect goods.'), b(14, 'Native Category 1 claim combines packaging, chemicals and indirect goods.')),
        26: (b(14, 'Native Category 1 claim combines packaging, chemicals and indirect goods.'), b(14, 'Native Category 1 claim combines packaging, chemicals and indirect goods.')),
        29: (a(25), b(25, 'Native method claim also specifies calculation in CO2 equivalents.')),
        32: (p([26, 27, 28], 'Only target magnitude, deadline and baseline are judged. No native claim judges the complementary climate-related characterization.'), p([26, 27], 'Absolute and specific energy targets are judged separately; neither judges the complementary climate-related characterization.')),
    },
    5: {
        13: (d(11, 'Native company-wide non-reporting claim omits the DC available-information restriction.'), a(11)),
        24: (d(23, 'Native non-reporting claim omits the available-information restriction; its baseline wording is GHG emissions rather than specifically GHG reduction.'), d(24, 'Native wording is GHG emissions base year; DC wording is GHG-reduction base year. Both retain the available-information restriction.')),
        25: (d(24, 'Native non-reporting claim omits the available-information restriction.'), a(25)),
        26: (d(25, 'Native non-reporting claim omits the available-information restriction.'), a(26)),
        27: (d(26, 'Native non-reporting claim omits the available-information restriction.'), a(27)),
        28: (d(27, 'Native claim combines removals and credits and omits the available-information restriction.'), b(28, 'Native absence claim combines removals and carbon credits.')),
        29: (d(27, 'Native claim combines removals and credits and omits the available-information restriction.'), b(28, 'Native absence claim combines removals and carbon credits.')),
        30: (d(22, 'Native non-reporting claim omits the available-information restriction.'), a(23)),
        31: (a(28), a(29)),
    },
    6: {
        2: (d(1, 'Native claim combines footprint assessment, risk analysis and governance and does not explicitly date the actual approach to 2023.'), p(1, 'Native carbon-footprint relationship omits the DC explicit 2023 qualifier.')),
        4: (a(0), a(0)),
        6: (b(4, 'Native intention combines risks and opportunities and strategy, financial planning and ERM.'), b(6, 'Native financial-planning intention combines risks and opportunities.')),
        12: (a(5), a(8)),
        14: (b(6, 'Native claim combines initial Scope 1 and Scope 2 calculations.'), b([9, 10, 11], 'Each native claim combines Scope 1 and Scope 2 and adds a separate purpose: ambitions, targets or reductions.')),
        22: (s([10, 11], 'The 2023 priority and the value-chain-profile purpose are separate claims; the purpose claim also adds mitigation planning.'), s([14, 15], 'The 2023 priority and the value-chain-profile purpose are judged separately.')),
        27: (d(16, 'Native blanket target-year absence omits the available-information limit and the specific 42% Scope 1 indicator.'), d(21, 'Native packet-scoped absence covers target years generally; it does not separately attach the absence to the 42% Scope 1 indicator.')),
        28: (d(16, 'Native blanket target-year absence omits the available-information limit and the specific 66.67% Scope 3 indicator.'), d(21, 'Native packet-scoped absence covers target years generally; the 66.67% Scope 3 attachment is not separately judged.')),
        29: (d(16, 'Native blanket target-year absence omits the available-information limit and the specific 94% location-based Scope 2 indicator.'), d(21, 'Native packet-scoped absence covers target years generally; the 94% location-based Scope 2 attachment is not separately judged.')),
        30: (d(16, 'Native blanket target-year absence omits the available-information limit and the specific 42% total-GHG indicator.'), d(21, 'Native packet-scoped absence covers target years generally; the 42% total-GHG attachment is not separately judged.')),
        31: (d(17, 'Native levers absence omits the available-information limit and does not separately name the 42% Scope 1 indicator.'), d(22, 'Native claim concerns the reported indicators collectively; the 42% Scope 1 attachment is not separately judged.')),
        32: (d(17, 'Native levers absence omits the available-information limit and does not separately name the 66.67% Scope 3 indicator.'), d(22, 'Native claim concerns the reported indicators collectively; the 66.67% Scope 3 attachment is not separately judged.')),
        33: (d(17, 'Native levers absence omits the available-information limit and does not separately name the 94% location-based Scope 2 indicator.'), d(22, 'Native claim concerns the reported indicators collectively; the 94% location-based Scope 2 attachment is not separately judged.')),
        34: (d(17, 'Native levers absence omits the available-information limit and does not separately name the 42% total-GHG indicator.'), d(22, 'Native claim concerns the reported indicators collectively; the 42% total-GHG attachment is not separately judged.')),
        39: (p(21, 'Native absence refers to the 2023 climate capital allocation but does not restate its USD 217,706.82 amount.'), p(27, 'Native absence refers to the 2023 capital allocation but does not restate its USD 217,706.82 amount.')),
        50: (s([24, 25], 'Actual influence on the transition approach and the analysis coverage are separate claims; coverage also includes physical and transition risks.'), s([33, 34, 35], 'Actual influence and physical/transition analysis coverage are separate claims.')),
        51: (s([24, 25], 'Actual influence and analysis coverage are separate claims; coverage also includes transition risks and opportunities.'), s([33, 34], 'Actual influence and physical-risk/opportunity coverage are separately judged.')),
        60: (s([31, 32], 'Board receipt of biannual oversight reporting and the combined topic list are separately judged.'), s([43, 44], 'Oversight through Board reporting and the climate-strategy reporting topic are separate claims.')),
        61: (s([31, 32], 'Board receipt of biannual oversight reporting and the combined topic list are separately judged.'), s([43, 46], 'Oversight through Board reporting and the financial-risk reporting topic are separate claims.')),
        62: (s([31, 32], 'Board receipt of biannual oversight reporting and the combined topic list are separately judged.'), s([43, 45], 'Oversight through Board reporting and the target-progress reporting topic are separate claims.')),
        63: (s([31, 32], 'Board receipt of biannual oversight reporting and the combined topic list are separately judged.'), s([43, 47], 'Oversight through Board reporting and the prevention/mitigation reporting topic are separate claims.')),
    },
    7: {
        11: (a(13), a(13)),
        26: (a(26), b(17, 'Native inventory claim lists all named Scope 3 activities as well as other activities.')),
        37: (b(35, 'Native actual-reinvestment claim combines further emissions reductions and renewable-energy transition.'), b(27, 'Native actual-reinvestment claim combines further emissions reductions and renewable-energy transition.')),
        39: (a(36), a(28)),
        40: (a(41), b(30, 'Native Scope 1 definition combines generator fuels, natural gas, refrigerants and vehicles.')),
        41: (a(38), b(30, 'Native Scope 1 definition combines generator fuels, natural gas, refrigerants and vehicles.')),
        45: (a(43), b(31, 'Native Scope 2 definition combines purchased electricity and steam.')),
        49: (s([47, 48], 'Reporting subjects and six-month frequency are separate claims; the subject includes the executive team as well as divisional CEOs.'), b(35, 'Native reporting claim combines divisional CEOs and the executive team.')),
    },
    8: {
        1: (a(0), a(0)),
        6: (a(5), s([5, 6], 'Board approval of Group strategy and inclusion of FasterForward in that strategy are separately judged.')),
        9: (p(8, 'Native action claim omits principal; it judges inclusion of energy efficiency only.'), a(9)),
        10: (p(10, 'Native action claim omits principal; it judges inclusion of real-estate optimisation only.'), a(11)),
        11: (p(9, 'Native action claim omits principal; it judges inclusion of renewable electricity procurement only.'), a(10)),
        13: (b(11, 'Native continued-programme claim combines energy and space efficiency.'), a(13)),
        16: (a(12), a(14)),
        21: (b(19, 'Native framework claim combines venues and suppliers and adds the energy-reduction purpose.'), b(21, 'Native supplier-engagement claim also asserts its energy-reduction purpose.')),
        34: (a(29), a(32)),
        35: (a(28), a(31)),
        36: (b(31, 'Native boundaries claim combines GHG Protocol and SBTi.'), a(34)),
        37: (b(31, 'Native boundaries claim combines GHG Protocol and SBTi.'), a(35)),
        40: (b(33, 'Native assurance claim combines Scopes 1, 2 and 3.'), b(38, 'Native assurance claim combines Scopes 1, 2 and 3.')),
        45: (s([34, 35, 36], 'Partnerships and the colleagues impact-identification claim are separate; the latter also adds quantification and mitigating activities.'), s([40, 41], 'Partnership and identification/quantification of eleven impacts are separate; the joint-work link is not separately judged.')),
        51: (d(39, 'Native claim explicitly limits absence to climate expenditure. The DC says expenditure; its disclosure context supplies the climate restriction.'), d(45, 'Native claim explicitly limits absence to climate-related expenditure; the DC relies on disclosure context for that restriction.')),
    },
    9: {
        7: (p([1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13], 'Native claims describe the three 2020 targets and the earlier objective, but never assert that all three built on that objective.'), p(7, 'Native claim asserts the shared built-on relationship but does not enumerate all three targets and their distinct baselines.')),
        13: (b(16, 'Native continued-action claim combines specific and absolute production emissions.'), a(11)),
        14: (b(16, 'Native continued-action claim combines specific and absolute production emissions.'), a(10)),
        15: (s([18, 19], 'The 50% target-coverage claim and the two Scope 2 accounting bases are judged separately; native outcomes are mixed.'), s([13, 15], 'The 50% Scope 2 coverage and its location-based reporting basis are separate claims.')),
        16: (s([18, 19], 'The 50% target-coverage claim and the two Scope 2 accounting bases are judged separately; native outcomes are mixed.'), s([13, 14], 'The 50% Scope 2 coverage and its market-based reporting basis are separate claims.')),
        19: (a(22), a(18)),
        20: (a(17), a(12)),
        21: (a(18), a(13)),
        22: (a(23), a(19)),
        23: (a(24), b(20, 'Native Scope 1 definition also specifies company operations.')),
        24: (b(25, 'Native Scope 1 claim combines fossil fuels generating electricity and heat.'), b(21, 'Native Scope 1 claim combines fossil fuels generating electricity and heat.')),
        27: (b(27, 'Native Scope 2 claim combines purchased electricity, steam, heating and cooling.'), b(23, 'Native Scope 2 claim combines purchased electricity, steam, heating and cooling.')),
        28: (b(27, 'Native Scope 2 claim combines purchased electricity, steam, heating and cooling.'), b(23, 'Native Scope 2 claim combines purchased electricity, steam, heating and cooling.')),
        29: (b(27, 'Native Scope 2 claim combines purchased electricity, steam, heating and cooling.'), b(23, 'Native Scope 2 claim combines purchased electricity, steam, heating and cooling.')),
        30: (b(27, 'Native Scope 2 claim combines purchased electricity, steam, heating and cooling.'), b(23, 'Native Scope 2 claim combines purchased electricity, steam, heating and cooling.')),
        31: (s([28, 32], 'Upstream/downstream reporting and inclusion of business travel are separately judged.'), s([24, 28], 'Upstream/downstream reporting and inclusion of business travel are separately judged.')),
        32: (s([28, 30], 'Upstream/downstream reporting and inclusion of capital goods are separately judged.'), s([24, 26], 'Upstream/downstream reporting and inclusion of capital goods are separately judged.')),
        33: (s([28, 33], 'Upstream/downstream reporting and inclusion of employee commuting are separately judged.'), s([24, 29], 'Upstream/downstream reporting and inclusion of employee commuting are separately judged.')),
        34: (s([28, 35], 'Upstream/downstream reporting and inclusion of end-of-life treatment are separately judged.'), s([24, 31], 'Upstream/downstream reporting and inclusion of end-of-life treatment are separately judged.')),
        35: (s([28, 29], 'Upstream/downstream reporting and inclusion of purchased goods/services are separately judged.'), s([24, 25], 'Upstream/downstream reporting and inclusion of purchased goods/services are separately judged.')),
        36: (b(28, 'Native Scope 3 reporting claim combines upstream and downstream activities.'), b(24, 'Native Scope 3 reporting claim combines upstream and downstream activities.')),
        37: (b(28, 'Native Scope 3 reporting claim combines upstream and downstream activities.'), b(24, 'Native Scope 3 reporting claim combines upstream and downstream activities.')),
        38: (s([28, 31], 'Upstream/downstream reporting and inclusion of transport/distribution are separately judged.'), s([24, 27], 'Upstream/downstream reporting and inclusion of transport/distribution are separately judged.')),
        39: (s([28, 34], 'Upstream/downstream reporting and inclusion of sold-product use are separately judged.'), s([24, 30], 'Upstream/downstream reporting and inclusion of sold-product use are separately judged.')),
        41: (r(42, 'Native reviews concern fields of action and objectives generally; no native claim attaches the reviews to this product-CO2 target-setting process.'), p(37, 'Native process claim combines fields of action and objectives but omits worldwide scope, all-business-unit coverage and 2015-2030 dates.')),
        42: (r(42, 'Native reviews concern fields of action and objectives generally; no native claim attaches the reviews to this product-CO2 target-setting process.'), p(37, 'Native process claim combines fields of action and objectives but omits worldwide scope, all-business-unit coverage and 2015-2030 dates.')),
        44: (p(40, 'Native validation claim names product CO2 target setting but omits worldwide scope, all-business-unit coverage and the 2015-2030 dates.'), p(35, 'Native validation claim omits the DC worldwide scope, all-business-unit coverage and the 2015-2030 dates.')),
    },
    10: {
        6: (b(2, 'Native control-approach claim combines Scope 1 and Scope 2.'), a(3)),
        7: (b(2, 'Native control-approach claim combines Scope 1 and Scope 2.'), a(4)),
        13: (s([3, 9], 'The financial-control boundary and the consolidated location-based total are judged separately; native outcomes are mixed.'), s([5, 11], 'The financial-control boundary and the consolidated location-based total are judged separately; native outcomes are mixed.')),
        14: (s([3, 8], 'The financial-control boundary and the consolidated market-based total are judged separately; native outcomes are mixed.'), s([5, 10], 'The financial-control boundary and the consolidated market-based total are judged separately; native outcomes are mixed.')),
        25: (a(19), a(24)),
        30: (s([24, 25], 'Purchased-goods/recycling life-cycle assessments and their ISO standard are separate claims.'), s([29, 31], 'Purchased-goods life-cycle assessments and their ISO standard are separate claims.')),
    },
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_numbers(text):
    numbers = set()
    for first, last in re.findall(r'Evidence\s+(\d+)(?:\s*[-–]\s*(\d+))?', text):
        numbers.update(range(int(first), int(last or first) + 1))
    assert numbers and numbers <= set(range(1, 31)), text
    return sorted(numbers)


def external_cells(framework, record, alignment, cards):
    indices, relation, note = alignment
    native = {c['claim_index']: c for c in record['claims']}
    assert len(native) == len(record['claims'])
    assert indices and len(set(indices)) == len(indices) and set(indices) <= set(native)
    prefix = 'RC' if framework == 'ragchecker' else 'RA'
    selected = [native[i] for i in indices]
    verdicts = ['supported' if c['supported'] else 'unsupported' for c in selected]
    counts = Counter(verdicts)
    if len(counts) == 1:
        judgment = f'{verdicts[0]} ({len(selected)} aligned native claim(s))'
    else:
        judgment = f'mixed ({counts["supported"]} supported; {counts["unsupported"]} unsupported native claims)'
    claim_text, reasons = [], []
    for c, verdict in zip(selected, verdicts):
        label = f'{prefix}{c["claim_index"]:03d}'
        text = ' | '.join(c['claim']) if isinstance(c['claim'], list) else c['claim']
        claim_text.append(f'{label} [{verdict}] {text}')
        if framework == 'ragas':
            reasons.append(f'{label}: {c["reason"]}')
        else:
            # These are native per-passage judgments, not an invented rationale.
            ev = c['evidence_verdicts']
            assert set(ev) == set(cards)
            assert c['supported'] == any(v == 'Entailment' for v in ev.values())
            reasons.append(label + ' (native per-evidence verdicts):\n' + '\n'.join(
                f'{card["prompt_label"]} [{card["source_label"]}]: {ev[eid]}'
                for eid, card in cards.items()))
    return judgment, '\n\n'.join(claim_text), relation, note, '\n\n'.join(reasons)


def comparison_explanation(review, rc, ra):
    statements = []
    for name, cells in (('RAGChecker', rc), ('RAGAS', ra)):
        judgment, _, relation, note, _ = cells
        if relation == 'equivalent':
            assert not judgment.startswith('mixed')
            agrees = judgment.startswith('supported') == (review['expert_support_class'] != 'unsupported')
            statements.append(f'{name} {"agrees" if agrees else "disagrees"} with the expert on binary support for the equivalent native proposition ({judgment}).')
        else:
            statements.append(f'{name}: {judgment}; alignment is {relation}. {note} This is not a separate native verdict on the exact BACE DC.')
    if review['likely_issue_stage_or_caveat'] == 'absence_evidence_representation':
        statements.append('The expert tests absence within the complete supplied packet. Missing positive EC support or neutral individual-passage verdicts do not by themselves refute that bounded absence; wider company-level absence is a different proposition.')
    statements.append('External native judgments are binary; they do not provide the BACE direct/inferred distinction or its unsupported-diagnosis taxonomy.')
    return ' '.join(statements)


def export():
    with CSV.open(encoding='utf-8-sig', newline='') as stream:
        original = list(csv.DictReader(stream))
    selected = [r for r in original if r['support_status_correct'] == 'no']
    assert len(original) == 443 and len(selected) == 133
    assert sum(r['bace_support_class'] == 'unsupported' for r in selected) == 99
    selected_keys = {(int(r['case_no']), int(r['claim_no'])) for r in selected}
    assert selected_keys == {(n, k) for n, mapping in ALIGNMENTS.items() for k in mapping}
    data = {n: case(n) for n in ALIGNMENTS}
    external = {name: {r['generation_case_id']: r for r in rows(path)} for name, path in EXTERNAL.items()}
    inputs = {CSV, RUN / 'plan.json', ROOT / PLAN['generation_cases'], ROOT / PLAN['generated_disclosures'], *EXTERNAL.values()}
    for value in data.values():
        short = value[0].split('stratified_by_evidence_type_n10__')[1]
        base = RUN / 'bace' / short
        inputs.update(base / name for name in (
            'dedup/dc_claims.jsonl', 'dedup/ec_claims.jsonl',
            'support/dc_support_sets.jsonl', 'diagnosis/dc_unsupported_diagnoses.jsonl',
            'candidates/dc_candidate_ecs.jsonl'))
    frozen = {str(path): sha(path) for path in inputs}
    for cid, source, disclosure, *_ in data.values():
        adapted = adapt_case(source, disclosure)
        for name, records in external.items():
            result = records[cid]
            assert result['framework'] == name and result['metric'] == 'faithfulness' and result['status'] == 'success'
            for key in ('generation_case_id', 'prompt_hash', 'response_hash', 'context_hash', 'evidence_ids', 'prompt_labels'):
                assert result[key] == adapted[key], (cid, name, key)
    exported = []
    for review in selected:
        n, k = int(review['case_no']), int(review['claim_no'])
        cid, source, disclosure, dcs, _, ecmap, aliases, support, diagnosis, candidates = data[n]
        dc = dcs[k - 1]
        dcid = dc['dc_id']
        assert dcid == review['dc_id'] and dc['dc_text'] == review['dc_text']
        sets = support[dcid]
        assert CLASSES[bace_class(sets)] == review['bace_support_class']
        diag = diagnosis.get(dcid, {})
        assert diag.get('unsupported_label', '') == review['bace_unsupported_label']
        assert diag.get('rationale', '') == review['bace_diagnosis_rationale']
        cards = {c['evidence_id']: c for c in source['prompt_evidence'] if c['shown_in_prompt']}
        by_label = {c['prompt_label']: c for c in cards.values()}
        assert len(cards) == 30
        chosen_ecs = list(dict.fromkeys(e for st in sets for e in st['ec_claim_ids'])) if sets else candidates[dcid]
        role = ('ECs in BACE returned support sets; set membership is listed separately.' if sets else
                'Candidate ECs only. BACE returned no sufficient support set; these are not accepted supporting ECs.' if chosen_ecs else
                'No candidate ECs and no returned support set. This does not establish absence of support in the raw packet.')
        ec_texts, ec_quotes = [], []
        for eid in chosen_ecs:
            ec = ecmap[eid]
            assert ec['generation_case_id'] == cid
            labels = sorted({p['prompt_label'] for p in ec['ec_provenance']}, key=lambda x: int(x.split()[-1]))
            ec_texts.append(f'{aliases[eid]} | {eid} | {", ".join(labels)}\n{ec["ec_text"]}')
            quotes = []
            for provenance in ec['ec_provenance']:
                card = cards[provenance['evidence_id']]
                for span in provenance['source_spans']:
                    quote = span['quote']
                    exact = quote in card['retrieval_text']
                    if not exact:
                        assert span['match_status'] == 'unmatched'
                    status = ('verbatim source excerpt' if exact else
                              'native EC anchor; unmatched to contiguous raw text; not a verbatim source quotation')
                    quotes.append(f'[{card["prompt_label"]} | {card["source_label"]} | {status}] {quote}')
            ec_quotes.append(aliases[eid] + '\n' + '\n'.join(dict.fromkeys(quotes)))
        labels = evidence_numbers(review['review_evidence_labels'])
        evidence = '\n\n'.join(
            f'[{by_label[f"Evidence {i}"]["prompt_label"]} | {by_label[f"Evidence {i}"]["source_label"]}]\n'
            f'{by_label[f"Evidence {i}"]["retrieval_text"]}' for i in labels)
        if len(labels) == 30:
            evidence_scope = ('All 30 prompt-visible evidence cards reproduced. The prior absence/insufficiency finding is bounded '
                              'to this complete supplied packet; it is not a claim about the complete annual report or all company publications.')
        else:
            evidence_scope = ('Full prompt-visible packet inspected in the prior review; cited cards reproduced here in full. '
                              'Disclosure excerpts clarify claim referents only and are not independent supporting evidence.')
        rc = external_cells('ragchecker', external['ragchecker'][cid], ALIGNMENTS[n][k][0], cards)
        ra = external_cells('ragas', external['ragas'][cid], ALIGNMENTS[n][k][1], cards)
        short = cid.split('stratified_by_evidence_type_n10__')[1]
        input_paths = [CSV, ROOT / PLAN['generation_cases'], ROOT / PLAN['generated_disclosures'],
                       *EXTERNAL.values(), *sorted(p for p in inputs if f'/bace/{short}/' in str(p))]
        record = {
            'case_no': str(n), 'claim_no': str(k), 'company': review['company'],
            'reporting_year': review['reporting_year'], 'task': review['task'],
            'dc_text': review['dc_text'],
            'ec_role': role, 'ec_text': '\n\n'.join(ec_texts) or 'None selected by BACE.',
            'bace_judgment': review['bace_support_class'],
            'bace_unsupported_diagnosis': review['bace_unsupported_label'] or 'not_generated',
            'bace_diagnosis_reason': review['bace_diagnosis_rationale'] or 'Not applicable: BACE classified this DC as supported.',
            'ragchecker_judgment': rc[0], 'ragchecker_native_claims': rc[1],
            'ragchecker_alignment': rc[2], 'ragchecker_alignment_note': rc[3],
            'ragchecker_evidence_verdicts': rc[4],
            'ragas_judgment': ra[0], 'ragas_native_claims': ra[1],
            'ragas_alignment': ra[2], 'ragas_alignment_note': ra[3], 'ragas_native_reasons': ra[4],
            'expert_judgment': review['expert_support_class'],
            'expert_unsupported_diagnosis': review['expert_unsupported_label'],
            'why_disagreement': (f'BACE classified the DC as {review["bace_support_class"]}; the prior source audit classified it as '
                                 f'{review["expert_support_class"]}. {review["expert_review_reason"]}'),
            'cross_framework_explanation': comparison_explanation(review, rc, ra),
            'likely_issue_stage_or_caveat': review['likely_issue_stage_or_caveat'],
            'raw_evidence_quotes': evidence, 'expert_evidence_scope': evidence_scope,
            'review_evidence_labels': review['review_evidence_labels'],
            'disclosure_source_quotes': '\n\n'.join(json.loads(review['disclosure_source_quotes'])),
            'bace_support_sets': '\n'.join(f'Set {j}: {st["support_type"]}; ' + ', '.join(aliases[e] for e in st['ec_claim_ids']) for j, st in enumerate(sets, 1)) or 'None returned.',
            'ec_source_quotes': '\n\n'.join(ec_quotes) or 'No selected EC provenance.',
            'dc_id': dcid, 'generation_case_id': cid,
            'native_index_convention': 'RC000 / RA000 denote native zero-based claim_index values; E001 aliases are case-local BACE EC indices. Repeated external IDs across DCs are not independent judgments.',
            'comparison_scope': ('RAGChecker and RAGAS: saved pilot_v1 faithfulness judgments on their own extracted claims, with identical raw inputs verified. '
                                 'BACE: pilot_v2. Equivalent = same proposition; broader = includes additional facts; partial = omits DC content; '
                                 'split = multiple separately judged claims; different_scope = different scope/modality; related = different proposition. '
                                 'No external framework was rerun on the BACE DC. Native support does not validate omitted qualifiers or unjudged conjunctions.'),
            'expert_review_scope': review['reviewer_type'] + '. ' + review['audit_scope'] + ' Prior expert verdict and explanation preserved; no new adjudication.',
            'source_files_and_sha256': '\n'.join(f'{path}\nSHA256 {frozen[str(path)]}' for path in input_paths),
        }
        exported.append(record)
    assert len({r['dc_id'] for r in exported}) == 133
    assert {r['dc_id'] for r in exported} == {r['dc_id'] for r in selected}
    assert all(r['why_disagreement'].endswith(old['expert_review_reason']) and
               r['expert_judgment'] == old['expert_support_class'] and
               r['expert_unsupported_diagnosis'] == old['expert_unsupported_label']
               for r, old in zip(exported, selected))
    assert all(sha(path) == frozen[str(path)] for path in inputs), 'Source file changed'
    # Keep spreadsheet cells below Excel's limit without truncating evidence.
    oversized = [(r['case_no'], r['claim_no'], key, len(value)) for r in exported for key, value in r.items() if len(value) > 32767]
    assert not oversized, oversized
    temporary = OUTPUT.with_suffix('.csv.tmp')
    with temporary.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(exported[0]))
        writer.writeheader()
        writer.writerows(exported)
    with temporary.open(encoding='utf-8-sig', newline='') as stream:
        assert list(csv.DictReader(stream)) == exported, 'CSV roundtrip mismatch'
    temporary.replace(OUTPUT)
    print(json.dumps({
        'output': str(OUTPUT), 'rows': len(exported), 'columns': len(exported[0]),
        'disagreement_directions': dict(Counter('BACE unsupported -> expert supported' if r['bace_judgment'] == 'unsupported' else 'BACE supported -> expert unsupported' for r in exported)),
        'ragchecker_alignments': dict(Counter(r['ragchecker_alignment'] for r in exported)),
        'ragas_alignments': dict(Counter(r['ragas_alignment'] for r in exported)),
        'frozen_input_files_verified': len(inputs), 'sha256': sha(OUTPUT),
    }, indent=2))


if __name__ == '__main__':
    export()
