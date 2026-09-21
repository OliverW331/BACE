"""Small counterbalanced live timing check; never starts the main experiment."""
from pathlib import Path
import json
import subprocess
import sys
import time

from common import ROOT, digest, read, rows, write

STAGES = [('candidates','candidate_selection','claim_candidate_calls.jsonl'),
          ('support','support_assessment','claim_support_calls.jsonl'),
          ('diagnosis','unsupported_diagnosis','claim_unsupported_diagnosis_calls.jsonl')]
IDENTITY_FILES = ['config/claim_execution.json','script/evaluation/claim_execution.py',
                  'script/benchmark_claim_execution.py',
                  *['script/evaluation/run_generation_claim_'+suffix+'.py' for _,suffix,_ in STAGES]]


def verify(report):
    if report['status']!='complete':
        raise ValueError('Runtime timing check is incomplete')
    from acceptance import validate_runtime_fingerprint
    for name,expected in report['code_and_config'].items():
        if digest(ROOT/name)!=expected:
            validate_runtime_fingerprint(name,expected)
    for name,expected in {**report['source_files'],**report['artifacts']}.items():
        if digest(ROOT/name)!=expected:
            raise ValueError('Runtime validation input or output changed: '+name)
    assert len(report['arms'])==12 and all(a['successful_jobs']==4 for a in report['arms'])
    assert all(a['workers'] in (1,2) for a in report['arms'])
    return True


def main():
    output=ROOT/'results/runtime_validation'
    path=output/'summary.json'
    identity={name:digest(ROOT/name) for name in IDENTITY_FILES}
    base=sorted((ROOT/'results/pilot_v1/cases').iterdir())[0]
    cached={stage:{r['dc_id']:r for r in rows(base/'bace'/stage/filename)
                   if r['call_status']=='success' and r.get('model_called') and r.get('attempts')}
            for stage,_,filename in STAGES}
    selected=sorted(set.intersection(*(set(v) for v in cached.values())))[:8]
    if len(selected)!=8:raise ValueError('Need eight existing model-call jobs in all three stages')
    sources=[base/'inputs/generation_cases.jsonl',base/'bace/dedup/ec_claims.jsonl',base/'bace/dedup/dc_claims.jsonl',
             base/'bace/candidates/dc_candidate_ecs.jsonl',base/'bace/support/dc_support_sets.jsonl',
             *[base/'bace'/stage/filename for stage,_,filename in STAGES]]
    source_identity={str(p.relative_to(ROOT)):digest(p) for p in sources}
    report=read(path) if path.exists() else {'schema_version':'claim_runtime_validation_v1','status':'running',
        'code_and_config':identity,'source_files':source_identity,'case_id':base.name,'dc_ids':selected,'arms':[],
        'method':'Eight preselected existing claim jobs per stage, four per round. Run workers 1 then 2 in round 0, and 2 then 1 in round 1. Identical source inputs and model settings; independent live responses. Model scores never select an arm.',
        'limitations':'Small timing sample for three claim stages only. Timing includes subprocess startup and retries; it is not a whole-study speedup estimate.'}
    if report['code_and_config']!=identity or report['source_files']!=source_identity:
        raise ValueError('Existing timing run has different code or source inputs')
    if report['status']=='complete':
        verify(report);print('Reuse completed runtime validation; no new model calls');return
    write(path,report)
    for stage,suffix,filename in STAGES:
        config_name={'candidates':'candidate_selection','support':'support','diagnosis':'unsupported_diagnosis'}[stage]
        common=['--ec-claims',str(base/'bace/dedup/ec_claims.jsonl'),'--dc-claims',str(base/'bace/dedup/dc_claims.jsonl'),
                '--config',str(ROOT/f'config/evaluation/configs/generation_claim_{config_name}_config.json'),
                '--case-id',base.name,'--progress-interval-seconds','0']
        if stage!='candidates':common+=['--candidate-selections',str(base/'bace/candidates/dc_candidate_ecs.jsonl'),'--generation-cases',str(base/'inputs/generation_cases.jsonl')]
        if stage=='diagnosis':common+=['--support-assessments',str(base/'bace/support/dc_support_sets.jsonl')]
        for round_id,order in enumerate(((1,2),(2,1))):
            for workers in order:
                arm_id=f'{stage}/round_{round_id}_workers_{workers}'
                if any(a['arm_id']==arm_id for a in report['arms']):continue
                directory=output/arm_id
                if directory.exists():
                    raise ValueError('Unfinished timing arm requires inspection before reuse: '+arm_id)
                directory.mkdir(parents=True)
                arguments=[sys.executable,str(ROOT/f'script/evaluation/run_generation_claim_{suffix}.py'),*common,
                           '--workers',str(workers),'--output-dir',str(directory)]
                for cid in selected[round_id*4:round_id*4+4]:arguments+=['--dc-id',cid]
                log=directory.with_suffix('.log')
                elapsed=0.0
                print('Timing '+arm_id,flush=True)
                for attempt in range(3):
                    start=time.monotonic()
                    with log.open('a') as stream:
                        result=subprocess.run(arguments+(['--resume'] if attempt else []),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
                    elapsed+=time.monotonic()-start
                    if result.returncode==0:break
                if not (directory/filename).exists():
                    raise ValueError('Timing arm produced no call records; inspect '+str(log))
                records=rows(directory/filename)
                latest={r['call_id']:r for r in records}
                if result.returncode or len(latest)!=4 or any(r['call_status']!='success' for r in latest.values()):
                    raise ValueError('Timing arm failed: '+arm_id)
                # A worker-count change must not modify model messages or job identity.
                for record in latest.values():
                    prior=cached[stage][record['dc_id']]
                    assert record['call_identity']==prior['call_identity']
                    assert all(a['messages_sha256']==prior['attempts'][-1]['messages_sha256'] for a in record['attempts'])
                arm={'arm_id':arm_id,'stage':stage,'round':round_id,'workers':workers,
                     'elapsed_seconds':round(elapsed,3),'successful_jobs':len(latest),
                     'rate_limit_events':log.read_text().count('RateLimitError')+sum(r.get('http_status')==429 for r in records),
                     'network_retries':sum(a.get('network_retries',0) for r in records for a in r.get('attempts',[]))}
                report['arms'].append(arm);write(path,report)
                print(json.dumps(arm),flush=True)
    report['stage_timings']={}
    for stage,_,_ in STAGES:
        times={workers:sum(a['elapsed_seconds'] for a in report['arms'] if a['stage']==stage and a['workers']==workers) for workers in (1,2)}
        report['stage_timings'][stage]={'serial_seconds':round(times[1],3),'parallel_seconds':round(times[2],3),'observed_speedup':round(times[1]/times[2],3)}
    report['artifacts']={str(p.relative_to(ROOT)):digest(p) for p in sorted(output.rglob('*')) if p.is_file() and p!=path}
    report['status']='complete';write(path,report);verify(report)
    print(json.dumps(report['stage_timings'],indent=2),flush=True)


if __name__=='__main__':main()
