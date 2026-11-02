"""Freeze common criteria and evidence-layer inputs before any new model call."""
import argparse
import difflib
import importlib.metadata
from common import EXP, BACE, ROOT, RESULTS, SOURCE_EXP, read, write, sha, now

def main(criterion):
    if (EXP/'freeze.json').exists() or any(RESULTS.glob('runs/*/calls.jsonl')):
        raise RuntimeError('Already frozen or called; do not retune this version.')
    source = (BACE/'config/evaluation/prompts/generation_claim_support_prompt_v1.txt'
              if criterion == 'bace' else SOURCE_EXP/'prompts'/f'{criterion}_v1.txt')
    original = source.read_text()
    prompt = original.replace('atomic\nevidence claims', 'evidence units')
    prompt = prompt.replace('atomic evidence claims', 'evidence units')
    prompt = prompt.replace('evidence claims', 'evidence units')
    prompt = prompt.replace('evidence claim', 'evidence unit')
    prompt = prompt.replace('evidence-claim identifiers', 'evidence-unit identifiers')
    anchor = 'Do not assess whether the evidence units themselves are true.'
    assert anchor in prompt
    prompt = prompt.replace(anchor, anchor+'\n\nAn evidence unit may contain one or several propositions. Apply the same\nsupport criteria to complete source passages and extracted propositions.\nThe ec_claims, ec_claim_id, ec_text and ec_claim_ids field names refer to these\nevidence units. Identifiers do not imply that a unit is atomic.')
    (EXP/'judge_prompt.txt').write_text(prompt)
    (EXP/'judge_prompt.diff').write_text(''.join(difflib.unified_diff(
        original.splitlines(True),prompt.splitlines(True),fromfile=str(source.relative_to(ROOT)),
        tofile='evidence_chain_common_judge')))
    plan = read(EXP/'input_plan.json')
    plan.update(criterion=criterion, criterion_source=str(source.relative_to(ROOT)),
        criterion_source_sha256=sha(source), judge_prompt_sha256=sha(EXP/'judge_prompt.txt'),
        frozen_at_utc=now(), status='FROZEN_BEFORE_FIRST_MODEL_CALL')
    write(EXP/'plan.json',plan)
    previous = read(SOURCE_EXP/'freeze.json')
    files = dict(previous['files'])
    files.update(plan['source_hashes'])
    for case in plan['cases']:
        files[case['cache_path']] = case['cache_sha256']
    for path in EXP.iterdir():
        if path.is_file() and path.name != 'freeze.json':
            files[str(path.relative_to(ROOT))] = sha(path)
    files[str(source.relative_to(ROOT))] = sha(source)
    environment = {d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
    assert environment == previous['environment'], 'Native environment changed'
    for name,digest in files.items():
        assert sha(ROOT/name)==digest, name
    write(EXP/'freeze.json', {'status':'FROZEN_BEFORE_FIRST_MODEL_CALL',
        'created_at_utc':now(),'files':files,'environment':environment,
        'counts':plan['counts'],'criterion':criterion})
    print(f'Frozen {criterion} criterion, {len(files)} files, {len(plan["pilot_jobs"])*3} technical-pilot records.')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--criterion',choices=['bace','ragas_style','ragchecker_style'],default='bace')
    main(parser.parse_args().criterion)
