# /// script
# requires-python = ">=3.11"
# dependencies = ["XlsxWriter==3.2.5", "openpyxl==3.1.5"]
# ///
"""Export a reproducible 500-DC sample as a nine-column review workbook.

One row per deduplicated unsupported DC. Candidate evidence cards and candidate
ECs are linked using the stored candidate selections, never semantic matching.
Use an isolated Python environment with the dependencies pinned above.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import sys

import openpyxl
from openpyxl.utils.escape import unescape
import xlsxwriter

HERE = Path(__file__).resolve().parents[1]
BACE = HERE.parent
ROOT = BACE.parent
RUN = BACE / 'results/main_v1'
DEST = HERE / 'validation/unsupported_diagnosis_validation_500.xlsx'
QA = HERE / 'outputs/qa/validation_workbook.json'
SAMPLE_SIZE = 500
SAMPLE_SEED = 20260923
HEADERS = [
    'Company name', 'Reporting year', 'Disclosure topic',
    'Generated disclosure literal source quote', 'Extracted DC',
    'Evidence candidates', 'Extracted EC', 'Diagnosis classification',
    'Unedited automatic rationale',
]
LABELS = (
    'non_disclosure_statement', 'contradiction', 'evidence_conflation',
    'factual_boundary_distortion', 'inferential_inflation', 'unsupported_novelty',
)
SOURCE_HASHES = {}
SOURCE_STATS = {}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def record(path, expected=None):
    path = Path(path)
    key = path.relative_to(ROOT).as_posix()
    before = path.stat()
    value = sha(path)
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), key
    if expected is not None:
        assert value == expected, f'Receipt mismatch: {key}'
    if key in SOURCE_HASHES:
        assert value == SOURCE_HASHES[key], f'Source changed: {key}'
    SOURCE_HASHES[key] = value
    SOURCE_STATS[key] = (after.st_size, after.st_mtime_ns)
    return path


def read(path, expected=None):
    return json.loads(record(path, expected).read_text())


def rows(path, expected=None):
    return [json.loads(line) for line in record(path, expected).read_text().splitlines() if line.strip()]


def stage_rows(base, receipts, stage, relative):
    path = base / relative
    expected = receipts[stage]['artifacts'][path.relative_to(BACE).as_posix()]
    return rows(path, expected)


def digest_row(values):
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def select_sample(pools):
    """Proportional quotas, at least one per class; stable seeded hash ranking."""
    total = sum(map(len, pools.values()))
    assert total >= SAMPLE_SIZE and all(pools[label] for label in LABELS)
    ideals = {label: Fraction(SAMPLE_SIZE * len(pools[label]), total) for label in LABELS}
    quotas = {label: max(1, int(ideals[label])) for label in LABELS}
    while sum(quotas.values()) < SAMPLE_SIZE:
        label = max((label for label in LABELS if quotas[label] < len(pools[label])), key=lambda label: ideals[label] - quotas[label])
        quotas[label] += 1
    while sum(quotas.values()) > SAMPLE_SIZE:
        label = min((label for label in LABELS if quotas[label] > 1), key=lambda label: ideals[label] - quotas[label])
        quotas[label] -= 1
    selected = set()
    for label in LABELS:
        ranked = sorted(pools[label], key=lambda pair: (hashlib.sha256(f'{SAMPLE_SEED}|{pair[0]}|{pair[1]}'.encode()).hexdigest(), pair))
        selected.update(ranked[:quotas[label]])
    assert len(selected) == SAMPLE_SIZE
    return selected, quotas


def build_row(case, dc, candidate_ids, ec_by_id, cards, diagnosis, generated, alias_by_id):
    # Deduplication removes only repeated identical source quotes; it never paraphrases.
    quotes = list(dict.fromkeys(q for p in dc['dc_provenance'] for q in p['source_quotes']))
    unmatched = [q for q in quotes if q not in generated]
    full_context = bool(unmatched or not quotes)
    literal = generated if full_context else '\n\n'.join(quotes)
    # Match the diagnostic request order: temporary EC aliases follow sorted original IDs.
    candidate_ids = sorted(candidate_ids, key=alias_by_id.__getitem__)
    evidence_ids = list(dict.fromkeys(eid for ecid in candidate_ids for eid in ec_by_id[ecid]['evidence_card_ids']))
    evidence_ids.sort(key=lambda eid: int(cards[eid]['prompt_label'].split()[-1]))
    ec_refs = {
        eid: [alias_by_id[ecid] for ecid in candidate_ids if eid in ec_by_id[ecid]['evidence_card_ids']]
        for eid in evidence_ids
    }
    evidence_blocks = []
    for eid in evidence_ids:
        card = cards[eid]
        assert card['shown_in_prompt'] is True
        refs = ', '.join(ec_refs[eid])
        evidence_blocks.append(
            f"[{card['prompt_label']} | source year {card['source_year']} | {card['source_label']}]\n"
            f"Candidate ECs: {refs}\n{card['retrieval_text']}"
        )
    ec_blocks = []
    for ecid in candidate_ids:
        ec = ec_by_id[ecid]
        labels = ', '.join(cards[eid]['prompt_label'] for eid in ec['evidence_card_ids'])
        ec_blocks.append(f"[{alias_by_id[ecid]} | {labels}]\n{ec['ec_text']}")
    evidence_text = '\n\n'.join(evidence_blocks) if evidence_blocks else 'No candidate ECs recorded; no associated candidate evidence cards.'
    ec_text = '\n\n'.join(ec_blocks) if ec_blocks else 'No candidate ECs recorded.'
    values = [
        case['company_name'], int(case['target_reporting_year']), case['task_title'],
        literal, dc['dc_text'], evidence_text, ec_text,
        diagnosis['unsupported_label'], diagnosis['rationale'],
    ]
    for index, value in enumerate(values):
        if isinstance(value, str):
            # Excel's cell limit must never silently truncate a source or rationale.
            assert len(value.encode('utf-16-le')) // 2 <= 32767, (case['generation_case_id'], dc['dc_id'], HEADERS[index], len(value))
    return values, full_context, unmatched, quotes, len(evidence_ids)


def main():
    execution = read(RUN / 'execution_status.json')
    assert not execution.get('active_cases') and execution['status'] not in ('running', 'finalizing')
    manifest = read(RUN / 'manifest.json')
    freeze = read(BACE / 'config/freeze.json')
    assert sha(BACE / 'config/freeze.json') == manifest['freeze_sha256']
    config_path = BACE / 'config/evaluation/configs/generation_claim_unsupported_diagnosis_config.json'
    config = read(config_path, freeze['files'][config_path.relative_to(BACE).as_posix()])
    min_width = int(config.get('diagnosis', {}).get('temporary_id_min_width', 3))
    global_path = record(BACE / 'evidence/inputs/generation_cases.jsonl', manifest['generation_input_sha256'])
    frozen_case_hashes = {}
    with global_path.open() as stream:
        for line in stream:
            if not line.strip():
                continue
            frozen_case = json.loads(line)
            frozen_case_hashes[frozen_case['generation_case_id']] = hashlib.sha256(json.dumps(frozen_case, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    assert set(frozen_case_hashes) == set(manifest['case_ids'])

    cases = []
    skipped = []
    pools = {label: [] for label in LABELS}
    for cid in manifest['case_ids']:
        base = RUN / 'cases' / cid
        state = read(base / 'state.json')
        receipts = state['stages']
        if not all(stage in receipts for stage in ['generation', 'dedup', 'candidates', 'support', 'diagnosis']):
            skipped.append(cid)
            continue
        case_rows = rows(base / 'inputs/generation_cases.jsonl')
        assert len(case_rows) == 1 and case_rows[0]['generation_case_id'] == cid
        case = case_rows[0]
        assert hashlib.sha256(json.dumps(case, sort_keys=True, ensure_ascii=False).encode()).hexdigest() == frozen_case_hashes[cid]
        task_match = re.match(r'([ESG])(\d+)-(\d+)', case['task_id'])
        task_sort = ('ESG'.index(task_match[1]), int(task_match[2]), int(task_match[3]))
        cases.append((case['company_name'].casefold(), case['target_reporting_year'], task_sort, cid, case, receipts))
        for diagnosis in stage_rows(base, receipts, 'diagnosis', 'bace/diagnosis/dc_unsupported_diagnoses.jsonl'):
            pools[diagnosis['unsupported_label']].append((cid, diagnosis['dc_claim_id']))
    cases.sort(key=lambda c: c[:4])
    selected, quotas = select_sample(pools)
    selected_cases = {cid for cid, did in selected}
    print(f'Selected {SAMPLE_SIZE} unsupported DCs from {sum(map(len, pools.values())):,}: {quotas}', flush=True)

    DEST.parent.mkdir(parents=True, exist_ok=True)
    temporary = DEST.with_name('.' + DEST.stem + '.building.xlsx')
    workbook = xlsxwriter.Workbook(temporary, {
        'constant_memory': True, 'strings_to_formulas': False, 'strings_to_urls': False,
    })
    workbook.set_properties({
        'title': 'Unsupported diagnosis validation: 500-DC sample',
        'subject': 'Manual review of frozen BACE main-run unsupported DC diagnoses',
        'comments': f'Proportional sample of {SAMPLE_SIZE} unsupported DCs, with at least one per diagnosis class; seed {SAMPLE_SEED}. Source text, DCs, ECs and rationales are preserved. Candidate evidence cards are contextual sources, not extra diagnostic inputs.',
    })
    sheet = workbook.add_worksheet('Unsupported DCs')
    sheet.freeze_panes(1, 3)
    sheet.hide_gridlines(2)
    sheet.set_zoom(75)
    body = workbook.add_format({'font_name': 'Calibri', 'font_size': 11, 'text_wrap': True, 'valign': 'top'})
    year_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 11, 'valign': 'top', 'align': 'center', 'num_format': '0'})
    header = workbook.add_format({'font_name': 'Calibri', 'font_size': 11, 'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'bg_color': '#7AAED6', 'font_color': '#203441', 'bottom': 1, 'bottom_color': '#547D9D'})
    fallback_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 11, 'text_wrap': True, 'valign': 'top', 'bg_color': '#FFF0DF'})
    palette = ['#EEF0F3', '#F2DDE5', '#DDF1E5', '#DFEBF5', '#FCE7D4', '#EBE3F3']
    label_styles = {label: workbook.add_format({'font_name': 'Calibri', 'font_size': 11, 'text_wrap': True, 'valign': 'top', 'bg_color': color}) for label, color in zip(LABELS, palette)}
    for col, width in enumerate([20, 12, 36, 66, 58, 88, 80, 30, 76]):
        sheet.set_column(col, col, width)
    sheet.set_row(0, 42)
    for col, title in enumerate(HEADERS):
        sheet.write_string(0, col, title, header)
    sampling_note = f'Sample: {SAMPLE_SIZE} of {sum(map(len, pools.values())):,} unsupported DCs. Proportional allocation with at least one per diagnosis class, using stable SHA-256 ranking with seed {SAMPLE_SEED}.\n\n' + '\n'.join(f'{label}: {quotas[label]} / {len(pools[label]):,}' for label in LABELS) + '\n\nOnly one contradiction example is included; this sample cannot precisely estimate accuracy for that rare class.'
    sheet.write_comment('A1', sampling_note, {'author': 'BACE export', 'width': 480, 'height': 230})
    sheet.write_comment('D1', 'Exact stored quotes are joined with blank lines. Orange cells contain the complete, verbatim generated disclosure because at least one recorded quote does not match contiguously (or no quote was recorded). Their comments preserve the original quote records. No generated text is paraphrased.', {'author': 'BACE export', 'width': 440, 'height': 180})
    sheet.write_comment('E1', 'One row per deduplicated unsupported DC. Company, reporting year, topic and the unedited DC text identify its source record. The export QA file also maps every Excel row to its original case and DC IDs. Supported DCs and unfinished diagnoses are not included.', {'author': 'BACE export', 'width': 440, 'height': 140})
    sheet.write_comment('F1', 'Complete prompt-visible evidence cards associated with the recorded candidate ECs. Each card is shown once, with its source year, source label and linked candidate EC aliases. These raw cards provide context for your review; the automatic diagnosis consumed extracted candidate ECs. Long cells retain the complete text; expand the formula bar or edit the cell to inspect it.', {'author': 'BACE export', 'width': 460, 'height': 190})
    sheet.write_comment('G1', 'Only ECs in this DC’s stored candidate selection are included. Temporary ec_### aliases and their order reproduce the diagnosis input convention; Evidence labels connect this column with the source-card column. The EC text itself is unedited. Original EC IDs can be recovered from the frozen case files using the Excel-row mapping in the export QA file.', {'author': 'BACE export', 'width': 460, 'height': 150})

    labels = Counter()
    row_hashes = []
    row_index = []
    fallbacks = []
    zero_candidates = 0
    card_appearances = 0
    max_lengths = [0] * 9
    for case_number, (_, _, _, cid, case, receipts) in enumerate(cases, start=1):
        if cid not in selected_cases:
            continue
        base = RUN / 'cases' / cid
        generated_rows = stage_rows(base, receipts, 'generation', 'generation/generated_disclosures.jsonl')
        assert len(generated_rows) == 1
        generated = generated_rows[0]['generated_text']
        dcs = stage_rows(base, receipts, 'dedup', 'bace/dedup/dc_claims.jsonl')
        ecs = stage_rows(base, receipts, 'dedup', 'bace/dedup/ec_claims.jsonl')
        candidate_rows = stage_rows(base, receipts, 'candidates', 'bace/candidates/dc_candidate_ecs.jsonl')
        support_rows = stage_rows(base, receipts, 'support', 'bace/support/dc_support_sets.jsonl')
        diagnoses = stage_rows(base, receipts, 'diagnosis', 'bace/diagnosis/dc_unsupported_diagnoses.jsonl')
        dc_by_id = {d['dc_id']: d for d in dcs}
        ec_by_id = {e['ec_id']: e for e in ecs}
        candidates = {r['dc_claim_id']: r['candidate_ec_ids'] for r in candidate_rows}
        support = {r['dc_claim_id']: r['support_sets'] for r in support_rows}
        diagnosed = {r['dc_claim_id']: r for r in diagnoses}
        assert len(diagnosed) == len(diagnoses) and len(dc_by_id) == len(dcs)
        assert set(support) == set(candidates) == set(dc_by_id)
        assert set(diagnosed) == {did for did, sets in support.items() if not sets}
        cards = {card['evidence_id']: card for card in case['prompt_evidence']}
        width = max(min_width, len(str(len(ecs))))
        aliases = {ecid: f'ec_{i:0{width}d}' for i, ecid in enumerate(sorted(ec_by_id), start=1)}
        # Retain the stored DC order within each company/year/topic.
        for dc in dcs:
            did = dc['dc_id']
            if (cid, did) not in selected:
                continue
            diagnosis = diagnosed[did]
            assert diagnosis['unsupported_label'] in LABELS
            values, full_context, unmatched, quotes, n_cards = build_row(case, dc, candidates[did], ec_by_id, cards, diagnosis, generated, aliases)
            row = len(row_hashes) + 1
            sheet.set_row(row, 132)
            for col, value in enumerate(values):
                if col == 1:
                    status = sheet.write_number(row, col, value, year_style)
                else:
                    fmt = label_styles[value] if col == 7 else fallback_style if col == 3 and full_context else body
                    status = sheet.write_string(row, col, value, fmt)
                assert status == 0, (row, col, status)
                max_lengths[col] = max(max_lengths[col], len(str(value)))
            if full_context:
                comment = f'Case ID: {cid}\nDC ID: {did}\n\nThe cell contains the complete, unedited generated disclosure. At least one stored source quote is not a contiguous substring, or no quote was recorded.\n\nUnedited recorded quotes:\n\n' + '\n\n'.join(quotes)
                assert len(comment) <= 32767
                sheet.write_comment(row, 3, comment, {'author': 'BACE export', 'width': 600, 'height': 260})
                fallbacks.append({'excel_row': row + 1, 'case_id': cid, 'dc_id': did, 'unmatched_quotes': unmatched})
            labels[diagnosis['unsupported_label']] += 1
            zero_candidates += not candidates[did]
            card_appearances += n_cards
            row_hashes.append(digest_row(values))
            row_index.append({'excel_row': row + 1, 'case_id': cid, 'dc_id': did})
        if case_number % 300 == 0:
            print(f'Exported {case_number}/{len(cases)} completed cases; {len(row_hashes):,} unsupported rows.', flush=True)

    sheet.autofilter(0, 0, len(row_hashes), 8)
    workbook.close()

    # Read every cell back through a second implementation: no truncation,
    # formula conversion, column drift, supported rows or duplicate expansion.
    check = openpyxl.load_workbook(temporary, read_only=True, data_only=False)
    assert check.sheetnames == ['Unsupported DCs']
    ws = check.active
    assert ws.max_column == 9 and ws.max_row == len(row_hashes) + 1
    iterator = ws.iter_rows()
    assert [c.value for c in next(iterator)] == HEADERS
    verified = Counter()
    for i, row in enumerate(iterator):
        assert not any(cell.data_type == 'f' for cell in row)
        # Excel encodes XML-forbidden controls as _xHHHH_. openpyxl retains
        # these escapes in inline strings; decode once according to OOXML.
        values = [unescape(c.value) if isinstance(c.value, str) else c.value for c in row]
        assert digest_row(values) == row_hashes[i], f'Cell content differs after XLSX round-trip: row {i + 2}'
        verified[values[7]] += 1
        if (i + 1) % 10000 == 0:
            print(f'Read-back verified {i + 1:,} rows.', flush=True)
    check.close()
    assert verified == labels
    assert dict(labels) == quotas and len(row_hashes) == SAMPLE_SIZE
    assert {(r['case_id'], r['dc_id']) for r in row_index} == selected
    assert len({(r['case_id'], r['dc_id']) for r in row_index}) == len(row_hashes)
    for relative, stats in SOURCE_STATS.items():
        stat = (ROOT / relative).stat()
        assert (stat.st_size, stat.st_mtime_ns) == stats, f'Source changed during export: {relative}'
    temporary.replace(DEST)
    QA.parent.mkdir(parents=True, exist_ok=True)
    QA.write_text(json.dumps({
        'workbook': DEST.relative_to(ROOT).as_posix(), 'sha256': sha(DEST),
        'headers': HEADERS, 'worksheets': 1, 'data_rows': len(row_hashes),
        'completed_cases': len(cases), 'incomplete_cases_excluded': skipped,
        'sampling': {'size': SAMPLE_SIZE, 'seed': SAMPLE_SEED,
                     'method': 'Proportional diagnosis-class quotas, minimum one per class, largest remaining deficit allocation; seeded SHA-256 ranking within each class.',
                     'population': {label: len(pools[label]) for label in LABELS},
                     'sample': quotas, 'sampled_cases': len(selected_cases)},
        'diagnosis_counts': dict(labels), 'no_candidate_ec_rows': zero_candidates,
        'candidate_card_appearances': card_appearances,
        'literal_quote_full_context_fallbacks': fallbacks,
        'maximum_cell_characters': dict(zip(HEADERS, max_lengths)),
        'read_back': 'All nine cells in every row match the source-derived content exactly after standard OOXML string-escape decoding; no formula cells.',
        'sources_sha256': SOURCE_HASHES, 'row_index': row_index,
        'exporter_sha256': sha(__file__),
        'dependencies': {'XlsxWriter': xlsxwriter.__version__, 'openpyxl': openpyxl.__version__},
    }, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'workbook': str(DEST), 'rows': len(row_hashes), 'columns': 9,
                      'full_context_quote_rows': len(fallbacks), 'bytes': DEST.stat().st_size,
                      'diagnosis_counts': dict(labels)}, indent=2), flush=True)


if __name__ == '__main__':
    main()
