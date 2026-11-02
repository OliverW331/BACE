"""Saved-record evidence-chain statistics and verdict-blinded review materials."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from evaluator_gap_analysis import ROOT, OUT, ClusterBootstrap, sha, save_json

EXP = ROOT/'BACE/experiments/evidence_chain_sample_v1'
RUN = ROOT/'BACE/results/evidence_chain_sample_v1'
DEST = OUT/'evidence_chain_sample'
CONDITIONS = ('raw_cards','all_ec','candidate_ec')
CONTRASTS = [('raw_cards','all_ec'),('all_ec','candidate_ec'),('raw_cards','candidate_ec')]

def read(path):
    return json.loads(Path(path).read_text())

def rows(path):
    with Path(path).open() as stream:
        for line in stream:
            if line.strip():yield json.loads(line)

def rank(namespace,value):
    return hashlib.sha256(f'20261002|{namespace}|{value}'.encode()).hexdigest()

def write_table(name,frame):
    (DEST/'tables').mkdir(parents=True,exist_ok=True)
    frame.to_csv(DEST/'tables'/f'{name}.csv',index=False)
    return frame

def calculate(frame):
    assert not frame.duplicated(['generation_case_id','dc_id']).any()
    complete=frame.assign(_valid=frame[list(CONDITIONS)].notna().all(axis=1)).groupby('generation_case_id')._valid.all()
    paired=frame.loc[frame.generation_case_id.isin(complete[complete].index)].copy()
    if paired.empty:raise ValueError('No complete three-layer disclosure')
    for c in (*CONDITIONS,'historical_bace'):paired[c]=paired[c].astype(bool)
    cases=paired.groupby(['company_id','company_name','generation_case_id']).agg(
        claims=('dc_id','size'),**{c:(c,'mean') for c in (*CONDITIONS,'historical_bace')}).reset_index()
    boot=ClusterBootstrap(cases.company_id)
    scores=[{'condition':c,'disclosures':len(cases),'claims':len(paired),**boot.mean(cases,c)} for c in CONDITIONS]
    pooled=[{'condition':c,'claims':len(paired),'supported':int(paired[c].sum()),
             'support_rate':paired[c].mean()} for c in CONDITIONS]
    effects,transitions,company=[],[],[]
    for left,right in CONTRASTS:
        name=f'{left}_minus_{right}'
        values=cases.assign(_delta=cases[left]-cases[right])
        effects.append({'contrast':name,'left':left,'reference':right,'disclosures':len(cases),
                        'claims':len(paired),**boot.mean(values,'_delta')})
        for old in [False,True]:
            den=int(paired[right].eq(old).sum())
            for new in [False,True]:
                n=int((paired[right].eq(old)&paired[left].eq(new)).sum())
                transitions.append({'contrast':name,'reference_supported':old,'left_supported':new,
                    'claims':n,'all_claims':len(paired),'reference_status_denominator':den,
                    'fraction_all_claims':n/len(paired),'fraction_reference_status':n/den if den else float('nan')})
        for (co,co_name),group in values.groupby(['company_id','company_name']):
            company.append({'contrast':name,'company_id':co,'company_name':co_name,
                'disclosures':len(group),'claims':int(group.claims.sum()),'delta':group._delta.mean()})
    patterns=[]
    for raw in [False,True]:
        for all_ec in [False,True]:
            for candidate in [False,True]:
                n=int((paired.raw_cards.eq(raw)&paired.all_ec.eq(all_ec)&paired.candidate_ec.eq(candidate)).sum())
                patterns.append({'raw_cards':raw,'all_ec':all_ec,'candidate_ec':candidate,
                    'claims':n,'all_claims':len(paired),'fraction':n/len(paired)})
    bridge=cases.assign(_delta=cases.candidate_ec-cases.historical_bace)
    reference=pd.DataFrame([{'comparison':'current_candidate_minus_historical_bace',
        'interpretation':'Common evidence-unit interface and current run versus historical atomic-claim interface; not a pure evidence effect.',
        **boot.mean(bridge,'_delta')}])
    return {'paired_claims':paired,'paired_cases':cases,'scores':pd.DataFrame(scores),
        'pooled':pd.DataFrame(pooled),'effects':pd.DataFrame(effects),
        'transitions':pd.DataFrame(transitions),'company_effects':pd.DataFrame(company),
        'support_patterns':pd.DataFrame(patterns),'historical_reference':reference,
        'excluded_disclosures':frame.loc[~frame.generation_case_id.isin(cases.generation_case_id),
            ['generation_case_id','company_id']].drop_duplicates()}

def review_packet(paired,plan):
    """A packet contains no model verdicts and no filled reviewer labels."""
    by_case={c['generation_case_id']:c for c in plan['cases']}
    chosen=[]
    for pattern,group in paired.groupby(list(CONDITIONS)):
        group=group.assign(_rank=[rank('review',c+'|'+d) for c,d in zip(group.generation_case_id,group.dc_id)]).sort_values('_rank')
        first=group.drop_duplicates('company_id').head(20)
        selected=pd.concat([first,group.loc[~group.index.isin(first.index)].head(max(0,20-len(first)))])
        for row in selected.to_dict('records'):
            chosen.append((row,pattern,len(group),len(selected)))
    packets,key,annotations=[],[],[]
    for row,pattern,population,sample in chosen:
        cid,dc=row['generation_case_id'],row['dc_id']
        case=read(ROOT/by_case[cid]['cache_path'])
        saved=next(x for x in case['dc_jobs'] if x['job']['dc_id']==dc)
        rid='review_'+rank('review_id',cid+'|'+dc)[:16]
        packets.append({'review_id':rid,'generation_case_id':cid,'dc_id':dc,
            'context_metadata':saved['job']['dynamic_input']['context_metadata'],
            'dc_claim':saved['job']['dynamic_input']['dc_claim'],
            'raw_cards':case['raw_units'],'all_ec':case['all_ec_input'],
            'candidate_ec':saved['job']['dynamic_input']['ec_claims'],
            'ec_original_by_alias':saved['job']['ec_original_by_alias'],
            'pre_dedup_occurrences':list(rows(ROOT/case['lineage_paths']['ec_occurrences'])),
            'source_paths':case['lineage_paths']})
        key.append({'review_id':rid,**dict(zip(CONDITIONS,pattern)),
            'stratum_population':population,'stratum_sample':sample,
            'selection':'Fixed hash, distinct companies preferred; not simple random sampling within the pattern.'})
        annotations.append({'review_id':rid,**{c:'' for c in ['reviewer_id','raw_support',
            'all_ec_support','candidate_support','temporal_rule','inference_rule',
            'evidence_locator','adjudication_notes']}})
    directory=DEST/'review'
    directory.mkdir(parents=True,exist_ok=True)
    annotation_path=directory/'annotations.csv'
    if annotation_path.exists():
        existing=pd.read_csv(annotation_path,dtype=str).fillna('')
        assert set(existing.review_id)=={p['review_id'] for p in packets}, 'Review cohort changed'
        if existing.drop(columns='review_id').ne('').any().any():
            save_json(directory/'status.json',{'status':'ANNOTATIONS_PRESENT_NOT_ADJUDICATED',
                'prepared':len(packets),'completed_independent_annotations':None,
                'scope':'Existing reviewer entries preserved; independent completion has not been verified.'})
            return
    with (directory/'verdict_blinded_packet.jsonl').open('w') as stream:
        for packet in sorted(packets,key=lambda p:p['review_id']):stream.write(json.dumps(packet,ensure_ascii=False)+'\n')
    pd.DataFrame(key).to_csv(directory/'analyst_key.csv',index=False)
    pd.DataFrame(annotations).to_csv(directory/'annotations.csv',index=False)
    save_json(directory/'status.json',{'status':'PREPARED_NOT_ANNOTATED','prepared':len(packets),
        'completed_independent_annotations':0,'scope':'Illustrative source review; no validated error prevalence.'})

def sampling_sensitivity(cases, plan):
    """Frame-composition sensitivity, with missing strata explicitly unrepresented."""
    metadata=pd.DataFrame([{k:c[k] for k in ['generation_case_id','company_id','company_name',
        'topic','year','task','stratum_disclosures','sampling_weight']} for c in plan['cases']])
    coverage=metadata.assign(analysed=metadata.generation_case_id.isin(cases.generation_case_id))
    joined=cases.merge(metadata[['generation_case_id','sampling_weight']],on='generation_case_id',validate='one_to_one')
    represented=int(joined.sampling_weight.sum())
    frame_count=plan['sampling']['frame_disclosures']
    estimates=[]
    comparisons=[(c,joined[c]) for c in CONDITIONS]+[
        (f'{left}_minus_{right}',joined[left]-joined[right]) for left,right in CONTRASTS]
    for name,values in comparisons:
        estimates.append({'quantity':name,'estimate':float((values*joined.sampling_weight).sum()/represented),
            'represented_frame_disclosures':represented,'unrepresented_frame_disclosures':frame_count-represented,
            'analysed_disclosures':len(joined),
            'interpretation':'Inverse-inclusion-weighted descriptive mean over represented company-topic strata; no finite-population confidence interval.'})
    return {'sampling_coverage':coverage,'frame_composition_sensitivity':pd.DataFrame(estimates)}

def load_analysis():
    DEST.mkdir(parents=True,exist_ok=True)
    if not (RUN/'status.json').exists():
        result={'ready':False,'status':'NOT_STARTED'}
        save_json(DEST/'readiness.json',result);return result
    status=read(RUN/'status.json')
    ready=status['mode']=='full' and status['status']=='COMPLETED' and all(
        x['recorded']==x['planned'] for x in status['conditions'].values())
    if not ready:
        result={'ready':False,'status':status['status'],'phase':status['mode']}
        save_json(DEST/'readiness.json',result);return result
    audit=read(RUN/'qa/completed_run_audit.json')
    assert audit['status']=='PASS'
    plan=read(EXP/'plan.json')
    freeze=read(EXP/'freeze.json')
    for name,digest in freeze['files'].items():assert sha(ROOT/name)==digest,name
    input_rows=[]
    for case in plan['cases']:
        cache=read(ROOT/case['cache_path'])
        assert sha(ROOT/case['cache_path'])==case['cache_sha256']
        for saved in cache['dc_jobs']:
            job=saved['job']
            input_rows.append({k:case[k] for k in ['generation_case_id','company_id','company_name']} |
                {'dc_id':job['dc_id'],'historical_bace':bool(saved['original_support_sets']),
                 'candidate_count':len(job['candidate_ec_aliases']),'all_ec_count':len(cache['all_ec_input']),
                 'raw_card_count':len(cache['raw_units'])})
    frame=pd.DataFrame(input_rows).set_index(['generation_case_id','dc_id'])
    failures=[]
    for item in audit['conditions']:
        condition=item['condition']
        path=RUN/'runs'/condition/'calls.jsonl'
        assert sha(path)==item['calls_sha256']
        values={}
        for record in rows(path):
            key=record['generation_case_id'],record['dc_id']
            assert key in frame.index and key not in values
            values[key]=bool(record['restored_output']['support_sets']) if record['call_status']=='success' else None
            if record['call_status']!='success':
                failures.append({'condition':condition,'generation_case_id':key[0],'dc_id':key[1],
                    'status':record['call_status'],'validation_error':record.get('validation_error'),
                    'error_type':record.get('error_type'),'source':str(path.relative_to(ROOT))})
        assert set(values)==set(frame.index)
        frame[condition]=pd.Series(values)
    frame=frame.reset_index()
    results=calculate(frame)
    results.update(sampling_sensitivity(results['paired_cases'],plan))
    for name,table in results.items():write_table(name,table)
    write_table('failed_records',pd.DataFrame(failures,columns=['condition','generation_case_id',
        'dc_id','status','validation_error','error_type','source']))
    write_table('execution_completeness',pd.DataFrame([{'condition':c,**v} for c,v in status['conditions'].items()]))
    review_packet(results['paired_claims'],plan)
    save_json(DEST/'provenance.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'plan_sha256':sha(EXP/'plan.json'),'freeze_sha256':sha(EXP/'freeze.json'),
        'raw_audit_sha256':sha(RUN/'qa/completed_run_audit.json'),'analysis_code_sha256':sha(__file__),
        'bootstrap':{'draws':2000,'seed':20260921,'resampling_unit':'company'},
        'primary_unit':'equally weighted complete sampled disclosure','independent_human_validation':False,
        'sampling':plan['sampling'],'reused_records':plan['reuse']['records'],
        'selection_ledger_sha256':sha(EXP/'selection.csv'),
        'interval_scope':'Observed company-bundle resampling; not exact finite-population sampling uncertainty or model-run variance.'})
    result={'ready':True,'status':'AUTOMATED_STATISTICS_COMPLETE_INDEPENDENT_REVIEW_PENDING'}
    save_json(DEST/'readiness.json',result)
    return {**result,**results}

if __name__=='__main__':
    result=load_analysis()
    print(result['status'])
    if result['ready']:print(result['scores'].to_string(index=False))
