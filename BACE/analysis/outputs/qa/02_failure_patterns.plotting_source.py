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