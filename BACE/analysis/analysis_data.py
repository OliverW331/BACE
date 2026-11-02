"""Read-only extraction of verified, native experiment results for four notebooks."""
from __future__ import annotations
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BACE = HERE.parent
ROOT = BACE.parent
OUT = HERE / 'outputs'
CACHE = OUT / 'snapshot'
SEED = 20260921
for directory in [BACE / 'script', BACE / 'script/evaluation']:
    sys.path.insert(0, str(directory))
from metrics import LABELS, bace_metrics, external_metrics
from external_evaluation import adapt_case
from acceptance import validate_run_freeze

STAGES = ('generation', 'direct', 'integrated', 'atomic', 'dedup', 'candidates', 'support', 'diagnosis', 'ragchecker', 'ragas')
BACE_STAGES = STAGES[:8]
METHODS = {'BACE': 'bace_support_rate_all_dc', 'RAGChecker': 'ragchecker_faithfulness', 'RAGAS': 'ragas_faithfulness'}
TASKS = ['E1-1','E1-3','E1-4','E1-6','S1-1','S1-4','S1-5','S1-14','G1-1','G1-2','G1-3','G1-4']
TYPE_NAMES = {'narrative': 'PDF narrative', 'pdf_narrative': 'PDF narrative', 'pdf_table_row': 'PDF table row', 'table_row': 'PDF table row', 'csv_metric': 'CSV metric'}

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def rows(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream if line.strip()]

def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')

class Sources:
    def __init__(self):
        self.hashes = {}
        self.stats = {}
    def record(self, path, expected=None):
        path = Path(path).resolve()
        key = str(path.relative_to(ROOT))
        if key not in self.hashes:
            before = path.stat()
            digest = sha(path)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError(f'Source changed while reading: {key}')
            self.hashes[key] = digest
            self.stats[key] = (after.st_size, after.st_mtime_ns)
        if expected is not None and self.hashes[key] != expected:
            raise ValueError(f'Source does not match frozen receipt: {key}')
        return path
    def json(self, path, expected=None):
        return read(self.record(path, expected))
    def jsonl(self, path, expected=None):
        return rows(self.record(path, expected))
    def finish(self):
        for key, before in self.stats.items():
            s = (ROOT/key).stat()
            if tuple(before) != (s.st_size, s.st_mtime_ns):
                raise ValueError(f'Source changed during analysis: {key}')

def run_identity():
    run = BACE/'results/main_v1'
    execution = read(run/'execution_status.json')
    # A process must actually be alive; a historical PID alone is not a running job.
    proc = Path('/proc') / str(execution.get('pid', -1)) / 'cmdline'
    if proc.exists():
        command = proc.read_bytes().replace(b'\0', b' ').decode(errors='replace')
        if 'BACE/run.py' in command or 'run.py main' in command:
            raise RuntimeError('Main experiment is running; wait for a stable source snapshot.')
    if execution.get('active_cases') or execution['status'] in ('running', 'finalizing'):
        raise RuntimeError('Run state is active; inspect the live run before analysing.')
    return run, execution

def build_snapshot():
    run, execution = run_identity()
    src = Sources()
    manifest = src.json(run/'manifest.json')
    freeze = src.json(BACE/'config/freeze.json')
    validate_run_freeze(manifest['freeze_sha256'])
    # Validate consumed frozen scientific inputs and calculation code, without loading embeddings.
    for path in ['config/experiment.json','config/tasks.json','script/evaluation/metrics.py',
                 'script/evaluation/external_evaluation.py','evidence/sample/sample.json',
                 'evidence/sample/sampling_frame.json']:
        src.record(BACE/path, freeze['files'].get(path))
    sample = src.json(BACE/'evidence/sample/sample.json')
    frame = src.json(BACE/'evidence/sample/sampling_frame.json')
    for name, expected in sample['source_hashes'].items():
        src.record(Path(name), expected)
    src.record(run/'execution_status.json')
    global_path=BACE/'evidence/inputs/generation_cases.jsonl'
    src.record(global_path,manifest['generation_input_sha256'])
    global_cases={}
    with global_path.open() as stream:
        for line in stream:
            case=json.loads(line)
            global_cases[case['generation_case_id']]=hashlib.sha256(json.dumps(case,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    assert set(global_cases)==set(manifest['case_ids'])
    visible_text_hashes={}
    selected = {x['company_id']:x for x in sample['selected']}
    selection = pd.DataFrame([{k:v for k,v in x.items() if k not in ('csv_valid_counts','pdf_reports','missing_csv_years','missing_pdf_years')} | {'selected':x['company_id'] in selected,'missing_csv_year_count':len(x['missing_csv_years']),'missing_pdf_year_count':len(x['missing_pdf_years'])} for x in frame])
    coverage = []
    for x in frame:
        for year in range(2015,2024):
            coverage.append({'company_id':x['company_id'],'company_name':x['company_name'],'year':year,
                             'eligible':x['eligible'],'selected':x['company_id'] in selected,
                             'csv_valid_metrics':x['csv_valid_counts'].get(str(year),0),
                             'pdf_valid_headers':len(x['pdf_reports'].get(str(year),[])) if year<2023 else np.nan})
    metrics, claim_rows, external_rows, visible, lengths = [], [], [], [], Counter()
    example_ids = set()
    for i,cid in enumerate(manifest['case_ids']):
        base = run/'cases'/cid
        state = src.json(base/'state.json')
        receipts = state['stages']
        def stage_rows(stage, name):
            path = base/name
            key = str(path.relative_to(BACE))
            return src.jsonl(path, receipts[stage]['artifacts'][key])
        case = src.jsonl(base/'inputs/generation_cases.jsonl')[0]
        assert case['generation_case_id'] == cid
        assert hashlib.sha256(json.dumps(case,sort_keys=True,ensure_ascii=False).encode()).hexdigest()==global_cases[cid]
        row = {'generation_case_id':cid, 'company_id':case['company_id'], 'company_name':case['company_name'],
               'sector':selected[case['company_id']]['primary_sics_sector'], 'country':selected[case['company_id']]['country'],
               'year':case['target_reporting_year'],'task_id':case['task_id'], 'task':case['task_id'].split('_')[0],
               'task_title':case['task_title'], 'standard':case['task_id'].split('-')[0], 'state_status':state.get('status', 'partial'),
               **{'stage_'+s:s in receipts for s in STAGES}}
        for card in case['prompt_evidence']:
            if not card['shown_in_prompt']:
                continue
            assert row['year']-4 <= card['source_year'] <= row['year']-(card['source_type']=='pdf')
            text_hash=hashlib.sha256(card['retrieval_text'].encode()).hexdigest()
            if card['evidence_id'] in visible_text_hashes: assert visible_text_hashes[card['evidence_id']]==text_hash
            visible_text_hashes[card['evidence_id']]=text_hash
            visible.append({'generation_case_id':cid,'company_id':case['company_id'],'target_year':row['year'],'task':row['task'],
                            'evidence_id':card['evidence_id'],'type':TYPE_NAMES[card['evidence_type']], 'source_year':card['source_year'],
                            'source_file':card['source_file'],'characters':len(card['retrieval_text'])})
            if i == 0:
                example_ids.add(card['evidence_id'])
        output = stage_rows('generation','generation/generated_disclosures.jsonl')
        assert len(output)==1 and output[0]['length_within_requested_range']
        response = output[0]
        adapted = adapt_case(case, response)
        row['word_count'] = response['generated_word_count']
        row['visible_evidence_count'] = len(adapted['contexts'])
        row['bace_complete'] = all(s in receipts for s in BACE_STAGES)
        if row['bace_complete']:
            ec = stage_rows('dedup','bace/dedup/ec_claims.jsonl')
            dc = stage_rows('dedup','bace/dedup/dc_claims.jsonl')
            support = stage_rows('support','bace/support/dc_support_sets.jsonl')
            diagnosis = stage_rows('diagnosis','bace/diagnosis/dc_unsupported_diagnoses.jsonl')
            candidates = stage_rows('candidates','bace/candidates/dc_candidate_ecs.jsonl')
            row.update(bace_metrics(ec,dc,support,diagnosis,candidates))
            si={x['dc_claim_id']:x['support_sets'] for x in support}
            di={x['dc_claim_id']:x for x in diagnosis}
            ci={x['dc_claim_id']:x['candidate_ec_ids'] for x in candidates}
            for d in dc:
                did=d['dc_id']; ss=si[did]
                label='direct' if any(x['support_type']=='direct' for x in ss) else 'inferred' if ss else di[did]['unsupported_label']
                qs=[q for p in d['dc_provenance'] for q in p['source_quotes']]
                claim_rows.append({'generation_case_id':cid,'dc_id':did,'dc_text':d['dc_text'],'label':label,
                                   'candidate_count':len(ci[did]),'support_set_count':len(ss),
                                   'min_support_set_size':min((len(x['ec_claim_ids']) for x in ss), default=0),
                                   'exact_quote_count':sum(q in response['generated_text'] for q in qs),'quote_count':len(qs)})
        for framework in ('ragchecker','ragas'):
            row[framework+'_complete'] = framework in receipts
            if framework in receipts:
                record = stage_rows(framework, f'evaluation/{framework}/results.jsonl')[-1]
                row.update(external_metrics(record,framework,adapted))
                for c in record['claims']:
                    external_rows.append({'generation_case_id':cid,'framework':framework,'claim_index':c['claim_index'],
                                          'claim_text':' '.join(c['claim']) if isinstance(c['claim'],list) else c['claim'],
                                          'supported':c['supported']})
        metrics.append(row)
        if (i+1)%300==0:
            print(f'Validated native results: {i+1}/{len(manifest["case_ids"])}', flush=True)
    # Stream all canonical cards; retain aggregates and exact observed length frequencies.
    canonical = Counter(); examples=[]; source_pdfs={}; verified_visible=set()
    for path in sorted((BACE/'evidence/canonical/indexes').glob('*.jsonl')):
        src.record(path, freeze['files'].get(str(path.relative_to(BACE))))
        with path.open() as f:
            for line in f:
                c=json.loads(line); typ=TYPE_NAMES[c['evidence_type']]
                canonical[(c['company_id'],c['source_year'],typ)]+=1
                lengths[(typ,len(c['retrieval_text']))]+=1
                if c['evidence_id'] in visible_text_hashes:
                    assert hashlib.sha256(c['retrieval_text'].encode()).hexdigest()==visible_text_hashes[c['evidence_id']]
                    verified_visible.add(c['evidence_id'])
                if c['evidence_id'] in example_ids:
                    examples.append(c)
                if c['source_type']=='pdf': source_pdfs[c['source_file']]=c['source_sha256']
        print(f'Counted canonical index: {path.name}', flush=True)
    assert verified_visible==set(visible_text_hashes)
    packages=[]
    for path in sorted((BACE/'evidence/builds/main_v1/companies').glob('*/manifests/package_*.json')):
        p=src.json(path,freeze['files'].get(str(path.relative_to(BACE))))
        for typ,ids in p['evidence_card_ids'].items():
            packages.append({'company_id':p['company_id'],'company_name':p['company_name'],'year':p['target_reporting_year'],'type':TYPE_NAMES[typ],'cards':len(ids)})
    df=pd.DataFrame(metrics)
    assert len(df)==len(manifest['case_ids']) and df.generation_case_id.is_unique
    assert set(df.loc[df.bace_complete & df.ragchecker_complete & df.ragas_complete,'generation_case_id'])==set(execution['completed_case_ids'])
    src.finish()
    CACHE.mkdir(parents=True, exist_ok=True)
    tables={'metrics':df,'claims':pd.DataFrame(claim_rows),'external_claims':pd.DataFrame(external_rows),'selection':selection,'coverage':pd.DataFrame(coverage),
            'visible':pd.DataFrame(visible),'canonical_counts':pd.DataFrame([dict(company_id=c,year=y,type=t,cards=n) for (c,y,t),n in canonical.items()]),
            'length_counts':pd.DataFrame([dict(type=t,characters=n,count=k) for (t,n),k in lengths.items()]),'packages':pd.DataFrame(packages)}
    for name,table in tables.items(): table.to_csv(CACHE/f'{name}.csv',index=False)
    save_json(CACHE/'canonical_examples.json',examples)
    save_json(CACHE/'source_pdfs.json',source_pdfs)
    save_json(CACHE/'sample.json',sample)
    save_json(CACHE/'execution.json',execution)
    save_json(CACHE/'sources.json',src.hashes)
    save_json(CACHE/'manifest.json',{'builder_sha256':sha(__file__),'case_count':len(df),'bace_complete':int(df.bace_complete.sum()),
              'source_files':len(src.hashes),'verification':'Exact hashes for consumed stage artifacts, source inputs and canonical indices; native claim identifiers, score denominators and shared contexts validated. Raw model-call histories and complete extraction lineage are not re-audited.',
              'seed':SEED,'tables':{n:sha(CACHE/f'{n}.csv') for n in tables}})
    return tables

def load_snapshot():
    run_identity()
    if not (CACHE/'manifest.json').exists() or read(CACHE/'manifest.json')['builder_sha256']!=sha(__file__):
        return build_snapshot()
    hashes=read(CACHE/'sources.json')
    if any(not (ROOT/p).exists() or sha(ROOT/p)!=h for p,h in hashes.items()):
        return build_snapshot()
    manifest=read(CACHE/'manifest.json')
    for name,h in manifest['tables'].items():
        if sha(CACHE/f'{name}.csv')!=h: raise ValueError('Derived cache was modified: '+name)
    return {n:pd.read_csv(CACHE/f'{n}.csv') for n in manifest['tables']}

def company_bootstrap(frame, column, draws=2000, seed=SEED):
    """Percentile interval; resample companies, retain every selected disclosure."""
    valid=frame.dropna(subset=[column])
    grouped=valid.groupby('company_id')[column].agg(['sum','count'])
    rng=np.random.default_rng(seed)
    take=rng.integers(0,len(grouped),size=(draws,len(grouped)))
    replicates=grouped['sum'].to_numpy()[take].sum(axis=1)/grouped['count'].to_numpy()[take].sum(axis=1)
    low,high=np.quantile(replicates,[.025,.975])
    return {'mean':float(valid[column].mean()),'low':float(low),'high':float(high),
            'companies':len(grouped),'disclosures':len(valid),'draws':draws}

def case_material(cid):
    base=BACE/'results/main_v1/cases'/cid
    return {'input':rows(base/'inputs/generation_cases.jsonl')[0],
            'response':rows(base/'generation/generated_disclosures.jsonl')[0],
            'dc':rows(base/'bace/dedup/dc_claims.jsonl'),'ec':rows(base/'bace/dedup/ec_claims.jsonl'),
            'support':rows(base/'bace/support/dc_support_sets.jsonl'),
            'diagnosis':rows(base/'bace/diagnosis/dc_unsupported_diagnoses.jsonl'),
            'candidates':rows(base/'bace/candidates/dc_candidate_ecs.jsonl'),
            **{f:rows(base/f'evaluation/{f}/results.jsonl')[-1] for f in ['ragchecker','ragas']}}

if __name__=='__main__':
    t=load_snapshot()
    print(t['metrics'][list(METHODS.values())].agg(['count','mean']).to_string())
