"""Verify the current scientific freeze, native runtime and all used source PDFs."""
from pathlib import Path
import json
import os
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis_data import BACE, ROOT, OUT, CACHE, read, sha, save_json
frozen=read(BACE/'config/freeze.json')
checks=[]
for i,(name,expected) in enumerate(frozen['files'].items(),1):
    path=BACE/name
    actual=sha(path)
    if actual!=expected: raise ValueError('Frozen file changed: '+name)
    checks.append({'source':'BACE/'+name,'sha256':actual})
    if i%40==0: print(f'Frozen-file hashes: {i}/{len(frozen["files"])}',flush=True)
for i,(name,expected) in enumerate(read(CACHE/'source_pdfs.json').items(),1):
    path=ROOT/'data/raw/reports_pdf'/name
    actual=sha(path)
    if actual!=expected:raise ValueError('PDF changed since canonical extraction: '+name)
    checks.append({'source':'data/raw/reports_pdf/'+name,'sha256':actual})
    if i%100==0: print(f'Raw PDF hashes: {i}',flush=True)
code="import importlib.metadata as m,json,platform; print(json.dumps({'python':platform.python_version(),'packages':{d.metadata['Name']:d.version for d in m.distributions()}}))"
runtime=json.loads(subprocess.check_output([str(BACE/'.venv/bin/python'),'-B','-c',code],text=True))
assert runtime['python']==frozen['environment']['python']
assert runtime['packages']==frozen['environment']['packages'],'Frozen runtime package inventory changed'
save_json(OUT/'integrity_report.json',{'frozen_files_verified':len(frozen['files']),'source_pdfs_verified':len(read(CACHE/'source_pdfs.json')),
          'native_runtime_matches_freeze':True,'freeze_sha256':sha(BACE/'config/freeze.json'),'checks':checks})
print('Scientific freeze, all source PDFs and original runtime verified.',flush=True)
