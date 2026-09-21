"""Concurrency, retry and native-response replay regressions; no network calls."""
from concurrent.futures import ThreadPoolExecutor
import contextlib
import hashlib
import importlib
import io
import json
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'script'),str(ROOT/'script/evaluation')]
from claim_execution import RequestGate, completed_jobs, retry_after, shared_retry_delay
from common import read, rows


def gate_worker(database, active, peak):
    gate = RequestGate('shared',2,database=database)
    def work(_):
        with gate.request():
            with active.get_lock():
                active.value += 1
                peak.value = max(peak.value,active.value)
            time.sleep(0.04)
            with active.get_lock():
                active.value -= 1
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(work,range(3)))


def abandoned_lease(database, pipe):
    gate = RequestGate('abandoned',1,database=database)
    with gate.request():
        pipe.send(True)
        os._exit(0)


class ClaimExecution(unittest.TestCase):
    def test_execution_revision_reuses_only_verified_predecessor_scripts(self):
        import acceptance
        from common import write
        name='script/evaluation/run_generation_claim_candidate_selection.py'
        before=hashlib.sha256(b'old scheduling').hexdigest()
        after=hashlib.sha256(b'new scheduling').hexdigest()
        original={'schema_version':'bace_freeze_v1','files':{name:before,'config/tasks.json':'fixed'},'environment':{'model':'fixed'}}
        old_hash=hashlib.sha256((json.dumps(original,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()).hexdigest()
        revised=json.loads(json.dumps(original));revised['files'][name]=after
        revised['execution_revision']={'previous_freeze_sha256':old_hash,'changed_files':{name:{'before':before,'after':after}}}
        self.assertEqual(acceptance.execution_predecessor(revised),original)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/name).parent.mkdir(parents=True);(root/name).write_bytes(b'new scheduling')
            write(root/'config/freeze.json',revised)
            with patch.object(acceptance,'ROOT',root):
                acceptance.validate_run_freeze(old_hash)
                acceptance.validate_completed_script(name,before)
                with self.assertRaises(ValueError):acceptance.validate_completed_script(name,'unrelated')
                (root/name).write_bytes(b'unreviewed change')
                with self.assertRaises(ValueError):acceptance.validate_completed_script(name,before)
        revised['files']['config/tasks.json']='changed'
        with self.assertRaises(ValueError):acceptance.execution_predecessor(revised)
        revised['execution_revision']['changed_files']['config/tasks.json']={'before':'fixed','after':'changed'}
        with self.assertRaises(ValueError):acceptance.execution_predecessor(revised)

    def test_workers_overlap_and_successes_survive_another_job_exception(self):
        barrier = threading.Barrier(2)
        jobs = [{'call_id':str(i)} for i in range(5)]
        def execute(item):
            index,job=item
            if index<=2:
                barrier.wait(timeout=3)
            if index==2:
                raise ValueError('Interrupted request')
            return job['call_id']
        records=[]
        with self.assertRaises(RuntimeError):
            for _,record in completed_jobs(jobs,execute,2):
                records.append(record)
        self.assertEqual(set(records),{'0','2','3','4'})

    def test_limit_is_shared_across_processes_and_threads(self):
        ctx=multiprocessing.get_context('fork')
        with tempfile.TemporaryDirectory() as d:
            database=str(Path(d)/'live.sqlite')
            active=ctx.Value('i',0);peak=ctx.Value('i',0)
            processes=[ctx.Process(target=gate_worker,args=(database,active,peak)) for _ in range(2)]
            for p in processes:p.start()
            for p in processes:
                p.join(10)
                self.assertEqual(p.exitcode,0)
            self.assertEqual(peak.value,2)
            self.assertEqual(active.value,0)
            gate=RequestGate('shared',2,database=database)
            with gate.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM leases').fetchone()[0],0)

    def test_dead_process_does_not_hold_a_request_slot(self):
        ctx=multiprocessing.get_context('fork')
        with tempfile.TemporaryDirectory() as d:
            database=str(Path(d)/'live.sqlite')
            parent,child=ctx.Pipe()
            p=ctx.Process(target=abandoned_lease,args=(database,child));p.start()
            self.assertTrue(parent.poll(5));self.assertTrue(parent.recv());p.join(5)
            self.assertEqual(p.exitcode,0)
            gate=RequestGate('abandoned',1,database=database)
            start=time.monotonic()
            with gate.request():pass
            self.assertLess(time.monotonic()-start,1)

    def test_retry_after_is_respected_and_shared(self):
        error=SimpleNamespace(status_code=429,response=SimpleNamespace(headers={'retry-after-ms':'12000'}))
        self.assertEqual(retry_after(error,2),12)
        error.response.headers={'retry-after':'15'}
        self.assertEqual(retry_after(error,2),15)
        with tempfile.TemporaryDirectory() as d:
            gate=RequestGate('cooldown',1,database=Path(d)/'live.sqlite')
            error.response.headers={'retry-after':'0.1'}
            shared_retry_delay(SimpleNamespace(_bace_request_gate=gate),error,0)
            start=time.monotonic()
            with RequestGate('cooldown',1,database=gate.database).request():pass
            self.assertGreaterEqual(time.monotonic()-start,0.07)

    def test_native_stages_keep_prompts_results_and_resume_under_concurrency(self):
        from generation_claims import sha256_json
        base=sorted((ROOT/'results/pilot_v1/cases').iterdir())[0]
        stages=[('candidates','candidate_selection','claim_candidate_calls.jsonl'),
                ('support','support_assessment','claim_support_calls.jsonl'),
                ('diagnosis','unsupported_diagnosis','claim_unsupported_diagnosis_calls.jsonl')]
        cached={stage:{r['dc_id']:r for r in rows(base/'bace'/stage/filename)
                       if r['call_status']=='success' and r.get('model_called') and r.get('attempts')}
                for stage,_,filename in stages}
        selected=sorted(set.intersection(*(set(v) for v in cached.values())))[:8]
        self.assertEqual(len(selected),8)
        for stage,suffix,filename in stages:
            module=importlib.import_module('run_generation_claim_'+suffix)
            config_name={'candidates':'candidate_selection','support':'support','diagnosis':'unsupported_diagnosis'}[stage]
            common=['--ec-claims',str(base/'bace/dedup/ec_claims.jsonl'),'--dc-claims',str(base/'bace/dedup/dc_claims.jsonl'),
                    '--config',str(ROOT/f'config/evaluation/configs/generation_claim_{config_name}_config.json'),
                    '--case-id',base.name,'--progress-interval-seconds','0']
            for cid in selected:common+=['--dc-id',cid]
            if stage!='candidates':
                common+=['--candidate-selections',str(base/'bace/candidates/dc_candidate_ecs.jsonl'),
                         '--generation-cases',str(base/'inputs/generation_cases.jsonl')]
            if stage=='diagnosis':common+=['--support-assessments',str(base/'bace/support/dc_support_sets.jsonl')]
            by_prompt={cached[stage][cid]['attempts'][-1]['messages_sha256']:cached[stage][cid] for cid in selected}
            calls=[]
            def create(**kwargs):
                record=by_prompt[sha256_json(kwargs['input'])]
                self.assertEqual(kwargs['model'],record['deployment_name'])
                for key,value in record['request_parameters'].items():self.assertEqual(kwargs[key],value)
                calls.append(record['call_id'])
                return SimpleNamespace(output_text=record['attempts'][-1]['raw_output'],
                                       model_dump=lambda **_:record['attempts'][-1]['api_response'])
            client=SimpleNamespace(responses=SimpleNamespace(create=create))
            with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
                for workers in (1,2,8):
                    output=Path(d)/str(workers)
                    argv=[module.__file__,*common,'--workers',str(workers),'--output-dir',str(output)]
                    with patch.object(sys,'argv',argv),patch.object(module,'make_client',return_value=client),patch.object(module,'attach_gate'):
                        try:
                            module.main()
                        except SystemExit:
                            self.fail(str([(r.get('error_type'),r.get('error_message'),r.get('validation_error')) for r in rows(output/filename)]))
                    expected=sorted([cached[stage][cid]['restored_output'] for cid in selected],key=lambda r:r['dc_claim_id'])
                    self.assertEqual(rows(module.output_paths(output)['results']),expected)
                    self.assertEqual(read(module.output_paths(output)['manifest'])['status'],'complete')
                    count=len(calls);before=(output/filename).read_bytes()
                    with patch.object(sys,'argv',argv+['--resume']),patch.object(module,'make_client',return_value=client),patch.object(module,'attach_gate'):
                        module.main()
                    self.assertEqual(len(calls),count)
                    self.assertEqual((output/filename).read_bytes(),before)


if __name__=='__main__':unittest.main()
