"""One resumable orchestration path for the engineering pilot and main study."""
import fcntl
import json
import os
import subprocess
import sys
import signal
import threading
import time
from functools import partial
from common import ROOT, digest, jsonl, read, rows, write
from progress import RunProgress
from scheduling import ExperimentInterrupted, ProcessControl, parallel_branches, run_cases

CONFIGS = ROOT/'config/evaluation/configs'


def repair_interrupted_tail(path):
    """Preserve and remove only a truncated final JSONL record after interruption."""
    data = path.read_bytes()
    if not data or data.endswith(b'\n'):
        return
    split = data.rfind(b'\n') + 1
    tail = data[split:]
    try:
        json.loads(tail)
    except (json.JSONDecodeError, UnicodeDecodeError):
        preserved = path.with_name(path.name+'.interrupted_tail.'+str(time.time_ns()))
        preserved.write_bytes(tail)
        with path.open('r+b') as f:
            f.truncate(split)
    else:
        with path.open('ab') as f:
            f.write(b'\n')


def immutable_json(path, payload):
    if path.exists():
        if read(path)!=payload:
            raise ValueError('Refusing changed run input: '+str(path))
    else:
        write(path,payload)


def stage(base, label, script, arguments, output, manifest_name, kind='standard', progress=None, checkpoint_lock=None, control=None):
    """Replay only identical completed stages; retry incomplete native manifests."""
    checkpoint_lock = checkpoint_lock or threading.Lock()
    control = control or ProcessControl()
    control.check()
    if progress:
        progress.begin_stage(base.name,label)
    manifest = output/manifest_name
    state_path = base/'state.json'
    with checkpoint_lock:
        state = read(state_path) if state_path.exists() else {'stages':{}}
    command = [sys.executable,str(ROOT/'script'/script),*map(str,arguments),'--output-dir',str(output)]
    if label in state['stages']:
        previous = state['stages'][label]
        if previous['command'] != command:
            raise ValueError('Stage identity changed: '+label)
        if previous['script_sha256'] != digest(ROOT/'script'/script):
            from acceptance import validate_completed_script
            validate_completed_script('script/'+script,previous['script_sha256'])
        for path,expected in previous['artifacts'].items():
            if digest(ROOT/path)!=expected:
                raise ValueError('Completed stage artifact changed: '+path)
        if progress:
            progress.finish_stage(base.name,label,reused=True)
        return
    log_path = base/'logs'/f'{label}.log'
    log_path.parent.mkdir(parents=True,exist_ok=True)
    attempts = read(ROOT/'config/experiment.json')['runtime']['max_stage_attempts']
    for attempt in range(attempts):
        if progress:
            progress.stage_state(base.name,f'run {attempt+1}/{attempts}',label)
        if manifest.exists():
            for path in output.glob('*.jsonl'):
                repair_interrupted_tail(path)
        invocation = command + (['--resume'] if manifest.exists() else [])
        with log_path.open('a') as log:
            log.write(json.dumps({'attempt':attempt+1,'command':invocation})+'\n')
            log.flush()
            returncode = control.run(invocation,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                                    env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PYTHONUNBUFFERED':'1'})
        current = read(manifest) if manifest.exists() else {}
        if progress:
            progress.stage_state(base.name,'validating',label)
        complete = current.get('status',current.get('run_status'))=='complete'
        if kind=='generation':
            complete = current.get('case_count_success')==1 and current.get('case_count_failed')==0 and not current.get('dry_run',True)
        if returncode==0 and complete:
            artifacts = {str(p.relative_to(ROOT)):digest(p) for p in output.rglob('*') if p.is_file()}
            with checkpoint_lock:
                state = read(state_path) if state_path.exists() else {'stages':{}}
                state['stages'][label] = {'command':command,'script_sha256':digest(ROOT/'script'/script),'artifacts':artifacts}
                write(state_path,state)
            if progress:
                progress.finish_stage(base.name,label,reused=False)
            return
        if attempt+1<attempts:
            if progress:
                progress.stage_state(base.name,'retry in 2s',label)
            control.stopped.wait(2)
            control.check()
    raise RuntimeError('Stage incomplete after retries: '+str(log_path.relative_to(ROOT)))


def run_case(case, run, progress=None, control=None):
    cid = case['generation_case_id']
    if progress:
        progress.begin_case(case)
    try:
        result = _locked_case(case,run,progress,control)
    except BaseException as exc:
        if progress:
            progress.finish_case(cid,error=exc,cancelled=isinstance(exc,ExperimentInterrupted))
        raise
    if progress:
        progress.finish_case(cid)
    return result


def _locked_case(case, run, progress, control):
    base = run/'cases'/case['generation_case_id']
    base.mkdir(parents=True,exist_ok=True)
    lock = (base/'.lock').open('w')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return _run_case(case,base,progress,control)
    finally:
        lock.close()


def _run_case(case, base, progress=None, control=None):
    execute_stage = partial(stage,progress=progress,checkpoint_lock=threading.Lock(),control=control)
    config = read(ROOT/'config/experiment.json')
    cid = case['generation_case_id']
    source = base/'inputs'
    source.mkdir(exist_ok=True)
    if (source/'generation_cases.jsonl').exists():
        if rows(source/'generation_cases.jsonl')!=[case]:
            raise ValueError('Case prompt differs from frozen input')
    else:
        jsonl(source/'generation_cases.jsonl',[case])
    input_manifest = read(ROOT/'evidence/inputs/generation_input_manifest.json')
    input_manifest.pop('artifact_sha256',None)
    input_manifest.update(generation_case_count=1,generation_cases_sha256=digest(source/'generation_cases.jsonl'),parent_manifest_sha256=digest(ROOT/'evidence/inputs/generation_input_manifest.json'))
    immutable_json(source/'generation_input_manifest.json',input_manifest)
    gen = base/'generation'
    execute_stage(base,'generation','generation/run_w2_generation.py',[
        '--generation-cases',source/'generation_cases.jsonl','--generation-input-manifest',source/'generation_input_manifest.json',
        '--run-id',base.parent.parent.name,'--provider','azure_openai','--model',config['generation']['model'],
        '--omit-temperature','--reasoning-effort',config['generation']['reasoning_effort'],
        '--max-output-tokens',config['generation']['max_output_tokens'],'--retry-attempts',config['generation']['retry_attempts']],gen,'generation_run_manifest.json','generation')
    inputs = {'generation_cases':source/'generation_cases.jsonl','generation_input_manifest':source/'generation_input_manifest.json',
              'generated_disclosures':gen/'generated_disclosures.jsonl','generation_run_manifest':gen/'generation_run_manifest.json'}
    def bace_branch():
        plan = {'schema_version':'bace_experiment_extraction_plan_v1','inputs':{k:str(v.relative_to(ROOT)) for k,v in inputs.items()},
                'input_hashes':{k:digest(v) for k,v in inputs.items()},'baseline_files':{},
                'cases':[{'generation_case_id':cid,'split':'development'}],
                'split_note':'Development is the inherited engineering execution label, not held-out validation.'}
        preceding = None
        for label,config_key in [('direct','extraction'),('integrated','integrated_review'),('atomic','atomicity_review')]:
            current = {**plan,'active_config':str((CONFIGS/config['bace'][config_key]).relative_to(ROOT))}
            if preceding:
                current['draft_dir'] = str(preceding.relative_to(ROOT))
            plan_path = source/f'{label}_plan.json'
            immutable_json(plan_path,current)
            target = base/'extraction'/label
            script = 'run_extraction_repair.py' if label=='direct' else 'run_staged_claim_refinement.py'
            execute_stage(base,label,'evaluation/'+script,['--plan',plan_path,'--split','development','--workers','2'],target,'claim_extraction_run_manifest.json')
            preceding = target
        common = ['--case-id',cid,'--run-id',base.parent.parent.name]
        dedup = base/'bace/dedup'
        execute_stage(base,'dedup','evaluation/run_generation_claim_semantic_dedup.py',[
            '--ec-occurrences',preceding/'ec_claim_occurrences.jsonl','--dc-occurrences',preceding/'dc_claim_occurrences.jsonl',
            '--config',CONFIGS/'generation_claim_semantic_dedup_config.json',*common],dedup,'semantic_dedup_run_manifest.json')
        claims = ['--ec-claims',dedup/'ec_claims.jsonl','--dc-claims',dedup/'dc_claims.jsonl']
        candidates = base/'bace/candidates'
        execute_stage(base,'candidates','evaluation/run_generation_claim_candidate_selection.py',[
            *claims,'--config',CONFIGS/'generation_claim_candidate_selection_config.json',*common],candidates,'claim_candidate_run_manifest.json')
        supporting = [*claims,'--candidate-selections',candidates/'dc_candidate_ecs.jsonl','--generation-cases',source/'generation_cases.jsonl']
        support = base/'bace/support'
        execute_stage(base,'support','evaluation/run_generation_claim_support_assessment.py',[
            *supporting,'--config',CONFIGS/'generation_claim_support_config.json',*common],support,'claim_support_run_manifest.json')
        execute_stage(base,'diagnosis','evaluation/run_generation_claim_unsupported_diagnosis.py',[
            *supporting,'--support-assessments',support/'dc_support_sets.jsonl','--config',CONFIGS/'generation_claim_unsupported_diagnosis_config.json',*common],base/'bace/diagnosis','claim_unsupported_diagnosis_run_manifest.json')
    external = read(CONFIGS/'external_evaluation_config.json')
    external['inputs'] = {k:str(inputs[k].relative_to(ROOT)) for k in ['generation_cases','generated_disclosures']}
    external['case_ids'] = [cid]
    external['selection_purpose'] = 'Frozen case from the common BACE 30-company, five-year, twelve-task matrix.'
    for name in ['ragchecker','ragas']:
        external['frameworks'][name]['output_dir'] = str((base/'evaluation'/name).relative_to(ROOT))
    immutable_json(source/'external_config.json',external)
    def external_branch(name):
        execute_stage(base,name,f'evaluation/run_{name}.py',['--config',source/'external_config.json'],base/'evaluation'/name,'manifest.json')
    parallel_branches({'bace':bace_branch,
                       'ragchecker':partial(external_branch,'ragchecker'),
                       'ragas':partial(external_branch,'ragas')})
    state = read(base/'state.json')
    state.update(status='complete',generation_case_id=cid)
    write(base/'state.json',state)
    return cid


def _run_experiment(scope, progress, control=None):
    control = control or ProcessControl()
    from acceptance import check_frozen, validate_run_freeze
    check_frozen()
    control.check()
    if scope=='main':
        readiness = read(ROOT/'readiness_report.json')
        if readiness.get('ready_for_main') is not True:
            raise ValueError('Main run requires a passed readiness report')
        if readiness['freeze_sha256']!=digest(ROOT/'config/freeze.json'):
            raise ValueError('Readiness report refers to a different freeze')
    all_cases = rows(ROOT/'evidence/inputs/generation_cases.jsonl')
    if scope=='pilot':
        selected = {c['generation_case_id'] for c in read(ROOT/'evidence/inputs/pilot_selection.json')['cases']}
        cases = [c for c in all_cases if c['generation_case_id'] in selected]
        if len(cases)!=12:
            raise ValueError('Pilot must contain all 12 prespecified cases')
    else:
        cases = all_cases
    run = ROOT/'results'/f'{scope}_v1'
    run.mkdir(parents=True,exist_ok=True)
    run_identity = {'scope':scope,'case_ids':[c['generation_case_id'] for c in cases],
                   'freeze_sha256':digest(ROOT/'config/freeze.json'),'generation_input_sha256':digest(ROOT/'evidence/inputs/generation_cases.jsonl')}
    if (run/'manifest.json').exists():
        prior = read(run/'manifest.json')
        validate_run_freeze(prior['freeze_sha256'])
        run_identity['freeze_sha256'] = prior['freeze_sha256']
    immutable_json(run/'manifest.json',run_identity)
    progress.expected = len(cases)
    progress.phase('running','Executing cases; detailed output stays in existing stage logs')
    failed = run_cases(cases,partial(run_case,run=run,progress=progress,control=control),
                       read(ROOT/'config/experiment.json')['runtime']['case_workers'],control)
    progress.phase('finalizing','Verifying frozen inputs and environment')
    check_frozen()
    if failed:
        raise RuntimeError(f'{len(failed)} cases failed; inspect {run}/execution_status.json and rerun the same command to resume')
    from summarize import summarize
    progress.phase('finalizing','Validating results and preparing summaries and human-review materials')
    progress.refresh()
    summarize(run,quiet=True)
    progress.phase('complete','All cases, final checks, summaries and human-review materials are complete')


def run_experiment(scope):
    if scope not in ('pilot','main'):
        raise ValueError('Unknown experiment scope')
    run = ROOT/'results'/f'{scope}_v1'
    run.mkdir(parents=True,exist_ok=True)
    with (run/'.run.lock').open('w') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('This experiment is already running')
        config = read(ROOT/'config/experiment.json')
        expected = config['expected_case_count'] if scope=='main' else config['pilot']['case_count']
        control = ProcessControl()
        interrupted = False
        previous = {sig:signal.signal(sig,control.cancel) for sig in (signal.SIGINT,signal.SIGTERM)}
        try:
            with RunProgress(scope,run,config['runtime']['case_workers'],expected) as progress:
                try:
                    _run_experiment(scope,progress,control)
                    control.check()
                except ExperimentInterrupted:
                    interrupted = True
                    progress.phase('interrupted','Stopped by user; saved outputs are resumable')
        finally:
            for sig,handler in previous.items():
                signal.signal(sig,handler)
        if interrupted:
            raise SystemExit(130)
