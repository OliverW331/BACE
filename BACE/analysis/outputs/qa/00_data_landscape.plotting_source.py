"""Consistent Python figure export, source data and rendered quality gates."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).resolve().parent/'outputs/.matplotlib'))
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd
from IPython.display import SVG, display, Markdown
from analysis_data import HERE, OUT, sha, save_json

SKILL = Path(os.environ.get('NATURE_FIGURE_SKILL', Path.home()/'.codex/skills/nature-figure'))
sys.path.insert(0,str(SKILL/'scripts'))
from audit_panel_alignment import require_matplotlib_panel_alignment
BLUE='#7AAED6'; GREEN='#83C5A3'; ORANGE='#F3B27A'; GREY='#B7BDC5'; INK='#283440'
METHOD_COLORS={'BACE':BLUE,'RAGChecker':GREEN,'RAGAS':ORANGE}
TYPE_COLORS={'PDF narrative':BLUE,'PDF table row':GREEN,'CSV metric':ORANGE}
LABEL_NAMES={'non_disclosure_statement':'Non-disclosure statement','contradiction':'Contradiction',
             'evidence_conflation':'Evidence conflation','factual_boundary_distortion':'Factual boundary distortion',
             'inferential_inflation':'Inferential inflation','unsupported_novelty':'Unsupported novelty'}
LABEL_COLORS=dict(zip(LABEL_NAMES,[GREY,'#CC8FA5',GREEN,BLUE,ORANGE,'#B8A6D9']))
CMAP=LinearSegmentedColormap.from_list('candy_blue',['#F3F7FB',BLUE,'#35688F'])

mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'], 'font.size':8,
 'axes.labelsize':8,'axes.titlesize':9,'xtick.labelsize':7,'ytick.labelsize':7,
 'legend.fontsize':7,'axes.spines.right':False,'axes.spines.top':False,'axes.linewidth':.65,
 'xtick.major.width':.6,'ytick.major.width':.6,'text.color':INK,'axes.labelcolor':INK,
 'xtick.color':INK,'ytick.color':INK,'legend.frameon':False,'svg.fonttype':'none','pdf.fonttype':42,
 'figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white','figure.dpi':120})

def canvas(height=85,cols=1,rows=1,width=183,left=.13,right=.96,bottom=.16,top=.88,wspace=.35,hspace=.5):
    fig,axs=plt.subplots(rows,cols,figsize=(width/25.4,height/25.4),squeeze=False)
    fig.subplots_adjust(left=left,right=right,bottom=bottom,top=top,wspace=wspace,hspace=hspace)
    if rows*cols>1:
        for i,ax in enumerate(axs.flat):
            ax.text(-.10,1.09,chr(97+i),transform=ax.transAxes,fontsize=9,fontweight='bold',va='bottom')
    return fig,axs.ravel()

def note(text):
    display(Markdown(text))

def ecdf(ax, values, color=BLUE,label=None,ls='-'):
    x=np.sort(np.asarray(values.dropna() if hasattr(values,'dropna') else values))
    ax.step(x,np.arange(1,len(x)+1)/len(x),where='post',color=color,label=label,ls=ls,lw=1.5)

def save_figure(fig,name,data,caption,axes=None):
    """Export the same figure three ways, measuring layout before every export."""
    from figure_narrative import explain_figure
    directory=OUT/'figures'/name[:2]; directory.mkdir(parents=True,exist_ok=True)
    base=directory/name
    frames=data if isinstance(data,dict) else {'data':data}
    reading=explain_figure(name,frames)
    for key,frame in frames.items():
        frame.to_csv(base.with_name(base.name+'__'+key).with_suffix('.csv'),index=False)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,axes=axes,json_out=str(base)+'.alignment.json',
                                       tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True)
    fig.savefig(str(base)+'.pdf',dpi=600)
    fig.savefig(str(base)+'.svg',dpi=600)
    fig.savefig(str(base)+'.png',dpi=600)
    text_audit=subprocess.run([sys.executable,str(SKILL/'scripts/audit_pdf_text.py'),str(base)+'.pdf','--json'],capture_output=True,text=True)
    Path(str(base)+'.text-audit.json').write_text(text_audit.stdout)
    collision=subprocess.run([sys.executable,str(SKILL/'scripts/audit_figure_collisions.py'),str(base)+'.pdf',
                              '--json-out',str(base)+'.collision-audit.json'],capture_output=True,text=True)
    Path(str(base)+'.collision-audit.txt').write_text(collision.stdout+collision.stderr)
    save_json(str(base)+'.metadata.json',{'figure':name,'caption':caption,'width_mm':float(fig.get_figwidth()*25.4),
          'height_mm':float(fig.get_figheight()*25.4),'png_dpi':600,'data_files':[base.name+'__'+key+'.csv' for key in frames],
          'audit_exit_codes':{'text':text_audit.returncode,'collision':collision.returncode},
          'exports':{ext:sha(str(base)+'.'+ext) for ext in ['pdf','svg','png']}})
    note(f'<a id="reading-{name}"></a>\n\n**Figure question · {name.replace("_", " ")}.** '+reading['question'])
    display(SVG(filename=str(base)+'.svg'))
    plt.close(fig)
    relative=base.relative_to(HERE).as_posix()
    links=[f'[{ext.upper()}]({relative}.{ext})' for ext in ['pdf','svg','png']]
    links += [f'[Source data: {key}]({relative}__{key}.csv)' for key in frames]
    note(caption+'\n\n'+ ' · '.join(links))
    after=('**Pattern and evidence.** '+reading['pattern']+'\n\n'
           '**Interpretation.** '+reading['meaning']+'\n\n'
           '**Limits and alternative readings.** '+reading['limits'])
    note(after)
    save_json(str(base)+'.reading.json',{'figure':name,**reading,'caption':caption,
              'source_sha256':{key:sha(base.with_name(base.name+'__'+key).with_suffix('.csv')) for key in frames},
              'narrative_code_sha256':sha(HERE/'figure_narrative.py')})
    # Keep the diagnostic exports to allow repair; fail the notebook on reliable geometry failures.
    if (text_audit.returncode or collision.returncode) and os.environ.get('BACE_ANALYSIS_DIAGNOSTIC') != '1':
        raise RuntimeError(f'Rendered QA requires repair: {name}; inspect its audit files.')

def quote_figure(name,title,blocks,data,caption):
    """A source-grounded reading plate; quote lengths determine physical height."""
    from matplotlib import font_manager, ft2font
    font=ft2font.FT2Font(font_manager.findfont('DejaVu Sans'))
    available=font.get_charmap()
    unsupported=sorted({ord(c) for _,text in blocks for c in text if not c.isspace() and ord(c) not in available})
    def display_text(text):
        return ''.join(f'[U+{ord(c):04X}]' if ord(c) in unsupported else c for c in text)
    if unsupported:
        caption+=' **Display note:** unsupported source glyphs are shown as Unicode code-point escapes ('+', '.join(f'U+{c:04X}' for c in unsupported)+'); the exact original text remains in the source table and case bundle.'
    wrapped=[(heading,'\n'.join(textwrap.wrap(display_text(text),104,break_long_words=False))) for heading,text in blocks]
    lines=sum(body.count('\n')+1 for _,body in wrapped)
    height=35+lines*3.3+len(blocks)*12
    fig,axs=canvas(height=height,left=.04,right=.98,bottom=.05,top=.90)
    ax=axs[0];ax.axis('off');ax.set_title(title,loc='left',pad=12)
    y=1.0
    for i,(heading,body) in enumerate(wrapped):
        ax.text(0,y,heading,va='top',fontweight='bold',fontsize=8,transform=ax.transAxes)
        y-=6/(height*.85)
        ax.text(0,y,body,va='top',fontsize=7.5,linespacing=1.35,transform=ax.transAxes)
        y-=(3.7*(body.count('\n')+1)+9)/(height*.85)
    save_figure(fig,name,data,caption)


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