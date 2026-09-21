"""Fail-closed experiment freeze and readiness gates; no model calls."""
from collections import Counter
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

from dotenv import load_dotenv
import numpy as np

from common import ROOT, digest, read, rows, write


def parallel_predecessor(frozen):
    """Reconstruct the accepted run before the parallel scheduling revision."""
    revision = frozen.get('parallel_revision')
    if revision is None:
        return frozen
    allowed = {'config/experiment.json','config/claim_execution.json','script/pipeline.py',
               'script/scheduling.py','script/progress.py','script/acceptance.py',
               'script/benchmark_claim_execution.py','script/benchmark_parallel.py',
               'script/evaluation/claim_execution.py','script/evaluation/external_evaluation.py',
               'script/evaluation/run_generation_claim_extraction.py',
               'script/evaluation/lineage_audit.py',
               'script/evaluation/run_generation_claim_semantic_dedup.py',
               'script/generation/run_w2_generation.py','tests/test_contracts.py',
               'tests/test_progress.py','tests/test_parallel.py','tests/test_claim_execution.py','results/runtime_validation/summary.json'}
    changes = revision['changed_files']
    if not changes or not set(changes)<=allowed:
        raise ValueError('Parallel revision cannot change scientific inputs, prompts or scoring')
    previous = {k:v for k,v in frozen.items() if k!='parallel_revision'}
    previous['files'] = dict(frozen['files'])
    for name,change in changes.items():
        if change['after']!=frozen['files'].get(name) or change['before']==change['after']:
            raise ValueError('Invalid parallel revision delta: '+name)
        if change['before'] is None:
            previous['files'].pop(name)
        else:
            previous['files'][name] = change['before']
    import hashlib
    if 'config/experiment.json' in changes:
        config = read(ROOT/'config/experiment.json')
        config['runtime']['case_workers'] = revision['previous_case_workers']
        encoded = (json.dumps(config,indent=2,ensure_ascii=True)+'\n').encode()
        if hashlib.sha256(encoded).hexdigest()!=changes['config/experiment.json']['before']:
            raise ValueError('Parallel revision changed more than the case worker count in the experiment protocol')
    encoded = (json.dumps(previous,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    if hashlib.sha256(encoded).hexdigest()!=revision['previous_freeze_sha256']:
        raise ValueError('Parallel predecessor cannot be reconstructed')
    return previous


def display_predecessor(frozen):
    """Bind the terminal-only revision to the exact accepted predecessor."""
    frozen = parallel_predecessor(frozen)
    revision = frozen.get('display_revision')
    if revision is None:
        return frozen
    allowed = {'script/progress.py','script/pipeline.py','script/summarize.py',
               'script/acceptance.py','tests/test_progress.py'}
    changes = revision['changed_files']
    if not changes or not set(changes)<=allowed:
        raise ValueError('Display revision cannot change model stages, inputs or scientific configuration')
    previous = {k:v for k,v in frozen.items() if k!='display_revision'}
    previous['files'] = dict(frozen['files'])
    for name,change in changes.items():
        if change['after']!=frozen['files'].get(name) or change['before']==change['after']:
            raise ValueError('Invalid display revision delta: '+name)
        if change['before'] is None:
            previous['files'].pop(name)
        else:
            previous['files'][name] = change['before']
    import hashlib
    encoded = (json.dumps(previous,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    if hashlib.sha256(encoded).hexdigest()!=revision['previous_freeze_sha256']:
        raise ValueError('Display predecessor cannot be reconstructed')
    return previous


def execution_predecessor(frozen):
    """Reconstruct the accepted predecessor; only scheduling files may differ."""
    frozen = display_predecessor(frozen)
    revision = frozen.get('execution_revision')
    if revision is None:
        return frozen
    allowed = {'config/claim_execution.json','script/evaluation/claim_execution.py',
               'script/evaluation/run_generation_claim_candidate_selection.py',
               'script/evaluation/run_generation_claim_support_assessment.py',
               'script/evaluation/run_generation_claim_unsupported_diagnosis.py',
               'script/benchmark_claim_execution.py','tests/test_claim_execution.py',
               'script/acceptance.py','script/pipeline.py','results/runtime_validation/summary.json'}
    changes = revision['changed_files']
    if not changes or not set(changes)<=allowed:
        raise ValueError('Execution revision cannot change scientific configuration, evidence, extraction or scoring')
    previous = {k:v for k,v in frozen.items() if k!='execution_revision'}
    previous['files'] = dict(frozen['files'])
    for name,change in changes.items():
        if change['after']!=frozen['files'].get(name) or change['before']==change['after']:
            raise ValueError('Invalid execution revision delta: '+name)
        if change['before'] is None:
            previous['files'].pop(name)
        else:
            previous['files'][name] = change['before']
    import hashlib
    encoded = (json.dumps(previous,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    if hashlib.sha256(encoded).hexdigest()!=revision['previous_freeze_sha256']:
        raise ValueError('Execution predecessor cannot be reconstructed')
    return previous


def validate_postprocessing_revision(frozen):
    """Verify the one preparation-time fix without weakening model/input locks."""
    frozen = execution_predecessor(frozen)
    revision = frozen.get('postprocessing_revision')
    if revision is None:
        return None
    allowed = {'script/summarize.py','script/pipeline.py','script/acceptance.py','tests/test_contracts.py'}
    changes = revision['changed_files']
    if not changes or not set(changes)<=allowed:
        raise ValueError('A postprocessing revision cannot change model stages, prompts, configuration or evidence')
    previous = {k:v for k,v in frozen.items() if k!='postprocessing_revision'}
    previous['files'] = dict(frozen['files'])
    for name,change in changes.items():
        if change['after']!=frozen['files'][name] or change['before']==change['after']:
            raise ValueError('Invalid postprocessing revision delta: '+name)
        previous['files'][name] = change['before']
    import hashlib
    encoded = (json.dumps(previous,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    if hashlib.sha256(encoded).hexdigest()!=revision['previous_freeze_sha256']:
        raise ValueError('Previous freeze cannot be reconstructed from the recorded delta')
    return revision['previous_freeze_sha256']


def validate_run_freeze(fingerprint):
    frozen = read(ROOT/'config/freeze.json')
    previous = validate_postprocessing_revision(frozen)
    accepted = {digest(ROOT/'config/freeze.json'),previous}
    if 'parallel_revision' in frozen:
        accepted.add(frozen['parallel_revision']['previous_freeze_sha256'])
    if 'display_revision' in frozen:
        accepted.add(frozen['display_revision']['previous_freeze_sha256'])
    if 'execution_revision' in frozen:
        accepted.add(frozen['execution_revision']['previous_freeze_sha256'])
    if fingerprint not in accepted or fingerprint is None:
        raise ValueError('Run belongs to an incompatible experiment freeze')


def validate_completed_script(name, fingerprint):
    frozen = read(ROOT/'config/freeze.json')
    validate_postprocessing_revision(frozen)
    current = digest(ROOT/name)
    change = frozen.get('parallel_revision',{}).get('changed_files',{}).get(name,{})
    if name in {'script/generation/run_w2_generation.py','script/evaluation/run_generation_claim_semantic_dedup.py','script/evaluation/run_generation_claim_extraction.py'} and change.get('before')==fingerprint and change.get('after')==current and frozen['files'][name]==current:
        return
    allowed = {'script/evaluation/run_generation_claim_candidate_selection.py',
               'script/evaluation/run_generation_claim_support_assessment.py',
               'script/evaluation/run_generation_claim_unsupported_diagnosis.py'}
    change = frozen.get('execution_revision',{}).get('changed_files',{}).get(name,{})
    if name not in allowed or change.get('before')!=fingerprint or change.get('after')!=current or frozen['files'][name]!=current:
        raise ValueError('Completed script is incompatible: '+name)


def validate_runtime_fingerprint(name, fingerprint):
    """Keep the old timing evidence historical, bound to a verified predecessor."""
    frozen = read(ROOT/'config/freeze.json')
    validate_postprocessing_revision(frozen)
    if digest(ROOT/name)!=frozen['files'][name]:
        raise ValueError('Unfrozen runtime source: '+name)
    if fingerprint not in {frozen['files'][name],parallel_predecessor(frozen)['files'].get(name)}:
        raise ValueError('Runtime evidence refers to an unverified source version: '+name)


def environment_identity():
    load_dotenv(ROOT/'.env',override=False)
    prefixes = ['GENERATION','CLAIM_EXTRACTION','CLAIM_DEDUP','CLAIM_CANDIDATE','CLAIM_SUPPORT','CLAIM_DIAGNOSIS','TEXT_EMBEDDING_3_LARGE']
    result = {}
    import hashlib
    for prefix in prefixes:
        for field in ['DEPLOYMENT','ENDPOINT','API_KEY']:
            key = prefix+'_AZURE_OPENAI_'+field
            if not os.environ.get(key):
                raise ValueError('Missing runtime environment variable: '+key)
            if field!='API_KEY':
                result[key] = hashlib.sha256(os.environ[key].encode()).hexdigest()
    return {'routing_hashes':result,'python':sys.version.split()[0],
            'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()}}


def freeze():
    required = ['evidence/sample/sample.json','evidence/sample/sampling_frame.json','evidence/sample/selected_companies.csv','evidence/mapping_corrections.json','evidence/pdf_build_report.json','evidence/quality_exclusions.json',
                'evidence/builds/main_v1/build_config.json','evidence/embeddings/manifest.json',
                'evidence/inputs/generation_cases.jsonl','evidence/inputs/generation_input_manifest.json',
                'evidence/inputs/retrieval_results.jsonl','evidence/inputs/query_bundles.jsonl',
                'evidence/inputs/pilot_selection.json','requirements.txt','requirements.lock.txt','run.py',
                'results/runtime_validation/summary.json']
    files = {ROOT/name for name in required}
    files.update((ROOT/'script').rglob('*.py'))
    files.update((ROOT/'tests').rglob('*.py'))
    files.update(p for p in (ROOT/'config').rglob('*') if p.is_file() and p.name!='freeze.json')
    files.update((ROOT/'evidence/canonical/indexes').glob('*.jsonl'))
    files.update((ROOT/'evidence/builds/main_v1').rglob('package_*.json'))
    files.update(ROOT/'evidence/embeddings'/name for name in ['embeddings.npy','card_metadata.jsonl'])
    value = {'schema_version':'bace_freeze_v1','files':{str(p.relative_to(ROOT)):digest(p) for p in sorted(files)},'environment':environment_identity()}
    path = ROOT/'config/freeze.json'
    if path.exists():
        for key in ('postprocessing_revision','execution_revision','display_revision','parallel_revision'):
            if key in read(path):value[key]=read(path)[key]
        validate_postprocessing_revision(value)
    if path.exists() and read(path)!=value:
        raise ValueError('Existing freeze differs; investigate and create a new experiment version')
    if path.exists():
        print(f'Reused identical freeze of {len(files)} files and the executable environment')
        return
    write(path,value)
    print(f'Frozen {len(files)} files and the executable environment')


def check_frozen():
    frozen = read(ROOT/'config/freeze.json')
    validate_postprocessing_revision(frozen)
    for name,expected in frozen['files'].items():
        if digest(ROOT/name)!=expected:
            raise ValueError('Frozen file changed: '+name)
    if environment_identity()!=frozen['environment']:
        raise ValueError('Model routing, interpreter or installed dependencies changed')
    return frozen


def check():
    checks,failures = {},[]
    def gate(name,call):
        try:
            checks[name] = call()
        except Exception as exc:
            failures.append({'gate':name,'reason':str(exc)})
            checks[name] = False
    gate('frozen_inputs_and_environment',lambda:bool(check_frozen()))
    def matrix():
        sys.path.insert(0,str(ROOT/'script/generation'))
        from run_w2_generation import validate_generation_input_manifest
        manifest_path = ROOT/'evidence/inputs/generation_input_manifest.json'
        validate_generation_input_manifest(read(manifest_path),manifest_path)
        sample = read(ROOT/'evidence/sample/sample.json')
        cases = rows(ROOT/'evidence/inputs/generation_cases.jsonl')
        assert len(sample['selected'])==30 and len(cases)==1800
        tasks = {c['task_id'] for c in cases}
        assert len(tasks)==12 and Counter(t.split('-')[0].lower() for t in tasks)=={'e1':4,'s1':4,'g1':4}
        expected = {(r['company_id'],y,t) for r in sample['selected'] for y in range(2019,2024) for t in tasks}
        actual = {(c['company_id'],c['target_reporting_year'],c['task_id']) for c in cases}
        assert actual==expected and len({c['generation_case_id'] for c in cases})==1800
        assert len(sample['quotas'])==11 and sum(sample['quotas'].values())==30
        return {'companies':30,'sectors':11,'years':5,'tasks':12,'cases':1800}
    gate('complete_experimental_matrix',matrix)
    def boundaries():
        sys.path.insert(0,str(ROOT/'script/rag'))
        import run_w2_retrieval_sanity_check as r
        lookup = r.load_evidence_cards(ROOT/'evidence')
        manifest_paths = sorted((ROOT/'evidence/builds/main_v1/companies').glob('*/manifests/package_*.json'))
        assert len(manifest_paths)==150
        for p in manifest_paths:
            m = read(p);year=m['target_reporting_year']
            assert m['included_source_years']=={'csv':list(range(year-4,year+1)),'pdf':list(range(year-4,year))}
            _,eligible,v = r.validate_candidate_pool({'manifest':m,'company_id':m['company_id'],'case_id':m['package_id']},lookup,False)
            assert eligible and not v['missing_manifest_references']
        for c in rows(ROOT/'evidence/inputs/generation_cases.jsonl'):
            p=ROOT/'evidence/builds/main_v1/companies'/c['company_id']/'manifests'/f"package_{c['target_reporting_year']}.json"
            allowed=set(r.get_allowed_evidence_ids(read(p)))
            shown=[e for e in c['prompt_evidence'] if e['shown_in_prompt']]
            assert shown and len(shown)<=30
            assert all(e['evidence_id'] in allowed and e['retrieval_text']==lookup[e['evidence_id']]['retrieval_text'] for e in shown)
            assert all(n<=10 for n in Counter(e['evidence_type'] for e in shown).values())
        excluded = read(ROOT/'evidence/mapping_corrections.json')['exclusions']
        assert len(excluded)==4 and all(e['evidence_id'] not in lookup for e in excluded)
        quality = read(ROOT/'evidence/quality_exclusions.json')
        assert all(e['evidence_id'] not in lookup for e in quality['excluded'])
        return {'packages':150,'canonical_cards':len(lookup),'excluded_mapping_errors':4,'unreadable_cards_quarantined':quality['excluded_count'],'cross_company_or_future_leaks':0}
    gate('evidence_windows_and_mapping_corrections',boundaries)
    def provenance():
        data = (ROOT/read(ROOT/'config/experiment.json')['data_root']).resolve()
        report = read(ROOT/'evidence/pdf_build_report.json')
        assert report['report_count']==len(report['reports'])
        for item in report['reports']:
            assert digest(data/'raw/reports_pdf'/item['source_file'])==item['fingerprint']['source_sha256']
            assert item['summary']['pages_processed']==item['summary']['pages_total']
            assert not item['summary']['errors']
        reused = {r['source_file']:r for r in report['reports'] if r.get('origin')=='copied_legacy_cards'}
        assert all(r.get('source_reextraction_verified') is True for r in reused.values())
        sample = read(ROOT/'evidence/sample/sample.json')
        for filename,expected in sample['source_hashes'].items():
            assert digest(filename)==expected
        return {'hashed_pdf_sources':report['report_count'],'freshly_verified_reused_reports':len(reused),'all_pages_processed':True,'raw_data_unchanged':True}
    gate('source_provenance',provenance)
    def vectors():
        m = np.load(ROOT/'evidence/embeddings/embeddings.npy',mmap_mode='r')
        metadata=rows(ROOT/'evidence/embeddings/card_metadata.jsonl')
        assert m.shape==(len(metadata),3072)
        assert len({r['evidence_id'] for r in metadata})==len(metadata)
        for start in range(0,len(m),4096):
            b=m[start:start+4096];assert np.isfinite(b).all() and np.allclose(np.linalg.norm(b,axis=1),1,atol=1e-5)
        return {'rows':len(m),'dimensions':3072}
    gate('vector_integrity',vectors)
    def tests():
        result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,capture_output=True,text=True)
        (ROOT/'tests/last_run.log').write_text(result.stdout+result.stderr)
        if result.returncode:
            raise ValueError('Tests failed; see tests/last_run.log')
        return True
    gate('automated_tests',tests)
    def execution():
        from benchmark_claim_execution import verify
        result = read(ROOT/'results/runtime_validation/summary.json')
        verify(result)
        return {'paired_jobs_per_stage':8,'stages':result['stage_timings'],
                'scope':'Historical timing under the preceding two-worker implementation; not a speedup estimate for the current scheduler.'}
    gate('bounded_claim_execution',execution)
    def parallel_execution():
        from benchmark_parallel import verify
        result = read(ROOT/'results/runtime_validation/summary.json')['parallel_validation']
        verify(result)
        return {'case_workers':read(ROOT/'config/experiment.json')['runtime']['case_workers'],
                'independent_branches':['BACE','RAGChecker','RAGAS'],
                'live_stage_timings':result['stage_timings'],
                'scope':'24 live integration jobs and offline concurrency/cancellation tests; no whole-study speedup estimate.'}
    gate('parallel_execution',parallel_execution)
    def pilot():
        run=ROOT/'results/pilot_v1'
        from summarize import summarize
        summary=summarize(run)
        assert summary['case_count']==12 and len(summary['task_counts'])==12
        assert all(v==1 for v in summary['task_counts'].values())
        assert read(run/'human_validation/sample_manifest.json')['human_annotations']==0
        return {'real_cases':12,'task_coverage':12,'native_evaluators':['BACE','RAGChecker 0.1.9','RAGAS 0.4.3'],'formal_human_annotations':0}
    gate('real_pilot_and_human_materials',pilot)
    report={'schema_version':'bace_readiness_v1','ready_for_main':not failures,'checks':checks,'unresolved_critical_items':failures,
            'freeze_sha256':digest(ROOT/'config/freeze.json') if (ROOT/'config/freeze.json').exists() else None,
            'main_command':str(ROOT/'.venv/bin/python')+' '+str(ROOT/'run.py')+' main',
            'scope':'Preparation, the original 12-case engineering pilot and bounded runtime validations. This acceptance check does not execute the main study. Formal human annotations have not been performed.',
            'limitations':['Native judges and claim extraction remain fallible; engineering acceptance is not evaluator validity.','Only four previously verified CSV mapping errors are excluded; other extracted metrics have not all been independently audited.','PDF evidence uses report-year windows, not historical publication-date cutoffs; source labels preserve measurement-year distinctions.','Sampling conditions define the 250-company complete-source subpopulation; inference to all 600 companies requires accounting for availability selection.']}
    write(ROOT/'readiness_report.json',report)
    lines=['# BACE readiness report','',f"Ready for main experiment: **{report['ready_for_main']}**",'',report['scope'],'','## Gates','']
    lines.extend(f'- {name}: {json.dumps(value)}' for name,value in checks.items())
    lines+=['','## Unresolved critical items','']
    lines+=[f'- {e["gate"]}: {e["reason"]}' for e in failures] if failures else ['None.']
    lines+=['','## Research limitations','']+['- '+s for s in report['limitations']]+['','## Main command','','```bash',report['main_command'],'```','', 'The same command resumes completed stages after validating their recorded hashes.']
    (ROOT/'READINESS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'ready_for_main':not failures,'failures':failures},indent=2))
    if failures:
        raise SystemExit(1)
