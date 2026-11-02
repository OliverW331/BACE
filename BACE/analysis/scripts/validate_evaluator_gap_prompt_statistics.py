"""Test fixed-denominator pairing, both flip directions and repeat missingness."""
import os
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import pandas as pd
import numpy as np
from evaluator_gap_prompt_sensitivity import compute_paired, DEST
from evaluator_gap_analysis import save_json

def main():
    frame=pd.DataFrame([
        ['a','A','a1','d1',True,False,True,True],
        ['a','A','a1','d2',False,True,False,False],
        ['a','A','a2','d3',True,None,True,True],
        ['a','A','a2','d4',False,False,True,False],
        ['b','B','b1','d5',False,True,False,None],
    ],columns=['company_id','company_name','generation_case_id','dc_id','original',
               'ragas_style','ragchecker_style','original_repeat'])
    r=compute_paired(frame)
    assert set(r['paired_cases'].generation_case_id)=={'a1','b1'}
    assert len(r['paired_claims'])==3
    scores=r['scores'].set_index('condition')
    assert scores.loc['original','estimate']==.25
    assert scores.loc['ragas_style','estimate']==.75
    assert r['effects'].set_index('condition').loc['ragas_style','estimate']==.5
    pooled=r['pooled'].set_index('condition')
    assert np.isclose(pooled.loc['ragas_style','support_rate'],2/3)
    t=r['transitions'].loc[lambda d:d.condition.eq('ragas_style')]
    assert t.loc[~t.original_supported&t.new_supported,'claims'].iloc[0]==2
    assert t.loc[t.original_supported&~t.new_supported,'claims'].iloc[0]==1
    assert t.claims.sum()==3
    assert t.loc[t.original_supported&~t.new_supported,'fraction_original_status'].iloc[0]==1
    repeat=r['repeat_effects'].set_index('condition')
    assert repeat.loc['original_repeat','disclosures']==1
    assert repeat.loc['original_repeat','estimate']==0
    assert repeat.loc['original_repeat','undefined_draws']>0
    overlap_frame=frame.copy()
    overlap_frame.loc[overlap_frame.dc_id.eq('d1'),'ragchecker_style']=False
    overlap_frame.loc[overlap_frame.dc_id.eq('d2'),'ragchecker_style']=True
    directions=compute_paired(overlap_frame)['flip_overlap_by_direction'].set_index('direction')
    additions=directions.loc['unsupported_to_supported']
    removals=directions.loc['supported_to_unsupported']
    assert additions.both_flips==1 and additions.union_flips==2 and additions.ragas_only==1
    assert additions.shared_fraction_of_union==.5 and additions.original_status_denominator==2
    assert removals.both_flips==1 and removals.union_flips==1 and removals.shared_fraction_of_union==1
    unchanged=compute_paired(frame.assign(ragas_style=frame.original,ragchecker_style=frame.original))
    assert unchanged['flip_overlap_by_direction'].union_flips.eq(0).all()
    assert unchanged['flip_overlap_by_direction'].shared_fraction_of_union.isna().all()
    try:
        compute_paired(frame.assign(ragas_style=None))
    except ValueError:
        pass
    else:
        raise AssertionError('Empty paired cohort should not produce a zero score')
    try:
        compute_paired(pd.concat([frame,frame.iloc[:1]]))
    except AssertionError:
        pass
    else:
        raise AssertionError('Duplicate claims were accepted')
    save_json(DEST/'qa/statistical_checks.json',{'status':'PASS','synthetic_fixture':True,
        'checks':['Whole disclosure excluded after one failed claim',
                  'Unbalanced macro and pooled estimates differ as expected',
                  'Both flip directions retained with explicit original-status denominators',
                  'Shared additions and removals retain distinct intersection/union counts',
                  'No flips leaves the shared fraction undefined rather than zero',
                  'Repeat-control missingness and undefined subgroup resamples retained',
                  'No complete cohort fails instead of returning zero', 'Duplicate claims rejected'],
        'actual_experiment_results':False})
    print('PASS: prompt-sensitivity pairing, denominators, transitions and repeat-control checks.')

if __name__=='__main__':main()
