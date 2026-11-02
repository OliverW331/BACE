"""Offline audit of selection, inherited pilot and every reused output."""
import csv
import hashlib
import json
from collections import defaultdict
from common import EXP, ROOT, BACE, RESULTS, CONDITIONS, read, rows, sha, rank, write, now, verify_frozen, native, condition_bundle
from run import validate_result
from audit_completed_run import audit_invalid_outputs

def main():
    verify_frozen()
    plan=read(EXP/'plan.json')
    parent=BACE/'experiments/evidence_chain_v1'
    frame=read(parent/'plan.json')['cases']
    grouped=defaultdict(list)
    for c in frame:grouped[(c['company_id'],c['task'][0])].append(c)
    expected={min(cs,key=lambda c:rank('sample_case',c['generation_case_id']))['generation_case_id'] for cs in grouped.values()}
    by_case={c['generation_case_id']:c for c in plan['cases']}
    assert set(by_case)==expected and len(expected)==90
    with (EXP/'selection.csv').open() as stream:ledger=list(csv.DictReader(stream))
    assert len(ledger)==1798
    assert {r['generation_case_id'] for r in ledger if r['selected']=='True'}==expected
    reused={(r['condition'],r['generation_case_id'],r['dc_id']):r for r in read(EXP/'reuse_ledger.json')}
    seen=set();_,prompt,_=condition_bundle()
    for condition in CONDITIONS:
        with (RESULTS/'runs'/condition/'calls.jsonl').open('rb') as stream:
            for line in stream:
                r=json.loads(line);key=(condition,r['generation_case_id'],r['dc_id'])
                assert key in reused and key not in seen;seen.add(key)
                provenance=reused[key]
                assert hashlib.sha256(line).hexdigest()==provenance['record_sha256']
                with (ROOT/provenance['source_path']).open('rb') as source:
                    original=next(v for i,v in enumerate(source,1) if i==provenance['source_line'])
                assert line==original
                case=read(ROOT/by_case[key[1]]['cache_path'])
                s=next(s for s in case['dc_jobs'] if s['job']['dc_id']==key[2])
                job=validate_result(r,{**s,'evidence_case':case},condition)
                audit_invalid_outputs(r,job)
                assert r['evidence_chain']['freeze_sha256']==plan['parent_freeze_sha256']
                assert r['model_id']==plan['model']['model_id'] and r['model_version']==plan['model']['model_version']
                assert r['deployment_name']==plan['deployment_name']
                for attempt in r['attempts']:
                    assert attempt['messages_sha256']==native.sha256_json(native.render_messages(prompt,job['dynamic_input']))
    assert seen==set(reused)
    pilot=read(BACE/'results/evidence_chain_v1/pilot_gate.json')
    assert pilot['status']=='PASS' and pilot['freeze_sha256']==plan['parent_freeze_sha256']
    assert (EXP/'judge_prompt.txt').read_bytes()==(parent/'judge_prompt.txt').read_bytes()
    write(RESULTS/'sample_ready.json',{'status':'PASS','created_at_utc':now(),
        'freeze_sha256':sha(EXP/'freeze.json'),'parent_freeze_sha256':plan['parent_freeze_sha256'],
        'selected_disclosures':90,'reused_records_verified':len(seen),'new_model_calls':0,
        'checks':['Metadata-only sample reproduced','Every reused record is byte-identical to source',
                  'Every reused input, prompt, model and native parsing verified','Successful parent technical gate retained']})
    print(f'PASS: 90 sampled disclosures and {len(seen)} exact reused records; no new model calls.')

if __name__=='__main__':main()
