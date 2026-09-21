#!/usr/bin/env python3
"""Run source-bound extraction with auditable deterministic claim rendering."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time

from dotenv import load_dotenv
from jsonschema import Draft202012Validator

from contextual_claims import canonicalize, ContextContractError
from generation_claims import (
    InputValidationError, add_call_identity, append_jsonl, build_dc_jobs, build_ec_jobs,
    make_dc_occurrences, make_ec_occurrences, read_json, read_jsonl, select_cases,
    sha256_file, sha256_json, utc_now, write_json, write_jsonl,
)
from run_generation_claim_extraction import (
    execute_job, load_and_validate_configuration, load_latest_call_records, make_client,
    make_quality_summary, merge_dicts, output_paths, prepare_output_directory, resolve_model,
    start_progress_heartbeat, stop_progress_heartbeat,
)

ROOT = Path(__file__).resolve().parents[2]


def canonical_call(record):
    """A separate adapter view for legacy occurrence/quality helpers."""
    return {**record, 'parsed_output': record['canonical_output'],
            'validated_output': record['canonical_output']}


def successful(record):
    if not record or record.get('call_status') != 'success':
        return False
    if (record.get('api_response') or {}).get('status') != 'completed':
        return False
    return record.get('canonical_output') == canonicalize(record['task'], record['parsed_output'])


def bind_output(record, job, schema):
    """Preserve native output; reject malformed contracts without hiding them."""
    record['output_processing_mode'] = 'schema_only_context_rendered'
    record['canonical_output'] = None
    if record['call_status'] != 'success':
        return record
    errors = sorted(Draft202012Validator(schema).iter_errors(record['parsed_output']), key=lambda e: str(e.path))
    try:
        if errors:
            raise ContextContractError(str(errors[0]))
        if (record.get('api_response') or {}).get('status') != 'completed':
            raise ContextContractError('Provider response is not completed')
        if job['task'] == 'ec':
            labels = [r['prompt_label'] for r in record['parsed_output']['evidence_results']]
            if labels != [r['prompt_label'] for r in job['evidence_records']]:
                raise ContextContractError('Evidence labels missing, duplicated or reordered')
        record['canonical_output'] = canonicalize(job['task'], record['parsed_output'])
    except ContextContractError as exc:
        record.update(call_status='invalid_output', output_valid=False, validation_error=str(exc))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--split', choices=('development', 'validation'), required=True)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--max-new-calls', type=int)
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    if args.workers < 1 or (args.max_new_calls is not None and args.max_new_calls < 1):
        parser.error('workers and max-new-calls must be positive')
    if args.resume and args.dry_run:
        parser.error('resume and dry-run are mutually exclusive')
    load_dotenv(ROOT / '.env', override=False)
    plan = read_json(args.plan)
    for filename, expected in plan['baseline_files'].items():
        if sha256_file(ROOT / filename) != expected:
            raise InputValidationError(f'Frozen original changed: {filename}')
    if args.split == 'validation':
        freeze = plan.get('validation_freeze', {})
        if freeze.get('validation_contents_reviewed_before_freeze') is not False:
            raise InputValidationError('Validation requires a frozen candidate')
        for filename, expected in freeze['candidate_files'].items():
            if sha256_file(ROOT / filename) != expected:
                raise InputValidationError(f'Frozen candidate changed: {filename}')
    baseline = read_json(ROOT / plan['baseline_dir'] / 'claim_extraction_run_manifest.json')
    lineage = baseline
    if 'generation_input_manifest' not in baseline['inputs']:
        lineage = read_json(ROOT / baseline['inputs']['source_run_dir'] / 'claim_extraction_run_manifest.json')
    inputs = {k: str((ROOT / v).resolve()) for k, v in lineage['inputs'].items() if k in ('generation_cases', 'generated_disclosures', 'generation_input_manifest', 'generation_run_manifest')}
    names = ('generation_cases', 'generated_disclosures', 'generation_input_manifest', 'generation_run_manifest')
    source_hashes = {name: sha256_file(Path(inputs[name])) for name in names}
    if any(source_hashes[n] != lineage['source_hashes'][n] for n in names):
        raise InputValidationError('Original source hash mismatch')
    selected_ids = [c['generation_case_id'] for c in plan['cases'] if c['split'] == args.split]
    cases, disclosures, selection_counts = select_cases(
        read_jsonl(Path(inputs['generation_cases'])), read_jsonl(Path(inputs['generated_disclosures'])),
        case_ids=set(selected_ids))
    by_id = {c['generation_case_id']: c for c in cases}
    cases = [by_id[cid] for cid in selected_ids]
    config_path = ROOT / plan['active_config']
    config, prompts, prompt_paths, schemas, schema_paths = load_and_validate_configuration(config_path)
    if config.get('output_validation', {}).get('mode') != 'schema_only':
        raise InputValidationError('Native output preservation requires schema_only')
    model_key, model, deployment, base_url, _ = resolve_model(config, model_key_override=None, dry_run=args.dry_run)
    source_hashes['config'] = sha256_file(config_path)
    code_files = [Path(__file__).resolve(), ROOT / 'script/evaluation/contextual_claims.py',
                  ROOT / 'script/evaluation/generation_claims.py', ROOT / 'script/evaluation/run_generation_claim_extraction.py']
    code_hashes = {str(p.relative_to(ROOT)): sha256_file(p) for p in code_files}
    contract_hash = sha256_json(code_hashes)
    jobs_by_task = {}
    for task, source_jobs in [('ec', build_ec_jobs(cases)), ('dc', build_dc_jobs(cases, disclosures))]:
        source_hashes[f'{task}_prompt'] = sha256_file(prompt_paths[task])
        source_hashes[f'{task}_response_schema'] = sha256_file(schema_paths[task])
        parameters = merge_dicts(model.get('request_parameters') or {}, (model.get('task_request_parameters') or {}).get(task, {}))
        baseline_calls = {r['job_summary']['generation_case_id']: r for r in read_jsonl(ROOT / plan['baseline_dir'] / f'{task}_extraction_calls.jsonl')}
        jobs_by_task[task] = {}
        for job in source_jobs:
            old = baseline_calls[job['generation_case_id']]
            if job['dynamic_input'] != old['dynamic_input'] or deployment != old['deployment_name'] or parameters != old['request_parameters']:
                raise InputValidationError('Source input or deployment/settings differ from baseline')
            job['job_input_hash'] = sha256_json({'original': job['job_input_hash'], 'contract_hash': contract_hash})
            ps, ss = config['prompts'][task], config['response_schemas'][task]
            jobs_by_task[task][job['generation_case_id']] = add_call_identity(job,
                prompt_version=ps['version'], prompt_sha256=ps['sha256'], schema_version=ss['version'],
                schema_sha256=ss['sha256'], model_key=model_key, model_id=model['model_id'],
                model_version=model.get('model_version'), deployment_name=deployment, request_parameters=parameters)
    jobs = [jobs_by_task[t][cid] for cid in selected_ids for t in ('ec', 'dc')]
    fingerprint = sha256_json({'source_hashes': source_hashes, 'code_hashes': code_hashes, 'jobs': [j['call_id'] for j in jobs]})
    output_dir = args.output_dir or args.plan.parent / plan['run_directories'][args.split]
    paths = output_paths(output_dir)
    previous = prepare_output_directory(output_dir=output_dir, paths=paths, resume=args.resume)
    if previous and (previous['run_fingerprint'] != fingerprint or previous['dry_run']):
        raise InputValidationError('Cannot resume a changed or dry run')
    manifest = {
        'schema_version': 'generation_claim_extraction_run_manifest_v1',
        'script_version': 'run_contextual_claim_extraction_v1', 'run_id': output_dir.name,
        'run_fingerprint': fingerprint, 'run_status': 'running', 'dry_run': args.dry_run,
        'started_at_utc': previous['started_at_utc'] if previous else utc_now(),
        'inputs': inputs, 'source_hashes': source_hashes, 'code_hashes': code_hashes,
        'filters': {'case_ids': selected_ids, 'only': 'both'},
        'model': {'model_key': model_key, 'model_id': model['model_id'], 'model_version': model.get('model_version'), 'deployment_name': deployment, 'provider': model['provider'], 'api_style': model['api_style'], 'request_parameters': model.get('request_parameters')},
        'prompts': {t: {'path': str(prompt_paths[t].resolve()), **config['prompts'][t]} for t in ('ec', 'dc')},
        'response_schemas': {t: {'path': str(schema_paths[t].resolve()), **config['response_schemas'][t]} for t in ('ec', 'dc')},
        'planned_jobs': {t: len(selected_ids) for t in ('ec', 'dc')},
        'output_processing_mode': 'schema_only_context_rendered',
        'outputs': {k: str(v.resolve()) for k, v in paths.items()},
        'comparison_condition': 'Identical original source and deployment/settings; contextual prompt/schema and deterministic rendering are the treatment.',
    }
    latest, all_records = load_latest_call_records(paths)
    pending = [j for j in jobs if not successful(latest.get(j['call_id']))]
    selected = pending[:args.max_new_calls] if args.max_new_calls else pending
    manifest['invocation'] = {'resume_skips': len(jobs) - len(pending), 'new_calls_planned': 0 if args.dry_run else len(selected), 'workers': args.workers}
    write_json(paths['manifest'], manifest)
    run_start = time.monotonic()
    client = None if args.dry_run or not selected else make_client(config=config, model=model, base_url=base_url)

    def run(job):
        label = job['task'] + ' ' + job['generation_case_id']
        print(label + ' started', flush=True)
        heartbeat = start_progress_heartbeat(label=label, interval_seconds=30, call_started=time.monotonic(), run_started=run_start)
        try:
            result = execute_job(job=job, client=client, deployment=deployment,
                prompt_text=prompts[job['task']], schema=schemas[job['task']],
                schema_spec=config['response_schemas'][job['task']], model_key=model_key, model=model, config=config)
            result = bind_output(result, job, schemas[job['task']])
            print(label + ' ' + result['call_status'], flush=True)
            return result
        finally:
            stop_progress_heartbeat(heartbeat)
    try:
        if not args.dry_run:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                for future in as_completed([pool.submit(run, job) for job in selected]):
                    result = future.result()
                    append_jsonl(paths[f'{result["task"]}_calls'], result)
                    latest[result['call_id']] = result
                    all_records.append(result)
    finally:
        ec_jobs, dc_jobs = ([j for j in jobs if j['task'] == t] for t in ('ec', 'dc'))
        accepted = {k: canonical_call(r) for k, r in latest.items() if successful(r)}
        ec_rows = make_ec_occurrences(ec_jobs, accepted, use_parsed_output=True)
        dc_rows = make_dc_occurrences(dc_jobs, accepted, use_parsed_output=True)
        write_jsonl(paths['ec_occurrences'], ec_rows)
        write_jsonl(paths['dc_occurrences'], dc_rows)
        write_jsonl(paths['failures'], [r for r in all_records if r['call_status'] != 'success'])
        for task in ('ec', 'dc'):
            if not paths[f'{task}_calls'].exists(): write_jsonl(paths[f'{task}_calls'], [])
        views = {k: canonical_call(r) if successful(r) else r for k, r in latest.items()}
        quality = make_quality_summary(selection_counts=selection_counts, ec_jobs=ec_jobs, dc_jobs=dc_jobs,
            latest_calls=views, all_call_records=all_records, ec_occurrences=ec_rows, dc_occurrences=dc_rows, dry_run=args.dry_run)
        write_json(paths['quality'], quality)
        manifest['quality_summary'] = quality
        manifest['run_status'] = 'dry_run_complete' if args.dry_run else ('complete' if all(j['call_id'] in accepted for j in jobs) else 'incomplete')
        if not args.dry_run and len(selected) < len(pending) and all(j['call_id'] in accepted for j in selected):
            manifest['run_status'] = 'paused'
        manifest['updated_at_utc'] = utc_now()
        write_json(paths['manifest'], manifest)
        print('Run status: ' + manifest['run_status'], flush=True)


if __name__ == '__main__':
    main()
