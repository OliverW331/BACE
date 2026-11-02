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