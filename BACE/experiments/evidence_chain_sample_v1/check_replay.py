"""Offline integration checks for condition inputs and citation restoration."""
from common import (EXP,ROOT,RESULTS,CONDITIONS,read,write,now,sha,
                    replay_job,native,verify_frozen)

def main():
    verify_frozen()
    plan=read(EXP/'plan.json')
    by_case={c['generation_case_id']:c for c in plan['cases']}
    checked=[]
    for selected in plan['pilot_jobs']:
        cid=selected['generation_case_id']
        case=read(ROOT/by_case[cid]['cache_path'])
        source=next(x for x in case['dc_jobs'] if x['job']['dc_id']==selected['dc_id'])
        saved={**source,'evidence_case':case}
        for condition in CONDITIONS:
            job=replay_job(saved,condition)
            assert job['dynamic_input']['dc_claim']==source['job']['dynamic_input']['dc_claim']
            assert job['dynamic_input']['context_metadata']==source['job']['dynamic_input']['context_metadata']
            assert job['request_parameters']==plan['model']['request_parameters']
            assert job['job_input_hash']==native.sha256_json(job['dynamic_input'])
            expected={'raw_cards':len(case['raw_units']),
                'all_ec':len(case['all_ec_input']),
                'candidate_ec':len(source['job']['candidate_ec_aliases'])}[condition]
            assert len(job['candidate_ec_aliases'])==expected
            if condition=='candidate_ec':
                assert job['dynamic_input']==source['job']['dynamic_input']
            if condition=='raw_cards':
                assert [x['ec_text'] for x in job['dynamic_input']['ec_claims']]==[x['text'] for x in case['raw_units']]
            # Synthetic parser fixture, not a semantic support judgment.
            sets=[] if not expected else [{'ec_claim_ids':[job['candidate_ec_aliases'][0]],'support_type':'direct'}]
            fixture={'dc_claim_id':job['dc_alias'],'support_sets':sets}
            validated=native.validate_support_response(fixture,
                expected_dc_id=job['dc_alias'],expected_ec_ids=job['candidate_ec_aliases'])
            restored=native.restore_original_ids(validated,original_dc_id=job['dc_id'],
                ec_original_by_alias=job['ec_original_by_alias'])
            if expected:
                assert restored['support_sets'][0]['ec_claim_ids']==[job['call_identity']['candidate_ec_ids'][0]]
            checked.append({'condition':condition,'generation_case_id':cid,'dc_id':job['dc_id'],'units':expected})
    write(RESULTS/'qa/offline_replay.json',{'status':'PASS','created_at_utc':now(),
        'freeze_sha256':sha(EXP/'freeze.json'),'model_calls':0,
        'scope':'Fixed targets and metadata, layer input sizes, unchanged candidate input and native ID restoration.',
        'checked':checked})
    print(f'PASS: {len(checked)} offline layer replays; no model calls.')

if __name__=='__main__':main()
