"""Build the four English notebooks from focused, reproducible analysis cells."""
from pathlib import Path
import subprocess
import sys
import textwrap
import nbformat as nbf

HERE=Path(__file__).resolve().parents[1]
SCAFFOLD=Path.home()/'.codex/skills/jupyter-notebook/scripts/new_notebook.py'
SETUP='''
from pathlib import Path
import sys
analysis_dir = Path.cwd()
if not (analysis_dir / 'analysis_data.py').exists():
    analysis_dir = analysis_dir / 'BACE' / 'analysis'
assert (analysis_dir / 'analysis_data.py').exists(), 'Run from the project root or analysis directory.'
sys.path.insert(0, str(analysis_dir))
sys.dont_write_bytecode = True
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from analysis_data import (load_snapshot, company_bootstrap, case_material, read, rows,
                           save_json, sha, HERE, BACE, ROOT, OUT, CACHE, SEED, METHODS, TASKS, LABELS)
from figure_style import (canvas, save_figure, quote_figure, ecdf, note,
                          BLUE, GREEN, ORANGE, GREY, INK, CMAP,
                          METHOD_COLORS, TYPE_COLORS, LABEL_NAMES, LABEL_COLORS)
tables = load_snapshot()
metrics = tables['metrics']
common = metrics.loc[metrics.bace_complete & metrics.ragchecker_complete & metrics.ragas_complete].copy()
bace = metrics.loc[metrics.bace_complete].copy()
claims = tables['claims']
sample = read(CACHE / 'sample.json')
execution = read(CACHE / 'execution.json')
note(f"**Snapshot:** {len(metrics):,} planned disclosures from {metrics.company_id.nunique()} companies; "
     f"{len(bace):,} complete BACE results and {len(common):,} common completed cases. "
     f"Run status: `{execution['status']}`. All results are automated; no human accuracy benchmark is supplied.")
'''
METHOD_NOTE='''
**Statistical scope.** The primary unit of presentation is a disclosure (company × year × task).
Repeated disclosures and extracted claims from the same company are dependent.
Where shown, 95% percentile intervals use 2,000 company-cluster bootstrap draws
(seed 20260921), resampling companies with replacement and retaining all their
observed disclosures. These are empirical, unweighted sample summaries, not
design-adjusted population estimates. They do not capture generation/judge
randomness or uncertainty due to the two missing BACE results. Subgroup comparisons
are descriptive; no hypothesis tests, significance stars or causal claims are made.
'''
END='''
## Reproducibility and interpretation boundary

Each figure is exported to `outputs/figures/` as editable PDF/SVG and 600 dpi PNG,
with its plotted source table(s), caption, and rendered QA records. The snapshot
manifest records source hashes and the verification scope. All observations are
retained unless an explicitly named cohort or case-selection rule is stated.

The source checks cover consumed artifacts and their completed-stage receipts,
shared prompt/context/response identity, and native metric arithmetic. They are
not a new audit of every raw model call or the entire extraction lineage.
Read the final audit report for figure-level visual checks and any reviewed warnings.
'''
READING_GUIDE='''
**How to read this notebook.** Each figure begins with a specific question. Its
caption explains the encodings and analysis scope; the following paragraphs
describe the observed pattern, its interpretation, and the remaining limits.
For multi-panel figures, read the individual panels and then their joint meaning.
“Middle half” means the 25th–75th percentiles. In an empirical cumulative
distribution (ECDF), the vertical coordinate is the proportion at or below the
horizontal value; a steep section marks a concentration of observations.
All of this text remains visible when code is hidden.
'''

def build(stem,title,sections):
    if len(sys.argv)>1 and stem not in sys.argv[1:]: return
    path=HERE/(stem+'.ipynb')
    subprocess.run([sys.executable,str(SCAFFOLD),'--kind','experiment','--title',title,'--out',str(path),'--force'],check=True,capture_output=True)
    nb=nbf.read(path,as_version=4)
    nb.cells=[]
    for kind,source in sections:
        cell=(nbf.v4.new_markdown_cell if kind=='md' else nbf.v4.new_code_cell)(textwrap.dedent(source).strip())
        if kind=='code': cell.metadata={'jupyter':{'source_hidden':True}}
        nb.cells.append(cell)
        if len(nb.cells)==1:
            nb.cells.append(nbf.v4.new_markdown_cell(textwrap.dedent(READING_GUIDE).strip()))
    nb.metadata.kernelspec={'display_name':'BACE analysis (Python)','language':'python','name':'bace-analysis'}
    nbf.write(nb,path)

s=[]
def md(x):s.append(('md',x))
def code(x):s.append(('code',x))
md('''# 00 · Where the evidence comes from

**Reader goal:** understand who and what the experiment covers, what was filtered,
and the difference between raw reports, extracted metrics, evidence cards and
what the generator actually saw.

**Reading route:** selection → geography and sectors → coverage → evidence scale
→ time boundaries → a traceable source-to-prompt example.

This is a retrospective data description. The country field comes from the
company register; it is not a map of offices, operations or environmental impacts.
''')
code(SETUP)
md('''## 1. How did the source register become the experimental sample?

The frozen eligibility rule requires a known SICS sector, at least one valid
nonempty CSV metric in every year 2015–2023, and a PDF with a valid header in every
year 2015–2022. Parsing is checked subsequently. Selection did not use evaluator
scores. One company is allocated to each eligible sector; the remaining places
use the frozen proportional allocation rule.
''')
code('''
selection = tables['selection']
stages = pd.DataFrame({'stage':['Source register','Eligible companies','Selected companies'],
                       'companies':[len(selection), int(selection.eligible.sum()), int(selection.selected.sum())]})
fig, (ax,) = canvas(height=75,left=.28)
ax.barh(stages.stage, stages.companies, color=[BLUE,GREEN,ORANGE],height=.55)
ax.invert_yaxis(); ax.set_xlabel('Companies'); ax.set_xlim(0, stages.companies.max()*1.13)
for i,n in enumerate(stages.companies): ax.text(n+8,i,str(n),va='center',fontsize=8)
ax.set_title('Selection narrows the population to a small, data-rich sample',loc='left')
save_figure(fig,'00_selection',stages,
    '**Read the figure:** bar lengths are company counts, not disclosures. No uncertainty interval applies to these census counts. '
    '**Boundary:** eligibility guarantees minimum source availability, not task completeness or extraction accuracy.')
''')
md('''## 2. Which places and sectors does the sample cover?

The map locates countries recorded for the selected companies. The sector plot
compares proportions at all three selection stages, so a small sector is not
mistaken for a large one merely because every sector receives at least one place.
''')
code('''
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
from matplotlib.colors import Normalize
from shapely.geometry import shape, box
countries = selection.loc[selection.selected].groupby('country').size().rename('companies').reset_index()
geo = read(HERE/'assets/ne_110m_admin_0_countries.geojson')
provenance = read(HERE/'assets/basemap_source.json')
assert sha(HERE/'assets/ne_110m_admin_0_countries.geojson') == provenance['sha256']
counts = countries.set_index('country').companies.to_dict()
fig, (ax,) = canvas(height=117,left=.06,right=.96,bottom=.12,top=.91)
patches, values, matched = [], [], set()
for feature in geo['features']:
    name = feature['properties']['ADMIN']
    if name in counts: matched.add(name)
    geometry = shape(feature['geometry']).intersection(box(-25,34,40,72))
    if geometry.is_empty: continue
    polys = list(geometry.geoms) if geometry.geom_type=='MultiPolygon' else [geometry]
    for poly in polys:
        if poly.geom_type=='Polygon':
            patches.append(Polygon(np.array(poly.exterior.coords))); values.append(counts.get(name,0))
assert matched == set(counts), f'Unmapped register countries: {set(counts)-matched}'
collection = PatchCollection(patches,cmap=CMAP,norm=Normalize(0,max(counts.values())),edgecolor='white',linewidth=.4)
collection.set_array(np.array(values)); ax.add_collection(collection)
ax.set_xlim(-25,40);ax.set_ylim(34,72);ax.set_aspect(1/np.cos(np.deg2rad(53)))
ax.axis('off'); ax.set_title('Selected companies by register country · Europe',loc='left')
cb=fig.colorbar(collection,ax=ax,orientation='horizontal',fraction=.045,pad=.025,shrink=.65)
cb.set_label('Selected companies');cb.set_ticks(range(0,max(counts.values())+1))
save_figure(fig,'00_geography',countries,
    '**Read the figure:** colour encodes selected company counts; zero means no selected company. All selected register countries lie in the displayed European extent. '
    'Natural Earth v5.1.2, public domain; cylindrical longitude/latitude display with aspect adjusted at 53°N. '
    '**Boundary:** this is register geography, not operational exposure; boundaries are contextual.')
''')
code('''
sector_rows=[]
for label, subset in [('Register',selection),('Eligible',selection[selection.eligible]),('Selected',selection[selection.selected])]:
    for sector,n in subset.groupby('primary_sics_sector',dropna=False).size().items():
        sector_rows.append({'cohort':label,'sector':sector if pd.notna(sector) else 'Unknown','companies':n,'denominator':len(subset),'percent':100*n/len(subset)})
sector_data=pd.DataFrame(sector_rows)
sector_order=sorted(sector_data.sector.unique())
fig,(ax,)=canvas(height=135,left=.43,top=.92,bottom=.13)
for j,(group,color,marker) in enumerate(zip(['Register','Eligible','Selected'],[BLUE,GREEN,ORANGE],['o','s','^'])):
    view=sector_data[sector_data.cohort==group].set_index('sector').reindex(sector_order).fillna(0)
    ax.scatter(view.percent,np.arange(len(view))+(j-1)*.20,color=color,marker=marker,s=24,label=group,edgecolor=INK,linewidth=.25)
ax.set_yticks(range(len(sector_order)),sector_order);ax.invert_yaxis();ax.set_xlabel('Companies within each cohort (%)')
ax.legend(loc='lower center',bbox_to_anchor=(.4,1.04),ncols=3)
save_figure(fig,'00_sector_selection',sector_data,
    '**Read the figure:** points show sector shares within each cohort; marker shape also distinguishes cohorts. All sectors, including missing classification, are retained. '
    '**Boundary:** stratification preserves sector coverage, not the original sector proportions; small selected sectors cannot support stable sector-specific inference.')
''')
md('''## 3. What coverage is available, and what does eligibility hide?

A nonzero source count is only an availability signal. It does not prove that a
report discusses a particular ESRS task. PDF counts below refer to valid headers
recorded during screening; canonical cards later reflect parsing and quarantine.
''')
code('''
coverage=tables['coverage']; selected_coverage=coverage[coverage.selected]
company_order=sorted(selected_coverage.company_name.unique())
fig,axs=canvas(height=185,cols=2,left=.24,right=.94,bottom=.11,top=.90,wspace=.45)
for ax,column,title in zip(axs,['csv_valid_metrics','pdf_valid_headers'],['Valid extracted CSV metrics','PDFs with valid headers']):
    grid=selected_coverage.pivot(index='company_name',columns='year',values=column).reindex(company_order)
    image=ax.imshow(np.ma.masked_invalid(grid.to_numpy()),aspect='auto',cmap=CMAP,vmin=0,interpolation='none')
    ax.set_facecolor('#D9DDE2');ax.set_xticks(range(len(grid.columns)),grid.columns,rotation=90)
    ax.set_yticks(range(len(grid)),grid.index if ax is axs[0] else ['']*len(grid));ax.tick_params(axis='both',length=0)
    ax.set_title(title,pad=12);ax.set_xlabel('Source year')
    # A shared figure-level horizontal strip avoids shrinking either comparison panel.
    cbax=fig.add_axes([.24 if ax is axs[0] else .665,.035,.23,.012]);cbax.set_label('<colorbar>')
    cbar=fig.colorbar(image,cax=cbax,orientation='horizontal')
    if column=='pdf_valid_headers': cbar.set_ticks([0,1,2])
save_figure(fig,'00_source_coverage',selected_coverage,
    '**Read the figure:** rows are the same 30 companies; columns are source years. Each panel has its own count scale. '
    'Grey in the PDF 2023 column is outside the required source window, not observed absence. '
    '**Boundary:** minimum annual coverage is selected by design; metric completeness and task relevance remain uneven.',axes=list(axs))
missing=selection.groupby(['missing_csv_year_count','missing_pdf_year_count'],dropna=False).size().reset_index(name='companies')
fig,(ax,)=canvas(height=80)
ax.scatter(missing.missing_csv_year_count,missing.missing_pdf_year_count,s=missing.companies*4+8,color=BLUE,edgecolor=INK,linewidth=.4)
ax.set_xlabel('Missing required CSV source years (out of 9)');ax.set_ylabel('Missing required PDF source years (out of 8)')
for n in [1,50,250]: ax.scatter([],[],s=n*4+8,color=BLUE,edgecolor=INK,linewidth=.4,label=str(n))
ax.legend(title='Companies',loc='center right',bbox_to_anchor=(1,.46),labelspacing=2.8,borderpad=1,handletextpad=1.8)
ax.set_xticks(range(10));ax.set_yticks(range(9));ax.set_xlim(-1,10);ax.set_ylim(-1.5,9.5);ax.set_title('Availability gaps across the entire company register',loc='left')
save_figure(fig,'00_screening_gaps',missing,
    '**Read the figure:** each point groups companies with the same two gap counts; marker area is 4 × company count + 8 points². '
    'All 600 screening records are included. No interval is shown for observed counts. Sector classification is an additional eligibility condition.')
''')
md('''## 4. How much evidence exists, and how much reaches a prompt?

Canonical cards are derived representations. One report may produce many cards;
a card can appear in several overlapping year packages and in several prompts.
These levels must not be added together or interpreted as independent evidence.
''')
code('''
canonical=tables['canonical_counts'];lengths=tables['length_counts'];visible=tables['visible']
fig,axs=canvas(height=85,cols=2,left=.19,right=.96,bottom=.20,top=.88,wspace=.65)
counts=canonical.groupby('type').cards.sum().reindex(TYPE_COLORS)
assert (counts>0).all() and (lengths.characters>0).all(), 'Logarithmic views require positive observed values.'
axs[0].scatter(counts.values,counts.index,color=list(TYPE_COLORS.values()),s=35,edgecolor=INK,linewidth=.4);axs[0].invert_yaxis()
axs[0].set_xscale('log');axs[0].set_xlim(1e4,1e6);axs[0].set_xticks([1e4,1e5,1e6],['10,000','100,000','1,000,000']);axs[0].set_xlabel('Canonical cards (log scale)');axs[0].set_title('Stored evidence')
for typ,color in TYPE_COLORS.items():
    view=lengths[lengths.type==typ].sort_values('characters')
    axs[1].step(view.characters,view['count'].cumsum()/view['count'].sum(),where='post',color=color,label=typ,ls={'PDF narrative':'-','PDF table row':'--','CSV metric':':'}[typ])
axs[1].set_xscale('log');axs[1].set_xticks([10,100,1000,10000],['10','100','1,000','10,000']);axs[1].set_xlabel('Characters per card (log scale)');axs[1].set_ylabel('Cumulative proportion')
from matplotlib.ticker import NullFormatter
for axis in axs: axis.xaxis.set_minor_formatter(NullFormatter())
axs[1].set_title('Card lengths');axs[1].legend(loc='lower right')
save_figure(fig,'00_evidence_scale',{'counts':counts.rename('cards').reset_index(),'length_frequencies':lengths},
    '**Read the figure:** panel a counts unique canonical cards by representation; panel b is the exact empirical cumulative distribution of retrieval-text lengths, weighted by the observed frequency of each length. '
    'No cards are sampled or dropped. Long cards contribute one observation each, not extra evidence units.')
prompt_counts=visible.groupby(['generation_case_id','type']).size().unstack(fill_value=0).reindex(metrics.generation_case_id,fill_value=0).reindex(columns=TYPE_COLORS,fill_value=0)
fig,(ax,)=canvas(height=82,left=.15)
for typ,color in TYPE_COLORS.items():
    frequency=prompt_counts[typ].value_counts().sort_index()
    ax.plot(frequency.index,frequency.values,marker={'PDF narrative':'o','PDF table row':'s','CSV metric':'^'}[typ],color=color,label=typ,lw=1.2)
ax.set_xlabel('Visible cards of a given type per disclosure');ax.set_ylabel('Disclosures');ax.legend(loc='upper left')
ax.set_xticks(range(11));ax.set_title('Retrieval caps the evidence actually shown',loc='left')
save_figure(fig,'00_visible_evidence',prompt_counts.reset_index(),
    '**Read the figure:** frequencies cover all planned disclosures, including zero-card strata. Retrieval selects up to 10 cards of each type using BM25/dense retrieval and reciprocal-rank fusion; unused slots are not redistributed. '
    '**Boundary:** the generator sees these selected cards, not the entire canonical library or source reports.')
note(f"**Observed:** {int(counts.sum()):,} canonical cards feed {len(tables['packages'][['company_id','year']].drop_duplicates())} overlapping company-year packages. "
     f"There are {len(visible):,} visible card appearances, representing {visible.evidence_id.nunique():,} distinct retrieved cards across {len(metrics):,} prompts.")
''')
md('''## 5. Which source years can inform a target-year disclosure?

For target year *t*, CSV evidence uses *t−4…t* and PDF evidence uses *t−4…t−1*.
These are report-year rules, not a historical publication-date cutoff. The use of
2023-edition ESRS task wording for earlier target years is an experimental task
framing, not evidence that those disclosures were legally required then.
''')
code('''
time_rows=[]
for target in sorted(metrics.year.unique()):
    for typ,lag in [('PDF',1),('CSV',0)]:
        for source in range(2015,2024):
            time_rows.append({'target_year':target,'type':typ,'source_year':source,'included':int(target-4<=source<=target-lag)})
time_data=pd.DataFrame(time_rows)
fig,axs=canvas(height=75,cols=2,left=.10,right=.95,bottom=.25,top=.80,wspace=.35)
from matplotlib.colors import ListedColormap
for ax,typ,color in zip(axs,['PDF','CSV'],[BLUE,ORANGE]):
    grid=time_data[time_data.type==typ].pivot(index='target_year',columns='source_year',values='included')
    ax.imshow(grid,aspect='auto',cmap=ListedColormap(['#EFF1F4',color]),vmin=0,vmax=1)
    ax.set_xticks(range(9),range(2015,2024),rotation=90);ax.set_yticks(range(5),grid.index)
    ax.set_xlabel('Permitted source year');ax.set_ylabel('Target year');ax.set_title(typ);ax.tick_params(length=0)
save_figure(fig,'00_time_windows',time_data,
    '**Read the figure:** coloured cells are allowed report years, grey cells are excluded by the protocol. This is the configured eligibility window, not a count of available records or proof of publication availability.')
''')
md('''## 6. Can a reader trace a prompt card back to a source?

The following deterministic example uses the first frozen case and the first
visible PDF narrative card. It illustrates the data path; it is not selected for
support success. The complete case evidence is exported alongside the figure.
''')
code('''
first_id=read(BACE/'results/main_v1/manifest.json')['case_ids'][0]
example=case_material(first_id)
card=next(c for c in example['input']['prompt_evidence'] if c['shown_in_prompt'] and c['evidence_type']=='narrative')
canonical_card=next(c for c in read(CACHE/'canonical_examples.json') if c['evidence_id']==card['evidence_id'])
assert canonical_card['retrieval_text']==card['retrieval_text']
example_dir=OUT/'examples';example_dir.mkdir(exist_ok=True)
save_json(example_dir/'00_source_to_prompt.json',{'case':example['input'],'canonical_card':canonical_card})
excerpt=card['retrieval_text'][:620]
blocks=[('Original source',f"{card['source_file']} · pages {card['page_start']}–{card['page_end']} · report year {card['source_year']}"),
        ('Derived representation',f"PDF narrative card. ID: {card['evidence_id']}"),
        ('Exact prompt excerpt'+(' (first 620 characters)' if len(card['retrieval_text'])>620 else ''),excerpt),
        ('Experimental use',f"{example['input']['company_name']} · target year {example['input']['target_reporting_year']} · {example['input']['task_id']}. The generator receives this text as {card['prompt_label']}.")]
quote_figure('00_provenance_example','A report becomes a card, then a bounded prompt input',blocks,
    pd.DataFrame([{'stage':a,'text':b} for a,b in blocks]),
    '**Read the figure:** the excerpt is copied verbatim from the frozen visible card and checked against the canonical index. Source filename and page references identify the underlying report. '
    '**Boundary:** a PDF-to-card transformation can lose layout or extraction detail; CSV values are also extracted outputs, not unquestioned ground truth.')
''')
md('''## What the reader should now be able to explain

- The sample is stratified and availability-filtered; it is not the entire register.
- Country and sector coverage constrain generalisation.
- Raw reports, extracted CSV metrics, canonical cards, overlapping packages and prompt-visible evidence are distinct objects.
- Complete annual availability does not imply complete task evidence.
- The next notebook assesses generated disclosures **within the visible evidence boundary**.
''')
md(END)
build('00_data_landscape','Where the evidence comes from',s)

s=[]
md('''# 01 · How strongly are disclosures supported?

**Reader goal:** distinguish overall support from its variation across disclosures,
tasks, companies and years, and interpret every indicator within its denominator.

**Reading route:** execution coverage → native support distribution → direct and
inferred support → task/company/year variation → secondary indicators and sensitivity.

An evidence claim (EC) is extracted from visible evidence; a disclosure claim (DC)
is extracted from generated text. BACE labels a DC direct if any accepted direct
support set exists; inferred if accepted sets exist but none is direct; otherwise
unsupported. These are automated judgements, not factual-truth labels.
''')
code(SETUP)
md(METHOD_NOTE)
md('''## 1. Is the analysis cohort complete?

Display completion before scores. Missing BACE branches are not zero support,
and an execution failure does not establish a false generated disclosure.
''')
code('''
status=pd.DataFrame({'stage':['Generation','BACE','RAGChecker','RAGAS'],
                     'complete':[int(metrics.stage_generation.sum()),int(metrics.bace_complete.sum()),int(metrics.ragchecker_complete.sum()),int(metrics.ragas_complete.sum())]})
status['missing']=len(metrics)-status.complete
fig,(ax,)=canvas(height=73,left=.23,right=.95)
ax.barh(status.stage,status.complete,color=[GREY,BLUE,GREEN,ORANGE]);ax.barh(status.stage,status.missing,left=status.complete,color='#6B737C')
ax.invert_yaxis();ax.set_xlabel('Planned disclosures');ax.set_xlim(0,len(metrics)*1.14)
for i,r in enumerate(status.itertuples()):ax.text(len(metrics)*1.01,i,f'{r.complete}/{len(metrics)}',va='center',fontsize=7)
save_figure(fig,'01_completion',status,
    '**Read the figure:** bars count completed branches; the narrow dark-grey remainder is missing. No scores are imputed. Completion is read from stage receipts and checked against execution status.')
missing=metrics.loc[~metrics.bace_complete,['company_name','year','task','state_status']]
note('**BACE gaps:** '+('; '.join(f'{r.company_name}, {r.year}, {r.task} ({r.state_status})' for r in missing.itertuples()) if len(missing) else 'None')+'.')
''')
md('''## 2. What does a typical disclosure look like?

The main score is supported DCs / all deduplicated DCs **within each disclosure**;
the main summary averages those disclosure-level rates. A pooled claim rate gives
more weight to disclosures producing more DCs and is reported separately.
''')
code('''
summary=company_bootstrap(bace,'bace_support_rate_all_dc')
fig,axs=canvas(height=87,cols=2,left=.11,right=.96,bottom=.22,top=.88,wspace=.42)
axs[0].hist(bace.bace_support_rate_all_dc,bins=np.linspace(0,1,21),color=BLUE,edgecolor='white',linewidth=.6)
axs[0].set_xlabel('Supported / all DCs');axs[0].set_ylabel('Disclosures');axs[0].set_xlim(0,1);axs[0].set_title('Full disclosure distribution')
parts=pd.DataFrame({'status':['Direct','Inferred','Unsupported'],'count':[bace.bace_supported_direct.sum(),bace.bace_supported_inferred.sum(),bace.bace_unsupported.sum()]})
parts['percent_all_dc']=100*parts['count']/parts['count'].sum()
axs[1].barh(parts.status,parts.percent_all_dc,color=[BLUE,GREEN,ORANGE]);axs[1].invert_yaxis();axs[1].set_xlim(0,100)
axs[1].set_xlabel('All deduplicated DCs (%)');axs[1].set_title('Claim-level decomposition')
save_figure(fig,'01_support_distribution',{'disclosures':bace[['generation_case_id','company_id','bace_support_rate_all_dc']],'claim_counts':parts},
    '**Read the figure:** panel a gives each disclosure one observation (20 equal-width bins); panel b pools DC counts, so it has a different weighting. '
    'All completed BACE disclosures and all their DCs are retained, including non-disclosure statements. Bar heights are observed counts/proportions; the macro interval is reported below.')
pooled=(bace.bace_supported_direct.sum()+bace.bace_supported_inferred.sum())/bace.bace_dc_count.sum()
''')
md('''## 3. Where does support vary across the twelve tasks?

Tasks are displayed in the frozen E1 → S1 → G1 order. Intervals use the same
company-cluster procedure in every row; they are not multiple-comparison tests.
''')
code('''
task_stats=pd.DataFrame([{'task':task,**company_bootstrap(bace[bace.task==task],'bace_support_rate_all_dc')} for task in TASKS])
fig,(ax,)=canvas(height=123,left=.22,top=.92,bottom=.12)
for i,r in enumerate(task_stats.itertuples()):
    color={'E1':BLUE,'S1':GREEN,'G1':ORANGE}[r.task.split('-')[0]]
    ax.errorbar(r.mean,i,xerr=[[r.mean-r.low],[r.high-r.mean]],fmt='o',color=color,ecolor=INK,elinewidth=.75,capsize=2,markersize=5)
ax.set_yticks(range(len(task_stats)),[f'{r.task}  (n={r.disclosures})' for r in task_stats.itertuples()]);ax.invert_yaxis()
ax.set_xlim(0,1);ax.set_xlabel('Mean disclosure support · 95% company-cluster interval')
ax.set_title('Task differences within the observed company sample',loc='left')
save_figure(fig,'01_task_support',task_stats,
    '**Read the figure:** points are disclosure-macro means; bars are 95% percentile intervals from 2,000 company-cluster resamples. n in each row counts disclosures; company counts are in source data. '
    '**Boundary:** task differences can reflect source relevance, generated content, extraction and judgement together.')
low=task_stats.loc[task_stats['mean'].idxmin()];high=task_stats.loc[task_stats['mean'].idxmax()]
''')
md('''## 4. Are aggregate results uniform across companies and years?

Every cell below averages completed tasks for one company-year. Grey would mark
an entirely missing company-year; partial cells retain their actual task count in
the source table. The same companies recur across years.
''')
code('''
cy=bace.groupby(['company_name','company_id','year']).agg(mean=('bace_support_rate_all_dc','mean'),disclosures=('generation_case_id','size')).reset_index()
grid=cy.pivot(index='company_name',columns='year',values='mean').sort_index()
fig,(ax,)=canvas(height=175,left=.30,right=.87,bottom=.10,top=.94)
im=ax.imshow(grid.to_numpy(),vmin=0,vmax=1,cmap=CMAP,aspect='auto');ax.set_facecolor(GREY)
ax.set_yticks(range(len(grid)),grid.index);ax.set_xticks(range(len(grid.columns)),grid.columns);ax.tick_params(length=0)
ax.set_xlabel('Target reporting year');ax.set_title('Mean support within each company-year',loc='left')
cbax=fig.add_axes([.90,.18,.018,.62]);cbax.set_label('<colorbar>');fig.colorbar(im,cax=cbax,label='Mean disclosure support')
save_figure(fig,'01_company_year',cy,
    '**Read the figure:** fixed 0–1 colour scale, alphabetical rows, no clustering or row normalisation. Cell counts are exported; incomplete tasks are not zeros. '
    '**Boundary:** these repeated company-year summaries are descriptive and cannot identify a temporal or company-specific cause.',axes=[ax])
year_stats=pd.DataFrame([{'year':year,**company_bootstrap(bace[bace.year==year],'bace_support_rate_all_dc')} for year in sorted(bace.year.unique())])
fig,(ax,)=canvas(height=73,left=.14)
ax.errorbar(year_stats.year,year_stats['mean'],yerr=[year_stats['mean']-year_stats.low,year_stats.high-year_stats['mean']],fmt='o-',color=BLUE,ecolor=INK,capsize=3)
ax.set_xticks(year_stats.year);ax.set_ylim(0,1);ax.set_xlabel('Target reporting year');ax.set_ylabel('Mean disclosure support')
save_figure(fig,'01_year_support',year_stats,
    '**Read the figure:** each point is a year-specific disclosure-macro mean with a 95% company-cluster bootstrap interval. Connecting lines guide the eye; the same companies recur. '
    '**Boundary:** changing source windows and task evidence preclude interpreting this as a causal improvement trend.')
''')
md('''## 5. What do the secondary indicators add?

- **ECCR:** distinct ECs appearing in any accepted support set / all extracted ECs.
  Alternative sets count toward its numerator. It is neither observed generator use nor ESRS completeness.
- **Inference rate:** DCs supported only by inference / all supported DCs.
- **Sensitivity:** exclude automatically labelled non-disclosure statements from the
  main support denominator. This is explicitly supplementary, not a replacement score.
- A multi-EC support set does not by itself imply inferential support.
''')
code('''
fig,axs=canvas(height=85,cols=2,left=.11,right=.96,bottom=.21,top=.87,wspace=.40)
for column,color,label,style in [('bace_eccr',BLUE,'ECCR','-'),('bace_inference_rate',GREEN,'Inference rate','--')]:
    ecdf(axs[0],bace[column],color,label,style)
axs[0].set_xlim(0,1);axs[0].set_xlabel('Metric value');axs[0].set_ylabel('Cumulative disclosures');axs[0].legend(loc='lower right')
delta=bace.bace_support_rate_excluding_non_disclosure_sensitivity-bace.bace_support_rate_all_dc
axs[1].hist(delta.dropna(),bins=20,color=ORANGE,edgecolor='white');axs[1].set_xlabel('Sensitivity minus main support rate');axs[1].set_ylabel('Disclosures')
save_figure(fig,'01_secondary_metrics',bace[['generation_case_id','company_id','bace_eccr','bace_inference_rate','bace_non_disclosure_statement','bace_support_rate_all_dc','bace_support_rate_excluding_non_disclosure_sensitivity']],
    '**Read the figure:** panel a shows exact empirical distributions (undefined ratios are excluded and counted below); panel b shows paired changes after removing non-disclosure statements. '
    '**Boundary:** a larger secondary metric is not automatically better quality.')
''')
md('''## What this establishes—and what it leaves open

The reader can now distinguish a typical disclosure from a pooled claim, locate
heterogeneity, and interpret uncertainty at the company level. The next notebook
asks what the unsupported claims actually say. None of these summaries proves
that a company is compliant, that a statement is false in the wider world, or
that the evaluator is correct.
''')
md(END)
build('01_evidence_support','How strongly are disclosures supported?',s)

s=[]
md('''# 02 · What lies behind an unsupported label?

**Reader goal:** recognise concrete diagnostic patterns while separating generated
content from evidence extraction, candidate selection and automated judgement.

**Reading route:** label composition → task prevalence → candidate and provenance
limits → six traceable cases → a source-layout check that challenges a label.

The six labels partition unsupported DCs in the frozen BACE pipeline. They are
**automated diagnostic categories**, not verified error classes. In particular,
a statement that a metric is not disclosed is not equivalent to fabricated data.
''')
code(SETUP)
md(METHOD_NOTE)
md('''## 1. Which labels dominate, and how often do they occur?

The same count answers different questions depending on its denominator:
all DCs, unsupported DCs, or disclosures containing at least one such label.
All three are retained below.
''')
code('''
unsupported=claims[claims.label.isin(LABELS)].copy()
composition=pd.DataFrame([{'label':label,'count':int((unsupported.label==label).sum()),
                          'disclosures':unsupported.loc[unsupported.label==label,'generation_case_id'].nunique()} for label in LABELS])
composition['percent_all_dc']=100*composition['count']/len(claims)
composition['percent_unsupported']=100*composition['count']/len(unsupported)
composition['percent_disclosures']=100*composition.disclosures/len(bace)
fig,axs=canvas(height=110,cols=2,left=.30,right=.96,bottom=.18,top=.88,wspace=.48)
y=np.arange(len(composition))
axs[0].barh(y,composition.percent_unsupported,color=[LABEL_COLORS[x] for x in LABELS])
for i,r in enumerate(composition.itertuples()): axs[0].text(r.percent_unsupported+2,i,f'{r.count:,}',va='center',fontsize=7)
axs[1].barh(y,composition.percent_disclosures,color=[LABEL_COLORS[x] for x in LABELS])
for ax in axs:
    ax.invert_yaxis();ax.set_xlim(0,100);ax.set_yticks(y,[LABEL_NAMES[x] for x in LABELS] if ax is axs[0] else ['']*len(y))
axs[0].set_xlabel('Unsupported DCs (%)');axs[1].set_xlabel('Completed disclosures (%)')
axs[0].set_title('Diagnostic composition');axs[1].set_title('At least one labelled DC')
save_figure(fig,'02_label_composition',composition,
    '**Read the figure:** panel a partitions all unsupported DCs; panel b measures label presence in a disclosure, so its bars can sum above 100%. '
    'All-DC proportions and exact counts accompany the figure. Counts are descriptive; claims within companies are dependent.')
top=composition.sort_values('count',ascending=False).iloc[0]
''')
md('''## 2. Do the same patterns appear across tasks?

Task-level proportions use **all DCs within each task** as the denominator.
This avoids making a task with very few unsupported claims look equally burdened
just because its unsupported subset has a distinctive composition.
''')
code('''
joined=claims.merge(bace[['generation_case_id','task']],on='generation_case_id',validate='many_to_one')
counts=pd.crosstab(joined.task,joined.label).reindex(index=TASKS,columns=LABELS,fill_value=0)
denominators=joined.groupby('task').size().reindex(TASKS)
rates=counts.div(denominators,axis=0)*100
fig,(ax,)=canvas(height=120,left=.14,right=.87,bottom=.29,top=.92)
im=ax.imshow(rates,cmap=CMAP,vmin=0,vmax=max(1,rates.to_numpy().max()),aspect='auto')
ax.set_yticks(range(len(TASKS)),TASKS);ax.set_xticks(range(len(LABELS)),['Non-disclosure','Contradiction','Conflation','Boundary','Inflation','Novelty'],rotation=45,ha='right',rotation_mode='anchor')
ax.tick_params(length=0);ax.set_title('Automated label burden by task',loc='left')
cbax=fig.add_axes([.90,.30,.018,.55]);cbax.set_label('<colorbar>');fig.colorbar(im,cax=cbax,label='All task DCs (%)')
source=rates.reset_index().melt(id_vars='task',var_name='label',value_name='percent_all_dc').merge(denominators.rename('all_dc'),on='task')
save_figure(fig,'02_task_patterns',source,
    '**Read the figure:** each cell is the percentage of all DCs in that task assigned the column label; all tasks and all six labels are shown. '
    'No clustering, row scaling, significance test or post-hoc task selection is used. Source data include each denominator.',axes=[ax])
''')
md('''## 3. Which parts of the pipeline require scrutiny?

A judgement can be affected by what was extracted from the evidence, which ECs
were offered as candidates, and how the judge read those ECs. An empty candidate
set is informative about this pipeline path; it does not prove that the full
visible source contained no relevant information. Literal quote localisation is
also only a provenance check, not a semantic fidelity test.
''')
code('''
checks=unsupported.groupby('label').agg(claims=('dc_id','size'),zero_candidates=('candidate_count',lambda x:int((x==0).sum())),
                                       no_exact_quote=('exact_quote_count',lambda x:int((x==0).sum()))).reindex(LABELS)
checks['zero_candidate_percent']=100*checks.zero_candidates/checks.claims
checks['no_exact_quote_percent']=100*checks.no_exact_quote/checks.claims
fig,(ax,)=canvas(height=102,left=.31,bottom=.18)
for j,(column,label,color,marker) in enumerate([('zero_candidate_percent','Zero candidate ECs',BLUE,'o'),('no_exact_quote_percent','No literal source quote',ORANGE,'s')]):
    ax.scatter(checks[column],np.arange(len(checks))+(j-.5)*.18,color=color,label=label,marker=marker,s=28,edgecolor=INK,linewidth=.3)
ax.set_yticks(range(len(checks)),[LABEL_NAMES[x] for x in checks.index]);ax.invert_yaxis();ax.set_xlim(0,100)
ax.set_xlim(-2,100);ax.set_xticks([0,20,40,60,80,100])
ax.set_xlabel('DCs within each automatic label (%)');ax.legend(loc='lower center',bbox_to_anchor=(.45,1.04),ncols=2)
save_figure(fig,'02_pipeline_checks',checks.reset_index(),
    '**Read the figure:** each point is a label-specific proportion among unsupported DCs. A literal quote must occur contiguously in the generated response. '
    '**Boundary:** noncontiguous table quotations can fail that check without being invented; neither indicator is an error-rate estimate.')
''')
md('''## 4. Six real cases: what changed between source and claim?

**Selection rule (fixed at the initial analysis snapshot):** for each label, sort all DCs with at least one literal
source quote by case and DC identifier; take one reproducible random example
(seed 20260921 plus the label index). This excludes unlocalised quotations only
from the illustrative sample; their counts remain above. No replacement is made
when the selected case challenges the automatic label. Selected IDs and original pool sizes are retained in a versioned manifest, so later completion of missing cases does not silently change these readings.

Each plate shows a verified generated excerpt, the extracted DC, a relevant
visible evidence excerpt and the unedited automatic rationale. The complete
visible evidence, candidates, ECs and generated text are exported in the case
bundle. The analyst's reading underneath is qualitative source inspection, not
blinded human adjudication or a population accuracy estimate.
''')
code('''
# These evidence-card choices are documented qualitative readings of the fixed random examples.
card_labels=['Evidence 21','Evidence 2','Evidence 7','Evidence 7','Evidence 13','Evidence 5']
review_notes=[
 'The selected DC explicitly reports non-disclosure in 2021. A zero-incident figure for 2017 does not fill that gap. This label should not be counted as fabrication or proof that the company withheld a metric.',
 'The narrative card flattens a two-column glossary. Inspection of the original PDF below assigns purchased CO2 to direct Scope 1 and electricity conversion factors to indirect Scope 2. The automatic rationale follows a misassociated extracted EC; this is not a clean generation-contradiction example.',
 'The generated sentence links earlier site assessments to a continuing 2022 priority. The 2021 source describes a more comprehensive approach and another card describes 2010–2017 assessments. The claimed ongoing priority and the relation between those statements require judgement; the automatic conflation label is not independently established.',
 'The wording about an online solution is supported in a 2019 report, while the generated disclosure is framed as 2022. The disputed boundary is temporal carry-forward. The excerpt alone cannot establish that the company stopped using the solution.',
 'The generated sentence uses “require”; the visible 2018 source uses “expect”. The table card interleaves neighbouring columns and is reproduced without repair. Other visible cards discuss supplier codes and strict procurement policies, so the strength of the complete obligation still requires contextual review. This illustrates modal-strength judgement, not a verified error count.',
 'The full visible card explicitly lists “Severity rate of workplace accident”. Its three retained ECs concern only identifying, prioritizing and validating risks. The diagnostic candidates omit the indicator. This is evidence of an extraction omission relevant to the rationale; the stronger target-year monitoring interpretation still needs review.'
]
examples=[]
fixed_examples=read(HERE/'assets/failure_example_selection.json')
for i,label in enumerate(LABELS):
    selected=fixed_examples[i]
    assert selected['label']==label
    original_pool_size=selected['pool_size']
    pick=claims[(claims.generation_case_id==selected['case_id'])&(claims.dc_id==selected['dc_id'])].iloc[0]
    assert pick.label==label and pick.exact_quote_count>0
    material=case_material(pick.generation_case_id)
    d=next(x for x in material['dc'] if x['dc_id']==pick.dc_id)
    diag=next(x for x in material['diagnosis'] if x['dc_claim_id']==pick.dc_id)
    card=next(c for c in material['input']['prompt_evidence'] if c['prompt_label']==card_labels[i])
    quotes=[q for p in d['dc_provenance'] for q in p['source_quotes'] if q in material['response']['generated_text']]
    quote=max(quotes,key=len)
    text=card['retrieval_text']
    start=max(0,text.find('We work closely')) if label=='inferential_inflation' else 0
    excerpt=text[start:start+720]
    case_name=f"{material['input']['company_name']} · {material['input']['target_reporting_year']} · {material['input']['task_id'].split('_')[0]}"
    blocks=[('Generated disclosure · verbatim',quote),('Extracted DC',d['dc_text']),
            (f"Visible evidence · {card['prompt_label']} · source year {card['source_year']}",excerpt),
            ('Automatic diagnostic rationale',diag['rationale'])]
    (OUT/'examples').mkdir(exist_ok=True)
    save_json(OUT/'examples'/f'02_{label}.json',{'selection':{'seed':SEED+i,'pool_size':original_pool_size,'dc_id':pick.dc_id},
              'selected_card':card,'analyst_note':review_notes[i],'material':material})
    quote_figure('02_example_'+label,case_name,blocks,pd.DataFrame([{'role':a,'text':b} for a,b in blocks]),
        f"**Automatic label: {LABEL_NAMES[label]}.** {original_pool_size:,} localisable DCs were eligible for this illustrative draw. "
        f"The evidence excerpt begins at character {start} and ends at {start+len(excerpt)}. [Full case and source references](outputs/examples/02_{label}.json).")
    examples.append({'label':label,'generation_case_id':pick.generation_case_id,'dc_id':pick.dc_id,'pool_size':original_pool_size,'card':card['evidence_id']})
pd.DataFrame(examples).to_csv(OUT/'examples/02_selection.csv',index=False)
''')
md('''## 5. Does the original source layout support the contradiction rationale?

For the ASML example, inspect the actual report page as well as the flattened
card. The two-column glossary defines direct Scope 1 using natural gas and
purchased CO₂, and indirect Scope 2 using electricity conversion factors. The
rendering below preserves the original page layout. It is an additional source
check; the original PDF page was not separately supplied to the generator.
''')
code('''
import pymupdf
pdf=ROOT/'data/raw/reports_pdf/2e1f7005-6454-4596-8e28-87214e82b95e_2018_AR.pdf'
expected=read(CACHE/'source_pdfs.json')[pdf.name]
assert sha(pdf)==expected
with pymupdf.open(pdf) as document:
    page=document[215]
    pix=page.get_pixmap(matrix=pymupdf.Matrix(3,3),clip=pymupdf.Rect(50,452,538,515))
    pixels=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,pix.n)
fig,(ax,)=canvas(height=55,left=.005,right=.995,bottom=.08,top=.88)
ax.imshow(pixels);ax.axis('off');ax.set_title('Original glossary rows · ASML Integrated Report 2018',loc='left',fontsize=9,x=.04)
save_figure(fig,'02_asml_source_layout',pd.DataFrame([{'source_file':pdf.name,'sha256':expected,'pdf_page':216,'printed_page':209,'clip_points':'50,452,538,515'}]),
    '**Read the source:** ASML Integrated Report 2018, PDF page 216 (printed page 209), glossary crop. Scope 1 and Scope 2 occupy separate rows. '
    '**Observed:** the automatic contradiction rationale assigns the electricity definition to Scope 1, contrary to the original row association. This reveals a source-representation/extraction problem; it does not estimate the frequency of such problems.')
''')
md('''## What the reader should now be able to explain

Diagnostic composition identifies where to inspect, not a final ledger of true
errors. A difference in year, scope, relation or obligation strength can explain
an automatic label. But visible evidence can be lost during EC extraction, and
PDF reading order can change an apparent contradiction. The selected examples
therefore support both substantive interpretation and scrutiny of the evaluator.
The next notebook compares what the three evaluators measure.
''')
md(END)
build('02_failure_patterns','What lies behind an unsupported label?',s)

s=[]
md('''# 03 · Why do the evaluators disagree?

**Reader goal:** distinguish native score differences, rank association,
segmentation differences and claim-level judgement, without treating the highest
or lowest score as evidence of evaluator quality.

**Reading route:** common cohort and definitions → paired score differences →
ranking → native claim counts → disagreements in both directions → validation needs.

BACE, RAGChecker and RAGAS evaluate the same generated text and visible evidence,
but construct different claim inventories. Their native rates therefore have
different denominators. The shared judge deployment also means that agreement
between them is not independent confirmation of correctness.
''')
code(SETUP)
md(METHOD_NOTE)
md('''## 1. How do the native scores differ on the same disclosures?

All paired comparisons below use the common completed cohort. External-only
cases remain in the execution inventory and their complete-cohort summaries are
reported explicitly rather than silently mixed into paired comparisons.
''')
code('''
summary_rows=[]
for method,column in METHODS.items():
    summary_rows.append({'method':method,'cohort':'Common',**company_bootstrap(common,column)})
    if method!='BACE':
        summary_rows.append({'method':method,'cohort':'All available',**company_bootstrap(metrics.dropna(subset=[column]),column)})
summary=pd.DataFrame(summary_rows)
fig,axs=canvas(height=87,cols=2,left=.12,right=.96,bottom=.22,top=.86,wspace=.45)
for method,column in METHODS.items():
    ecdf(axs[0],common[column],METHOD_COLORS[method],method,{'BACE':'-','RAGChecker':'--','RAGAS':':'}[method])
axs[0].set_xlim(0,1);axs[0].set_xlabel('Native support / faithfulness score');axs[0].set_ylabel('Cumulative disclosures');axs[0].legend(loc='upper left')
differences=[]
for j,other in enumerate(['RAGChecker','RAGAS']):
    column='difference_'+other
    common[column]=common[METHODS['BACE']]-common[METHODS[other]]
    stats=company_bootstrap(common,column);differences.append({'contrast':'BACE − '+other,**stats})
    axs[1].errorbar(stats['mean'],j,xerr=[[stats['mean']-stats['low']],[stats['high']-stats['mean']]],fmt=['s','^'][j],color=METHOD_COLORS[other],ecolor=INK,capsize=3)
axs[1].axvline(0,color=GREY,lw=.8,ls='--');axs[1].set_yticks([0,1],['BACE − RAGChecker','BACE − RAGAS'],fontsize=7)
axs[1].set_ylim(-.6,1.6);axs[1].set_xlim(-.5,.05);axs[1].set_xlabel('Mean paired difference · 95% interval')
save_figure(fig,'03_native_comparison',{'scores':common[['generation_case_id','company_id',*METHODS.values()]],'cohort_summary':summary,'paired_differences':pd.DataFrame(differences)},
    '**Read the figure:** panel a gives each common disclosure equal weight; panel b first subtracts scores within the same disclosure, then bootstraps company clusters. '
    'The intervals describe paired native score gaps, not differences in evaluator accuracy.')
for r in summary.itertuples():
    note(f"**{r.method}, {r.cohort.lower()} cohort:** mean {r.mean:.1%} (95% interval {r.low:.1%}–{r.high:.1%}; {r.disclosures:,} disclosures, {r.companies} companies).")
''')
md('''## 2. Do high-scoring disclosures stay high across evaluators?

Score-level agreement and rank association are distinct. A shared ordering can
coexist with a large systematic difference in score level. Every point below is
a common disclosure; overplotting is handled with transparency, not sampling.
''')
code('''
from scipy.stats import spearmanr
pairs=[('BACE','RAGChecker'),('BACE','RAGAS'),('RAGChecker','RAGAS')]
rank_rows=[]
fig,axs=canvas(height=78,cols=3,left=.09,right=.97,bottom=.25,top=.82,wspace=.45)
for ax,(a,b) in zip(axs,pairs):
    x=common[METHODS[a]];y=common[METHODS[b]]
    ax.scatter(x,y,s=5,alpha=.45,color=METHOD_COLORS[b],edgecolors='none',rasterized=True)
    ax.plot([0,1],[0,1],color=GREY,ls='--',lw=.7);ax.set_xlim(0,1);ax.set_ylim(0,1)
    ax.set_xticks([0,.5,1]);ax.set_yticks([0,.5,1]);ax.set_xlabel(a);ax.set_ylabel(b)
    rho=float(spearmanr(x,y).statistic);rank_rows.append({'method_a':a,'method_b':b,'spearman_rho':rho,'disclosures':len(common),'companies':common.company_id.nunique()})
    ax.set_title(f'Spearman ρ = {rho:.2f}',fontsize=8)
save_figure(fig,'03_rank_agreement',{'scores':common[['generation_case_id','company_id',*METHODS.values()]],'rank_associations':pd.DataFrame(rank_rows)},
    '**Read the figure:** the dashed line is equal native scores, not a fitted regression. Spearman coefficients are descriptive and include ties. '
    'No p-values are reported because disclosures are clustered and the purpose is descriptive. Shared judge deployment limits independence.')
''')
md('''## 3. How much does the claim inventory differ?

Before attributing a score gap to stricter judgement, inspect the extracted claim
counts. Different segmentation, omitted content and non-disclosure treatment can
change both numerator and denominator. A count difference alone cannot quantify
how much of a score gap it caused.
''')
code('''
claim_columns={'BACE':'bace_dc_count','RAGChecker':'ragchecker_claim_count','RAGAS':'ragas_claim_count'}
fig,axs=canvas(height=85,cols=2,left=.12,right=.95,bottom=.22,top=.88,wspace=.43)
for method,column in claim_columns.items():
    ecdf(axs[0],common[column],METHOD_COLORS[method],method,{'BACE':'-','RAGChecker':'--','RAGAS':':'}[method])
axs[0].set_xlabel('Native claims per disclosure');axs[0].set_ylabel('Cumulative disclosures');axs[0].legend(loc='lower right')
claim_delta=common.bace_dc_count-common.ragchecker_claim_count
score_delta=common.bace_support_rate_all_dc-common.ragchecker_faithfulness
axs[1].scatter(claim_delta,score_delta,s=7,color=BLUE,alpha=.45,edgecolors='none',rasterized=True)
axs[1].axhline(0,color=GREY,lw=.7,ls='--');axs[1].set_xlabel('BACE − RAGChecker claim count');axs[1].set_ylabel('BACE − RAGChecker score')
save_figure(fig,'03_claim_inventories',common[['generation_case_id','company_id',*claim_columns.values(),*METHODS.values()]],
    '**Read the figure:** panel a includes every native claim count; panel b compares within-disclosure count and score differences. No causal decomposition is implied. '
    'DC totals and comparator claim totals are different inventories, not a shared set of propositions.')
''')
md('''## 4. Where do disagreements concentrate by task?

A paired gap can vary by task. This chart retains the fixed task order and both
comparators; it does not select only tasks with the largest gap.
''')
code('''
gaps=[]
for task in TASKS:
    view=common[common.task==task].copy()
    for other in ['RAGChecker','RAGAS']:
        view['gap']=view.bace_support_rate_all_dc-view[METHODS[other]]
        gaps.append({'task':task,'comparison':other,**company_bootstrap(view,'gap')})
gaps=pd.DataFrame(gaps)
fig,(ax,)=canvas(height=123,left=.17,right=.96,bottom=.14,top=.85)
for j,(other,marker) in enumerate([('RAGChecker','s'),('RAGAS','^')]):
    view=gaps[gaps.comparison==other].set_index('task').loc[TASKS]
    ax.errorbar(view['mean'],np.arange(len(TASKS))+(j-.5)*.22,xerr=[view['mean']-view.low,view.high-view['mean']],fmt=marker,color=METHOD_COLORS[other],ecolor=METHOD_COLORS[other],capsize=2,label='BACE − '+other,markersize=4)
ax.axvline(0,color=GREY,lw=.7,ls='--');ax.set_yticks(range(len(TASKS)),TASKS);ax.invert_yaxis();ax.set_xlim(-.65,.1)
ax.set_xlabel('Mean paired native score difference · 95% company-cluster interval');ax.legend(loc='lower center',bbox_to_anchor=(.5,1.04),ncols=2)
save_figure(fig,'03_task_disagreement',gaps,
    '**Read the figure:** each point is a within-task paired macro difference, with the same 2,000-draw company bootstrap procedure. '
    'All task rows are shown, including reduced denominators from the incomplete BACE cases. No multiple-comparison significance claim is made.')
''')
md('''## 5. Can we compare individual claims without pretending inventories match?

The following audit matches only **identical text after Unicode case-folding and
whitespace normalisation within the same case**. RAGChecker triples are joined
with spaces; no semantic matching or punctuation removal is performed. Ambiguous
repeated keys are excluded from this narrow alignment audit and counted.

This deliberately restricted overlap cannot estimate global evaluator accuracy
or agreement. Unmatched claims are not disagreements: they may be paraphrases,
splits, merges or omissions.
''')
code('''
normalise=lambda text:' '.join(str(text).casefold().split())
left=claims[claims.generation_case_id.isin(common.generation_case_id)].copy()
left['key']=left.dc_text.map(normalise);left['supported']=left.label.isin(['direct','inferred'])
ext=tables['external_claims'];alignment=[];matched_tables=[]
for framework in ['ragchecker','ragas']:
    right=ext[(ext.framework==framework)&ext.generation_case_id.isin(common.generation_case_id)].copy()
    right['key']=right.claim_text.map(normalise)
    keys=['generation_case_id','key']
    lu=left[~left.duplicated(keys,keep=False)];ru=right[~right.duplicated(keys,keep=False)]
    match=lu.merge(ru,on=keys,suffixes=('_bace','_external'),validate='one_to_one')
    match['agreement']=match.supported_bace==match.supported_external
    alignment.append({'framework':framework,'bace_claims':len(left),'external_claims':len(right),'matched_pairs':len(match),
                      'agreements':int(match.agreement.sum()),'bace_ambiguous_rows':len(left)-len(lu),'external_ambiguous_rows':len(right)-len(ru)})
    matched_tables.append(match)
alignment=pd.DataFrame(alignment)
fig,(ax,)=canvas(height=73,left=.22)
coverage=100*alignment.matched_pairs/alignment.bace_claims
ax.barh(['RAGChecker','RAGAS'],coverage,color=[GREEN,ORANGE]);ax.set_xlim(0,100);ax.set_xlabel('BACE DCs with a unique exact-text partner (%)')
for i,r in enumerate(alignment.itertuples()):ax.text(coverage.iloc[i]+1,i,f'{r.matched_pairs:,} pairs',va='center',fontsize=8)
save_figure(fig,'03_alignment_coverage',alignment,
    '**Read the figure:** bars show alignment coverage, not support or agreement. Ambiguous key counts and total native inventories are exported. '
    '**Boundary:** selection into exact-text overlap is highly non-random; matched judgement agreement cannot be extrapolated to all claims.')
for r in alignment.itertuples():
    note(f"**{r.framework}:** {r.matched_pairs:,} unique exact-text pairs; {r.agreements:,} have matching binary verdicts. "
         f"Ambiguous rows excluded: BACE {r.bace_ambiguous_rows:,}, comparator {r.external_ambiguous_rows:,}. Unmatched rows remain in all native score analyses.")
for framework,matched in zip(['ragchecker','ragas'],matched_tables):
    matched.to_csv(OUT/f'{framework}_exact_text_pairs.csv',index=False)
''')
md('''## 6. What do disagreements in both directions look like?

**Case selection:** among common cases, select the minimum and maximum
BACE-minus-RAGChecker score gaps (ties broken by case ID). These are deliberately
extreme illustrations, not representative estimates. Show all three native
scores and claim inventories; retain the full generated text and both comparison
outputs in the exported case bundle.
''')
code('''
common['gap_rc']=common.bace_support_rate_all_dc-common.ragchecker_faithfulness
ordered=common.sort_values(['gap_rc','generation_case_id'])
for direction,row in [('lower',ordered.iloc[0]),('higher',ordered.iloc[-1])]:
    material=case_material(row.generation_case_id)
    local=claims[claims.generation_case_id==row.generation_case_id]
    label_counts=local.label.value_counts()
    blocks=[('Common generated disclosure · first 700 characters',material['response']['generated_text'][:700]),
            ('Native scores and denominators','; '.join(f"{method}: {row[column]:.1%}, {int(row[claim_columns[method]])} claims" for method,column in METHODS.items())),
            ('BACE claim inventory','; '.join(f'{label.replace("_"," ")}: {n}' for label,n in label_counts.items())),
            ('Interpretation boundary','The score direction is a native-output difference. It does not establish which evaluator is correct. Inspect claim segmentation, visible evidence, source-year boundaries and judgement together.')]
    (OUT/'examples').mkdir(exist_ok=True)
    save_json(OUT/'examples'/f'03_bace_{direction}_than_ragchecker.json',{'selection_rule':'Extreme paired score gap; case ID breaks ties','gap':float(row.gap_rc),'material':material})
    quote_figure('03_case_'+direction,f'{row.company_name} · {row.year} · {row.task}',blocks,
        pd.DataFrame([{'role':a,'text':b} for a,b in blocks]),
        f'**Observed:** BACE minus RAGChecker = {row.gap_rc:+.3f}. This is an extreme case selected to explain a disagreement direction; it is not an accuracy example. [Full case](outputs/examples/03_bace_{direction}_than_ragchecker.json).')
''')
md('''### Two concrete judgement paths

These fixed, source-inspected examples complement the extreme-case summaries.
The related native claims are displayed as written; this is a qualitative
comparison, not an assertion that whole claim inventories align one-to-one.
''')
code('''
case_ids={
 'source_coverage':'w2__text_embedding_3_large__stratified_by_evidence_type_n10__investec__2021__g1_4_corruption_bribery_incidents',
 'combined_evidence':'w2__text_embedding_3_large__stratified_by_evidence_type_n10__banco_bpm__2021__e1_6_ghg_emissions'}
for kind,cid in case_ids.items():
    material=case_material(cid)
    if kind=='source_coverage':
        did='dc_ac42ae6401085c4c4b25ea9a5a8a6b3f'
        dc=next(c for c in material['dc'] if c['dc_id']==did)
        diagnosis=next(c for c in material['diagnosis'] if c['dc_claim_id']==did)
        rc=next(c for c in material['ragchecker']['claims'] if 'employees, clients, suppliers and other stakeholders' in ' '.join(c['claim']))
        card=next(c for c in material['input']['prompt_evidence'] if c['prompt_label']=='Evidence 7')
        blocks=[('BACE DC · unsupported novelty',dc['dc_text']),
                ('BACE rationale',diagnosis['rationale']),
                ('RAGChecker native claim · supported',' | '.join(rc['claim'])),
                ('Visible source · 2017 annual report, PDF page 102',card['retrieval_text'])]
        reading='The full visible source explicitly mentions suppliers in the risk definition. BACE judged an extracted EC/candidate representation, while RAGChecker judged card-level contexts. This evidence challenges the absence-of-anchor rationale; it does not establish full 2021 temporal validity or global comparator superiority.'
    else:
        did='dc_63aa1cb575b94ec6692de318547d7e6b'
        dc=next(c for c in material['dc'] if c['dc_id']==did)
        support=next(c for c in material['support'] if c['dc_claim_id']==did)
        assert support['support_sets'][0]['support_type']=='inferred'
        ec_ids=support['support_sets'][0]['ec_claim_ids']
        ecs=[c for c in material['ec'] if c['ec_id'] in ec_ids]
        rc=next(c for c in material['ragchecker']['claims'] if 'were identical to' in c['claim'])
        ra=next(c for c in material['ragas']['claims'] if 'were identical to' in c['claim'])
        evidence_ids={eid for ec in ecs for eid in ec['evidence_card_ids']}
        evidence=[c for c in material['input']['prompt_evidence'] if c['evidence_id'] in evidence_ids]
        values='; '.join(f"{c['metric']}: {c['value_text']} {c['unit'] or ''}" for c in evidence)
        blocks=[('BACE DC · inferred from a four-EC support set',dc['dc_text']),
                ('RAGChecker native claim · unsupported',' | '.join(rc['claim'])),
                ('RAGAS · supported',ra['reason']),('Visible 2021 CSV values',values)]
        reading='The equality statement requires comparing four values across evidence cards. BACE accepted one inferred set containing four ECs; RAGChecker marked every individual context neutral for its equality claim; RAGAS accepted the comparison. This illustrates the role of evidence combination. The underlying CSV values remain extracted data and are not independently verified emissions.'
        assert len(ec_ids)==4 and not rc['supported'] and ra['supported']
    save_json(OUT/'examples'/f'03_{kind}_reading.json',{'case_id':cid,'dc_id':did,'reading':reading,'blocks':blocks})
    quote_figure('03_judgement_'+kind,material['input']['company_name']+' · a concrete judgement path',blocks,
        pd.DataFrame([{'role':a,'text':b} for a,b in blocks]),
        '**Read the plate:** native claims and reasons are quoted without semantic rewriting; the source texts come from the same frozen prompt. Full case material is available in the companion case bundle.')
''')
md('''## What would establish which evaluator is more accurate?

A defensible follow-up requires a shared, independently reviewed target:

1. Audit evidence and disclosure extraction against the complete original visible
   source, including omitted propositions and ambiguous source layouts.
2. Define a shared proposition inventory or an explicitly reviewed mapping that
   represents one-to-many segmentation and reports unmatched content.
3. Have blinded reviewers assess support with all relevant visible evidence,
   preserve sampling probabilities, and adjudicate disagreements.
4. Report evaluator performance against that reference with company-level
   dependence and annotation uncertainty accounted for.

The existing preparation material contains no completed formal human annotations.
A BACE-only DC sample cannot, by itself, fairly benchmark comparator extraction
coverage. Shared model deployment further limits treating agreement as validation.

**Reader checkpoint:** a lower native score means fewer native claims were judged
supported under that pipeline. It does not automatically mean a more accurate,
more useful or more trustworthy evaluator.
''')
md(END)
build('03_evaluator_comparison','Why do the evaluators disagree?',s)
