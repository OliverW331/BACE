"""Check delivered notebooks, numbers, figure source, exports and QA records."""
from pathlib import Path
import json
import sys
import subprocess
import nbformat
import pandas as pd
import numpy as np
import pymupdf
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis_data import HERE,OUT,CACHE,read,save_json,sha,company_bootstrap,LABELS
from figure_style import SKILL
qa=OUT/'qa';qa.mkdir(exist_ok=True)
expected=['00_data_landscape','01_evidence_support','02_failure_patterns','03_evaluator_comparison']
notebook_checks=[]
for name in expected:
    path=HERE/(name+'.ipynb');nb=nbformat.read(path,as_version=4);nbformat.validate(nb)
    code=[c for c in nb.cells if c.cell_type=='code']
    assert [c.execution_count for c in code]==list(range(1,len(code)+1)),name
    assert not any(o.output_type=='error' for c in code for o in c.outputs),name
    figures=sum('image/svg+xml' in o.get('data',{}) for c in code for o in c.outputs)
    assert figures>0
    source=qa/(name+'.plotting_source.py')
    source.write_text((HERE/'figure_style.py').read_text()+'\n\n'+'\n\n'.join(c.source for c in code))
    audit=subprocess.run([sys.executable,str(SKILL/'scripts/validate_figure.py'),str(source),'--json'],capture_output=True,text=True)
    source_report=json.loads(audit.stdout);save_json(qa/(name+'.source-audit.json'),source_report)
    assert not [f for f in source_report['findings'] if f['level']=='FAIL'],name
    notebook_checks.append({'notebook':path.name,'code_cells':len(code),'saved_figures':figures,'sha256':sha(path),'source_warnings':[f for f in source_report['findings'] if f['level']=='WARN']})
figure_checks=[]
for path in sorted((OUT/'figures').rglob('*.metadata.json')):
    meta=read(path);base=path.with_name(meta['figure'])
    assert meta['width_mm']==183 or abs(meta['width_mm']-183)<1e-9
    assert not any(meta['audit_exit_codes'].values()),meta['figure']
    for ext,digest in meta['exports'].items():assert sha(str(base)+'.'+ext)==digest
    for name in meta['data_files']:assert (path.parent/name).exists()
    with Image.open(str(base)+'.png') as png:
        assert all(abs(x-600)<.1 for x in png.info['dpi'])
        assert abs(png.width-183/25.4*600)<2
    text=read(str(base)+'.text-audit.json');collision=read(str(base)+'.collision-audit.json');alignment=read(str(base)+'.alignment.json')
    assert text['auditable'] and text['below_minimum_count']==0
    assert collision['auditable'] and collision['summary']['fail']==0
    assert alignment['auditable'] or not alignment['applicable']
    assert alignment['summary']['fail']==0
    figure_checks.append({'figure':meta['figure'],'minimum_vector_font_pt':text['minimum_found_pt'],'alignment':alignment['verdict'],
                          'collision_warnings':collision['summary']['warn'],'width_mm':meta['width_mm'],'height_mm':meta['height_mm'],
                          'panels':len(alignment.get('layout',{}).get('panels',[]))})
assert sum(x['saved_figures'] for x in notebook_checks)==len(figure_checks)
# Rasterised source text needs its own effective glyph-size check.
crop_table=pd.read_csv(OUT/'figures/02/02_asml_source_layout__data.csv').iloc[0]
clip=pymupdf.Rect(*map(float,crop_table.clip_points.split(',')))
from analysis_data import ROOT
with pymupdf.open(ROOT/'data/raw/reports_pdf'/crop_table.source_file) as source:
    page=source[int(crop_table.pdf_page)-1]
    sizes=[s['size'] for b in page.get_text('dict')['blocks'] if 'lines' in b for line in b['lines'] for s in line['spans'] if pymupdf.Rect(s['bbox']).intersects(clip)]
crop_pdf=OUT/'figures/02/02_asml_source_layout.pdf'
with pymupdf.open(crop_pdf) as rendered:
    scale=pymupdf.Rect(rendered[0].get_image_info()[0]['bbox']).width/clip.width
effective=min(sizes)*scale
assert effective>=5
save_json(qa/'source_crop_font_check.json',{'source_minimum_font_pt':min(sizes),'display_scale':scale,'minimum_effective_crop_font_pt':effective,'pdf_sha256':sha(crop_pdf),'result':'pass'})
m=pd.read_csv(CACHE/'metrics.csv');c=pd.read_csv(CACHE/'claims.csv');b=m[m.bace_complete]
assert len(m)==1800 and m.generation_case_id.is_unique
assert len(c)==int(b.bace_dc_count.sum())
assert c.label.isin([*LABELS,'direct','inferred']).all()
for label in LABELS:
    assert int((c.label==label).sum())==int(b['bace_'+label].sum())
assert np.allclose((b.bace_supported_direct+b.bace_supported_inferred)/b.bace_dc_count,b.bace_support_rate_all_dc)
assert m.loc[~m.bace_complete,'bace_support_rate_all_dc'].isna().all()
# A deliberately unbalanced two-company fixture checks the disclosure-weighted point estimate.
fixture=pd.DataFrame({'company_id':['a']*9+['b'],'value':[1.0]*9+[0.0]})
r=company_bootstrap(fixture,'value',draws=1000)
assert r['companies']==2 and r['disclosures']==10 and r['mean']==.9
assert r['low']==0 and r['high']==1
for n in read(CACHE/'manifest.json')['tables']:
    assert sha(CACHE/(n+'.csv'))==read(CACHE/'manifest.json')['tables'][n]
save_json(qa/'acceptance_checks.json',{'notebooks':notebook_checks,'figures':figure_checks,'native_arithmetic_and_cohort_checks':'pass',
          'company_bootstrap_fixture':'pass','scope':'Automated checks; see QA_REVIEW.md for source-based interpretation and visual review.'})
print(f'Validated {len(notebook_checks)} executed notebooks and {len(figure_checks)} complete figure exports.')
