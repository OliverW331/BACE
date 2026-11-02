"""Wait for this live run, then audit and calculate saved-data evidence-chain outputs."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
BACE=HERE.parents[1]
ROOT=BACE.parent
RESULTS=BACE/'results/evidence_chain_v1'

def read(path):return json.loads(path.read_text())
def write(value):
    p=RESULTS/'finish_status.json'
    t=p.with_suffix('.tmp');t.write_text(json.dumps(value,indent=2)+'\n');t.replace(p)
def marker(pid):
    try:
        fields=Path(f'/proc/{pid}/stat').read_text().rpartition(')')[2].split()
        return None if fields[0]=='Z' else fields[19]
    except (FileNotFoundError,ProcessLookupError):return None

def main():
    lock=(RESULTS/'finish.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    while True:
        state=read(RESULTS/'status.json')
        if state['mode']=='full' and state['status']=='COMPLETED':break
        if state['mode']!='full' or marker(state['pid'])!=state['process_marker']:
            write({'status':'WAITING_FOR_RUN_RESUMPTION','pid':os.getpid(),
                   'reason':'Recorded full-run process is no longer live; no replacement job was launched.'})
            return
        write({'status':'WAITING_ON_VERIFIED_LIVE_RUN','pid':os.getpid(),
               'process_marker':marker(os.getpid()),'run_pid':state['pid'],
               'run_process_marker':state['process_marker'],'checked_at_unix':time.time()})
        time.sleep(10)
    commands=[
        [str(BACE/'.venv/bin/python'),'-B',str(HERE/'audit_completed_run.py')],
        [str(BACE/'analysis/.venv/bin/python'),'-B',str(BACE/'analysis/scripts/validate_evaluator_gap_evidence_chain.py')],
        [str(BACE/'analysis/.venv/bin/python'),'-B',str(BACE/'analysis/evaluator_gap_evidence_chain.py')],
        [str(BACE/'analysis/.venv/bin/python'),'-B',str(BACE/'analysis/scripts/validate_evaluator_gap_evidence_chain.py'),'--completed']]
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
    with (RESULTS/'finish.log').open('a',buffering=1) as log:
        for cmd in commands:
            write({'status':'POSTPROCESSING','pid':os.getpid(),'process_marker':marker(os.getpid()),'command':cmd})
            result=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            if result.returncode:
                write({'status':'POSTPROCESSING_FAILED','command':cmd,'returncode':result.returncode})
                return
    write({'status':'AUTOMATED_STATISTICS_COMPLETE_NOTEBOOK_AND_REVIEW_PENDING',
           'requires':'Integrate and interpret final evidence-chain results in notebook 04; independent reviewer annotations are pending.'})

if __name__=='__main__':main()
