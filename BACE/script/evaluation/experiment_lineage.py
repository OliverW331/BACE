"""Bind extraction directly to a new experiment's frozen generation artifacts."""
from pathlib import Path
from generation_claims import InputValidationError, read_json, read_jsonl, sha256_file
from run_generation_claim_extraction import validate_source_manifests

ROOT = Path(__file__).resolve().parents[2]


def load_plan_inputs(plan):
    names = ('generation_cases','generated_disclosures','generation_input_manifest','generation_run_manifest')
    inputs = {k:str((ROOT/plan['inputs'][k]).resolve()) for k in names}
    hashes = {k:sha256_file(Path(v)) for k,v in inputs.items()}
    if hashes != plan['input_hashes']:
        raise InputValidationError('Frozen experiment input changed')
    validate_source_manifests(
        generation_cases_path=Path(inputs['generation_cases']),
        generation_input_manifest_path=Path(inputs['generation_input_manifest']),
        generated_disclosures_path=Path(inputs['generated_disclosures']),
        generation_run_manifest_path=Path(inputs['generation_run_manifest']),
        case_count=len(read_jsonl(Path(inputs['generation_cases']))),
        disclosure_count=len(read_jsonl(Path(inputs['generated_disclosures']))))
    return inputs, hashes
