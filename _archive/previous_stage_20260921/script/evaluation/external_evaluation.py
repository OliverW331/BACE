"""Shared frozen-input adapter, Responses transport and resumable native evaluations."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / 'config/evaluation/configs/external_evaluation_config.json'
GROUP_TITLES = {'PDF Narrative Evidence', 'PDF Table Row Evidence', 'CSV Metric Evidence'}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def json_digest(value):
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False))


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(2 ** 20):
            h.update(chunk)
    return h.hexdigest()


def read_rows(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    temporary.replace(path)


def append_row(path, row):
    with Path(path).open('a') as stream:
        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
        stream.flush()


def unique_index(rows, key):
    result = {}
    for row in rows:
        if row[key] in result:
            raise ValueError(f'Duplicate {key}: {row[key]}')
        result[row[key]] = row
    return result


def adapt_case(case, output):
    """Reconstruct only visible blocks, verifying each against the recorded prompt."""
    cid = case['generation_case_id']
    if output['generation_case_id'] != cid or output['generation_status'] != 'success':
        raise ValueError(f'Output identity/status mismatch: {cid}')
    prompt_hash = digest(case['generation_prompt'])
    if prompt_hash != case['prompt_metadata']['prompt_hash'] or prompt_hash != output['prompt_hash']:
        raise ValueError(f'Prompt hash mismatch: {cid}')
    if digest(output['generated_text']) != output['generated_text_hash']:
        raise ValueError(f'Response hash mismatch: {cid}')
    prefix = 'Instruction\n\n' + case['instruction'] + '\n\nEvidence\n\n'
    if not case['generation_prompt'].startswith(prefix):
        raise ValueError(f'Unrecognized recorded prompt layout: {cid}')
    section = case['generation_prompt'][len(prefix):]
    cursor, group = 0, None
    contexts, evidence_ids, labels = [], [], []
    for card in case['prompt_evidence']:
        if not card['shown_in_prompt']:
            continue
        if digest(card['retrieval_text']) != card['retrieval_text_hash']:
            raise ValueError(f'Evidence hash mismatch: {cid}')
        block = f"{card['prompt_label']}\n\nSource:\n{card['source_label']}\n\nText:\n{card['retrieval_text']}"
        position = section.find(block, cursor)
        if position < cursor:
            raise ValueError(f'Evidence block absent/out of order: {cid}, {card["prompt_label"]}')
        gap = section[cursor:position].strip()
        if gap:
            separator = '-' * 50 + '\n\n'
            if gap.startswith(separator):
                gap = gap[len(separator):]
            if gap not in GROUP_TITLES:
                raise ValueError(f'Unmapped prompt-visible material: {cid}')
            group = gap
        if group is None:
            raise ValueError(f'Missing evidence group heading: {cid}')
        contexts.append(group + '\n\n' + block)
        evidence_ids.append(card['evidence_id'])
        labels.append(card['prompt_label'])
        cursor = position + len(block)
    if section[cursor:].strip() or not contexts or len(labels) != len(set(labels)):
        raise ValueError(f'Incomplete or duplicate evidence mapping: {cid}')
    return {
        'generation_case_id': cid, 'company_name': case['company_name'],
        'target_reporting_year': case['target_reporting_year'], 'task_id': case['task_id'],
        'query': case['instruction'], 'response': output['generated_text'],
        'contexts': contexts, 'evidence_ids': evidence_ids, 'prompt_labels': labels,
        'prompt_hash': prompt_hash, 'response_hash': output['generated_text_hash'],
        'context_hash': json_digest(contexts),
    }


def load_cases(config):
    inputs = ROOT / config['inputs']['generation_cases']
    outputs = ROOT / config['inputs']['generated_disclosures']
    cases = unique_index(read_rows(inputs), 'generation_case_id')
    responses = unique_index(read_rows(outputs), 'generation_case_id')
    selected = config['case_ids']
    if len(selected) != len(set(selected)):
        raise ValueError('Duplicate configured case IDs')
    # Validate the full frozen run, then select the engineering pilot.
    if set(cases) != set(responses):
        raise ValueError('Input and output case sets differ')
    adapted = {cid: adapt_case(case, responses[cid]) for cid, case in cases.items()}
    return [adapted[cid] for cid in selected]


def strict_schema(schema):
    """Apply the Responses strict-object contract to native Pydantic output models."""
    schema = json.loads(json.dumps(schema))
    def visit(node):
        if isinstance(node, dict):
            if node.get('type') == 'object':
                node['additionalProperties'] = False
                node['required'] = list(node.get('properties', {}))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(schema)
    return schema


def endpoint_url(endpoint):
    parts = urlsplit(endpoint.strip())
    if parts.scheme != 'https' or not parts.netloc:
        raise ValueError('Expected an HTTPS Azure endpoint')
    path = parts.path.rstrip('/')
    for suffix in ('/openai/v1/responses', '/openai/responses'):
        if path.endswith(suffix):
            path = path[:-len(suffix)]
            break
    if path.endswith('/openai/v1'):
        path += '/'
    elif path.endswith('/openai'):
        path += '/v1/'
    else:
        path += '/openai/v1/'
    return urlunsplit((parts.scheme, parts.netloc, path, '', ''))


class ResponsesTransport:
    def __init__(self, config, framework, output_dir, identity):
        from openai import OpenAI
        judge = config['judge']
        self.model = os.environ[judge['deployment_name_env']]
        self.parameters = judge['request_parameters']
        self.client = OpenAI(api_key=os.environ[judge['api_key_env']],
                             base_url=endpoint_url(os.environ[judge['endpoint_env']]),
                             timeout=config['runtime']['request_timeout_seconds'], max_retries=0)
        self.framework, self.config, self.identity = framework, config, identity
        self.path = output_dir / 'calls.jsonl'
        self.lock = threading.Lock()
        self.cache = {}
        if self.path.exists():
            for record in read_rows(self.path):
                if record['status'] == 'success':
                    self.cache[record['cache_key']] = record
        self.case_id = None
        self.trace = []

    def start_case(self, case_id):
        self.case_id, self.trace = case_id, []

    def complete(self, prompt, stage, response_model=None, validator=None):
        schema = strict_schema(response_model.model_json_schema()) if response_model else None
        key = json_digest({'identity': self.identity, 'case_id': self.case_id,
                           'stage': stage, 'prompt': prompt, 'schema': schema})
        cached = self.cache.get(key)
        if cached:
            parsed = response_model.model_validate_json(cached['raw_output']) if response_model else cached['raw_output']
            if validator:
                validator(cached['raw_output'])
            with self.lock:
                self.trace.append({**cached, 'cache_hit': True})
            return parsed
        runtime = self.config['runtime']
        for attempt in range(runtime['max_retries'] + 1):
            started = time.monotonic()
            record = {'schema_version': 'external_evaluation_call_v1', 'framework': self.framework,
                      'generation_case_id': self.case_id, 'stage': stage, 'cache_key': key,
                      'attempt': attempt, 'created_at_utc': now(), 'prompt': prompt,
                      'prompt_hash': digest(prompt), 'response_schema': schema,
                      'model': self.model, 'request_parameters': self.parameters,
                      'max_output_tokens': runtime['max_output_tokens'], 'cache_hit': False}
            try:
                kwargs = {'model': self.model, 'input': [{'role': 'user', 'content': prompt}],
                          'max_output_tokens': runtime['max_output_tokens'], **self.parameters}
                if schema:
                    kwargs['text'] = {'format': {'type': 'json_schema', 'name': response_model.__name__,
                                                 'schema': schema, 'strict': True}}
                response = self.client.responses.create(**kwargs)
                raw = response.output_text
                record.update(raw_output=raw, usage=response.usage.model_dump(mode='json') if response.usage else {},
                              provider_response=response.model_dump(mode='json'))
                if response.status != 'completed' or not raw.strip():
                    raise ValueError(f'Incomplete, refused or empty response: {response.status}')
                parsed = response_model.model_validate_json(raw) if response_model else raw
                if validator:
                    record['parse_audit'] = validator(raw)
                if response_model:
                    record['parsed_output'] = parsed.model_dump(mode='json')
                record['status'] = 'success'
            except Exception as error:
                record.update(status='error', error_type=type(error).__name__, error_message=str(error),
                              http_status=getattr(error, 'status_code', None))
                failure = error
            record['elapsed_seconds'] = round(time.monotonic() - started, 3)
            with self.lock:
                append_row(self.path, record)
                self.trace.append(record)
                if record['status'] == 'success':
                    self.cache[key] = record
            if record['status'] == 'success':
                return parsed
            if attempt == runtime['max_retries'] or record.get('http_status') in (400, 401, 403, 404):
                raise failure
            time.sleep(min(2 ** (attempt + 1), 16))
        raise RuntimeError('Unreachable retry state')

    def case_usage(self):
        fresh = [r for r in self.trace if not r['cache_hit']]
        keys = ('input_tokens', 'output_tokens', 'total_tokens')
        return {'requests_this_attempt': len(fresh),
                'cache_hits': sum(r['cache_hit'] for r in self.trace),
                **{key: sum(r.get('usage', {}).get(key, 0) or 0 for r in fresh) for key in keys}}


def run(framework, factory):
    parser = argparse.ArgumentParser(description=f'Run native {framework} faithfulness on frozen disclosures.')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--max-cases', type=int)
    parser.add_argument('--case-id', action='append')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if config['frameworks'][framework]['metrics'] != ['faithfulness']:
        raise ValueError('Only reference-answer-free faithfulness is supported')
    cases = load_cases(config)
    selected = cases
    if args.case_id:
        unknown = set(args.case_id) - {c['generation_case_id'] for c in cases}
        if unknown:
            raise ValueError(f'Case IDs are outside the configured pilot: {unknown}')
        selected = [c for c in cases if c['generation_case_id'] in args.case_id]
    if args.max_cases is not None:
        if args.max_cases < 1:
            raise ValueError('--max-cases must be positive')
        selected = selected[:args.max_cases]
    if args.dry_run:
        print(json.dumps({'framework': framework, 'configured_cases': len(cases),
                          'selected_cases': len(selected), 'reference_answer_required': False,
                          'evidence_counts': [len(c['contexts']) for c in selected],
                          'input_validation': 'passed'}, indent=2))
        return
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=False)
    os.environ['RAGAS_DO_NOT_TRACK'] = 'true'
    os.environ['HF_HUB_OFFLINE'] = '1'
    for key in ('deployment_name_env', 'endpoint_env', 'api_key_env'):
        if not os.environ.get(config['judge'][key]):
            raise ValueError(f'Missing configured environment variable: {config["judge"][key]}')
    versions = {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}
    for name, expected in config['package_versions'].items():
        if importlib.metadata.version(name) != expected:
            raise ValueError(f'Package version differs: {name}')
    identity = {'config': config, 'source_hashes': {name: file_digest(ROOT / path) for name, path in config['inputs'].items()},
                'scripts': {name: file_digest(Path(__file__).parent / name) for name in ['external_evaluation.py', f'run_{framework}.py']},
                'framework': framework, 'versions': versions,
                'judge_deployment': os.environ[config['judge']['deployment_name_env']],
                'judge_endpoint_hash': digest(endpoint_url(os.environ[config['judge']['endpoint_env']]))}
    identity_hash = json_digest(identity)
    directory = args.output_dir or ROOT / config['frameworks'][framework]['output_dir']
    directory = directory.resolve()
    manifest_path = directory / 'manifest.json'
    results_path = directory / 'results.jsonl'
    if directory.exists() and any(directory.iterdir()):
        if not args.resume or not manifest_path.exists():
            raise ValueError('Output exists; use --resume for the identical run')
        manifest = json.loads(manifest_path.read_text())
        if manifest['identity_hash'] != identity_hash:
            raise ValueError('Resume identity mismatch: inputs, config, source or environment changed')
    else:
        directory.mkdir(parents=True, exist_ok=True)
        manifest = {'schema_version': 'external_evaluation_manifest_v1', 'framework': framework,
                    'identity': identity, 'identity_hash': identity_hash, 'created_at_utc': now(),
                    'case_ids': config['case_ids'], 'reference_answer_policy': 'absent; faithfulness only',
                    'context_serialization': 'Exact visible card blocks with their visible group heading; no hidden metadata.'}
    manifest.update(status='running', updated_at_utc=now())
    write_json(manifest_path, manifest)
    transport = ResponsesTransport(config, framework, directory, identity_hash)
    evaluator = factory(config, transport)
    latest = {r['generation_case_id']: r for r in read_rows(results_path)} if results_path.exists() else {}
    failures = 0
    for case in selected:
        cid = case['generation_case_id']
        if latest.get(cid, {}).get('status') == 'success':
            print(f'Skipping completed case: {cid}', flush=True)
            continue
        print(f'Evaluating {framework}: {cid}', flush=True)
        started = time.monotonic()
        transport.start_case(cid)
        result = {key: case[key] for key in ('generation_case_id', 'company_name', 'target_reporting_year', 'task_id', 'prompt_hash', 'response_hash', 'context_hash')}
        result.update(framework=framework, metric='faithfulness', created_at_utc=now(),
                      evidence_ids=case['evidence_ids'], prompt_labels=case['prompt_labels'])
        try:
            result.update(evaluator(case))
            if result['claim_count'] == 0 or not math.isfinite(result['score']):
                result.update(status='invalid_empty_claims', score=None)
            else:
                if not 0 <= result['score'] <= 1:
                    raise ValueError('Native score outside [0, 1]')
                result['status'] = 'success'
        except Exception as error:
            result.update(status='error', score=None, error_type=type(error).__name__, error_message=str(error))
            failures += 1
        result.update(elapsed_seconds=round(time.monotonic() - started, 3), usage=transport.case_usage())
        append_row(results_path, result)
        latest[cid] = result
        valid = [r for r in latest.values() if r['status'] == 'success']
        manifest.update(updated_at_utc=now(), completed_cases=len(valid),
                        mean_faithfulness=sum(r['score'] for r in valid) / len(valid) if valid else None,
                        case_statuses={key: row['status'] for key, row in latest.items()})
        write_json(manifest_path, manifest)
        print(json.dumps({'case': cid, 'status': result['status'], 'score': result['score'],
                          'claims': result.get('claim_count'), 'usage': result['usage']}, ensure_ascii=False), flush=True)
        if failures:
            break
    manifest.update(status='complete' if len(latest) == len(cases) and all(r['status'] == 'success' for r in latest.values()) else 'partial', updated_at_utc=now())
    write_json(manifest_path, manifest)
    if failures:
        raise SystemExit('Evaluation failed; inspect results.jsonl and calls.jsonl before resuming.')
