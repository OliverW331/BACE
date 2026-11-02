"""Fixed-claim evidence-representation experiment; imports make no API calls."""
from __future__ import annotations
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

EXP = Path(__file__).resolve().parent
BACE = EXP.parents[1]
ROOT = BACE.parent
RESULTS = BACE/'results/evidence_chain_v1'
SOURCE_EXP = BACE/'experiments/prompt_sensitivity_v1'
CONDITIONS = ('raw_cards', 'all_ec', 'candidate_ec')
SEED = 20261002
sys.dont_write_bytecode = True
sys.path.insert(0, str(BACE/'script/evaluation'))
import run_generation_claim_support_assessment as native
import external_evaluation as external

def read(path):
    return json.loads(Path(path).read_text())

def rows(path):
    with Path(path).open() as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            h.update(block)
    return h.hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def rank(namespace, value):
    return hashlib.sha256(f'{SEED}|{namespace}|{value}'.encode()).hexdigest()

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)

@lru_cache(maxsize=4)
def condition_bundle(condition=None):
    config, _, _, schema, _ = native.load_and_validate_configuration(
        BACE/'config/evaluation/configs/generation_claim_support_config.json')
    config = copy.deepcopy(config)
    path = EXP/'judge_prompt.txt'
    config['prompt'] = {'file':str(path), 'version':'evidence_chain_judge_v1', 'sha256':sha(path)}
    return config, path.read_text(), schema

def replay_job(saved, condition):
    """Keep native schema/executor and DC; substitute only evidence units."""
    config, _, _ = condition_bundle()
    job = copy.deepcopy(saved['job'])
    case = saved['evidence_case']
    if condition == 'all_ec':
        job['dynamic_input']['ec_claims'] = copy.deepcopy(case['all_ec_input'])
    elif condition == 'raw_cards':
        units = case['raw_units']
        job['dynamic_input']['ec_claims'] = [
            {'ec_claim_id':x['alias'], 'ec_text':x['text']} for x in units]
        job['ec_original_by_alias'] = {x['alias']:x['unit_id'] for x in units}
    elif condition != 'candidate_ec':
        raise ValueError(condition)
    unit_aliases = [x['ec_claim_id'] for x in job['dynamic_input']['ec_claims']]
    unit_ids = [job['ec_original_by_alias'][x] for x in unit_aliases]
    job['candidate_ec_aliases'] = unit_aliases
    job['requires_model'] = bool(unit_aliases)
    job['job_input_hash'] = native.sha256_json(job['dynamic_input'])
    job['call_identity'].update(candidate_ec_ids=unit_ids,
        job_input_hash=job['job_input_hash'], prompt_version=config['prompt']['version'],
        prompt_sha256=config['prompt']['sha256'])
    job['call_id'] = 'support_'+native.sha256_json(job['call_identity'])[:32]
    return job

def verify_frozen():
    frozen = read(EXP/'freeze.json')
    for name, digest in frozen['files'].items():
        if sha(ROOT/name) != digest:
            raise ValueError(f'Frozen file changed: {name}')
    return frozen
