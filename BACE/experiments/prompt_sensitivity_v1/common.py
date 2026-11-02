"""Shared paths and exact native support replay; no model calls on import."""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
from functools import lru_cache
from datetime import datetime, timezone

EXP = Path(__file__).resolve().parent
BACE = EXP.parents[1]
ROOT = BACE.parent
RESULTS = BACE / 'results/prompt_sensitivity_v1'
ANALYSIS = BACE / 'analysis/outputs/evaluator_gap/prompt_sensitivity'
sys.dont_write_bytecode = True
sys.path.insert(0, str(BACE / 'script/evaluation'))
import run_generation_claim_support_assessment as native

CONDITIONS = ('ragas_style', 'ragchecker_style')
SEED = 20261001

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(2**20), b''):
            h.update(chunk)
    return h.hexdigest()

def rank(namespace, value):
    return hashlib.sha256(f'{SEED}|{namespace}|{value}'.encode()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def rows(path):
    with Path(path).open() as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    temp.replace(path)

def now():
    return datetime.now(timezone.utc).isoformat()

def native_configuration():
    return native.load_and_validate_configuration(
        BACE / 'config/evaluation/configs/generation_claim_support_config.json')

@lru_cache(maxsize=3)
def condition_bundle(condition):
    config, original, _, schema, _ = native_configuration()
    config = copy.deepcopy(config)
    if condition == 'original_repeat':
        prompt = original
    else:
        path = EXP / 'prompts' / f'{condition}_v1.txt'
        prompt = path.read_text()
        config['prompt'] = {'file': str(path), 'version': f'prompt_sensitivity_{condition}_v1',
                            'sha256': sha(path)}
    return config, prompt, schema

def replay_job(saved, condition):
    config, _, _ = condition_bundle(condition)
    job = copy.deepcopy(saved['job'])
    job['call_identity']['prompt_version'] = config['prompt']['version']
    job['call_identity']['prompt_sha256'] = config['prompt']['sha256']
    # Native hashes deliberately remain native. A separate condition/run ledger
    # prevents historical cache reuse even when the repeat call_id is identical.
    job['call_id'] = 'support_' + native.sha256_json(job['call_identity'])[:32]
    return job

def verify_frozen():
    frozen = read(EXP / 'freeze.json')
    for path, expected in frozen['files'].items():
        if sha(ROOT / path) != expected:
            raise ValueError(f'Frozen experiment file changed: {path}')
    return frozen
