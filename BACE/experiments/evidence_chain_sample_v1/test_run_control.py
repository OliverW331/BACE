"""Exercise cancellation/draining and resume with synthetic calls and no API client."""
import json
import os
from pathlib import Path
import signal
import tempfile
import time
from unittest.mock import patch, Mock
import run as runner
from common import RESULTS, write, sha

def main():
    with tempfile.TemporaryDirectory() as directory:
        dest=Path(directory)
        plan={'counts':{'claims_per_condition':1},'model_key':'fixture','model':{},
              'deployment_name':'fixture','reuse':{'records':0}}
        saved={'job':{'generation_case_id':'fixture_case','dc_id':'fixture_dc','job_input_hash':'fixture'}}
        call_keys=[]; stop_first=[True]
        def execute(**kwargs):
            condition=kwargs['job']['condition'];call_keys.append(condition)
            if stop_first[0]:
                stop_first[0]=False
                time.sleep(.02)
                os.kill(os.getpid(),signal.SIGTERM)
            else:
                time.sleep(.05)
            return {'generation_case_id':'fixture_case','dc_id':'fixture_dc','call_status':'success',
                    'usage':{},'model_called':True,'restored_output':{'support_sets':[]}}
        def tasks(plan,latest,mode):
            for c in runner.CONDITIONS:
                if (c,'fixture_case','fixture_dc') not in latest:yield c,saved
        def read(path):
            return plan if path.name=='plan.json' else {'status':'PASS','freeze_sha256':'fixture'}
        config={'runtime':{'request_timeout_seconds':1},'response_schema':{}}
        with patch.multiple(runner,RESULTS=dest,verify_frozen=lambda:None,read=read,sha=lambda p:'fixture',
                            condition_bundle=lambda *args:(config,'fixture',{}),
                            settings=lambda *args:{},attach_gate=lambda *args:None,tasks=tasks,
                            validate_result=lambda *args:None,
                            replay_job=lambda s,c:{'condition':c,'job_input_hash':'fixture'}), \
             patch.object(runner.native,'resolve_model',return_value=('fixture',{},'fixture','fixture')), \
             patch.object(runner.native,'make_client',return_value=Mock()), \
             patch.object(runner.native,'execute_job',side_effect=execute):
            runner.run('full',2)
            status=json.loads((dest/'status.json').read_text())
            assert status['status']=='STOPPED_BY_USER' and status['inflight']==0
            assert sum(c['recorded'] for c in status['conditions'].values())==2
            runner.run('full',2)
            status=json.loads((dest/'status.json').read_text())
            assert status['status']=='COMPLETED' and status['inflight']==0
            assert all(c['recorded']==1 for c in status['conditions'].values())
            assert len(call_keys)==3 and len(set(call_keys))==3
    write(RESULTS/'qa/run_control.json',{'status':'PASS','model_calls':0,
        'checks':['SIGTERM stops new scheduling','Active synthetic outputs are journalled',
                  'Resume calls only missing jobs','No duplicate records'],
        'test_code_sha256':sha(__file__),'runner_sha256':sha(Path(runner.__file__))})
    print('PASS: synthetic cancellation/draining/resume; no model calls.')

if __name__=='__main__':main()
