"""Supplement the census with exact-phrase counts and saved-source lineage."""
from pathlib import Path
from collections import Counter, defaultdict
import ast
import csv
import hashlib
import json
import re

from audit import ROOT, OUT, REF

PROVENANCE = []


def load(path):
    data = path.read_bytes()
    PROVENANCE.append({'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(data).hexdigest()})
    if path.suffix == '.jsonl':
        return [json.loads(line) for line in data.splitlines() if line.strip()]
    return json.loads(data)


def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    static_paths = [
        'BACE/script/data_2_evidence/csv_2_evidence.py',
        '_archive/previous_stage_20260921/script/data_2_evidence/csv_2_evidence.py',
        'BACE/script/prepare_evidence.py',
        'BACE/script/rag/build_w2_generation_inputs.py',
        'BACE/script/rag/run_w2_retrieval_sanity_check.py',
        'BACE/script/evaluation/generation_claims.py',
        'BACE/script/evaluation/run_generation_claim_extraction.py',
        'BACE/script/evaluation/run_generation_claim_semantic_dedup.py',
        'BACE/config/evaluation/prompts/generation_ec_claim_extraction_prompt_v8.txt',
        'BACE/config/evaluation/prompts/generation_ec_claim_patch_review_prompt_v4.txt',
        'BACE/config/evaluation/prompts/generation_ec_claim_atomicity_review_prompt_v2.txt',
        'BACE/config/evaluation/configs/generation_claim_extraction_config_v8.json',
        'data/raw/datasets/indicator_metadata.csv',
    ]
    for rel in static_paths:
        PROVENANCE.append({'path': rel, 'sha256': hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()})
    builders = [next(n for n in ast.parse((ROOT / rel).read_text()).body
                     if isinstance(n, ast.FunctionDef) and n.name == 'construct_retrieval_text')
                for rel in static_paths[:2]]
    inherited_builder_equal = ast.dump(builders[0]) == ast.dump(builders[1])
    with (OUT / 'flagged_final_ec.csv').open() as f:
        flags = list(csv.DictReader(f))
    patterns = {
        'under_ESRS': r'\bunder ESRS\b',
        'disclosure_requirement': r'\bdisclosure requirements?\b',
        'ESG_topic': r'\bESG topic\b',
        'parallel_E1_phrase': r'under ESRS E1 disclosure requirement E1-\d+',
        'user_S1_phrase': r'under ESRS S1 disclosure requirement S1-14',
        'user_G1_phrase': r'under ESRS G1 disclosure requirement G1-6',
    }
    phrase_counts = {}
    for name, pattern in patterns.items():
        matching = [r for r in flags if re.search(pattern, r['ec_text'], re.I)]
        phrase_counts[name] = {'regex': pattern, 'count': len(matching),
                               'by_source_standard': dict(Counter(r['source_standard'] for r in matching)),
                               'cases': len({r['generation_case_id'] for r in matching})}
    picks = {
        'E1': next(r for r in flags if re.search(patterns['parallel_E1_phrase'], r['ec_text'])),
        'S1': next(r for r in flags if 'mowi__2023__s1_14' in r['generation_case_id'] and re.search(patterns['user_S1_phrase'], r['ec_text'])),
        'G1': next(r for r in flags if 'intertek__2019__g1_2' in r['generation_case_id'] and re.search(patterns['user_G1_phrase'], r['ec_text'])),
    }
    traces = {}
    for kind, pick in picks.items():
        case = ROOT / 'BACE/results/main_v1/cases' / pick['generation_case_id']
        eid = pick['evidence_ids']
        inp = load(case / 'inputs/generation_cases.jsonl')[0]
        card = next(r for r in inp['prompt_evidence'] if r['evidence_id'] == eid)
        trace = {'case': case.name, 'task_id': inp['task_id'], 'card': card, 'final_ec': pick, 'stages': {}}
        for stage in ['direct','integrated','atomic']:
            calls = load(case / f'extraction/{stage}/ec_extraction_calls.jsonl')
            call = next(c for c in reversed(calls) if c.get('output_valid'))
            result = next(r for r in call['canonical_output']['evidence_results'] if r['prompt_label'] == card['prompt_label'])
            trace['stages'][stage] = {
                'call_id': call['call_id'], 'started_at_utc': call['started_at_utc'],
                'prompt_version': call['call_identity']['prompt_version'],
                'prompt_sha256': call['call_identity']['prompt_sha256'],
                'output_processing_mode': call['output_processing_mode'],
                'compiled_evidence_result': result,
                'raw_output_contains_exact_final_claim': pick['ec_text'] in call['raw_output'],
                'native_response_contains_under_ESRS': 'under ESRS' in json.dumps(call['api_response']),
            }
            if stage == 'direct':
                native = json.loads(call['raw_output'])
                trace['stages'][stage]['raw_evidence_result'] = next(r for r in native['evidence_results'] if r['prompt_label'] == card['prompt_label'])
            else:
                patch = json.loads(call['raw_output'])
                trace['stages'][stage]['raw_patch_for_card'] = next((r for r in patch['evidence_results'] if r['prompt_label'] == card['prompt_label']), None)
        traces[kind] = trace

    wanted = {t['card']['evidence_id'] for t in traces.values()}
    wanted_indicators = {eid.split('::')[3] for eid in wanted}
    with (ROOT / 'data/raw/datasets/indicator_metadata.csv').open() as f:
        metadata = {r['id']: r for r in csv.DictReader(f) if r['id'] in wanted_indicators}
    path = ROOT / 'data/processed/results/esg_indicators_postprocessed.csv'
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    PROVENANCE.append({'path': str(path.relative_to(ROOT)), 'sha256': h.hexdigest()})
    raw_rows = {}
    with path.open() as f:
        reader = csv.DictReader(f)
        for record_index, row in enumerate(reader, 1):
            eid = 'csv::' + '::'.join(row[k] for k in ['company_id','year','data_point_id'])
            if eid in wanted:
                raw_rows[eid] = {'csv_data_record_index': record_index, 'row': row}
    for trace in traces.values():
        eid = trace['card']['evidence_id']
        trace['indicator_metadata'] = metadata[eid.split('::')[3]]
        trace['processed_source_row'] = raw_rows[eid]

    manifest_path = ROOT / 'BACE/analysis/validation/_private/sample_manifest.json'
    manifest = load(manifest_path)
    flagged_manifest = Counter()
    final_texts = {}
    mismatches = []
    for r in manifest['records']:
        cid = r['generation_case_id']
        if cid not in final_texts:
            final_texts[cid] = {e['ec_text'] for e in load(ROOT / 'BACE/results/main_v1/cases' / cid / 'bace/dedup/ec_claims.jsonl')}
        flagged_manifest['review_units'] += 1
        unit_flagged = False
        unit_exact = False
        for e in r['dynamic_input']['ec_claims']:
            text = e['ec_text']
            flagged_manifest['ec_presentations'] += 1
            ref = bool(REF.search(text))
            exact = bool(re.search(patterns['user_S1_phrase'] + '|' + patterns['user_G1_phrase'], text))
            flagged_manifest['ec_presentations_with_reference'] += ref
            flagged_manifest['ec_presentations_with_exact_user_phrase'] += exact
            unit_flagged |= ref
            unit_exact |= exact
            if text not in final_texts[cid]:
                mismatches.append({'sample_id': r['sample_id'], 'ec_text': text})
        flagged_manifest['review_units_with_reference_ec'] += unit_flagged
        flagged_manifest['review_units_with_exact_user_phrase'] += unit_exact

    with (OUT / 'same_card_variation.csv').open() as f:
        variation = next(r for r in csv.DictReader(f) if r['standard'] == 'S1')
    variation['claims'] = {}
    for which in ['example_case_without','example_case_with']:
        cid = variation[which]
        ecs = load(ROOT / 'BACE/results/main_v1/cases' / cid / 'bace/dedup/ec_claims.jsonl')
        variation['claims'][which] = [e['ec_text'] for e in ecs if variation['evidence_id'] in e['evidence_card_ids']]

    # Verify census file hashes against the saved per-stage execution receipts.
    census = load(OUT / 'input_manifest.json')
    states = {}
    receipt = Counter()
    receipt_mismatches = []
    for f in census['files']:
        path = Path(f['path'])
        if path.parts[:4] != ('BACE','results','main_v1','cases') or path.parts[5] == 'inputs':
            continue
        cid = path.parts[4]
        if cid not in states:
            states[cid] = load(ROOT / 'BACE/results/main_v1/cases' / cid / 'state.json')
        artifact_path = str(Path(*path.parts[1:]))
        expected = {v for stage in states[cid]['stages'].values() for k,v in stage.get('artifacts',{}).items() if k == artifact_path}
        receipt['checked_files'] += 1
        if not expected:
            receipt['without_completed_stage_receipt'] += 1
        elif expected == {f['sha256']}:
            receipt['matched_files'] += 1
        else:
            receipt_mismatches.append({'path': f['path'], 'expected': sorted(expected), 'actual': f['sha256']})
    save('trace_results.json', {'access_date': '2026-10-26', 'phrase_counts': phrase_counts,
                               'current_and_archived_builder_AST_equal': inherited_builder_equal,
                               'traces': traces, 'same_card_example': variation,
                               'review_manifest_counts': dict(flagged_manifest),
                               'review_manifest_text_mismatches': mismatches,
                               'receipt_counts': dict(receipt), 'receipt_mismatches': receipt_mismatches})
    save('trace_input_manifest.json', {'files': PROVENANCE,
         'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    print(json.dumps({'phrases': phrase_counts, 'review': dict(flagged_manifest), 'receipt': dict(receipt),
                      'review_mismatches': len(mismatches), 'receipt_mismatches': len(receipt_mismatches)}), flush=True)


if __name__ == '__main__':
    main()
