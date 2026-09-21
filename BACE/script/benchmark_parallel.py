"""Bounded native parallel-runtime validation; never starts main-study cases."""
from concurrent.futures import ThreadPoolExecutor
import json
import subprocess
import sys
import time

from common import ROOT, digest, read, rows, write

STAGES = [('candidates','candidate_selection','claim_candidate_calls.jsonl'),
          ('support','support_assessment','claim_support_calls.jsonl'),
          ('diagnosis','unsupported_diagnosis','claim_unsupported_diagnosis_calls.jsonl')]
SOURCES = ['config/experiment.json','config/claim_execution.json','script/benchmark_parallel.py',
           'script/pipeline.py','script/scheduling.py','script/progress.py',
           'script/evaluation/claim_execution.py','script/evaluation/external_evaluation.py',
           'script/evaluation/run_generation_claim_extraction.py',
           'script/evaluation/run_generation_claim_semantic_dedup.py',
           'script/generation/run_w2_generation.py',
           *[f'script/evaluation/run_generation_claim_{suffix}.py' for _,suffix,_ in STAGES]]


def verify(result):
    if result['status']!='complete':
        raise ValueError('Parallel runtime validation is incomplete')
    for name,expected in {**result['sources'],**result['inputs'],**result['artifacts']}.items():
        if digest(ROOT/name)!=expected:
            raise ValueError('Parallel validation source/output changed: '+name)
    assert len(result['arms'])==3 and all(a['successful_jobs']==8 for a in result['arms'])
    return True


def main():
    path = ROOT/'results/runtime_validation/summary.json'
    report = read(path)
    identity = {name:digest(ROOT/name) for name in SOURCES}
    result = report.get('parallel_validation')
    if result:
        if result['sources']!=identity:
            raise ValueError('Parallel validation source changed')
        if result['status']=='complete':
            verify(result);print('Reused runtime validation; no model calls');return
    else:
        result = {'status':'running','sources':identity,'inputs':{},'arms':[],
                  'method':'First eight pilot cases in stable case-ID order; first successful model-call DC ID in each stage. Eight native jobs concurrently submitted per stage with the production pacing and shared resource gates. Verify identical original call identities and model messages.',
                  'limitations':'24 live job executions verify runtime integration. No paired speedup or full-study throughput estimate is claimed.'}
        report['parallel_validation'] = result
        write(path,report)
    bases = sorted((ROOT/'results/pilot_v1/cases').iterdir())[:8]
    output = ROOT/'results/runtime_validation/parallel'
    for stage,suffix,filename in STAGES:
        if any(a['stage']==stage for a in result['arms']):
            continue
        source_records = {}
        for base in bases:
            cached = {r['dc_id']:r for r in rows(base/'bace'/stage/filename)
                      if r['call_status']=='success' and r.get('model_called') and r.get('attempts')}
            source_records[base.name] = cached[sorted(cached)[0]]
            inputs = [base/'bace'/stage/filename,base/'bace/dedup/ec_claims.jsonl',base/'bace/dedup/dc_claims.jsonl']
            if stage!='candidates':
                inputs += [base/'bace/candidates/dc_candidate_ecs.jsonl',base/'inputs/generation_cases.jsonl']
            if stage=='diagnosis':
                inputs += [base/'bace/support/dc_support_sets.jsonl']
            result['inputs'].update({str(p.relative_to(ROOT)):digest(p) for p in inputs})
        write(path,report)
        def execute(base):
            prior = source_records[base.name]
            directory = output/stage/base.name
            directory.mkdir(parents=True,exist_ok=True)
            config_name = {'candidates':'candidate_selection','support':'support','diagnosis':'unsupported_diagnosis'}[stage]
            args = [sys.executable,str(ROOT/f'script/evaluation/run_generation_claim_{suffix}.py'),
                    '--ec-claims',str(base/'bace/dedup/ec_claims.jsonl'),
                    '--dc-claims',str(base/'bace/dedup/dc_claims.jsonl'),
                    '--config',str(ROOT/f'config/evaluation/configs/generation_claim_{config_name}_config.json'),
                    '--case-id',base.name,'--dc-id',prior['dc_id'],'--progress-interval-seconds','0','--output-dir',str(directory)]
            if stage!='candidates':
                args += ['--candidate-selections',str(base/'bace/candidates/dc_candidate_ecs.jsonl'),
                         '--generation-cases',str(base/'inputs/generation_cases.jsonl')]
            if stage=='diagnosis':
                args += ['--support-assessments',str(base/'bace/support/dc_support_sets.jsonl')]
            log_path = directory.parent/(base.name+'.log')
            for _ in range(3):
                resume = ['--resume'] if any(directory.glob('*manifest.json')) else []
                with log_path.open('a') as log:
                    code = subprocess.run(args+resume,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
                if code==0:
                    break
            records = rows(directory/filename)
            latest = {r['call_id']:r for r in records}
            assert code==0 and len(latest)==1 and all(r['call_status']=='success' for r in latest.values()), directory
            for record in latest.values():
                assert record['call_identity']==prior['call_identity']
                assert all(a['messages_sha256']==prior['attempts'][-1]['messages_sha256'] for a in record['attempts'])
            return {'retries':sum(a.get('network_retries',0) for r in records for a in r.get('attempts',[])),
                    'rate_limit_log_mentions':log_path.read_text().count('RateLimitError')}
        print('Validating '+stage+' (8 jobs)',flush=True)
        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=8) as pool:
            measurements = list(pool.map(execute,bases))
        arm = {'stage':stage,'successful_jobs':len(measurements),'elapsed_seconds':round(time.monotonic()-start,3),
               'network_retries':sum(m['retries'] for m in measurements),
               'rate_limit_log_mentions':sum(m['rate_limit_log_mentions'] for m in measurements)}
        result['arms'].append(arm);write(path,report);print(json.dumps(arm),flush=True)
    result['stage_timings'] = {a['stage']:a['elapsed_seconds'] for a in result['arms']}
    result['artifacts'] = {str(p.relative_to(ROOT)):digest(p) for p in output.rglob('*') if p.is_file()}
    result['status']='complete';write(path,report);verify(result)


if __name__=='__main__':
    main()
