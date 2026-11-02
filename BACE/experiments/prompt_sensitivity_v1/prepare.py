"""Verify the full historical cohort and freeze exact support-stage inputs."""
from __future__ import annotations
import csv
import difflib
import importlib.metadata
import json
from pathlib import Path
import sys
from collections import defaultdict

from common import (EXP, BACE, ROOT, RESULTS, CONDITIONS, SEED, native, sha,
                    rank, read, rows, write, now, native_configuration)

def main():
    if (EXP / 'freeze.json').exists():
        raise RuntimeError('Already frozen; verify or resume the existing experiment.')
    if any(RESULTS.glob('runs/*/calls.jsonl')):
        raise RuntimeError('Cannot prepare after model calls exist.')
    config, original_prompt, prompt_path, schema, schema_path = native_configuration()
    model_key = config['current_primary_model']
    model = config['models'][model_key]
    source_hashes = {}
    def record(path, expected=None):
        path = Path(path).resolve()
        digest = sha(path)
        if expected is not None:
            assert digest == expected, str(path)
        source_hashes[str(path.relative_to(ROOT))] = digest
        return digest

    snapshot = BACE / 'analysis/outputs/snapshot'
    snap_manifest = read(snapshot / 'manifest.json')
    for p in [snapshot / 'manifest.json', snapshot / 'claims.csv', snapshot / 'metrics.csv']:
        record(p)
    # Snapshot's own ledger is checked, not merely copied into a new manifest.
    for name in ('claims', 'metrics'):
        record(snapshot / (name + '.csv'), snap_manifest['tables'][name])
    with (snapshot / 'metrics.csv').open() as f:
        all_metrics = list(csv.DictReader(f))
    cohort = [m for m in all_metrics if all(m[k] == 'True' for k in
               ('bace_complete', 'ragas_complete', 'ragchecker_complete'))]
    cohort.sort(key=lambda m: m['generation_case_id'])
    claim_index = defaultdict(dict)
    with (snapshot / 'claims.csv').open() as f:
        for row in csv.DictReader(f):
            claim_index[row['generation_case_id']][row['dc_id']] = row
    assert set(claim_index) == {m['generation_case_id'] for m in cohort}
    groups = defaultdict(list)
    for m in cohort:
        groups[m['company_id']].append(m['generation_case_id'])
    repeat_ids = {cid for ids in groups.values() for cid in sorted(ids, key=lambda c: rank('repeat', c))[:2]}
    assert len(repeat_ids) == 2 * len(groups)
    RESULTS.mkdir(parents=True, exist_ok=True)
    cache = RESULTS / 'inputs'
    cache.mkdir(exist_ok=True)
    case_rows, pilot_candidates = [], defaultdict(list)
    total = empty = supported = 0
    for index, metric in enumerate(cohort, 1):
        cid = metric['generation_case_id']
        base = BACE / 'results/main_v1/cases' / cid
        support = base / 'bace/support'
        manifest_path = support / 'claim_support_run_manifest.json'
        manifest = read(manifest_path)
        identity = manifest['run_identity']
        record(manifest_path)
        assert identity['prompt_sha256'] == sha(prompt_path)
        assert identity['schema_sha256'] == sha(schema_path)
        assert identity['model_id'] == model['model_id']
        assert identity['model_version'] == model['model_version']
        assert identity['model_key'] == model_key
        assert identity['request_parameters'] == model['request_parameters']
        record(identity['config_path'], identity['config_sha256'])
        inputs = identity['inputs']
        for item in inputs.values():
            record(item['path'], item['sha256'])
        ec = list(rows(inputs['ec_claims']['path']))
        dc = list(rows(inputs['dc_claims']['path']))
        candidates = native.validate_candidate_selections(
            list(rows(inputs['candidate_selections']['path'])), ec_rows=ec,
            dc_rows=dc, path=Path(inputs['candidate_selections']['path']))
        native.validate_claim_rows(ec, dc, ec_path=Path(inputs['ec_claims']['path']),
                                   dc_path=Path(inputs['dc_claims']['path']))
        context = native.index_generation_case_context(
            list(rows(inputs['generation_cases']['path'])), claim_rows=dc,
            path=Path(inputs['generation_cases']['path']))
        jobs = native.build_jobs(ec_rows=ec, dc_rows=dc, case_context_by_id=context,
            candidate_by_dc_id=candidates, case_ids=[cid], requested_dc_ids=None,
            max_dcs=None, config=config, prompt_spec=config['prompt'],
            schema_spec=config['response_schema'], model_key=model_key, model=model,
            deployment=identity['deployment_name'])
        calls_path = support / 'claim_support_calls.jsonl'
        result_path = support / 'dc_support_sets.jsonl'
        record(calls_path)
        record(result_path)
        latest = {r['call_id']: r for r in rows(calls_path)}
        result = {r['dc_claim_id']: r for r in rows(result_path)}
        expected = claim_index[cid]
        assert {j['dc_id'] for j in jobs} == set(expected) == set(identity['selected_dc_ids'])
        output = cache / f'{cid}.jsonl'
        with output.open('w') as f:
            for job in jobs:
                call = latest[job['call_id']]
                assert call['call_status'] == 'success' and call['output_valid']
                assert call['dynamic_input'] == job['dynamic_input']
                assert call['call_identity'] == job['call_identity']
                assert call['dc_temporary_id'] == job['dc_alias']
                assert call['ec_temporary_id_map'] == job['ec_original_by_alias']
                check = native.validate_support_response(call['validated_output'],
                    expected_dc_id=job['dc_alias'], expected_ec_ids=job['candidate_ec_aliases'])
                restored = native.restore_original_ids(check, original_dc_id=job['dc_id'],
                    ec_original_by_alias=job['ec_original_by_alias'])
                assert restored == call['restored_output']
                assert restored['support_sets'] == result[job['dc_id']]['support_sets']
                target = expected[job['dc_id']]
                assert target['dc_text'] == job['dynamic_input']['dc_claim']['dc_text']
                assert int(target['candidate_count']) == len(job['candidate_ec_aliases'])
                assert int(target['support_set_count']) == len(restored['support_sets'])
                assert bool(restored['support_sets']) == (target['label'] in ('direct', 'inferred'))
                saved = {'job': job, 'original_support_sets': restored['support_sets'],
                         'company_id': metric['company_id'], 'company_name': metric['company_name'],
                         'year': int(metric['year']), 'task': metric['task']}
                f.write(json.dumps(saved, ensure_ascii=False, separators=(',', ':')) + '\n')
                total += 1
                empty += not job['requires_model']
                supported += bool(restored['support_sets'])
                if cid in repeat_ids and job['requires_model']:
                    pilot_candidates[metric['company_id']].append((cid, job['dc_id']))
        case_rows.append({k: metric[k] for k in ('generation_case_id', 'company_id', 'company_name', 'year', 'task')} |
                        {'claims': len(jobs), 'zero_candidates': sum(not j['requires_model'] for j in jobs),
                         'original_supported': sum(bool(latest[j['call_id']]['restored_output']['support_sets']) for j in jobs),
                         'repeat_control': cid in repeat_ids, 'cache_path': str(output.relative_to(ROOT)),
                         'cache_sha256': sha(output), 'deployment_name': identity['deployment_name']})
        if index % 100 == 0:
            print(f'Verified {index}/{len(cohort)} disclosures, {total} claims', flush=True)

    assert len({c['deployment_name'] for c in case_rows}) == 1
    pilots = [min(values, key=lambda v: rank('pilot', '|'.join(v))) for values in pilot_candidates.values()]
    pilots.sort()
    for p in [prompt_path, schema_path, EXP / 'PROTOCOL.md', EXP / 'common.py', EXP / 'prepare.py', EXP / 'run.py']:
        record(p)
    native_freeze = read(BACE / 'config/freeze.json')
    for name, expected in native_freeze['files'].items():
        record(BACE / name, expected)
    source_prompts = [BACE / '.venv/lib/python3.11/site-packages/ragas/metrics/collections/faithfulness/util.py',
                      BACE / '.venv/lib/python3.11/site-packages/refchecker/checker/checker_prompts.py']
    for p in source_prompts:
        record(p)
    for condition in CONDITIONS:
        p = EXP / 'prompts' / f'{condition}_v1.txt'
        record(p)
        diff = ''.join(difflib.unified_diff(original_prompt.splitlines(True), p.read_text().splitlines(True),
                     fromfile='original_bace', tofile=condition))
        (EXP / f'{condition}.diff').write_text(diff)
        record(EXP / f'{condition}.diff')
    assert (EXP / 'prompts/ragas_style_v1.txt').read_text().split('## Support type')[1] == (EXP / 'prompts/ragchecker_style_v1.txt').read_text().split('## Support type')[1]
    plan = {'created_at_utc': now(), 'seed': SEED, 'cases': case_rows,
            'excluded_case_ids': [m['generation_case_id'] for m in all_metrics if m not in cohort],
            'pilot_jobs': [{'generation_case_id': cid, 'dc_id': dc} for cid, dc in pilots],
            'counts': {'disclosures': len(cohort), 'companies': len(groups), 'claims_per_full_condition': total,
                       'zero_candidates_per_full_condition': empty, 'model_calls_per_full_condition': total-empty,
                       'original_supported': supported, 'repeat_disclosures': len(repeat_ids),
                       'repeat_claims': sum(c['claims'] for c in case_rows if c['repeat_control']),
                       'repeat_model_calls': sum(c['claims']-c['zero_candidates'] for c in case_rows if c['repeat_control'])},
            'model': model, 'model_key': model_key, 'deployment_name': case_rows[0]['deployment_name'],
            'original_config_sha256': sha(BACE / 'config/evaluation/configs/generation_claim_support_config.json'),
            'source_hashes': source_hashes, 'status': 'PREPARED_NOT_RUN'}
    write(EXP / 'plan.json', plan)
    record(EXP / 'plan.json')
    frozen_files = dict(source_hashes)
    for c in case_rows:
        frozen_files[c['cache_path']] = c['cache_sha256']
    write(EXP / 'freeze.json', {'created_at_utc': now(), 'files': frozen_files,
          'status': 'FROZEN_BEFORE_FIRST_NEW_MODEL_CALL', 'counts': plan['counts'],
          'environment': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}})
    print(json.dumps(plan['counts'], indent=2), flush=True)

if __name__ == '__main__':
    main()
