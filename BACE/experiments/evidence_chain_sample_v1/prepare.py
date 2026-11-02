"""Freeze an outcome-independent 90-text amendment and reuse exact saved records."""
from collections import defaultdict, Counter
import csv
import hashlib
import importlib.metadata

from common import EXP, ROOT, BACE, RESULTS, read, write, rows, sha, now, rank, CONDITIONS

PARENT = BACE/'experiments/evidence_chain_v1'
PARENT_RUN = BACE/'results/evidence_chain_v1'

def main():
    assert not (EXP/'freeze.json').exists(), 'This amendment is already frozen'
    assert not any(RESULTS.glob('runs/*/calls.jsonl')), 'Existing sampled journals'
    previous = read(PARENT/'freeze.json')
    for path,digest in previous['files'].items():
        assert sha(ROOT/path)==digest, path
    env = {d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
    assert env==previous['environment']
    assert read(PARENT_RUN/'status.json')['status']=='STOPPED_FOR_SAMPLING'
    stopped=read(PARENT_RUN/'sampling_stop.json')
    for path,digest in stopped['retained_journal_sha256'].items():
        assert sha(ROOT/path)==digest, 'Parent journals changed after cancellation'
    pilot=read(PARENT_RUN/'pilot_gate.json')
    assert pilot['status']=='PASS' and pilot['freeze_sha256']==sha(PARENT/'freeze.json')
    assert (EXP/'judge_prompt.txt').read_bytes()==(PARENT/'judge_prompt.txt').read_bytes()
    parent=read(PARENT/'plan.json')
    strata=defaultdict(list)
    for case in parent['cases']:
        strata[(case['company_id'],case['task'][0])].append(case)
    assert len(strata)==90 and {s[1] for s in strata}=={'E','S','G'}
    selected=[]; ledger=[]
    for (company,topic),members in sorted(strata.items()):
        ordered=sorted(members,key=lambda c:rank('sample_case',c['generation_case_id']))
        for index,case in enumerate(ordered):
            ledger.append({k:case[k] for k in ['generation_case_id','company_id','company_name','year','task','claims']} |
                {'topic':topic,'stratum_disclosures':len(members),'rank':index+1,
                 'hash_rank':rank('sample_case',case['generation_case_id']),
                 'inclusion_probability':1/len(members),'selected':index==0})
            if index==0:
                selected.append({**case,'topic':topic,'stratum_disclosures':len(members),
                    'inclusion_probability':1/len(members),'sampling_weight':len(members)})
    assert len(selected)==90 and len({c['company_id'] for c in selected})==30
    for company in {c['company_id'] for c in selected}:
        assert {c['topic'] for c in selected if c['company_id']==company}=={'E','S','G'}
    with (EXP/'selection.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(ledger[0]));writer.writeheader();writer.writerows(ledger)
    ids={c['generation_case_id'] for c in selected}
    reused=[]; counts=Counter()
    for condition in CONDITIONS:
        source=PARENT_RUN/'runs'/condition/'calls.jsonl'
        target=RESULTS/'runs'/condition/'calls.jsonl';target.parent.mkdir(parents=True,exist_ok=True)
        seen=set()
        with target.open('wb') as out,source.open('rb') as stream:
            for line_number,line in enumerate(stream,1):
                if not line.strip():continue
                import json
                record=json.loads(line)
                if record['generation_case_id'] not in ids:continue
                key=(record['generation_case_id'],record['dc_id'])
                assert key not in seen;seen.add(key)
                out.write(line)
                reused.append({'condition':condition,'generation_case_id':key[0],'dc_id':key[1],
                    'source_path':str(source.relative_to(ROOT)),'source_line':line_number,
                    'record_sha256':hashlib.sha256(line).hexdigest()})
                counts[condition]+=1
    write(EXP/'reuse_ledger.json',reused)
    claims=sum(c['claims'] for c in selected)
    zeros=sum(c['zero_candidates'] for c in selected)
    checks=[]
    for case in selected:
        cache=read(ROOT/case['cache_path'])
        assert len(cache['dc_jobs'])==case['claims']
        checks.append({'generation_case_id':case['generation_case_id'],
                       'dc_id':cache['dc_jobs'][0]['job']['dc_id']})
    plan={k:parent[k] for k in ['model','model_key','deployment_name','criterion',
        'criterion_source','criterion_source_sha256','judge_prompt_sha256']}
    plan.update(status='AMENDMENT_FROZEN_BEFORE_NEW_CALLS_WITH_DECLARED_REUSE',
        created_at_utc=now(),cases=selected,pilot_jobs=checks,
        pilot_jobs_purpose='Offline input checks only; parent technical pilot is reused without calls.',
        parent_plan_sha256=sha(PARENT/'plan.json'),parent_freeze_sha256=sha(PARENT/'freeze.json'),
        counts={'disclosures':len(selected),'companies':30,'claims_per_condition':claims,
            'planned_records':3*claims,'zero_candidates':zeros,'unlinked_occurrences':sum(c['unlinked_occurrences'] for c in selected)},
        sampling={'seed':20261002,'namespace':'sample_case','strata':'company_id by first task character (E/S/G)',
            'per_stratum':1,'frame_disclosures':len(parent['cases']),'frame_claims':parent['counts']['claims_per_condition'],
            'selection_uses_outcomes':False,'stratum_sizes':dict(Counter(len(s) for s in strata.values()))},
        reuse={'records':sum(counts.values()),'conditions':dict(counts),'all_recorded_statuses_retained':True})
    write(EXP/'plan.json',plan)
    files=dict(previous['files'])
    for path in [PARENT/'freeze.json',PARENT_RUN/'sampling_stop.json',PARENT_RUN/'pilot_gate.json',
                 *[PARENT_RUN/'runs'/c/'calls.jsonl' for c in CONDITIONS]]:
        files[str(path.relative_to(ROOT))]=sha(path)
    for name in ['common.py','run.py','prepare.py','check_replay.py','verify_sample.py',
                 'PROTOCOL.md','README.md','judge_prompt.txt','judge_prompt.diff','selection.csv','reuse_ledger.json','plan.json']:
        path=EXP/name;files[str(path.relative_to(ROOT))]=sha(path)
    write(EXP/'freeze.json',{'status':plan['status'],'created_at_utc':now(),'files':files,
        'environment':env,'counts':plan['counts'],'criterion':plan['criterion']})
    summary={'status':'PREPARED_NOT_STARTED','created_at_utc':now(),
        'plan_sha256':sha(EXP/'plan.json'),'freeze_sha256':sha(EXP/'freeze.json'),
        'frame_counts':parent['counts'],'sample_counts':plan['counts'],
        'reused_records':sum(counts.values()),'remaining_records':3*claims-sum(counts.values()),
        'planned_record_reduction_fraction':1-claims/parent['counts']['claims_per_condition'],
        'nominal_model_jobs_before_reuse_and_retries':3*claims-zeros,
        'token_savings':'Not an exact token saving; input sizes, output lengths and retries vary.',
        'selection_code_sha256':sha(__file__)}
    write(RESULTS/'preparation_summary.json',summary)
    print(summary)

if __name__=='__main__':main()
