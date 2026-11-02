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

fig,axs=canvas(height=85,cols=2,left=.11,right=.96,bottom=.21,top=.87,wspace=.40)
for column,color,label,style in [('bace_eccr',BLUE,'ECCR','-'),('bace_inference_rate',GREEN,'Inference rate','--')]:
    ecdf(axs[0],bace[column],color,label,style)
axs[0].set_xlim(0,1);axs[0].set_xlabel('Metric value');axs[0].set_ylabel('Cumulative disclosures');axs[0].legend(loc='lower right')
delta=bace.bace_support_rate_excluding_non_disclosure_sensitivity-bace.bace_support_rate_all_dc
axs[1].hist(delta.dropna(),bins=20,color=ORANGE,edgecolor='white');axs[1].set_xlabel('Sensitivity minus main support rate');axs[1].set_ylabel('Disclosures')
save_figure(fig,'01_secondary_metrics',bace[['generation_case_id','company_id','bace_eccr','bace_inference_rate','bace_non_disclosure_statement','bace_support_rate_all_dc','bace_support_rate_excluding_non_disclosure_sensitivity']],
    '**Read the figure:** panel a shows exact empirical distributions (undefined ratios are excluded and counted below); panel b shows paired changes after removing non-disclosure statements. '
    '**Boundary:** a larger secondary metric is not automatically better quality.')