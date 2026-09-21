#!/usr/bin/env python3
"""Optionally refine a completed extraction against its unchanged source input.

Both stages retain native call records. Draft claims are untrusted proposals;
this runner does not use support verdicts, reference answers or human labels.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import time

from generation_claims import (
    InputValidationError, add_call_identity, append_jsonl, build_dc_jobs, build_ec_jobs,
    make_dc_occurrences, make_ec_occurrences, read_json, read_jsonl, select_cases,
    sha256_file, sha256_json, utc_now, write_json, write_jsonl,
)
from run_generation_claim_extraction import (
    execute_job, load_and_validate_configuration, load_latest_call_records, make_client,
    make_quality_summary, merge_dicts, output_paths, prepare_output_directory, resolve_model,
    should_skip_on_resume, start_progress_heartbeat, stop_progress_heartbeat,
)


def attach_draft(job, draft):
    """Bind an exact successful draft to a job without changing its source."""
    if draft.get('call_status') != 'success' or draft.get('api_response', {}).get('status') != 'completed':
        raise InputValidationError('Refinement requires a completed successful draft')
    if draft.get('task') != job['task'] or draft.get('job_summary', {}).get('generation_case_id') != job['generation_case_id']:
        raise InputValidationError('Draft task or case does not match source job')
    if draft.get('dynamic_input') != job['dynamic_input']:
        raise InputValidationError('Draft source input differs from the original source job')
    if not isinstance(draft.get('parsed_output'), dict):
        raise InputValidationError('Draft has no structured extraction')
    result = dict(job)
    result['dynamic_input'] = {**job['dynamic_input'], 'draft_extraction': draft['parsed_output']}
    result['draft_call_id'] = draft['call_id']
    result['job_input_hash'] = sha256_json({
        'source_job_input_hash': job['job_input_hash'],
        'draft_call_id': draft['call_id'],
        'dynamic_input': result['dynamic_input'],
    })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draft-run-dir', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--case-id', action='append', default=[])
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    draft_path = args.draft_run_dir / 'claim_extraction_run_manifest.json'
    draft_manifest = read_json(draft_path)
    if draft_manifest.get('run_status') != 'complete':
        raise InputValidationError('Draft run must be complete')
    inputs = draft_manifest['inputs']
    for name in ('generation_cases', 'generated_disclosures', 'generation_input_manifest', 'generation_run_manifest'):
        if sha256_file(Path(inputs[name])) != draft_manifest['source_hashes'][name]:
            raise InputValidationError(f'Original source changed: {name}')
    cases, disclosures, selection_counts = select_cases(
        read_jsonl(Path(inputs['generation_cases'])), read_jsonl(Path(inputs['generated_disclosures'])),
        case_ids=set(args.case_id or draft_manifest['filters']['case_ids']),
    )
    if not cases:
        raise InputValidationError('No source cases selected')
    if args.case_id and {c['generation_case_id'] for c in cases} != set(args.case_id):
        raise InputValidationError('Some requested source cases were not found')
    config, prompts, prompt_paths, schemas, schema_paths = load_and_validate_configuration(args.config)
    if config.get('output_validation', {}).get('mode') != 'schema_only':
        raise InputValidationError('Refinement requires schema_only output preservation')
    model_key, model, deployment, base_url, _ = resolve_model(config, model_key_override=None, dry_run=args.dry_run)
    source_hashes = {**draft_manifest['source_hashes'], 'draft_manifest': sha256_file(draft_path), 'config': sha256_file(args.config)}
    source_hashes['refinement_runner'] = sha256_file(Path(__file__))
    jobs = []
    for task, source_jobs in [('ec', build_ec_jobs(cases)), ('dc', build_dc_jobs(cases, disclosures))]:
        call_path = args.draft_run_dir / f'{task}_extraction_calls.jsonl'
        source_hashes[f'draft_{task}_calls'] = sha256_file(call_path)
        source_hashes[f'{task}_prompt'] = sha256_file(prompt_paths[task])
        source_hashes[f'{task}_response_schema'] = sha256_file(schema_paths[task])
        drafts = {r['job_summary']['generation_case_id']: r for r in read_jsonl(call_path)}
        parameters = merge_dicts(model.get('request_parameters') or {}, (model.get('task_request_parameters') or {}).get(task, {}))
        for source_job in source_jobs:
            draft = drafts.get(source_job['generation_case_id'])
            if draft is None:
                raise InputValidationError('No draft for a selected case')
            if draft['deployment_name'] != deployment or draft['request_parameters'] != parameters:
                raise InputValidationError('Refinement model settings differ from draft')
            job = attach_draft(source_job, draft)
            ps, ss = config['prompts'][task], config['response_schemas'][task]
            jobs.append(add_call_identity(job, prompt_version=ps['version'], prompt_sha256=ps['sha256'],
                schema_version=ss['version'], schema_sha256=ss['sha256'], model_key=model_key,
                model_id=model['model_id'], model_version=model.get('model_version'),
                deployment_name=deployment, request_parameters=parameters))
    fingerprint = sha256_json({'source_hashes': source_hashes, 'job_ids': [j['call_id'] for j in jobs]})
    paths = output_paths(args.output_dir)
    previous = prepare_output_directory(output_dir=args.output_dir, paths=paths, resume=args.resume)
    if previous and (previous['run_fingerprint'] != fingerprint or previous['dry_run']):
        raise InputValidationError('Cannot resume a changed or dry-run refinement')
    manifest = {
        'schema_version': 'generation_claim_extraction_run_manifest_v1',
        'script_version': 'run_claim_extraction_refinement_v1', 'run_id': args.output_dir.name,
        'run_fingerprint': fingerprint, 'run_status': 'running', 'dry_run': args.dry_run,
        'started_at_utc': previous['started_at_utc'] if previous else utc_now(),
        'inputs': inputs, 'source_hashes': source_hashes,
        'draft_run': {'manifest': str(draft_path.resolve()), 'directory': str(args.draft_run_dir.resolve())},
        'comparison_condition': 'Same source and model settings; revision additionally receives its first-stage draft.',
        'filters': {'case_ids': [c['generation_case_id'] for c in cases], 'only': 'both'},
        'model': {**draft_manifest['model'], 'deployment_name': deployment},
        'prompts': {t: {'path': str(prompt_paths[t].resolve()), **config['prompts'][t]} for t in ('ec', 'dc')},
        'response_schemas': {t: {'path': str(schema_paths[t].resolve()), **config['response_schemas'][t]} for t in ('ec', 'dc')},
        'planned_jobs': {t: sum(j['task'] == t for j in jobs) for t in ('ec', 'dc')},
        'output_processing_mode': 'schema_only', 'outputs': {k: str(v.resolve()) for k, v in paths.items()},
    }
    write_json(paths['manifest'], manifest)
    latest, all_records = load_latest_call_records(paths)
    run_start = time.monotonic()
    client = None if args.dry_run else make_client(config=config, model=model, base_url=base_url)
    try:
        if not args.dry_run:
            for index, job in enumerate(jobs, 1):
                if should_skip_on_resume(latest.get(job['call_id'])):
                    print(f'[{index}/{len(jobs)}] resume skip {job["task"]}', flush=True)
                    continue
                label = f'[{index}/{len(jobs)}] {job["task"]} {job["generation_case_id"]}'
                print(label + ' started', flush=True)
                heartbeat = start_progress_heartbeat(label=label, interval_seconds=30,
                    call_started=time.monotonic(), run_started=run_start)
                try:
                    result = execute_job(job=job, client=client, deployment=deployment,
                        prompt_text=prompts[job['task']], schema=schemas[job['task']],
                        schema_spec=config['response_schemas'][job['task']], model_key=model_key,
                        model=model, config=config)
                finally:
                    stop_progress_heartbeat(heartbeat)
                result['draft_call_id'] = job['draft_call_id']
                append_jsonl(paths[f'{job["task"]}_calls'], result)
                latest[job['call_id']] = result
                all_records.append(result)
                print(label + ' ' + result['call_status'], flush=True)
    finally:
        ec_jobs, dc_jobs = ([j for j in jobs if j['task'] == t] for t in ('ec', 'dc'))
        successful = {k: r for k, r in latest.items() if r['call_status'] == 'success'}
        ec_rows = make_ec_occurrences(ec_jobs, successful, use_parsed_output=True)
        dc_rows = make_dc_occurrences(dc_jobs, successful, use_parsed_output=True)
        write_jsonl(paths['ec_occurrences'], ec_rows)
        write_jsonl(paths['dc_occurrences'], dc_rows)
        write_jsonl(paths['failures'], [r for r in all_records if r['call_status'] != 'success'])
        for task in ('ec', 'dc'):
            if not paths[f'{task}_calls'].exists(): write_jsonl(paths[f'{task}_calls'], [])
        quality = make_quality_summary(selection_counts=selection_counts, ec_jobs=ec_jobs, dc_jobs=dc_jobs,
            latest_calls=latest, all_call_records=all_records, ec_occurrences=ec_rows, dc_occurrences=dc_rows, dry_run=args.dry_run)
        write_json(paths['quality'], quality)
        manifest['quality_summary'] = quality
        manifest['run_status'] = 'dry_run_complete' if args.dry_run else ('complete' if all(j['call_id'] in successful for j in jobs) else 'incomplete')
        manifest['updated_at_utc'] = utc_now()
        manifest['completed_at_utc'] = manifest['updated_at_utc'] if manifest['run_status'] in ('complete', 'dry_run_complete') else None
        write_json(paths['manifest'], manifest)
        print('Run status: ' + manifest['run_status'], flush=True)


if __name__ == '__main__':
    main()
