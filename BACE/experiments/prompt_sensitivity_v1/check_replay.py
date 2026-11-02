"""Offline replay checks using synthetic API responses, never a live model."""
from __future__ import annotations
import copy
import json
from types import SimpleNamespace

from common import (RESULTS, CONDITIONS, native, rows, condition_bundle,
                    replay_job, write, now)
from run import validate_result

def main():
    saved = next(s for p in sorted((RESULTS/'inputs').glob('*.jsonl'))
                 for s in rows(p) if s['job']['requires_model'])
    job = saved['job']
    schema_checks = []
    for payload in [
        {'dc_claim_id': job['dc_alias'], 'support_sets': [{'ec_claim_ids': ['unknown'], 'support_type': 'direct'}]},
        {'dc_claim_id': job['dc_alias'], 'support_sets': [{'ec_claim_ids': [], 'support_type': 'direct'}]},
        {'dc_claim_id': 'wrong', 'support_sets': []},
        {'dc_claim_id': job['dc_alias'], 'support_sets': [], 'verdict': 1},
    ]:
        try:
            native.validate_support_response(payload, expected_dc_id=job['dc_alias'],
                                             expected_ec_ids=job['candidate_ec_aliases'])
        except native.OutputValidationError:
            schema_checks.append(True)
        else:
            raise AssertionError('Invalid payload accepted')
    request_calls = []
    original_create = native.create_response
    output = {'dc_claim_id': job['dc_alias'], 'support_sets': [
        {'ec_claim_ids': job['candidate_ec_aliases'][:1], 'support_type': 'direct'}]}
    class FakeResponse:
        output_text = json.dumps(output)
        def model_dump(self):
            return {'status': 'completed', 'usage': {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2}}
    def fake(client, **kwargs):
        request_calls.append(kwargs)
        return FakeResponse()
    try:
        native.create_response = fake
        for condition in (*CONDITIONS, 'original_repeat'):
            cfg, prompt, schema = condition_bundle(condition)
            replay = replay_job(saved, condition)
            model = cfg['models'][cfg['current_primary_model']]
            record = native.execute_job(job=replay, client=object(),
                deployment=job['call_identity']['deployment_name'], prompt_text=prompt,
                schema=schema, schema_spec=cfg['response_schema'], model_key=cfg['current_primary_model'],
                model=model, config=cfg)
            validate_result(record, saved, condition)
            assert record['call_status'] == 'success'
            request = request_calls[-1]
            assert request['input'][0] == {'role': 'system', 'content': prompt}
            assert request['input'][1] == native.render_messages(prompt, job['dynamic_input'])[1]
            assert request['reasoning'] == job['request_parameters']['reasoning']
        assert all(request_calls[0]['input'][1] == r['input'][1] for r in request_calls)
        assert all(request_calls[0]['text'] == r['text'] for r in request_calls)
        empty = copy.deepcopy(saved)
        empty['job']['candidate_ec_aliases'] = []
        empty['job']['call_identity']['candidate_ec_ids'] = []
        empty['job']['dynamic_input']['ec_claims'] = []
        empty['job']['requires_model'] = False
        count = len(request_calls)
        cfg, prompt, schema = condition_bundle('ragas_style')
        r = native.execute_job(job=replay_job(empty, 'ragas_style'), client=None,
            deployment=job['call_identity']['deployment_name'], prompt_text=prompt, schema=schema,
            schema_spec=cfg['response_schema'], model_key=cfg['current_primary_model'],
            model=cfg['models'][cfg['current_primary_model']], config=cfg)
        assert len(request_calls) == count and not r['model_called'] and r['restored_output']['support_sets'] == []
    finally:
        native.create_response = original_create
    report = {'status': 'PASS', 'created_at_utc': now(), 'live_model_calls': 0,
        'checks': ['Invalid IDs, empty support members, wrong DC and extra fields rejected',
                   'Exact user serialization, request parameters and schema across three prompts',
                   'Native parser and original-ID restoration on synthetic valid response',
                   'Empty-candidate job returns unsupported without model call']}
    write(RESULTS / 'qa/offline_replay.json', report)
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
