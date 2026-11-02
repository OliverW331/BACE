"""Verify the complete prompt analysis against its fixed cohort and raw-call audit."""
from pathlib import Path
import json
import sys

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
sys.dont_write_bytecode=True
import numpy as np
import pandas as pd
from evaluator_gap_analysis import ROOT,sha,save_json
from evaluator_gap_prompt_sensitivity import DEST,EXP,RUN,VARIANTS,load_analysis

def main():
    readiness=json.loads((DEST/'readiness.json').read_text())
    assert readiness['ready'], 'No final prompt results to validate'
    audit=json.loads((RUN/'qa/completed_run_audit.json').read_text())
    assert audit['status']=='PASS' and audit['all_planned_jobs_recorded']
    for condition in audit['conditions']:
        path=RUN/'runs'/condition['condition']/'calls.jsonl'
        assert sha(path)==condition['calls_sha256']
    plan=json.loads((EXP/'plan.json').read_text())
    provenance=json.loads((DEST/'provenance.json').read_text())
    assert provenance['plan_sha256']==sha(EXP/'plan.json')
    assert provenance['freeze_sha256']==sha(EXP/'freeze.json')
    tables=DEST/'tables'
    before={p.name:sha(p) for p in tables.glob('*.csv')}
    # Re-running the saved-input calculation must reproduce every table and
    # deterministic example selection; it never creates further model calls.
    before_examples=sha(DEST/'examples.json')
    result=load_analysis()
    assert before=={p.name:sha(p) for p in tables.glob('*.csv')}
    assert before_examples==sha(DEST/'examples.json')
    paired=result['paired_claims']
    cases=result['paired_cases']
    expected={c['generation_case_id']:c for c in plan['cases']}
    assert paired.generation_case_id.nunique()==len(cases)
    assert not paired.duplicated(['generation_case_id','dc_id']).any()
    for cid, group in paired.groupby('generation_case_id'):
        assert len(group)==expected[cid]['claims'], 'Denominator shrank inside a disclosure'
        assert group[['original',*VARIANTS]].notna().all().all()
    zero=paired.candidate_count.eq(0)
    assert not paired.loc[zero,['original',*VARIANTS]].any().any()
    failures=result['failed_records']
    for row in result['completeness'].itertuples():
        assert int(failures.condition.eq(row.condition).sum())==row.failed_claims
    failed_main=failures.loc[failures.condition.isin(VARIANTS)]
    assert not set(failed_main.generation_case_id)&set(cases.generation_case_id)
    scores=result['scores'].set_index('condition')
    effects=result['effects'].set_index('condition')
    pooled=result['pooled'].set_index('condition')
    independent={}
    for condition in ['original',*VARIANTS]:
        # Count supported claims and divide by the frozen denominator for each
        # disclosure, independent of the cached per-disclosure means.
        sums=paired.groupby('generation_case_id')[condition].sum()
        rates={cid:float(n)/expected[cid]['claims'] for cid,n in sums.items()}
        independent[condition]=rates
        assert np.isclose(scores.loc[condition,'estimate'],np.mean(list(rates.values())))
        assert np.isclose(pooled.loc[condition,'support_rate'],paired[condition].sum()/len(paired))
    for condition in VARIANTS:
        delta=np.array([independent[condition][cid]-independent['original'][cid]
                        for cid in sorted(independent['original'])])
        assert np.isclose(effects.loc[condition,'estimate'],delta.mean())
        matrix=result['transitions'].loc[lambda f:f.condition.eq(condition)]
        assert matrix.claims.sum()==len(paired)
        for row in matrix.itertuples():
            mask=paired.original.eq(row.original_supported)&paired[condition].eq(row.new_supported)
            assert mask.sum()==row.claims
            den=paired.original.eq(row.original_supported).sum()
            assert den==row.original_status_denominator
            assert np.isclose(row.fraction_all_claims,row.claims/len(paired))
            if den:assert np.isclose(row.fraction_original_status,row.claims/den)
        # A separate company-count-weighted bootstrap verifies CI endpoints,
        # preserving the common random draws and disclosure weighting.
        cid_list=sorted(independent['original'])
        companies=sorted({expected[cid]['company_id'] for cid in cid_list})
        sums=np.array([sum(d for cid,d in zip(cid_list,delta) if expected[cid]['company_id']==co)
                       for co in companies])
        denominators=np.array([sum(expected[cid]['company_id']==co for cid in cid_list) for co in companies])
        rng=np.random.default_rng(20260921)
        draws=rng.integers(0,len(companies),size=(2000,len(companies)))
        weights=np.array([np.bincount(d,minlength=len(companies)) for d in draws])
        reps=(weights@sums)/(weights@denominators)
        lo,hi=np.quantile(reps,[.025,.975])
        assert np.allclose([lo,hi],effects.loc[condition,['low','high']].astype(float),atol=1e-12)
    company=result['company_effects']
    for condition in VARIANTS:
        f=company.loc[company.condition.eq(condition)]
        assert np.isclose(np.average(f.delta,weights=f.disclosures),effects.loc[condition,'estimate'])
    overlap=result['flip_overlap']
    assert overlap.claims.sum()==len(paired)
    directional=result['flip_overlap_by_direction'].set_index('direction')
    for direction,old in [('unsupported_to_supported',False),('supported_to_unsupported',True)]:
        row=directional.loc[direction]
        scope=paired.loc[paired.original.eq(old)]
        sets=[]
        for condition in VARIANTS:
            changed=scope.loc[scope[condition].ne(scope.original)]
            sets.append(set(zip(changed.generation_case_id,changed.dc_id)))
        left,right=sets
        assert row.original_status_denominator==len(scope)
        assert row.ragas_flips==len(left) and row.ragchecker_flips==len(right)
        assert row.both_flips==len(left&right) and row.union_flips==len(left|right)
        assert row.ragas_only==len(left-right) and row.ragchecker_only==len(right-left)
        if left|right:
            assert np.isclose(row.shared_fraction_of_union,len(left&right)/len(left|right))
        else:
            assert pd.isna(row.shared_fraction_of_union)
    repeat=result['repeat_effects']
    if not repeat.empty:
        assert repeat.disclosures.nunique()==1 and repeat.claims.nunique()==1
        assert repeat.disclosures.max()<=plan['counts']['repeat_disclosures']
    examples=result['examples']['examples']
    bykey=paired.set_index(['generation_case_id','dc_id'])
    for example in examples:
        row=bykey.loc[(example['generation_case_id'],example['dc_id'])]
        assert len(example['dynamic_input']['ec_claims'])==row.candidate_count
        aliases=example['ec_original_by_alias']
        allowed={aliases[e['ec_claim_id']] for e in example['dynamic_input']['ec_claims']}
        for condition in ['original',*VARIANTS]:
            sets=example[condition+'_support_sets']
            assert bool(sets)==bool(row[condition])
            assert all(set(s['ec_claim_ids'])<=allowed for s in sets)
    save_json(DEST/'qa/final_statistics.json',{'status':'PASS',
        'all_raw_call_hashes_match_completed_audit':True,'tables_byte_identical_on_reproduction':True,
        'example_selection_reproduced':True,'fixed_denominators_verified':True,
        'paired_disclosures':len(cases),'paired_claims':len(paired),
        'ci_verified_independently_with_company_multiplicities':True,
        'both_transition_directions_verified':True,'example_support_references_verified':True,
        'failure_details_reconcile_with_execution_counts':True,
        'directional_overlap_verified_with_claim_id_sets':True,
        'human_accuracy_validation':False,'validator_sha256':sha(__file__)})
    print('PASS: full prompt tables, fixed denominators, paired intervals, transitions, repeats and examples.')

if __name__=='__main__':main()
