"""Resume-safe interleaved replay of frozen BACE support jobs.

Run with the existing native interpreter and PYTHONDONTWRITEBYTECODE=1.
The pilot gate evaluates transport and schema integrity, never support rates.
"""
from __future__ import annotations
import argparse
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import fcntl
import json
import os
from pathlib import Path
import sys
import time

from common import (EXP, BACE, ROOT, RESULTS, CONDITIONS, native, read, rows,
                    write, now, rank, sha, condition_bundle, replay_job, verify_frozen)
from claim_execution import attach_gate, settings, process_marker

ALL = (*CONDITIONS, 'original_repeat')

def latest_outcomes():
    latest = {}
    for condition in ALL:
        path = RESULTS / 'runs' / condition / 'calls.jsonl'
        if path.exists():
            for record in rows(path):
                latest[(condition, record['generation_case_id'], record['dc_id'])] = {
                    'status': record['call_status'], 'http_status': record.get('http_status'),
                    'usage': record.get('usage', {}), 'model_called': record['model_called'],
                    'supported': bool((record.get('restored_output') or {}).get('support_sets'))
                        if record['call_status'] == 'success' else None}
    return latest

def tasks(plan, latest, mode):
    pilot = {(v['generation_case_id'], v['dc_id']) for v in plan['pilot_jobs']}
    case_order = sorted(plan['cases'], key=lambda c: rank('case_order', c['generation_case_id']))
    for case in case_order:
        cid = case['generation_case_id']
        conditions = (*CONDITIONS, 'original_repeat') if case['repeat_control'] else CONDITIONS
        if mode == 'pilot' and not any(p[0] == cid for p in pilot):
            continue
        for saved in rows(ROOT / case['cache_path']):
            dc = saved['job']['dc_id']
            if mode == 'pilot' and (cid, dc) not in pilot:
                continue
            order = list(conditions)
            if int(rank('condition_order', cid + '|' + dc)[0], 16) % 2:
                order[:2] = reversed(order[:2])
            for condition in order:
                key = condition, cid, dc
                # Exhausted failures stay missing. Never silently select a new
                # response by repeatedly rerunning unsuccessful or successful jobs.
                if key not in latest:
                    yield condition, saved

def validate_result(record, saved, condition):
    job = replay_job(saved, condition)
    assert record['call_identity'] == job['call_identity']
    assert record['dynamic_input'] == saved['job']['dynamic_input']
    assert record['request_parameters'] == saved['job']['request_parameters']
    assert record['candidate_ec_ids'] == saved['job']['call_identity']['candidate_ec_ids']
    if record['call_status'] == 'success':
        checked = native.validate_support_response(record['validated_output'],
            expected_dc_id=job['dc_alias'], expected_ec_ids=job['candidate_ec_aliases'])
        assert native.restore_original_ids(checked, original_dc_id=job['dc_id'],
                    ec_original_by_alias=job['ec_original_by_alias']) == record['restored_output']
    return job

def run(mode, workers):
    verify_frozen()
    plan = read(EXP / 'plan.json')
    RESULTS.mkdir(parents=True, exist_ok=True)
    lock = (RESULTS / 'run.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    latest = latest_outcomes()
    frozen_hash = sha(EXP / 'freeze.json')
    if mode == 'full':
        pilot = read(RESULTS / 'pilot_gate.json')
        assert pilot['status'] == 'PASS' and pilot['freeze_sha256'] == sha(EXP / 'freeze.json')
    config, _, _ = condition_bundle('original_repeat')
    model_key, model, deployment, base_url = native.resolve_model(
        config, model_key_override=plan['model_key'], dry_run=False)
    assert deployment == plan['deployment_name'], 'Deployment differs from frozen historical run'
    assert model == plan['model'], 'Model configuration differs'
    client = native.make_client(config=config, model=model, base_url=base_url)
    execution = settings('support', workers)
    attach_gate(client, 'support', execution, config['runtime']['request_timeout_seconds'])
    start = time.monotonic()
    session = now().replace(':', '').replace('+', '_')
    handles = {}
    for condition in ALL:
        directory = RESULTS / 'runs' / condition
        directory.mkdir(parents=True, exist_ok=True)
        handles[condition] = (directory / 'calls.jsonl').open('a', buffering=1)
    planned = {c: plan['counts']['claims_per_full_condition'] for c in CONDITIONS}
    planned['original_repeat'] = plan['counts']['repeat_claims']
    if mode == 'pilot':
        planned = {c: len(plan['pilot_jobs']) for c in ALL}
    submitted = completed = 0
    fatal = None
    active = {}
    recent = deque(maxlen=20)
    counts = {c: {'planned': planned[c], 'recorded': 0, 'valid': 0, 'failed': 0,
                  'input_tokens': 0, 'output_tokens': 0} for c in ALL}
    def count_outcome(condition, value):
        count = counts[condition]
        count['recorded'] += 1
        count['valid' if value['status'] == 'success' else 'failed'] += 1
        for k in ('input_tokens', 'output_tokens'):
            count[k] += value['usage'].get(k) or 0
    for (condition, _, _), value in latest.items():
        count_outcome(condition, value)

    def snapshot(status):
        report = {'status': status, 'mode': mode, 'pid': os.getpid(),
                  'process_marker': process_marker(os.getpid()), 'updated_at_utc': now(),
                  'session': session, 'elapsed_seconds': round(time.monotonic()-start, 1),
                  'submitted_this_session': submitted, 'completed_this_session': completed,
                  'inflight': len(active), 'conditions': counts, 'fatal': fatal,
                  'freeze_sha256': frozen_hash, 'execution': execution}
        write(RESULTS / 'status.json', report)
        return report

    def execute(item):
        condition, saved = item
        cfg, prompt, schema = condition_bundle(condition)
        job = replay_job(saved, condition)
        record = native.execute_job(job=job, client=client, deployment=deployment,
            prompt_text=prompt, schema=schema, schema_spec=cfg['response_schema'],
            model_key=model_key, model=model, config=cfg)
        validate_result(record, saved, condition)
        record['prompt_sensitivity'] = {'condition': condition, 'session': session,
            'phase': mode, 'frozen_input_sha256': saved['job']['job_input_hash'],
            'freeze_sha256': frozen_hash}
        return record

    pending = iter(tasks(plan, latest, mode))
    print(f'Starting {mode}; workers={workers}; frozen exact-input replay', flush=True)
    snapshot('RUNNING')
    last_report = time.monotonic()
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            exhausted = False
            while active or not exhausted:
                while not fatal and not exhausted and len(active) < workers:
                    item = next(pending, None)
                    if item is None:
                        exhausted = True
                        break
                    active[pool.submit(execute, item)] = item
                    submitted += 1
                if fatal:
                    exhausted = True
                if not active:
                    break
                done, _ = wait(active, timeout=10, return_when=FIRST_COMPLETED)
                for future in done:
                    condition, saved = active.pop(future)
                    try:
                        record = future.result()
                    except Exception as exc:
                        fatal = {'type': type(exc).__name__, 'message': 'Replay invariant or executor exception; inspect failure record.'}
                        write(RESULTS / f'exception_{session}.json', {
                            'condition': condition, 'generation_case_id': saved['job']['generation_case_id'],
                            'dc_id': saved['job']['dc_id'], 'error_type': type(exc).__name__, 'error': str(exc)})
                        continue
                    handles[condition].write(json.dumps(record, ensure_ascii=False, separators=(',', ':'))+'\n')
                    handles[condition].flush()
                    key = condition, record['generation_case_id'], record['dc_id']
                    assert key not in latest
                    latest[key] = {'status': record['call_status'], 'http_status': record.get('http_status'),
                        'usage': record.get('usage', {}), 'model_called': record['model_called'],
                        'supported': bool((record.get('restored_output') or {}).get('support_sets'))
                            if record['call_status'] == 'success' else None}
                    count_outcome(condition, latest[key])
                    recent.append(latest[key])
                    completed += 1
                    if record.get('http_status') in (400, 401, 403, 404):
                        fatal = {'type': record['error_type'], 'http_status': record['http_status'],
                                 'message': 'Persistent request/authentication/deployment failure'}
                    if len(recent) == 20 and all(v['status'] == 'api_error' for v in recent):
                        fatal = {'type': 'ConsecutiveTransportFailures', 'message': '20 exhausted API failures'}
                if time.monotonic() - last_report >= 10:
                    report = snapshot('DRAINING_AFTER_ERROR' if fatal else 'RUNNING')
                    last_report = time.monotonic()
                    print(json.dumps({'completed_this_session': completed, 'elapsed_seconds': report['elapsed_seconds'],
                                      'inflight': len(active)}, ensure_ascii=False), flush=True)
        terminal = 'STOPPED_ERROR' if fatal else 'COMPLETED'
        report = snapshot(terminal)
        write(RESULTS / 'sessions' / f'{session}.json', report)
        if mode == 'pilot' and not fatal:
            good = all(v['recorded'] == planned[c] and v['failed'] == 0 for c,v in report['conditions'].items())
            write(RESULTS / 'pilot_gate.json', {'status': 'PASS' if good else 'FAIL',
                'checked': 'All planned pilot jobs have native-valid output, exact inputs and preserved settings; scores were not a gate.',
                'freeze_sha256': sha(EXP / 'freeze.json'), 'conditions': report['conditions'],
                'session': session, 'created_at_utc': now()})
            if not good:
                raise RuntimeError('Technical pilot did not complete with valid outputs.')
        print(json.dumps(report, indent=2), flush=True)
        if fatal:
            raise RuntimeError('Run stopped after a persistent failure; successful calls retained.')
    finally:
        for handle in handles.values():
            handle.close()
        client.close()
        lock.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['pilot', 'full'], required=True)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    run(args.mode, args.workers)
