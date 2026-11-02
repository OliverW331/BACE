"""Exercise final result loading on temporary synthetic journals, with no API calls."""
import copy
import json
from pathlib import Path
import sys
import tempfile

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
sys.dont_write_bytecode=True
import evaluator_gap_prompt_sensitivity as analysis
from evaluator_gap_analysis import sha,save_json

def main():
    destination=analysis.DEST/'qa/loading_checks.json'
    # Deliberate whole-disclosure missingness and unequal claim counts test the
    # journal merge and source-cache path, not just the downstream dataframe.
    specs=[('a1','a',[(True,False,True),(False,True,False)],True),
           ('a2','a',[(True,None,None),(False,False,True)],True),
           ('b1','b',[(False,True,False)],False)]
    with tempfile.TemporaryDirectory(prefix='bace-prompt-loading-test-') as tmp:
        root=Path(tmp)
        analysis.ROOT=root;analysis.EXP=root/'experiment';analysis.RUN=root/'run';analysis.DEST=root/'analysis'
        analysis.EXP.mkdir();analysis.RUN.mkdir()
        cases=[];saved_rows=[]
        parameters={'reasoning':{'effort':'medium'},'store':False}
        for cid,company,claims,repeat in specs:
            path=root/'inputs'/f'{cid}.jsonl';path.parent.mkdir(exist_ok=True)
            saved=[]
            for i,(old,ragas,checker) in enumerate(claims):
                dc=f'{cid}_dc{i}'
                dynamic={'context_metadata':{'company_name':company,'target_reporting_year':2020},
                         'dc_claim':{'dc_claim_id':'dc001','dc_text':f'Synthetic assertion {dc}.'},
                         'ec_claims':[{'ec_claim_id':'ec001','ec_text':'Synthetic fixture evidence.'}]}
                support=[{'ec_claim_ids':['ec-original'],'support_type':'direct'}]
                row={'job':{'generation_case_id':cid,'dc_id':dc,'job_input_hash':analysis.digest_json(dynamic),
                            'dynamic_input':dynamic,'candidate_ec_aliases':['ec001'],
                            'ec_original_by_alias':{'ec001':'ec-original'}},
                     'company_id':company,'company_name':company,'original_support_sets':support if old else []}
                saved.append(row)
                saved_rows.append((row,{'ragas_style':ragas,'ragchecker_style':checker,'original_repeat':old},repeat))
            path.write_text(''.join(json.dumps(x)+'\n' for x in saved))
            cases.append({'generation_case_id':cid,'company_id':company,'company_name':company,
                          'claims':len(claims),'zero_candidates':0,'repeat_control':repeat,
                          'cache_path':str(path.relative_to(root)),'cache_sha256':sha(path)})
        plan={'cases':cases,'counts':{'claims_per_full_condition':5,'repeat_claims':4,'repeat_disclosures':2},
              'model':{'request_parameters':parameters},'deployment_name':'SYNTHETIC_FIXTURE_ONLY'}
        save_json(analysis.EXP/'plan.json',plan)
        save_json(analysis.EXP/'freeze.json',{'files':{c['cache_path']:c['cache_sha256'] for c in cases}})
        freeze_hash=sha(analysis.EXP/'freeze.json')
        conditions={}
        for condition in (*analysis.VARIANTS,'original_repeat'):
            journal=[]
            for saved,verdicts,repeat in saved_rows:
                if condition=='original_repeat' and not repeat:continue
                verdict=verdicts[condition]
                record={'generation_case_id':saved['job']['generation_case_id'],'dc_id':saved['job']['dc_id'],
                        'dynamic_input':saved['job']['dynamic_input'],
                        'call_identity':{'job_input_hash':saved['job']['job_input_hash']},
                        'prompt_sensitivity':{'freeze_sha256':freeze_hash},'request_parameters':parameters,
                        'deployment_name':plan['deployment_name'],
                        'call_status':'success' if verdict is not None else
                            ('api_error' if condition=='ragas_style' else 'invalid_output'),
                        'restored_output':{'support_sets':[{'ec_claim_ids':['ec-original'],'support_type':'direct'}] if verdict else []}
                            if verdict is not None else None}
                if verdict is None:
                    record['validation_error']=('Synthetic strict-superset validation failure.'
                        if condition=='ragchecker_style' else None)
                    record['error_type']='SyntheticTransportError' if condition=='ragas_style' else None
                    record['attempts']=[{'output_attempt':i,'network_retries':0} for i in range(3)]
                journal.append(record)
            path=analysis.RUN/'runs'/condition/'calls.jsonl';path.parent.mkdir(parents=True)
            path.write_text(''.join(json.dumps(x)+'\n' for x in journal))
            conditions[condition]={'recorded':len(journal),'valid':sum(x['call_status']=='success' for x in journal),
                                   'failed':sum(x['call_status']!='success' for x in journal)}
        state={'mode':'full','status':'RUNNING','conditions':conditions}
        save_json(analysis.RUN/'status.json',state)
        pending=analysis.load_analysis()
        assert not pending['ready'] and not (analysis.DEST/'tables/scores.csv').exists()
        state['status']='COMPLETED';save_json(analysis.RUN/'status.json',state)
        result=analysis.load_analysis()
        assert result['ready'] and len(result['paired_claims'])==3
        assert set(result['paired_cases'].generation_case_id)=={'a1','b1'}
        assert result['scores'].set_index('condition').loc['original','estimate']==.25
        assert result['effects'].set_index('condition').loc['ragas_style','estimate']==.5
        assert result['disclosure_completeness'].set_index('condition').loc['ragas_style','incomplete_disclosures']==1
        failures=result['failed_records']
        assert len(failures)==2 and set(failures.call_status)=={'api_error','invalid_output'}
        assert failures.generation_case_id.eq('a2').all() and failures.output_attempts.eq(3).all()
        assert failures.record_sha256.str.len().eq(64).all()
        invalid=failures.loc[failures.call_status.eq('invalid_output')].iloc[0]
        assert invalid.validation_error=='Synthetic strict-superset validation failure.'
        assert invalid.source_calls_path=='run/runs/ragchecker_style/calls.jsonl'
        before={p.name:sha(p) for p in (analysis.DEST/'tables').glob('*.csv')}
        examples=sha(analysis.DEST/'examples.json')
        again=analysis.load_analysis()
        assert before=={p.name:sha(p) for p in (analysis.DEST/'tables').glob('*.csv')}
        assert examples==sha(analysis.DEST/'examples.json')
    save_json(destination,{'status':'PASS','synthetic_temporary_fixture':True,'model_calls':0,
        'checks':['Running state withholds final score tables',
                  'Cached inputs join exact journal identities and hashes',
                  'Exhausted API and minimality failures remain missing and exclude their whole disclosure',
                  'Failure types, attempt counts, source paths and record hashes remain traceable',
                  'Main macro contrast preserves unequal original denominators',
                  'Complete outputs and example selection reproduce byte-identically'],
        'fixture_outputs_retained':False,'validator_sha256':sha(__file__)})
    print('PASS: final-journal loading, readiness, missingness and reproducibility; synthetic files removed.')

if __name__=='__main__':main()
