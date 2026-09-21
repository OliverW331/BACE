"""Parallel dependency, durable output, shared quota and cancellation contracts."""
from concurrent.futures import ThreadPoolExecutor
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'script'),str(ROOT/'script/evaluation')]
from common import read, rows, write
from scheduling import ExperimentInterrupted, ProcessControl, parallel_branches, run_cases
from claim_execution import RequestGate, attach_gate, process_marker
import pipeline
from progress import RunProgress


class ParallelTests(unittest.TestCase):
    def test_extraction_lineage_accepts_only_the_recorded_transport_revision(self):
        import acceptance
        name='script/evaluation/run_generation_claim_extraction.py'
        old=hashlib.sha256(b'old transport').hexdigest()
        new=hashlib.sha256(b'new transport').hexdigest()
        original={'files':{name:old},'environment':{'fixed':True}}
        fingerprint=hashlib.sha256((json.dumps(original,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()).hexdigest()
        revised={'files':{name:new},'environment':original['environment'],
                 'parallel_revision':{'previous_freeze_sha256':fingerprint,'changed_files':{name:{'before':old,'after':new}}}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/name;p.parent.mkdir(parents=True);p.write_bytes(b'new transport')
            write(root/'config/freeze.json',revised)
            with patch.object(acceptance,'ROOT',root):
                acceptance.validate_completed_script(name,old)
                with self.assertRaises(ValueError):acceptance.validate_completed_script(name,'unrelated')
                p.write_bytes(b'unreviewed change')
                with self.assertRaises(ValueError):acceptance.validate_completed_script(name,old)

    def test_local_coordination_paces_concurrent_request_starts(self):
        from claim_execution import coordination_database
        database = coordination_database()
        self.assertNotIn(str(ROOT),str(database))
        self.assertEqual(database.parent.stat().st_uid,os.getuid())
        with tempfile.TemporaryDirectory() as d:
            gate=RequestGate('paced',4,database=Path(d)/'requests.sqlite',spacing=0.06)
            starts=[]
            def execute(_):
                with gate.request():
                    starts.append(time.monotonic())
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(execute,range(4)))
            starts.sort()
            self.assertTrue(all(b-a>=0.04 for a,b in zip(starts,starts[1:])))

    def test_sigint_stops_the_experiment_and_records_interrupted_status(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            write(root/'config/experiment.json',{'runtime':{'case_workers':16},'pilot':{'case_count':12}})
            child_code='import os,sys,time;from pathlib import Path;Path(sys.argv[1]).write_text(str(os.getpid()));time.sleep(60)'
            code=('import sys\nfrom pathlib import Path\n'
                  'sys.path.insert(0,sys.argv[1])\nimport pipeline\n'
                  'pipeline.ROOT=Path(sys.argv[2])\n'
                  'pipeline._run_experiment=lambda scope,progress,control:control.run([sys.executable,"-c",sys.argv[3],str(pipeline.ROOT/"child.pid")])\n'
                  'pipeline.run_experiment("pilot")\n')
            process=subprocess.Popen([sys.executable,'-c',code,str(ROOT/'script'),str(root),child_code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            child=None
            try:
                deadline=time.monotonic()+5
                while not (root/'child.pid').exists() and time.monotonic()<deadline:
                    time.sleep(0.02)
                self.assertTrue((root/'child.pid').exists())
                child=int((root/'child.pid').read_text())
                process.send_signal(signal.SIGINT)
                stdout,stderr=process.communicate(timeout=5)
                self.assertEqual(process.returncode,130,(stdout,stderr))
                self.assertEqual(read(root/'results/pilot_v1/execution_status.json')['status'],'interrupted')
                self.assertIsNone(process_marker(child))
            finally:
                if process.poll() is None:
                    process.kill();process.communicate()
                if child and process_marker(child):
                    os.killpg(child,signal.SIGKILL)

    def test_sixteen_cases_can_run_and_cancellation_stops_new_submissions(self):
        control = ProcessControl(); barrier = threading.Barrier(16)
        started = []; lock = threading.Lock()
        def execute(case):
            with lock:
                started.append(case['generation_case_id'])
            barrier.wait(timeout=10)
            control.cancel()
            control.check()
        with self.assertRaises(ExperimentInterrupted):
            run_cases([{'generation_case_id':str(i)} for i in range(1800)],execute,16,control)
        self.assertEqual(len(started),16)

    def test_parallel_stages_merge_receipts_and_keep_success_after_sibling_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);write(root/'config/experiment.json',{'runtime':{'max_stage_attempts':1}})
            script=root/'script/fixture.py';script.parent.mkdir()
            script.write_text('import argparse,json,time\nfrom pathlib import Path\np=argparse.ArgumentParser();p.add_argument("--output-dir");a=p.parse_args()\no=Path(a.output_dir);o.mkdir(parents=True,exist_ok=True)\ntime.sleep(0.1)\n(o/"manifest.json").write_text(json.dumps({"status":"complete"}))\n')
            base=root/'case';lock=threading.Lock()
            def stage(name):
                pipeline.stage(base,name,'fixture.py',[],base/name,'manifest.json',checkpoint_lock=lock)
            with patch.object(pipeline,'ROOT',root):
                parallel_branches({name:lambda name=name:stage(name) for name in ('bace','ragchecker','ragas')})
                state=read(base/'state.json')
                self.assertEqual(set(state['stages']),{'bace','ragchecker','ragas'})
                before=(base/'state.json').read_bytes()
                with patch.object(pipeline.subprocess,'Popen',side_effect=AssertionError('Do not rerun completed stages')):
                    parallel_branches({name:lambda name=name:stage(name) for name in state['stages']})
                self.assertEqual((base/'state.json').read_bytes(),before)
            saved=[]
            def failure():raise ValueError('one branch failed')
            with self.assertRaises(RuntimeError):
                parallel_branches({'failed':failure,'saved':lambda:saved.append(True)})
            self.assertEqual(saved,[True])

    def test_actual_case_starts_all_three_evaluators_after_generation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);config=read(ROOT/'config/experiment.json')
            write(root/'config/experiment.json',config)
            write(root/'evidence/inputs/generation_input_manifest.json',{'generation_case_count':1800})
            write(root/'config/evaluation/configs/external_evaluation_config.json',read(ROOT/'config/evaluation/configs/external_evaluation_config.json'))
            case={'generation_case_id':'fixture','company_name':'Fixture','target_reporting_year':2023,'task_id':'E1-1'}
            base=root/'results/pilot_v1/cases/fixture';write(base/'state.json',{'stages':{}})
            seen=[];lock=threading.Lock();barrier=threading.Barrier(3)
            def execute(base,label,script,args,output,manifest,*unused,**kwargs):
                if label in ('direct','ragchecker','ragas'):
                    self.assertIn('generation',seen)
                    barrier.wait(timeout=3)
                with lock:
                    seen.append(label)
                if label=='generation':
                    output.mkdir();(output/'generated_disclosures.jsonl').write_text('{}\n');write(output/'generation_run_manifest.json',{})
            with patch.object(pipeline,'ROOT',root),patch.object(pipeline,'CONFIGS',root/'config/evaluation/configs'),patch.object(pipeline,'stage',side_effect=execute):
                pipeline._run_case(case,base)
            bace=[s for s in seen if s not in ('ragchecker','ragas')]
            self.assertEqual(bace,['generation','direct','integrated','atomic','dedup','candidates','support','diagnosis'])

    def test_cancel_terminates_child_and_grandchild_processes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);control=ProcessControl();errors=[]
            code='import os,subprocess,sys,time\nfrom pathlib import Path\np=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"])\nPath(sys.argv[1]).write_text(str(os.getpid())+","+str(p.pid))\ntime.sleep(60)'
            def execute():
                try:control.run([sys.executable,'-c',code,str(root/'pids')])
                except ExperimentInterrupted:errors.append(True)
            thread=threading.Thread(target=execute);thread.start()
            deadline=time.monotonic()+5
            while not (root/'pids').exists() and time.monotonic()<deadline:time.sleep(0.02)
            self.assertTrue((root/'pids').exists())
            pids=list(map(int,(root/'pids').read_text().split(',')))
            control.cancel();thread.join(5)
            self.assertFalse(thread.is_alive());self.assertEqual(errors,[True])
            deadline=time.monotonic()+2
            while any(process_marker(p) for p in pids) and time.monotonic()<deadline:time.sleep(0.02)
            self.assertTrue(all(process_marker(p) is None for p in pids))
            self.assertFalse(control.processes)

    def test_external_and_bace_support_share_one_adaptive_resource(self):
        import claim_execution
        with tempfile.TemporaryDirectory() as d,patch.object(claim_execution,'coordination_database',return_value=Path(d)/'live.sqlite'):
            clients=[SimpleNamespace(base_url='https://fixture/openai/v1/') for _ in range(3)]
            for stage,client in zip(('support','ragchecker','ragas'),clients):
                attach_gate(client,stage,{'max_inflight':16,'resource':'support'})
            gates=[c._bace_request_gate for c in clients]
            self.assertEqual(len({g.key for g in gates}),1)
            gates[0].cooldown(2);gates[1].cooldown(2)
            with gates[0].connect() as db:
                self.assertEqual(db.execute('SELECT capacity FROM resources').fetchone()[0],8)
                db.execute('UPDATE resources SET blocked_until=0,resized_at=?',(time.time()-10,))
            for _ in range(8):gates[2].success()
            with gates[0].connect() as db:
                self.assertEqual(db.execute('SELECT capacity FROM resources').fetchone()[0],9)

    def test_semantic_dedup_parallel_replays_identical_native_outputs(self):
        import run_generation_claim_semantic_dedup as module
        from generation_claims import sha256_json
        base=sorted((ROOT/'results/pilot_v1/cases').iterdir())[0]
        cached=rows(base/'bace/dedup/semantic_dedup_calls.jsonl')
        by_prompt={r['attempts'][-1]['messages_sha256']:r for r in cached if r.get('model_called')}
        self.assertEqual(len(by_prompt),2)
        calls=[]
        def create(**kwargs):
            record=by_prompt[sha256_json(kwargs['input'])]
            self.assertEqual(kwargs['model'],record['deployment_name'])
            for key,value in record['request_parameters'].items():self.assertEqual(kwargs[key],value)
            calls.append(record['call_id'])
            return SimpleNamespace(output_text=record['attempts'][-1]['raw_output'],model_dump=lambda **_:record['attempts'][-1]['api_response'])
        client=SimpleNamespace(responses=SimpleNamespace(create=create))
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            output=Path(d)/'dedup'
            args=[module.__file__,'--ec-occurrences',str(base/'extraction/atomic/ec_claim_occurrences.jsonl'),
                  '--dc-occurrences',str(base/'extraction/atomic/dc_claim_occurrences.jsonl'),
                  '--config',str(ROOT/'config/evaluation/configs/generation_claim_semantic_dedup_config.json'),
                  '--case-id',base.name,'--output-dir',str(output),'--progress-interval-seconds','0']
            with patch.object(sys,'argv',args),patch.object(module,'make_client',return_value=client):module.main()
            self.assertEqual(len(calls),2)
            for filename in ('ec_claims.jsonl','dc_claims.jsonl'):
                self.assertEqual(rows(output/filename),rows(base/'bace/dedup'/filename))
            with patch.object(sys,'argv',args+['--resume']),patch.object(module,'make_client',return_value=client):module.main()
            self.assertEqual(len(calls),2)

    def test_progress_keeps_eight_lines_with_sixteen_active_cases(self):
        with tempfile.TemporaryDirectory() as d:
            progress=RunProgress('main',Path(d),16,1800,stream=io.StringIO())
            for i in range(16):
                cid=str(i);progress.begin_case({'generation_case_id':cid,'company_name':'Example','target_reporting_year':2023,'task_id':'E1-1_transition_plan'})
                for stage in ('candidates','ragchecker','ragas'):progress.begin_stage(cid,stage)
                progress.finish_stage(cid,'ragas',reused=False)
            state=progress.snapshot();lines=progress.lines(state)
            self.assertEqual(len(lines),8);self.assertIn('Running 16',lines[1]);self.assertIn('RA:done',lines[3])
            state['elapsed_seconds']=6;lines=progress.lines(state)
            self.assertTrue(lines[3].startswith('[5]'));self.assertIn('Page 2/4',lines[-1])

    def test_parallel_revision_allows_worker_count_but_not_scientific_changes(self):
        import acceptance
        config={'runtime':{'case_workers':4},'generation':{'model':'fixed'}}
        old_hash=hashlib.sha256((json.dumps(config,indent=2,ensure_ascii=True)+'\n').encode()).hexdigest()
        original={'files':{'config/experiment.json':old_hash},'environment':{'fixed':True}}
        previous_hash=hashlib.sha256((json.dumps(original,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()).hexdigest()
        config['runtime']['case_workers']=16
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);write(root/'config/experiment.json',config)
            revised={'files':{'config/experiment.json':'new'},'environment':original['environment'],
                     'parallel_revision':{'previous_case_workers':4,'previous_freeze_sha256':previous_hash,
                                          'changed_files':{'config/experiment.json':{'before':old_hash,'after':'new'}}}}
            with patch.object(acceptance,'ROOT',root):
                self.assertEqual(acceptance.parallel_predecessor(revised),original)
                config['generation']['model']='changed';write(root/'config/experiment.json',config)
                with self.assertRaises(ValueError):acceptance.parallel_predecessor(revised)


if __name__=='__main__':unittest.main()
