"""Execute each notebook in a fresh, isolated Python kernel and export reading HTML."""
import json
import os
from pathlib import Path
import sys
import time
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from jupyter_client.kernelspec import KernelSpecManager

HERE=Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR']=str(HERE/'outputs/.matplotlib')
os.environ['IPYTHONDIR']=str(HERE/'outputs/.ipython')
os.environ['JUPYTER_DATA_DIR']=str(HERE/'outputs/.jupyter')
os.environ['PYTHONDONTWRITEBYTECODE']='1'
kernel=HERE/'outputs/.jupyter/kernels/bace-analysis';kernel.mkdir(parents=True,exist_ok=True)
(kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
 'display_name':'BACE analysis (Python)','language':'python'}))
reports=[]
paths=[HERE/name for name in sys.argv[1:]] if len(sys.argv)>1 else sorted(HERE.glob('0*.ipynb'))
for path in paths:
    start=time.time();nb=nbformat.read(path,as_version=4)
    for cell in nb.cells:
        if cell.cell_type=='code':cell.outputs=[];cell.execution_count=None
    print('Executing '+path.name,flush=True)
    try:
        NotebookClient(nb,timeout=1200,kernel_name='bace-analysis',resources={'metadata':{'path':str(HERE)}}).execute()
    except Exception:
        nbformat.write(nb,path)
        raise
    nbformat.write(nb,path)
    exporter=HTMLExporter();exporter.exclude_input=True;exporter.exclude_input_prompt=True
    body,_=exporter.from_notebook_node(nb)
    body=body.replace('href="outputs/', 'href="')
    (HERE/'outputs'/path.with_suffix('.html').name).write_text(body)
    report={'notebook':path.name,'seconds':round(time.time()-start,2),'code_cells':sum(c.cell_type=='code' for c in nb.cells),'errors':0}
    reports.append(report);(HERE/'outputs'/(path.stem+'.execution.json')).write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
all_reports=[json.loads(p.read_text()) for p in sorted((HERE/'outputs').glob('0*.execution.json'))]
(HERE/'outputs/execution_report.json').write_text(json.dumps(all_reports,indent=2)+'\n')
