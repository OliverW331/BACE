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
