"""Build resumable vectors and freeze all 1,800 retrieval/generation inputs."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys

import numpy as np

from common import ROOT, csvfile, digest, jsonl, read, rows, write
sys.path.insert(0,str(ROOT/'script/rag'))
import embed_evidence_cards as embedding
import run_w2_retrieval_sanity_check as retrieval
import build_w2_generation_inputs as generation

BASE = ROOT/'evidence'
VECTORS = BASE/'embeddings'
INPUTS = BASE/'inputs'
SETTING = 'stratified_by_evidence_type_n10'


def text_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def embed_texts(texts):
    return embedding.encode_texts_openai(
        model_name=os.environ['TEXT_EMBEDDING_3_LARGE_AZURE_OPENAI_DEPLOYMENT'],texts=texts,
        batch_size=len(texts),normalize=True,api_key_env='TEXT_EMBEDDING_3_LARGE_AZURE_OPENAI_API_KEY',
        base_url=embedding.normalize_azure_base_url(os.environ['TEXT_EMBEDDING_3_LARGE_AZURE_OPENAI_ENDPOINT']),
        dimensions=3072,max_retries=3,request_timeout=120)


def cache_chunk(texts, namespace='documents'):
    key = text_hash(json.dumps({'texts':texts,'model':'text-embedding-3-large','dimensions':3072,'deployment':os.environ['TEXT_EMBEDDING_3_LARGE_AZURE_OPENAI_DEPLOYMENT']},sort_keys=True))
    path = VECTORS/'batches'/namespace/(key+'.npy')
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        matrix = np.load(path)
    else:
        matrix = embed_texts(texts)
        with path.with_suffix('.tmp').open('wb') as f:
            np.save(f,matrix)
        path.with_suffix('.tmp').replace(path)
    if matrix.shape != (len(texts),3072) or not np.isfinite(matrix).all() or not np.allclose(np.linalg.norm(matrix,axis=1),1,atol=1e-5):
        raise ValueError('Invalid cached vectors: '+str(path))
    write(path.with_suffix('.json'),{'batch_file':str(path.relative_to(VECTORS)),'text_hashes':[text_hash(t) for t in texts]})
    return matrix


def make_vectors(cards):
    """Reuse exact prior text vectors, then embed only previously unseen text."""
    VECTORS.mkdir(parents=True,exist_ok=True)
    mapping = [{'evidence_id':c['evidence_id'],'company_id':c['company_id'],'retrieval_text_hash':text_hash(c['retrieval_text']),'embedding_row':i} for i,c in enumerate(cards)]
    fingerprint = text_hash(json.dumps(mapping,sort_keys=True))
    manifest_path = VECTORS/'manifest.json'
    if manifest_path.exists():
        manifest = read(manifest_path)
        if manifest['input_fingerprint'] != fingerprint:
            raise ValueError('Vector inputs changed')
        for name,value in manifest['artifacts'].items():
            if digest(VECTORS/name) != value:
                raise ValueError('Vector artifact changed: '+name)
        return np.load(VECTORS/'embeddings.npy',mmap_mode='r'),mapping
    matrix = np.lib.format.open_memmap(VECTORS/'embeddings.tmp.npy',mode='w+',dtype='float32',shape=(len(cards),3072))
    legacy = ROOT.parent/'evidence_pilot/embeddings/pilot_embedding_models/text-embedding-3-large'
    legacy_meta = {}
    if (legacy/'embedding_manifest.json').exists():
        identity = read(legacy/'embedding_manifest.json')
        if identity['model_name_or_path']=='text-embedding-3-large' and identity['embedding_dimension']==3072 and identity['document_prefix']=='' and identity['api_model_name']==os.environ['TEXT_EMBEDDING_3_LARGE_AZURE_OPENAI_DEPLOYMENT']:
            legacy_meta = {r['retrieval_text_hash']:r['embedding_row'] for r in rows(legacy/'card_metadata.jsonl')}
            legacy_matrix = np.load(legacy/'embeddings.npy',mmap_mode='r')
    pending, reused = [], 0
    cached_texts = {}
    for path in sorted((VECTORS/'batches/documents').glob('*.json')):
        batch = read(path)
        for i,key in enumerate(batch['text_hashes']):
            cached_texts[key] = (batch['batch_file'],i)
    cached_matrices = {}
    preparation_reused = 0
    for i,c in enumerate(cards):
        old = legacy_meta.get(mapping[i]['retrieval_text_hash'])
        if old is not None:
            matrix[i] = legacy_matrix[old]
            reused += 1
        elif mapping[i]['retrieval_text_hash'] in cached_texts:
            filename,row = cached_texts[mapping[i]['retrieval_text_hash']]
            if filename not in cached_matrices:
                cached_matrices[filename] = np.load(VECTORS/filename,mmap_mode='r')
            matrix[i] = cached_matrices[filename][row]
            preparation_reused += 1
        else:
            pending.append(i)
    import tiktoken
    encoder = tiktoken.get_encoding('cl100k_base')
    limits = read(ROOT/'config/experiment.json')['embedding']
    chunks, chunk, token_count = [], [], 0
    for i in pending:
        count = len(encoder.encode_ordinary(cards[i]['retrieval_text']))
        if chunk and (len(chunk)>=limits['batch_size'] or token_count+count>limits['max_batch_tokens']):
            chunks.append(chunk)
            chunk,token_count = [],0
        chunk.append(i)
        token_count += count
    if chunk:
        chunks.append(chunk)
    print(f'Vectors: {len(cards)} cards, {reused} exact prior-stage vectors, {preparation_reused} cached preparation vectors, {len(pending)} new',flush=True)
    failures = []
    with ThreadPoolExecutor(max_workers=read(ROOT/'config/experiment.json')['embedding']['workers']) as pool:
        futures = {pool.submit(cache_chunk,[cards[i]['retrieval_text'] for i in ids]):ids for ids in chunks}
        for n,future in enumerate(as_completed(futures),1):
            try:
                matrix[futures[future]] = future.result()
            except Exception as exc:
                failures.append({'card_ids':[cards[i]['evidence_id'] for i in futures[future]],'error':str(exc)})
                write(VECTORS/'batch_failures.json',failures)
                print(f'Embedding batch failed; cached successful batches remain reusable: {exc}',flush=True)
            if n%20==0 or n==len(chunks):
                print(f'Vector chunks {n}/{len(chunks)}',flush=True)
    if failures:
        raise RuntimeError(f'{len(failures)} embedding batches failed; see batch_failures.json and rerun preparation')
    matrix.flush()
    del matrix
    (VECTORS/'embeddings.tmp.npy').replace(VECTORS/'embeddings.npy')
    matrix = np.load(VECTORS/'embeddings.npy',mmap_mode='r')
    jsonl(VECTORS/'card_metadata.jsonl',mapping)
    write(manifest_path,{'schema_version':'bace_vector_manifest_v1','input_fingerprint':fingerprint,
          'model':'text-embedding-3-large','dimensions':3072,'provider':'azure_openai','normalized':True,
          'index_type':'exact_cosine_matrix_with_evidence_id_rows',
          'document_prefix':'','card_count':len(cards),'reused_exact_text_vectors':reused,'reused_preparation_vectors':preparation_reused,
          'legacy_matrix_sha256':digest(legacy/'embeddings.npy') if legacy_meta else None,
          'artifacts':{n:digest(VECTORS/n) for n in ['embeddings.npy','card_metadata.jsonl']}})
    shutil.rmtree(VECTORS/'batches/documents',ignore_errors=True)
    return matrix,mapping


def input_fingerprint(rconfig,gconfig):
    return text_hash(json.dumps({'vectors':digest(VECTORS/'manifest.json'),'build':digest(BASE/'builds/main_v1/build_config.json'),'config':digest(ROOT/'config/experiment.json'),'tasks':digest(ROOT/'config/tasks.json'),'queries':digest(ROOT/'config/queries.json'),'retrieval':rconfig,'generation':gconfig},sort_keys=True))


def prepare():
    config = read(ROOT/'config/experiment.json')
    specs = retrieval.load_task_specs(ROOT/'config/tasks.json')
    templates = retrieval.load_query_templates(ROOT/'config/queries.json')
    if set(specs)-set(templates):
        raise ValueError('Each task requires explicit retrieval templates')
    rconfig = retrieval.load_retrieval_config(ROOT/config['retrieval'],'hybrid_rrf')
    gconfig = generation.load_generation_config(ROOT/config['generation']['prompt'])
    final_manifest_path = INPUTS/'generation_input_manifest.json'
    if final_manifest_path.exists() and read(final_manifest_path).get('artifact_sha256'):
        final = read(final_manifest_path)
        if final['input_fingerprint'] != input_fingerprint(rconfig,gconfig):
            raise ValueError('Prepared inputs differ from the current configuration')
        groups = [(INPUTS,final['artifact_sha256']),
                  (VECTORS,read(VECTORS/'manifest.json')['artifacts']),
                  (BASE/'canonical/indexes',read(BASE/'builds/main_v1/build_config.json')['index_hashes'])]
        for directory,hashes in groups:
            for name,expected in hashes.items():
                if digest(directory/name) != expected:
                    raise ValueError('Prepared input changed: '+name)
        print('Reused all 1,800 prepared inputs',flush=True)
        return
    manifests = retrieval.load_package_manifests(BASE,'main_v1',set(config['target_years']),None,None)
    cases = retrieval.build_cases(manifests,list(specs),specs)
    if len(cases)!=1800:
        raise ValueError('Expected exactly 1,800 cases')
    cards = sorted(retrieval.load_evidence_cards(BASE).values(),key=lambda c:c['evidence_id'])
    lookup = {c['evidence_id']:c for c in cards}
    matrix,mapping = make_vectors(cards)
    id_to_index = {r['evidence_id']:r['embedding_row'] for r in mapping}
    artifacts = retrieval.EmbeddingArtifacts(VECTORS,VECTORS/'embeddings.npy',VECTORS/'card_metadata.jsonl',None,matrix,id_to_index,{v:k for k,v in id_to_index.items()},{})
    bundles = [retrieval.render_query_bundle(c,specs[c['task_id']],templates) for c in cases]
    queries = sorted(set(s['query_text'] for b in bundles for s in b['subqueries']))
    query_vectors = {}
    for start in range(0,len(queries),256):
        texts = queries[start:start+256]
        values = cache_chunk(texts,'queries')
        query_vectors.update(zip(texts,values))
    # Run the unchanged rank/fusion/selection functions against frozen vectors.
    # Query preparation happens once, so the main run needs no retrieval API calls.
    retrieval.embed_query = lambda text, model_config:query_vectors[text]
    spec = {'setting_name':SETTING,'selection_mode':'stratified_by_evidence_type','per_evidence_type_top_n':10,'evidence_block_order':['narrative','pdf_table_row','csv_metric']}
    records, generated, summary = [], [], []
    source_fingerprint = input_fingerprint(rconfig,gconfig)
    for n,(case,bundle) in enumerate(zip(cases,bundles),1):
        path = INPUTS/'retrieval_cases'/(case['case_id']+'.json')
        if path.exists():
            cached = read(path)
            if cached['input_fingerprint']!=source_fingerprint:
                raise ValueError('Frozen retrieval inputs changed')
            record = cached['record']
        else:
            _,eligible,validation = retrieval.validate_candidate_pool(case,lookup,False)
            if validation.get('missing_manifest_references'):
                raise ValueError('Missing package references')
            ranked,diagnostics,stats = retrieval.run_case_retrieval(case,specs[case['task_id']],bundle,eligible,artifacts,{'normalize_corpus_embeddings':False},rconfig)
            if stats['missing_embedding_mappings']:
                raise ValueError('Missing embedding mappings')
            record = retrieval.make_result_records(case,bundle,ranked,lookup,validation,[spec],rconfig)[SETTING]
            record['missing_embedding_mappings'] = 0
            write(path,{'input_fingerprint':source_fingerprint,'record':record})
        gcase = generation.build_generation_case(record,embedding_model='text_embedding_3_large',retrieval_condition='hybrid_rrf',selection_setting=SETTING,task_specs=specs,group_order=spec['evidence_block_order'],generation_config=gconfig)
        records.append(record)
        generated.append(gcase)
        summary.append(generation.summary_row(gcase))
        if n%30==0:
            print(f'Retrieval cases {n}/1800',flush=True)
    jsonl(INPUTS/'retrieval_results.jsonl',records)
    jsonl(INPUTS/'query_bundles.jsonl',bundles)
    jsonl(INPUTS/'generation_cases.jsonl',generated)
    csvfile(INPUTS/'generation_cases_summary.csv',summary)
    write(INPUTS/'generation_input_manifest.json',{'schema_version':'w2_generation_input_manifest_v1','script_version':'bace_prepare_inputs_v1','generation_case_count':len(generated),'input_fingerprint':source_fingerprint,'generation_cases_sha256':digest(INPUTS/'generation_cases.jsonl'),'generation_config_version':gconfig['config_version'],'generation_config_status':'frozen','prompt_layout_version':generation.PROMPT_LAYOUT_VERSION,'generation_input_schema_version':generation.GENERATION_INPUT_SCHEMA_VERSION,'evidence_id_in_prompt':False,'prompt_label_maps_to_evidence_id':True,'citation_required':False,'evidence_group_order':spec['evidence_block_order'],'instruction_template':gconfig['instruction_template'],'output_length_words':gconfig['output_length_words']})
    selected = read(BASE/'sample/sample.json')['selected']
    sectors = sorted(set(c['primary_sics_sector'] for c in selected))
    pilot = []
    for i,task in enumerate(specs):
        sector = sectors[i%len(sectors)]
        company = [c for c in selected if c['primary_sics_sector']==sector][i//len(sectors)]
        year = config['target_years'][i%5]
        c = next(c for c in generated if c['company_id']==company['company_id'] and c['target_reporting_year']==year and c['task_id']==task)
        pilot.append({k:c[k] for k in ['generation_case_id','company_id','company_name','target_reporting_year','task_id']})
    write(INPUTS/'pilot_selection.json',{'purpose':'Prespecified engineering pilot covering all 12 tasks; no score-based selection.','cases':pilot})
    final = read(final_manifest_path)
    final['artifact_sha256'] = {name:digest(INPUTS/name) for name in ['retrieval_results.jsonl','query_bundles.jsonl','generation_cases.jsonl','generation_cases_summary.csv','pilot_selection.json']}
    write(final_manifest_path,final)
    shutil.rmtree(INPUTS/'retrieval_cases')
    print('Prepared 1,800 generation inputs and 12 pilot case IDs',flush=True)


if __name__ == '__main__':
    prepare()
