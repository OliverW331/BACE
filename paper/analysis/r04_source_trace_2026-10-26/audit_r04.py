"""Reproduce R04's source/EC mapping from saved records without model calls."""
from pathlib import Path
import hashlib
import json

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
CID = 'w2__text_embedding_3_large__stratified_by_evidence_type_n10__omv__2023__g1_2_supplier_relationships'
DID = 'dc_c34e88b73a00b1cf0682594cb512f84d'
CASE = ROOT / 'BACE/results/main_v1/cases' / CID
INPUTS = {}


def read(path):
    b = path.read_bytes()
    INPUTS[str(path.relative_to(ROOT))] = hashlib.sha256(b).hexdigest()
    if path.suffix == '.jsonl':
        return [json.loads(x) for x in b.splitlines() if x.strip()]
    return json.loads(b)


def main():
    case = read(CASE / 'inputs/generation_cases.jsonl')[0]
    state = read(CASE / 'state.json')
    evidence = {r['prompt_label']: r for r in case['prompt_evidence']}
    eid = evidence['Evidence 5']['evidence_id']
    result = {'access_date': '2026-10-26', 'case_id': CID, 'dc_id': DID,
              'evidence_5': evidence['Evidence 5'], 'stages': {}}
    for stage in ['direct', 'integrated', 'atomic']:
        calls = read(CASE / f'extraction/{stage}/ec_extraction_calls.jsonl')
        call = next(r for r in reversed(calls) if r.get('output_valid'))
        output = next(r for r in call['canonical_output']['evidence_results'] if r['prompt_label'] == 'Evidence 5')
        raw = next(r for r in json.loads(call['raw_output'])['evidence_results'] if r['prompt_label'] == 'Evidence 5')
        occurrences = read(CASE / f'extraction/{stage}/ec_claim_occurrences.jsonl')
        own = [r for r in occurrences if r['evidence_id'] == eid]
        assert output['claims'] == [] and own == []
        result['stages'][stage] = {'call_id': call['call_id'], 'canonical_output': output,
                                   'raw_output_for_evidence_5': raw, 'occurrence_count': len(own)}
    ecs = read(CASE / 'bace/dedup/ec_claims.jsonl')
    by_id = {r['ec_id']: r for r in ecs}
    assert all(eid not in r['evidence_card_ids'] for r in ecs)
    candidates = next(r for r in read(CASE / 'bace/candidates/dc_candidate_ecs.jsonl') if r['dc_claim_id'] == DID)
    support = next(r for r in read(CASE / 'bace/support/dc_support_sets.jsonl') if r['dc_claim_id'] == DID)
    diagnosis = next(r for r in read(CASE / 'bace/diagnosis/dc_unsupported_diagnoses.jsonl') if r['dc_claim_id'] == DID)
    assert len(candidates['candidate_ec_ids']) == 1
    ec = by_id[candidates['candidate_ec_ids'][0]]
    assert ec['evidence_card_ids'] == [evidence['Evidence 14']['evidence_id']]
    result.update(final_ec_count=len(ecs), evidence_5_final_ec_count=0,
                  candidate_ec=ec, candidate_source=evidence['Evidence 14'],
                  candidate_output=candidates, support=support, diagnosis=diagnosis)
    for stage, filename in [('candidates','claim_candidate_calls.jsonl'), ('support','claim_support_calls.jsonl')]:
        call = next(r for r in reversed(read(CASE / f'bace/{stage}/{filename}'))
                    if r.get('dc_id') == DID and r.get('output_valid'))
        result[stage + '_call'] = {'call_id': call['call_id'],
                                  'dynamic_input': call['dynamic_input'],
                                  'restored_output': call['restored_output']}
    result['header_presence_in_supplied_cards'] = {
        text: [c['prompt_label'] for c in evidence.values() if text.lower() in c['retrieval_text'].lower()]
        for text in ['On-time payment', 'Key topics and concerns', 'Stakeholder groups', 'Type of OMV engagement']}
    for name, index in [('ragas',48), ('ragchecker',51)]:
        rows = read(CASE / f'evaluation/{name}/results.jsonl')
        result[name] = next(r for r in rows[-1]['claims'] if r['claim_index'] == index)
    packet = read(ROOT / 'paper/analysis/residual_gap_review_2026-10-20/packets/R04.json')
    assert packet['candidate_ecs'] == [ec]
    assert packet['all_ecs'] == ecs
    assert result['ragchecker']['evidence_verdicts'][eid] == 'Entailment'
    assert result['ragchecker']['evidence_verdicts'][evidence['Evidence 14']['evidence_id']] == 'Neutral'
    comparisons = read(ROOT / 'paper/analysis/prompt_gap_review_2026-10-22/selected_prompt_results.json')['R04']
    result['prompt_variants'] = comparisons
    for rel in ['data/raw/reports_pdf/4a868d73-3310-4e93-a8dc-a6b88b252509_2019_SR.pdf',
                'paper/analysis/reader_layout_2026-10-22/build_minimal_readers.py',
                'BACE/config/evaluation/prompts/generation_ec_claim_atomicity_review_prompt_v2.txt']:
        INPUTS[rel] = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    verified = []
    for stage in state['stages'].values():
        for rel, expected in stage['artifacts'].items():
            path = 'BACE/' + rel
            if path in INPUTS:
                assert INPUTS[path] == expected, path
                verified.append(path)
    result['verified_receipt_files'] = verified
    result['pdf_visual_inspection'] = {
        'page': 159, 'row_label': 'Suppliers and contractors',
        'column_label': 'Key topics and concerns raised by stakeholders',
        'cell_item': 'On-time payment',
        'status': 'Verified visually against rendered original PDF page; this header is absent from the supplied evidence cards.',
        'image': 'omv_2019_page_159.png'}
    (OUT / 'trace.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'provenance.json').write_text(json.dumps({
        'inputs': INPUTS, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'access_date': '2026-10-26', 'model_calls': 0, 'frozen_artifacts_modified': False,
    }, indent=2) + '\n')
    print(json.dumps({'final_ecs': len(ecs), 'evidence_5_final_ecs': 0,
                      'candidate_source': evidence['Evidence 14']['prompt_label'],
                      'verified_receipt_files': len(verified)}))


if __name__ == '__main__':
    main()
