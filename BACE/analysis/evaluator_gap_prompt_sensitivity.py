"""Read saved prompt-sensitivity runs; never import an evaluator or call an API."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from evaluator_gap_analysis import ROOT, OUT, ClusterBootstrap, sha, save_json

EXP = ROOT / 'BACE/experiments/prompt_sensitivity_v1'
RUN = ROOT / 'BACE/results/prompt_sensitivity_v1'
DEST = OUT / 'prompt_sensitivity'
VARIANTS = ('ragas_style', 'ragchecker_style')
LABELS = {'original': 'Original BACE', 'ragas_style': 'BACE–RAGAS-style',
          'ragchecker_style': 'BACE–RAGChecker-style', 'original_repeat': 'Original BACE repeat'}

def json_rows(path):
    with Path(path).open() as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def digest_json(value):
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(text.encode()).hexdigest()

def table(name, frame):
    (DEST / 'tables').mkdir(parents=True, exist_ok=True)
    frame.to_csv(DEST / 'tables' / f'{name}.csv', index=False)
    return frame

def transition_rows(frame, condition):
    original = frame.original.astype(bool)
    changed = frame[condition].astype(bool)
    counts = []
    for old in (True, False):
        denominator = int(original.eq(old).sum())
        for new in (True, False):
            n = int((original.eq(old) & changed.eq(new)).sum())
            counts.append({'condition': condition, 'original_supported': old,
                           'new_supported': new, 'claims': n, 'all_claims': len(frame),
                           'original_status_denominator': denominator,
                           'fraction_all_claims': n / len(frame),
                           'fraction_original_status': n/denominator if denominator else np.nan})
    return counts

def compute_paired(frame):
    """Exclude whole incomplete disclosures; preserve fixed original denominators."""
    assert not frame.duplicated(['generation_case_id','dc_id']).any()
    required = ['original', *VARIANTS]
    available = frame.assign(_complete=frame[required].notna().all(axis=1))
    complete = available.groupby('generation_case_id')._complete.all()
    paired = frame.loc[frame.generation_case_id.isin(complete[complete].index)].copy()
    if paired.empty:
        raise ValueError('No complete three-condition disclosures')
    for c in required:
        paired[c] = paired[c].astype(bool)
    case = paired.groupby(['company_id', 'company_name', 'generation_case_id']).agg(
        claims=('dc_id','size'), original=('original','mean'),
        ragas_style=('ragas_style','mean'), ragchecker_style=('ragchecker_style','mean')).reset_index()
    boot = ClusterBootstrap(case.company_id)
    scores, effects, pooled = [], [], []
    for condition in required:
        scores.append({'condition': condition, 'label': LABELS[condition],
                       'disclosures': len(case), 'claims': len(paired), **boot.mean(case, condition)})
        pooled.append({'condition': condition, 'supported': int(paired[condition].sum()),
                       'claims': len(paired), 'support_rate': paired[condition].mean()})
    transitions, company = [], []
    for condition in VARIANTS:
        case[f'{condition}_delta'] = case[condition] - case.original
        effects.append({'condition': condition, 'label': LABELS[condition],
                        'disclosures': len(case), 'claims': len(paired),
                        **boot.mean(case, f'{condition}_delta')})
        transitions.extend(transition_rows(paired, condition))
        for (cid, name), group in case.groupby(['company_id','company_name']):
            company.append({'condition': condition, 'company_id': cid, 'company_name': name,
                            'disclosures': len(group), 'claims': int(group.claims.sum()),
                            'original_rate': group.original.mean(), 'new_rate': group[condition].mean(),
                            'delta': group[f'{condition}_delta'].mean()})
    a = paired.ragas_style.ne(paired.original)
    b = paired.ragchecker_style.ne(paired.original)
    overlap = pd.DataFrame([{'ragas_flipped': x, 'ragchecker_flipped': y,
                  'claims': int((a.eq(x)&b.eq(y)).sum()), 'denominator': len(paired)}
                 for x in (False,True) for y in (False,True)])
    both = a & b
    assert paired.loc[both, 'ragas_style'].eq(paired.loc[both, 'ragchecker_style']).all()
    directional_overlap=[]
    for direction,old in [('unsupported_to_supported',False),('supported_to_unsupported',True)]:
        scope=paired.original.eq(old)
        shared=int((scope&a&b).sum())
        union=int((scope&(a|b)).sum())
        directional_overlap.append({'direction':direction,
            'original_status_denominator':int(scope.sum()),
            'ragas_flips':int((scope&a).sum()),'ragchecker_flips':int((scope&b).sum()),
            'both_flips':shared,'ragas_only':int((scope&a&~b).sum()),
            'ragchecker_only':int((scope&~a&b).sum()),'union_flips':union,
            'shared_fraction_of_union':shared/union if union else np.nan})
    repeat_complete = paired.assign(_valid=paired.original_repeat.notna()).groupby('generation_case_id')._valid.all()
    repeat = paired.loc[paired.generation_case_id.isin(repeat_complete[repeat_complete].index)].copy()
    repeat_scores, repeat_flips = [], []
    if not repeat.empty:
        repeat['original_repeat'] = repeat.original_repeat.astype(bool)
        repeat_case = repeat.groupby(['company_id','generation_case_id'])[
            ['original',*VARIANTS,'original_repeat']].mean().reset_index()
        for condition in (*VARIANTS,'original_repeat'):
            values = repeat_case.assign(_difference=repeat_case[condition]-repeat_case.original)
            repeat_scores.append({'condition': condition, 'disclosures': len(values), 'claims': len(repeat),
                                  **boot.mean(values, '_difference')})
            repeat_flips.extend(transition_rows(repeat, condition))
    return {'paired_claims': paired, 'paired_cases': case, 'scores': pd.DataFrame(scores),
            'effects': pd.DataFrame(effects), 'pooled': pd.DataFrame(pooled),
            'transitions': pd.DataFrame(transitions), 'company_effects': pd.DataFrame(company),
            'flip_overlap': overlap, 'flip_overlap_by_direction':pd.DataFrame(directional_overlap),
            'repeat_effects': pd.DataFrame(repeat_scores),
            'repeat_transitions': pd.DataFrame(repeat_flips)}

def load_analysis():
    """Readiness is explicit: an active or partially scheduled run yields no score."""
    DEST.mkdir(parents=True, exist_ok=True)
    if not (EXP/'plan.json').exists():
        return {'ready': False, 'status': 'PREPARING', 'completeness': pd.DataFrame()}
    plan = json.loads((EXP/'plan.json').read_text())
    status = json.loads((RUN/'status.json').read_text()) if (RUN/'status.json').exists() else {}
    planned = {c:plan['counts']['claims_per_full_condition'] for c in VARIANTS}
    planned['original_repeat'] = plan['counts']['repeat_claims']
    completeness = pd.DataFrame([{'condition': c, 'planned_claims': n,
        'recorded_claims': status.get('conditions',{}).get(c,{}).get('recorded',0),
        'valid_claims': status.get('conditions',{}).get(c,{}).get('valid',0),
        'failed_claims': status.get('conditions',{}).get(c,{}).get('failed',0)} for c,n in planned.items()])
    completeness['pending_claims'] = completeness.planned_claims-completeness.recorded_claims
    table('execution_completeness', completeness)
    ready = (status.get('mode')=='full' and status.get('status')=='COMPLETED'
             and completeness.pending_claims.eq(0).all())
    readiness = {'ready': bool(ready), 'status': status.get('status','PREPARED_NOT_RUN'),
                 'phase': status.get('mode'), 'plan_sha256': sha(EXP/'plan.json'),
                 'run_status_updated_at_utc': status.get('updated_at_utc'),
                 'freeze_sha256': sha(EXP/'freeze.json'),
                 'reason': 'All scheduled claims recorded; whole-disclosure complete-case analysis.' if ready
                 else 'Final primary scores withheld until full scheduling is terminal and all planned jobs are recorded.'}
    save_json(DEST/'readiness.json', readiness)
    if not ready:
        return {**readiness, 'completeness': completeness, 'plan': plan}
    frozen = json.loads((EXP/'freeze.json').read_text())
    frozen_hash = sha(EXP/'freeze.json')
    for path, expected in frozen['files'].items():
        assert sha(ROOT/path)==expected, path
    input_rows = []
    for case in plan['cases']:
        for saved in json_rows(ROOT/case['cache_path']):
            job=saved['job']
            input_rows.append({'generation_case_id':job['generation_case_id'], 'dc_id':job['dc_id'],
                'company_id':saved['company_id'], 'company_name':saved['company_name'],
                'original':bool(saved['original_support_sets']),
                'original_sets':json.dumps(saved['original_support_sets'],ensure_ascii=False),
                'input_hash':job['job_input_hash'], 'candidate_count':len(job['candidate_ec_aliases']),
                'repeat_selected':case['repeat_control']})
    frame = pd.DataFrame(input_rows)
    assert not frame.duplicated(['generation_case_id','dc_id']).any()
    source_hashes = {}
    failures = []
    failure_columns = ['condition', 'generation_case_id', 'dc_id', 'call_id', 'call_status',
        'output_attempts', 'network_retries', 'validation_error', 'error_type', 'error_message',
        'http_status', 'finished_at_utc', 'source_calls_path', 'record_sha256']
    for condition in (*VARIANTS,'original_repeat'):
        path=RUN/'runs'/condition/'calls.jsonl'
        source_hashes[str(path.relative_to(ROOT))]=sha(path)
        records=[]
        for record in json_rows(path):
            assert digest_json(record['dynamic_input'])==record['call_identity']['job_input_hash']
            assert record['prompt_sensitivity']['freeze_sha256']==frozen_hash
            assert record['request_parameters']==plan['model']['request_parameters']
            assert record['deployment_name']==plan['deployment_name']
            valid=record['call_status']=='success'
            sets=record['restored_output']['support_sets'] if valid else None
            if not valid:
                attempts=record.get('attempts', [])
                failures.append({'condition':condition,
                    **{k:record.get(k) for k in ['generation_case_id','dc_id','call_id','call_status',
                        'validation_error','error_type','error_message','http_status','finished_at_utc']},
                    'output_attempts':len(attempts),
                    'network_retries':sum(int(a.get('network_retries') or 0) for a in attempts),
                    'source_calls_path':str(path.relative_to(ROOT)),
                    'record_sha256':digest_json(record)})
            records.append({'generation_case_id':record['generation_case_id'],'dc_id':record['dc_id'],
                condition:bool(sets) if valid else None, condition+'_status':record['call_status'],
                condition+'_sets':json.dumps(sets,ensure_ascii=False),
                condition+'_input_hash':record['call_identity']['job_input_hash']})
        rec=pd.DataFrame(records)
        assert not rec.duplicated(['generation_case_id','dc_id']).any()
        eligible = frame.loc[frame.repeat_selected] if condition=='original_repeat' else frame
        assert set(zip(rec.generation_case_id,rec.dc_id)) == set(zip(eligible.generation_case_id,eligible.dc_id))
        frame=frame.merge(rec,on=['generation_case_id','dc_id'],how='left',validate='one_to_one')
        present=frame[condition+'_input_hash'].notna()
        assert frame.loc[present,'input_hash'].eq(frame.loc[present,condition+'_input_hash']).all()
        assert len(rec)==planned[condition]
        assert int(rec[condition].notna().sum())==int(completeness.loc[completeness.condition.eq(condition),'valid_claims'].iloc[0])
    results=compute_paired(frame)
    results['failed_records']=pd.DataFrame(failures,columns=failure_columns)
    for name, value in results.items():
        table(name,value)
    completion=[]
    for condition in (*VARIANTS,'original_repeat'):
        eligible=frame.loc[frame.repeat_selected] if condition=='original_repeat' else frame
        complete=eligible.groupby('generation_case_id')[condition].apply(lambda v:v.notna().all())
        completion.append({'condition':condition,'planned_disclosures':len(complete),
                           'complete_disclosures':int(complete.sum()),'incomplete_disclosures':int((~complete).sum())})
    disclosure_completeness=table('disclosure_completeness',pd.DataFrame(completion))
    excluded=frame.loc[~frame.generation_case_id.isin(results['paired_cases'].generation_case_id),
        ['generation_case_id','dc_id',*[c+'_status' for c in VARIANTS]]]
    table('excluded_claims_in_incomplete_disclosures',excluded)
    examples=select_examples(results['paired_claims'],plan)
    save_json(DEST/'examples.json',examples)
    save_json(DEST/'provenance.json',{'computed_at_utc':datetime.now(timezone.utc).isoformat(),
        'plan_sha256':sha(EXP/'plan.json'),
        'freeze_sha256':sha(EXP/'freeze.json'),'source_calls':source_hashes,'code_sha256':sha(__file__),
        'plotting_code_sha256':sha(Path(__file__).with_name('evaluator_gap_prompt_figures.py')),
        'shared_plotting_code_sha256':sha(Path(__file__).with_name('evaluator_gap_figures.py')),
        'source_files_verified':len(frozen['files']),'bootstrap':{'draws':2000,'seed':20260921,'unit':'company'},
        'tables':{p.name:sha(p) for p in sorted((DEST/'tables').glob('*.csv'))},
        'model_calls_from_analysis':0,'human_validation_completed':False})
    return {**readiness,**results,'completeness':completeness,
            'disclosure_completeness':disclosure_completeness,'examples':examples,'plan':plan}

def select_examples(frame,plan):
    selected={}
    for condition in VARIANTS:
        for direction,old,new in [('unsupported_to_supported',False,True),('supported_to_unsupported',True,False)]:
            subset=frame.loc[frame.original.eq(old)&frame[condition].eq(new)].copy()
            subset['_rank']=[hashlib.sha256(f'20261001|example|{condition}|{direction}|{cid}|{dc}'.encode()).hexdigest()
                             for cid,dc in zip(subset.generation_case_id,subset.dc_id)]
            subset=subset.sort_values('_rank')
            diverse=subset.drop_duplicates('company_id').head(3)
            if len(diverse)<3:
                diverse=pd.concat([diverse,subset.loc[~subset.index.isin(diverse.index)].head(3-len(diverse))])
            for row in diverse.to_dict('records'):
                key=row['generation_case_id'],row['dc_id']
                selected.setdefault(key,{'selection_reasons':[],'row':row})['selection_reasons'].append(condition+'/'+direction)
    examples=[]
    for case in plan['cases']:
        cid=case['generation_case_id']
        if not any(key[0]==cid for key in selected):
            continue
        for saved in json_rows(ROOT/case['cache_path']):
            key=cid,saved['job']['dc_id']
            if key in selected:
                chosen=selected[key]
                examples.append({'generation_case_id':cid,'dc_id':key[1],
                    'input_cache':{'path':case['cache_path'],'sha256':case['cache_sha256']},
                    'selection_reasons':chosen['selection_reasons'],
                    'dynamic_input':saved['job']['dynamic_input'],
                    'ec_original_by_alias':saved['job']['ec_original_by_alias'],
                    'original_support_sets':saved['original_support_sets'],
                    **{c+'_support_sets':json.loads(chosen['row'][c+'_sets']) for c in VARIANTS},
                    'interpretation':'Illustrative automated disagreement; no independent correctness label.'})
    return {'selection':'Fixed hash ranking, up to three per variant/direction, distinct companies preferred.',
            'examples':examples,'human_validation':False}
