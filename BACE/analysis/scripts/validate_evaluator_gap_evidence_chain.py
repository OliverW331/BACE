"""Verify unequal disclosure weights, bidirectional changes and whole-case exclusion."""
from pathlib import Path
import argparse
import json
import sys

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
sys.dont_write_bytecode=True
import numpy as np
import pandas as pd
from evaluator_gap_evidence_chain import calculate, DEST, EXP, RUN, CONDITIONS, CONTRASTS
from evaluator_gap_analysis import save_json,sha

def main():
    data=[]
    def add(company,case,triples):
        for i,(raw,all_ec,candidate) in enumerate(triples):
            data.append({'company_id':company,'company_name':company,'generation_case_id':case,
                'dc_id':f'{case}_{i}','raw_cards':raw,'all_ec':all_ec,'candidate_ec':candidate,
                'historical_bace':False})
    add('a','a1',[(True,False,False),(True,True,True)])
    add('a','a2',[(False,True,False)])
    add('b','b1',[(True,False,False)]*4)
    add('b','b2',[(True,True,None),(False,False,True)])
    result=calculate(pd.DataFrame(data))
    assert len(result['paired_claims'])==7 and len(result['paired_cases'])==3
    assert set(result['excluded_disclosures'].generation_case_id)=={'b2'}
    scores=result['scores'].set_index('condition')
    assert np.allclose(scores.loc[['raw_cards','all_ec','candidate_ec'],'estimate'],[2/3,1/2,1/6])
    pooled=result['pooled'].set_index('condition')
    assert np.isclose(pooled.loc['raw_cards','support_rate'],6/7)
    effects=result['effects'].set_index('contrast')
    assert np.allclose(effects.loc[['raw_cards_minus_all_ec','all_ec_minus_candidate_ec',
        'raw_cards_minus_candidate_ec'],'estimate'],[1/6,1/3,1/2])
    assert np.allclose(effects.loc['raw_cards_minus_all_ec',['low','high']].astype(float),[-.25,1])
    matrix=result['transitions'].loc[lambda f:f.contrast.eq('raw_cards_minus_all_ec')]
    assert matrix.claims.sum()==7
    assert matrix.loc[~matrix.reference_supported&matrix.left_supported,'claims'].item()==5
    assert matrix.loc[matrix.reference_supported&~matrix.left_supported,'claims'].item()==1
    assert result['support_patterns'].claims.sum()==7
    try:calculate(pd.DataFrame(data+[data[0]]))
    except AssertionError:pass
    else:raise AssertionError('Duplicate claim IDs were accepted')
    save_json(DEST/'qa/statistical_checks.json',{'status':'PASS','fixture_only':True,
        'checks':['Unequal disclosure weights versus pooled claims','Three paired contrasts',
                  'Both transition directions','Whole-disclosure missingness','Duplicate rejection'],
        'validator_sha256':sha(__file__)})
    print('PASS: evidence-chain weighting, transitions, missingness and duplicate checks.')

def completed():
    read=lambda p:json.loads(p.read_text())
    assert read(DEST/'readiness.json')['ready']
    audit=read(RUN/'qa/completed_run_audit.json')
    assert audit['status']=='PASS'
    for item in audit['conditions']:
        assert sha(RUN/'runs'/item['condition']/'calls.jsonl')==item['calls_sha256']
    plan=read(EXP/'plan.json')
    expected={c['generation_case_id']:c for c in plan['cases']}
    tables=DEST/'tables'
    claims=pd.read_csv(tables/'paired_claims.csv')
    cases=pd.read_csv(tables/'paired_cases.csv')
    assert not claims.duplicated(['generation_case_id','dc_id']).any()
    assert claims[list(CONDITIONS)].notna().all().all()
    for cid,group in claims.groupby('generation_case_id'):
        assert len(group)==expected[cid]['claims']
    assert not claims.loc[claims.candidate_count.eq(0),'candidate_ec'].any()
    failures=pd.read_csv(tables/'failed_records.csv')
    assert not set(failures.generation_case_id)&set(cases.generation_case_id)
    rates=claims.groupby(['company_id','generation_case_id'])[list(CONDITIONS)].mean().reset_index()
    scores=pd.read_csv(tables/'scores.csv').set_index('condition')
    effects=pd.read_csv(tables/'effects.csv').set_index('contrast')
    companies=sorted(rates.company_id.unique())
    rng=np.random.default_rng(20260921)
    draws=rng.integers(0,len(companies),size=(2000,len(companies)))
    weights=np.array([np.bincount(d,minlength=len(companies)) for d in draws])
    denominators=np.array([rates.company_id.eq(c).sum() for c in companies])
    def check(values,row):
        sums=np.array([values.loc[rates.company_id.eq(c)].sum() for c in companies])
        reps=(weights@sums)/(weights@denominators)
        assert np.allclose([values.mean(),*np.quantile(reps,[.025,.975])],
            row[['estimate','low','high']].astype(float),atol=1e-12)
    for condition in CONDITIONS:check(rates[condition],scores.loc[condition])
    transitions=pd.read_csv(tables/'transitions.csv')
    for left,right in CONTRASTS:
        name=f'{left}_minus_{right}'
        check(rates[left]-rates[right],effects.loc[name])
        for row in transitions.loc[transitions.contrast.eq(name)].itertuples():
            mask=claims[left].eq(row.left_supported)&claims[right].eq(row.reference_supported)
            assert mask.sum()==row.claims
            den=claims[right].eq(row.reference_supported).sum()
            assert den==row.reference_status_denominator
            assert np.isclose(row.fraction_all_claims,row.claims/len(claims))
            if den:assert np.isclose(row.fraction_reference_status,row.claims/den)
    patterns=pd.read_csv(tables/'support_patterns.csv')
    assert patterns.claims.sum()==len(claims)
    for row in patterns.itertuples():
        assert (claims.raw_cards.eq(row.raw_cards)&claims.all_ec.eq(row.all_ec)&claims.candidate_ec.eq(row.candidate_ec)).sum()==row.claims
    provenance=read(DEST/'provenance.json')
    assert provenance['plan_sha256']==sha(EXP/'plan.json')
    assert provenance['freeze_sha256']==sha(EXP/'freeze.json')
    save_json(DEST/'qa/final_statistics.json',{'status':'PASS','paired_disclosures':len(cases),
        'paired_claims':len(claims),'independent_score_and_effect_intervals':True,
        'fixed_denominators_and_transitions':True,'all_eight_patterns_verified':True,
        'independent_human_validation':False,'validator_sha256':sha(__file__)})
    print('PASS: completed evidence-chain scores, intervals, denominators, transitions and patterns.')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--completed',action='store_true')
    args=parser.parse_args()
    completed() if args.completed else main()
