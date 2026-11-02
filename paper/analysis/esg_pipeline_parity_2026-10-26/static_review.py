"""Record prompt content, task-query structure and historical file differences."""
from pathlib import Path
import difflib
import hashlib
import json
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
HASHES = {}


def text(rel):
    p = ROOT / rel
    b = p.read_bytes()
    HASHES[rel] = hashlib.sha256(b).hexdigest()
    return b.decode()


def main():
    base = 'BACE/config/evaluation/prompts/'
    ec = text(base + 'generation_ec_claim_extraction_prompt_v8.txt')
    dc = text(base + 'generation_dc_claim_extraction_prompt_v8.txt')
    examples = []
    for match in re.finditer(r'^([A-F])\. (.+)$', ec, re.M):
        examples.append({'example': match[1], 'heading': match[2],
                         'line': ec[:match.start()].count('\n') + 1,
                         'domain_review': 'generic unresolved reference' if match[1] == 'D' else 'environment/climate/emissions'})
    queries = json.loads(text('BACE/config/queries.json'))
    tasks = json.loads(text('BACE/config/tasks.json'))
    old_tasks = json.loads(text('_archive/previous_stage_20260921/config/tasks/esrs_e1_s1_g1_task_specs.json'))
    old_by_id = {r['task_id']: r for r in old_tasks['tasks']}
    task_rows = [{'task_id': t['task_id'], 'field_names': sorted(t),
                  'query_count': len(queries['templates'][t['task_id']]),
                  'matches_archived_combined_task_record': t == old_by_id[t['task_id']]}
                 for t in tasks['tasks']]
    old = text('_archive/previous_stage_20260921/config/evaluation/prompts/generation_ec_claim_extraction_prompt_v1.txt')
    diff = ''.join(difflib.unified_diff(old.splitlines(keepends=True), ec.splitlines(keepends=True),
                   fromfile='archived_ec_extraction_v1.txt',tofile='current_ec_extraction_v8.txt'))
    (OUT / 'archived_v1_to_current_v8.diff').write_text(diff)
    history = [
        {'aspect':'Permitted source context', 'archived_v1':'Only Text is factual source material; Source fields organize records but do not assert facts.',
         'current_v8':'Visible Source labels can identify report/speaker and source-relative dates; report attribution is required for report-derived ECs.'},
        {'aspect':'Unresolved references','archived_v1':'Do not leave unresolved references; use a faithful non-specific description when no unique referent is available.',
         'current_v8':'Preserve genuinely unresolved expressions such as This and record unresolved_context; do not invent a referent type.'},
        {'aspect':'Worked examples','archived_v1':'No A-F worked-example section.',
         'current_v8':'Six A-F worked examples; five concern environment/climate/emissions and one is generic.'},
        {'aspect':'Output fields','archived_v1':'Claim text and source quotes.',
         'current_v8':'Adds unresolved_context and explicit unextracted_spans with reasons.'},
    ]
    source_paths = ['BACE/script/pipeline.py','BACE/script/evaluation/generation_claims.py',
                    'BACE/script/rag/build_w2_generation_inputs.py','BACE/script/rag/run_w2_retrieval_sanity_check.py',
                    'BACE/config/evaluation/prompts/generation_ec_claim_patch_review_prompt_v4.txt',
                    'BACE/config/evaluation/prompts/generation_ec_claim_atomicity_review_prompt_v2.txt',
                    'BACE/config/evaluation/prompts/generation_claim_support_prompt_v1.txt',
                    'BACE/config/evaluation/prompts/generation_claim_unsupported_diagnosis_prompt_v1.txt',
                    'paper/analysis/ec_metadata_audit_2026-10-26/summary.json',
                    'paper/analysis/r04_source_trace_2026-10-26/trace.json']
    for p in source_paths:
        text(p)
    r = {'access_date':'2026-10-26', 'direct_ec_dc_common_body_identical': ec.split('\nEVIDENCE RULES')[0] == dc.split('\nDISCLOSURE RULES')[0],
         'direct_examples': examples, 'task_query_inventory':task_rows,
         'historical_file_comparison':history,
         'historical_scope_limit':'This compares preserved prompt/config files. It does not identify a unique author-intended early E baseline or establish which old prompt version every historical output used.',
         'input_sha256':HASHES, 'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (OUT / 'static_review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'direct_common_body_equal':r['direct_ec_dc_common_body_identical'],
                      'example_count':len(examples),'all_tasks_same_keys':len({tuple(x['field_names']) for x in task_rows})==1}))


if __name__ == '__main__':
    main()
