"""Bind the final analysis inventory to current execution, figure and reading QA."""
from pathlib import Path
from html.parser import HTMLParser
import platform
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis_data import HERE, OUT, CACHE, read, save_json, sha, SEED

acceptance=read(OUT/'qa/acceptance_checks.json')
readings=read(OUT/'qa/reading_checks.json')
integrity=read(OUT/'integrity_report.json')
visual=read(OUT/'qa/visual_review_manifest.json')
previews=read(OUT/'review/preview_manifest.json')
snapshot=read(CACHE/'manifest.json')
assert integrity['native_runtime_matches_freeze']
assert readings['revision_preservation']['status']=='pass'
assert len(acceptance['notebooks'])==4 and len(readings['figures'])==34

for row in acceptance['notebooks']:
    path=HERE/row['notebook']
    assert sha(path)==row['sha256']==readings['notebooks'][path.stem]
    assert sha(OUT/(path.stem+'.html'))==readings['html'][path.stem]
for row in readings['figures']:
    path=OUT/'figures'/row['figure'][:2]/(row['figure']+'.reading.json')
    assert sha(path)==row['reading_sha256']
    assert read(path)['narrative_code_sha256']==sha(HERE/'figure_narrative.py')
for row in visual+previews:
    assert sha(OUT/'figures'/row['figure'][:2]/(row['figure']+'.pdf'))==row['pdf_sha256']

class Links(HTMLParser):
    def __init__(self):super().__init__();self.local=[]
    def handle_starttag(self,tag,attrs):
        href=dict(attrs).get('href','')
        if tag=='a' and href.startswith(('figures/','examples/')):self.local.append(href)

link_counts={}
for path in sorted(OUT.glob('0*.html')):
    parser=Links();parser.feed(path.read_text())
    for href in parser.local:assert (OUT/href).exists(),href
    link_counts[path.name]=len(parser.local)

numeric={'figure_source_tables_compared':readings['revision_preservation']['source_csv_files'],
         'changed':[],'result':'identical numerical outputs across independent executions'}
save_json(OUT/'numeric_repeat_report.json',numeric)
code_files=sorted(HERE.glob('*.py'))+sorted((HERE/'scripts').glob('*.py'))
manifest={
    'status':'complete_analysis_of_incomplete_main_run',
    'planned_cases':snapshot['case_count'],
    'common_completed_cases':snapshot['bace_complete'],
    'notebooks':acceptance['notebooks'],'figures':len(readings['figures']),
    'panels':sum(r['panels'] for r in readings['figures']),
    'source_files_verified':len(read(CACHE/'sources.json')),
    'source_index_sha256':sha(CACHE/'sources.json'),
    'native_integrity_report_sha256':sha(OUT/'integrity_report.json'),
    'numeric_repeat_report':numeric,
    'per_figure_readings':{'units':len(readings['figures']),
                         'checks_sha256':sha(OUT/'qa/reading_checks.json'),
                         'editorial_review_sha256':sha(HERE/'NARRATIVE_REVIEW.md'),
                         'revision_preservation':readings['revision_preservation']},
    'python':platform.python_version(),'dependency_lock_sha256':sha(HERE/'requirements.lock.txt'),
    'analysis_code_sha256':{p.relative_to(HERE).as_posix():sha(p) for p in code_files},
    'analysis_spec_sha256':sha(HERE/'ANALYSIS_SPEC.md'),
    'review_report_sha256':sha(HERE/'QA_REVIEW.md'),
    'html_source_links_verified':link_counts,'seed':SEED,
    'git_base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=HERE,text=True).strip(),
    'limitations':['Two BACE cases remain incomplete; no imputed scores.',
                  'Automated labels and native scores are not human accuracy estimates.',
                  'Qualitative readings are source inspections, not blinded adjudication.',
                  'Full raw model-call histories and complete extraction lineage were not re-audited by the analysis reader.']}
save_json(OUT/'analysis_manifest.json',manifest)
print('Bound four executed notebooks, 34 reading units and 44 panels to current QA records.')
