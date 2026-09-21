#!/usr/bin/env python3
"""Re-render retained native groups without another model call or source change."""
from __future__ import annotations
import argparse
from copy import deepcopy
from pathlib import Path
from jsonschema import Draft202012Validator
from contextual_claims import canonicalize
from generation_claims import (build_dc_jobs, build_ec_jobs, make_dc_occurrences, make_ec_occurrences,
    read_json, read_jsonl, select_cases, sha256_file, sha256_json, utc_now, write_json, write_jsonl)
from run_contextual_claim_extraction import canonical_call
from run_generation_claim_extraction import output_paths, make_quality_summary
ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--native-run-dir', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    ap.add_argument('--replacement-run-dir', type=Path)
    args = ap.parse_args()
    if args.output_dir.exists(): raise ValueError('Choose a new output directory')
    native_path = args.native_run_dir / 'claim_extraction_run_manifest.json'
    native = read_json(native_path)
    for key in ('generation_cases', 'generated_disclosures', 'generation_input_manifest', 'generation_run_manifest'):
        if sha256_file(Path(native['inputs'][key])) != native['source_hashes'][key]:
            raise ValueError('Original input changed')
    cases, disclosures, counts = select_cases(read_jsonl(Path(native['inputs']['generation_cases'])),
        read_jsonl(Path(native['inputs']['generated_disclosures'])), case_ids=set(native['filters']['case_ids']))
    paths = output_paths(args.output_dir)
    args.output_dir.mkdir(parents=True)
    latest, jobs, records, hashes = {}, {}, [], {}
    for task, source_jobs in [('ec', build_ec_jobs(cases)), ('dc', build_dc_jobs(cases, disclosures))]:
        call_path = args.native_run_dir / f'{task}_extraction_calls.jsonl'
        hashes[str(call_path.resolve())] = sha256_file(call_path)
        by_case = {r['job_summary']['generation_case_id']: r for r in read_jsonl(call_path)}
        if args.replacement_run_dir:
            replacement = args.replacement_run_dir / f'{task}_extraction_calls.jsonl'
            if replacement.exists():
                hashes[str(replacement.resolve())] = sha256_file(replacement)
                for row in read_jsonl(replacement):
                    cid = row['job_summary']['generation_case_id']
                    previous = by_case[cid]
                    for key in ('dynamic_input', 'deployment_name', 'request_parameters', 'messages_sha256'):
                        if row[key] != previous[key]: raise ValueError('Replacement request changed')
                    for key in ('prompt_sha256', 'schema_sha256'):
                        if row['call_identity'][key] != previous['call_identity'][key]: raise ValueError('Replacement prompt/schema changed')
                    by_case[cid] = row
        spec = native['response_schemas'][task]
        if sha256_file(Path(spec['path'])) != spec['sha256']: raise ValueError('Native schema changed')
        validator = Draft202012Validator(read_json(Path(spec['path'])))
        task_rows = []
        for job in source_jobs:
            record = deepcopy(by_case[job['generation_case_id']])
            if record['dynamic_input'] != job['dynamic_input'] or (record.get('api_response') or {}).get('status') != 'completed':
                raise ValueError('Source mismatch or provider response incomplete')
            validator.validate(record['parsed_output'])
            if task == 'ec' and [r['prompt_label'] for r in record['parsed_output']['evidence_results']] != [r['prompt_label'] for r in job['evidence_records']]:
                raise ValueError('Missing or reordered evidence labels')
            record['native_record_sha256'] = sha256_json(record)
            record['native_call_status'] = record['call_status']
            record['native_validation_error'] = record.get('validation_error')
            record['canonical_output'] = canonicalize(task, record['parsed_output'])
            record.update(call_status='success', output_valid=True, validation_error=None,
                output_processing_mode='schema_only_context_rendered', rendered_at_utc=utc_now())
            job['call_id'] = record['call_id']
            latest[record['call_id']] = canonical_call(record)
            task_rows.append(record)
        jobs[task] = source_jobs
        records.extend(task_rows)
        write_jsonl(paths[f'{task}_calls'], task_rows)
    ec = make_ec_occurrences(jobs['ec'], latest, use_parsed_output=True)
    dc = make_dc_occurrences(jobs['dc'], latest, use_parsed_output=True)
    write_jsonl(paths['ec_occurrences'], ec)
    write_jsonl(paths['dc_occurrences'], dc)
    write_jsonl(paths['failures'], [])
    quality = make_quality_summary(selection_counts=counts, ec_jobs=jobs['ec'], dc_jobs=jobs['dc'],
        latest_calls=latest, all_call_records=records, ec_occurrences=ec, dc_occurrences=dc, dry_run=False)
    write_json(paths['quality'], quality)
    manifest = {**native, 'script_version': 'render_contextual_claim_run_v1', 'run_id': args.output_dir.name,
        'run_status': 'complete', 'outputs': {k: str(v.resolve()) for k,v in paths.items()},
        'native_code_hashes': native['code_hashes'],
        'code_hashes': {**native['code_hashes'], 'script/evaluation/contextual_claims.py': sha256_file(ROOT/'script/evaluation/contextual_claims.py'),
                        'script/evaluation/render_contextual_claim_run.py': sha256_file(Path(__file__))},
        'rendering_lineage': {'native_manifest': str(native_path.resolve()), 'native_manifest_sha256': sha256_file(native_path),
            'native_call_files': hashes, 'new_model_calls': 0,
            'reason': 'Accept a complete sentence in either stem or completion; reject an empty combined proposition. Native JSON and provider records remain unchanged.'},
        'quality_summary': quality, 'updated_at_utc': utc_now()}
    manifest['run_fingerprint'] = sha256_json({'native_fingerprint': native['run_fingerprint'], 'code_hashes': manifest['code_hashes']})
    write_json(paths['manifest'], manifest)
    print(f'Rendered {len(records)} retained native calls; new model calls: 0')


if __name__ == '__main__': main()
