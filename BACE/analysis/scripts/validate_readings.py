"""Audit actual saved reading order and recompute per-figure prose from source data.

This proves coverage, provenance and rendering order, not scientific validity.
NARRATIVE_REVIEW.md records the separate editorial/source review.
"""
from pathlib import Path
from html.parser import HTMLParser
import json
import re
import sys
import nbformat
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis_data import HERE, OUT, read, sha, save_json
from figure_narrative import explain_figure


class ReadingHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.links=[]
        self.input_areas=0

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        # Markdown source cells also use jp-InputArea in nbconvert HTML.
        # Only the editor class identifies a rendered code input.
        if 'jp-InputArea-editor' in attrs.get('class','').split():
            self.input_areas+=1
        if tag=='a' and 'href' in attrs:
            self.links.append(attrs['href'])

    def handle_data(self,data):
        self.parts.append(data)


expected_counts={'00_data_landscape':9,'01_evidence_support':6,
                 '02_failure_patterns':10,'03_evaluator_comparison':9}
checks=read(OUT/'qa/acceptance_checks.json')
panel_counts={f['figure']:f['panels'] for f in checks['figures']}
records=[]
for stem,count in expected_counts.items():
    notebook=HERE/(stem+'.ipynb')
    nb=nbformat.read(notebook,as_version=4)
    outputs=[]
    for cell in nb.cells:
        if cell.cell_type!='code':
            continue
        assert cell.metadata.get('jupyter',{}).get('source_hidden') is True
        for output in cell.outputs:
            data=output.get('data',{})
            if 'image/svg+xml' in data:
                outputs.append(('figure',data['image/svg+xml']))
            elif 'text/markdown' in data:
                outputs.append(('markdown',data['text/markdown']))
    html_path=OUT/(stem+'.html')
    page=ReadingHTML();page.feed(html_path.read_text())
    visible=' '.join(' '.join(page.parts).split())
    assert page.input_areas==0,stem
    seen=[]
    for i,(kind,content) in enumerate(outputs):
        if kind!='figure':continue
        assert outputs[i-1][0]=='markdown'
        match=re.search(r'id="reading-([^"]+)"',outputs[i-1][1])
        assert match, (stem,i,'Missing immediate figure question')
        name=match.group(1);assert name.startswith(stem[:2]) and name not in seen
        base=OUT/'figures'/stem[:2]/name
        reading=read(str(base)+'.reading.json')
        meta=read(str(base)+'.metadata.json')
        assert reading['narrative_code_sha256']==sha(HERE/'figure_narrative.py')
        frames={}
        for key,digest in reading['source_sha256'].items():
            path=base.with_name(name+'__'+key).with_suffix('.csv')
            assert sha(path)==digest
            frames[key]=pd.read_csv(path,float_precision='round_trip')
        recomputed=explain_figure(name,frames)
        for key,value in recomputed.items():assert reading[key]==value,(name,key)
        assert reading['panels']==panel_counts[name],name
        assert reading['question'] in outputs[i-1][1]
        assert outputs[i+1][0]=='markdown' and meta['caption'] in outputs[i+1][1]
        assert outputs[i+2][0]=='markdown'
        for key in ['pattern','meaning','limits']:
            assert reading[key] in outputs[i+2][1],(name,key,'Missing saved prose')
        # Every field must survive HTML conversion, not merely exist in source code.
        positions=[]
        for key in ['question','pattern','meaning','limits']:
            text=' '.join(reading[key].split())
            assert text in visible,(name,key,'Missing code-hidden HTML prose')
            positions.append(visible.index(text))
        assert positions==sorted(positions),(name,'HTML order')
        seen.append(name)
        records.append({'figure':name,'notebook':notebook.name,'panels':reading['panels'],
                        'reading_sha256':sha(str(base)+'.reading.json'),
                        'coverage_and_output_order':'pass','source_recomputation':'pass',
                        'code_hidden_html':'pass'})
    assert len(seen)==count,(stem,len(seen),count)
    for href in page.links:
        if href.startswith(('figures/','examples/')):
            assert (OUT/href).exists(),href
assert len(records)==34 and sum(r['panels'] for r in records)==44

baseline_path=OUT/'qa/pre_narrative_revision.json'
preservation={'status':'baseline unavailable'}
if baseline_path.exists():
    baseline=read(baseline_path)
    changed=[rel for rel,digest in baseline.items() if sha(OUT/rel)!=digest]
    assert not changed,changed
    preservation={'source_csv_files':sum(p.endswith('.csv') for p in baseline),
                  'pixel_identical_png_files':sum(p.endswith('.png') for p in baseline),
                  'changed':changed,'status':'pass'}
save_json(OUT/'qa/reading_checks.json',{
    'notebooks':{stem:sha(HERE/(stem+'.ipynb')) for stem in expected_counts},
    'html':{stem:sha(OUT/(stem+'.html')) for stem in expected_counts},
    'figures':records,'revision_preservation':preservation,
    'scope':'Mechanical coverage, source recomputation, saved output order and HTML visibility. '
            'Scientific/editorial validity requires the separate source-based review.'})
print(f'Validated {len(records)} complete reading units, 44 panels, four code-hidden HTML exports.')
print(json.dumps(preservation))
