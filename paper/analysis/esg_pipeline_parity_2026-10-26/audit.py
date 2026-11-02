"""Audit saved main-study prompt identities across E1, S1 and G1.

Uses only the Python standard library and saved local files. No experiments,
credentials, project imports or frozen-output mutations are involved.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
CASE_ROOT = ROOT / 'BACE/results/main_v1/cases'
FILES = []
MISSING = []
RECEIPT = Counter()
RECEIPT_MISMATCH = []
CONTRACT = ('prompt_version', 'prompt_sha256', 'schema_version', 'schema_sha256',
            'model_key', 'model_id', 'model_version', 'deployment_name', 'request_parameters')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def sha(value):
    return hashlib.sha256(value).hexdigest()


def read(path, receipts=None):
    if not path.exists():
        MISSING.append(str(path.relative_to(ROOT)))
        return
    h = hashlib.sha256()
    n = 0
    with path.open('rb') as stream:
        if path.suffix == '.jsonl':
            for line in stream:
                h.update(line)
                if line.strip():
                    n += 1
                    yield json.loads(line)
        else:
            b = stream.read()
            h.update(b)
            n = 1
            yield json.loads(b)
    rel = str(path.relative_to(ROOT))
    digest = h.hexdigest()
    FILES.append({'path': rel, 'sha256': digest, 'records': n, 'bytes': path.stat().st_size})
    if receipts is not None:
        expected = receipts.get(str(path.relative_to(ROOT / 'BACE')))
        if expected is None:
            RECEIPT['no_completed_receipt'] += 1
        elif expected == digest:
            RECEIPT['matched'] += 1
        else:
            RECEIPT_MISMATCH.append({'path': rel, 'expected': expected, 'actual': digest})


def one(path, receipts=None):
    return next(iter(list(read(path, receipts))), None)


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    local_prompt_hashes = {p.stem: sha(p.read_bytes()) for p in (ROOT / 'BACE/config/evaluation/prompts').glob('*.txt')}
    generation_template = one(ROOT / 'BACE/config/prompts/generation_prompt_templates.json')['instruction_template']
    config = one(ROOT / 'BACE/config/experiment.json')
    manifests = [('generation', 'generation/generation_run_manifest.json')]
    manifests += [(x, f'extraction/{x}/claim_extraction_run_manifest.json') for x in ['direct','integrated','atomic']]
    manifests += [(s, f'bace/{s}/{f}_run_manifest.json') for s,f in [
        ('dedup','semantic_dedup'), ('candidates','claim_candidate'),
        ('support','claim_support'), ('diagnosis','claim_unsupported_diagnosis')]]
    call_files = [(f'{s}_{kind}', f'extraction/{s}/{kind}_extraction_calls.jsonl')
                  for s in ['direct','integrated','atomic'] for kind in ['ec','dc']]
    call_files += [(s, f'bace/{s}/{f}.jsonl') for s,f in [
        ('dedup','semantic_dedup_calls'), ('candidates','claim_candidate_calls'),
        ('support','claim_support_calls'), ('diagnosis','claim_unsupported_diagnosis_calls')]]
    manifest_groups = defaultdict(Counter)
    call_groups = defaultdict(Counter)
    schemas = defaultdict(Counter)
    statuses = defaultdict(Counter)
    conditions = defaultdict(Counter)
    available = Counter()
    family_cases = Counter()
    generations = Counter()
    instruction_failures = []
    declared_hash_failures = []
    signatures = {}
    native_processing = defaultdict(Counter)
    ledger = []
    empty_sources = defaultdict(Counter)
    chosen_cases = []
    for index, case_dir in enumerate(sorted(p for p in CASE_ROOT.iterdir() if p.is_dir()), 1):
        case = one(case_dir / 'inputs/generation_cases.jsonl')
        family = case['task_id'].split('-')[0]
        family_cases[family] += 1
        state = one(case_dir / 'state.json')
        receipts = {k: v for s in state['stages'].values() for k, v in s.get('artifacts', {}).items()}
        expected = generation_template.format(company_name=case['company_name'], target_reporting_year=case['target_reporting_year'], task_title=case['task_title'])
        generations[family + '_checked'] += 1
        if case['instruction'] != expected:
            instruction_failures.append(case_dir.name)
        prefix = 'Instruction\n\n' + case['instruction'].strip() + '\n\nEvidence\n\n'
        if not case['generation_prompt'].startswith(prefix):
            instruction_failures.append(case_dir.name + ':prompt_prefix')
        cards = {c['prompt_label']: c for c in case['prompt_evidence'] if c['shown_in_prompt']}
        for stage, rel in manifests:
            r = one(case_dir / rel, receipts)
            if r is None:
                continue
            available[(family,stage)] += 1
            if stage == 'generation':
                contract = {'model': r['generation_model'], 'prompt_policy': r['prompt_policy']}
                conditions[(stage,family)][r.get('script_version', 'UNRECORDED')] += 1
            elif stage in ['direct','integrated','atomic']:
                contract = {'model': r['model'], 'prompts': {k: {x:v[x] for x in ['version','sha256']} for k,v in r['prompts'].items()},
                            'schemas': {k: {x:v[x] for x in ['version','sha256']} for k,v in r['response_schemas'].items()},
                            'config_sha256': r['source_hashes']['config'],
                            'output_processing_mode': r['output_processing_mode'],
                            'report_attribution_mode': r.get('report_attribution_mode'),
                            'review_focus': r.get('review_focus')}
                conditions[(stage,family)][canonical(r.get('code_hashes',{}))] += 1
            else:
                identity = r['run_identity']
                contract = {k: identity.get(k) for k in ['config_sha256','prompt_sha256','schema_sha256','model_key','model_id','model_version','deployment_name','request_parameters']}
                conditions[(stage,family)][r['script_version']] += 1
            signature = sha(canonical(contract).encode())
            signatures[signature] = contract
            manifest_groups[(stage,family)][signature] += 1
        for slot, rel in call_files:
            by_slot = Counter()
            for call in read(case_dir / rel, receipts):
                actual_slot = slot
                if slot == 'dedup':
                    actual_slot += '_' + call.get('claim_kind', 'UNKNOWN')
                identity = call.get('call_identity',{})
                contract = {k: identity.get(k) for k in CONTRACT}
                signature = sha(canonical(contract).encode())
                signatures[signature] = contract
                call_groups[(actual_slot,family)][signature] += 1
                by_slot[actual_slot] += 1
                statuses[(actual_slot,family)][canonical({'status':call.get('call_status'),'output_valid':call.get('output_valid'),'model_called':call.get('model_called')})] += 1
                dynamic = call.get('dynamic_input',{})
                shape = {'keys': sorted(dynamic), 'context_metadata_keys': sorted(dynamic.get('context_metadata',{}))}
                schemas[(actual_slot,family)][canonical(shape)] += 1
                native_processing[(actual_slot,family)][str(call.get('output_processing_mode','not_recorded'))] += 1
                prompt_hash = identity.get('prompt_sha256')
                version = identity.get('prompt_version')
                if version:
                    if version in local_prompt_hashes and local_prompt_hashes[version] != prompt_hash:
                        declared_hash_failures.append({'case':case_dir.name,'slot':actual_slot,'call_id':call.get('call_id'),'version':version})
                if actual_slot == 'direct_ec' and call.get('output_valid'):
                    for unit in (call.get('canonical_output') or {}).get('evidence_results',[]):
                        card = cards[unit['prompt_label']]
                        kind = card['evidence_type']
                        c = empty_sources[(family,kind)]
                        c['successful_call_card_presentations'] += 1
                        if not unit['claims']:
                            c['zero_claim_presentations'] += 1
                            for reason in {x.get('reason','UNRECORDED') for x in unit.get('unextracted_spans',[])}:
                                c['zero_claim_reason_' + reason] += 1
            for actual_slot,n in by_slot.items():
                ledger.append({'case':case_dir.name,'family':family,'stage_slot':actual_slot,'saved_call_records':n})
        if index % 100 == 0:
            print('Audited saved prompt identities', index, '/ 1800', flush=True)

    def groups(obj):
        return [{'stage':k[0], 'family':k[1], 'variants':dict(v)} for k,v in sorted(obj.items())]
    comparison = []
    for stage in sorted({k[0] for k in call_groups}):
        sets = {f:set(call_groups[(stage,f)]) for f in sorted(family_cases)}
        comparison.append({'stage':stage, 'identical_signature_sets_across_families':len({tuple(sorted(s)) for s in sets.values()}) == 1,
                           'signature_counts_by_family':{f:len(s) for f,s in sets.items()},
                           'saved_records_by_family':{f:sum(call_groups[(stage,f)].values()) for f in sets}})
    archive = ROOT / '_archive/previous_stage_20260921'
    comparisons = []
    for p in sorted((ROOT/'BACE/config/evaluation/prompts').glob('*.txt')):
        old = archive / 'config/evaluation/prompts' / p.name
        if old.exists():
            FILES.extend({'path':str(q.relative_to(ROOT)),'sha256':sha(q.read_bytes()),'bytes':q.stat().st_size} for q in [p,old])
            comparisons.append({'prompt':p.name, 'same_as_archived_same_filename': p.read_bytes()==old.read_bytes()})
    old_template = one(archive / 'config/prompts/generation_prompt_templates.json')['instruction_template']
    output = {'access_date':'2026-10-26','completed_at_utc':datetime.now(timezone.utc).isoformat(),
              'scope':'All saved main_v1 EC/DC extraction, integrated/atomic review, dedup, candidate, support and diagnosis call records; all available corresponding manifests and generation instructions.',
              'case_counts_by_family':dict(family_cases), 'available_manifests':[{'family':k[0],'stage':k[1],'count':v} for k,v in sorted(available.items())],
              'generation_instruction_checks':dict(generations), 'generation_instruction_failures':instruction_failures,
              'declared_prompt_hash_failures':declared_hash_failures,
              'call_contract_comparison':comparison, 'call_contract_groups':groups(call_groups),
              'manifest_contract_groups':groups(manifest_groups), 'dynamic_input_shapes':groups(schemas),
              'call_statuses':groups(statuses), 'output_processing_modes':groups(native_processing),
              'script_code_identities':groups(conditions), 'contract_signatures':signatures,
              'direct_ec_empty_source_screen':[{'family':k[0],'evidence_type':k[1],**dict(v)} for k,v in sorted(empty_sources.items())],
              'archive_same_filename_comparison':comparisons,
              'generation_instruction_same_as_archive':old_template==generation_template,
              'missing_files':MISSING, 'receipt_checks':dict(RECEIPT), 'receipt_mismatches':RECEIPT_MISMATCH,
              'limitations':['Prompt identity parity does not establish equal extraction quality across domains.',
                             'A zero-claim source is not automatically an extraction error.',
                             'Saved call records include retries and deterministic skips; they are not independent experimental observations.',
                             'Same-named archived prompts are file comparisons, not proof of which historical run used them.']}
    write('results.json',output)
    write('input_manifest.json',{'files':FILES,'script_sha256':sha(Path(__file__).read_bytes())})
    with (OUT/'case_call_counts.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,list(ledger[0]));w.writeheader();w.writerows(ledger)
    print(json.dumps({'call_contract_comparison':comparison,'receipt_checks':dict(RECEIPT),'generation_instruction_failures':len(instruction_failures),'hash_failures':len(declared_hash_failures)}),flush=True)


if __name__ == '__main__':
    main()
