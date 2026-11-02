"""Audit every completed replay record against frozen jobs and native parsing."""
from collections import Counter
from functools import lru_cache
import importlib.metadata
import json

from common import (EXP, ROOT, RESULTS, CONDITIONS, native, read, rows, write,
                    sha, now, condition_bundle, replay_job, verify_frozen)
from run import validate_result

def audit_invalid_outputs(record, job):
    """Reproduce native rejection without repairing or retrying any output."""
    rejected = 0
    for attempt in record['attempts']:
        if attempt['status'] != 'invalid_output':
            continue
        try:
            payload = json.loads(attempt['raw_output'])
            native.validate_support_response(payload,
                expected_dc_id=job['dc_alias'],
                expected_ec_ids=job['candidate_ec_aliases'])
        except (json.JSONDecodeError, native.OutputValidationError) as exc:
            assert str(exc) == attempt['validation_error'], 'Rejection reason changed'
        else:
            raise AssertionError('Recorded invalid output passes the frozen parser')
        rejected += 1
    if record['call_status'] == 'invalid_output':
        assert rejected == len(record['attempts']) and rejected > 0
        assert record['raw_output'] == record['attempts'][-1]['raw_output']
        assert record['validation_error'] == record['attempts'][-1]['validation_error']
        assert record['validated_output'] is None and record['restored_output'] is None
        assert record['output_valid'] is False
    return rejected

def main():
    frozen=verify_frozen()
    env={d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
    assert env==frozen['environment'], 'Native environment changed'
    plan=read(EXP/'plan.json')
    status=read(RESULTS/'status.json')
    assert status['mode']=='full' and status['status']=='COMPLETED'
    by_case={c['generation_case_id']:c for c in plan['cases']}
    @lru_cache(maxsize=8)
    def inputs(cid):
        case=read(ROOT/by_case[cid]['cache_path'])
        return {s['job']['dc_id']:{**s,'evidence_case':case} for s in case['dc_jobs']}
    audits=[]
    for condition in CONDITIONS:
        cfg,prompt,schema=condition_bundle(condition)
        cases=plan['cases']
        expected={(c['generation_case_id'],s['job']['dc_id']) for c in cases
                  for s in read(ROOT/c['cache_path'])['dc_jobs']}
        seen=set(); counts=Counter(); usage=Counter()
        path=RESULTS/'runs'/condition/'calls.jsonl'
        for record in rows(path):
            key=record['generation_case_id'],record['dc_id']
            assert key in expected and key not in seen
            seen.add(key)
            saved=inputs(key[0])[key[1]]
            job=validate_result(record,saved,condition)
            counts['invalid_attempts_reproduced']+=audit_invalid_outputs(record,job)
            assert record['model_id']==plan['model']['model_id']
            assert record['model_version']==plan['model']['model_version']
            assert record['deployment_name']==plan['deployment_name']
            expected_messages=native.sha256_json(native.render_messages(prompt,job['dynamic_input']))
            for attempt in record['attempts']:
                assert attempt['messages_sha256']==expected_messages
            assert record['model_called']==job['requires_model']
            if record['call_status']=='success' and record['model_called']:
                assert record['attempts'][-1]['api_response']['status']=='completed'
            if not job['requires_model']:
                assert record['call_status']=='success' and record['restored_output']['support_sets']==[]
                assert not record['attempts']
            counts[record['call_status']]+=1
            counts['model_called' if record['model_called'] else 'deterministic']+=1
            for k,v in record.get('usage',{}).items():
                usage[k]+=v or 0
        assert seen==expected
        assert counts['success']==status['conditions'][condition]['valid']
        audits.append({'condition':condition,'planned':len(expected),'recorded':len(seen),
                       'counts':dict(counts),'usage':dict(usage),'calls_sha256':sha(path)})
        print(f'Verified every {condition} record: {len(seen)}',flush=True)
    write(RESULTS/'qa/completed_run_audit.json',{'status':'PASS','created_at_utc':now(),
        'all_planned_jobs_recorded':True,'every_dynamic_input_and_message_hash_verified':True,
        'native_parser_reapplied':True,'invalid_output_rejections_reproduced':True,
        'native_environment_unchanged':True,
        'source_files_verified':len(frozen['files']),'conditions':audits,
        'limits':'Structural and provenance audit; no independent semantic correctness assessment.'})

if __name__=='__main__':main()
