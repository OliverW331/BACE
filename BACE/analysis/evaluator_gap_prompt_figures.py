"""Saved-data plots for the controlled BACE prompt intervention."""
import matplotlib.pyplot as plt
import numpy as np
from evaluator_gap_figures import canvas, save_figure, BLUE, GREEN, INK, GREY
from evaluator_gap_prompt_sensitivity import LABELS, VARIANTS

def plot_prompt_effects(results):
    if not results['ready']:
        return
    effects=results['effects']
    fig,ax=canvas(height=82,left=.34,top=.90,bottom=.25)
    for i,row in enumerate(effects.itertuples()):
        mean,low,high=100*np.array([row.estimate,row.low,row.high])
        ax.errorbar(mean,i,xerr=[[mean-low],[high-mean]],fmt='o',capsize=3,
                    color=[BLUE,GREEN][i],markersize=6)
    ax.axvline(0,color=GREY,lw=.8,ls='--')
    ax.set_yticks(range(len(effects)),[LABELS[c].replace('BACE–','BACE / ') for c in effects.condition])
    ax.set_xlabel('New prompt minus original BACE (percentage points)')
    ax.set_ylim(1.6,-.6)
    n=int(effects.iloc[0].disclosures)
    pattern='; '.join(f"{LABELS[r.condition]}: {100*r.estimate:+.2f} pp (95% CI {100*r.low:+.2f} to {100*r.high:+.2f})"
                      for r in effects.itertuples())+'.'
    save_figure(fig,'04_prompt_sensitivity_effects',effects,
        'How much does changing judgment instructions change BACE support rates?',
        f'Paired disclosure-macro changes on {n:,} complete disclosures. Points are mean differences; '
        'bars are 95% company-cluster percentile intervals (2,000 draws). The zero line denotes no net change.',
        pattern,
        'Targets, candidate evidence, metadata, model request settings and support-set output are held fixed; judgment instructions differ.',
        'These are adapted BACE conditions, not native baseline scores. Intervals condition on observed runs. '
        'A score increase is not evidence of improved accuracy or a causal allocation of the native score gap.')

def plot_prompt_transitions(results):
    if not results['ready']:
        return
    data=results['transitions']
    fig,axes=plt.subplots(1,2,figsize=(183/25.4,90/25.4))
    fig.subplots_adjust(left=.15,right=.98,bottom=.25,top=.82,wspace=.40)
    largest=data.claims.max()
    for ax,condition in zip(axes,VARIANTS):
        subset=data.loc[data.condition.eq(condition)]
        matrix=np.array([[subset.loc[subset.original_supported.eq(old)&subset.new_supported.eq(new),'claims'].iloc[0]
                          for new in [True,False]] for old in [True,False]])
        ax.imshow(matrix,cmap='Blues',vmin=0,vmax=max(largest,1),aspect='auto')
        for i in range(2):
            denominator=matrix[i].sum()
            for j in range(2):
                rate=f'{100*matrix[i,j]/denominator:.1f}% of row' if denominator else 'Undefined row rate'
                ax.text(j,i,f'{matrix[i,j]:,}\n{rate}',ha='center',va='center',fontsize=8,
                        color='white' if matrix[i,j]>largest*.6 else INK)
        ax.set_xticks([0,1],['Supported','Unsupported'])
        ax.set_yticks([0,1],['Supported','Unsupported'])
        ax.set_xlabel('New prompt judgment')
        ax.set_ylabel('Original BACE judgment')
        ax.set_title(LABELS[condition].replace('BACE–','BACE / '),pad=9)
        for spine in ax.spines.values():
            spine.set_visible(False)
    flips=data.loc[data.original_supported.ne(data.new_supported)]
    pattern='; '.join(f"{LABELS[r.condition]}, {'supported → unsupported' if r.original_supported else 'unsupported → supported'}: "
                      f'{r.claims:,} claims ({100*r.fraction_original_status:.2f}% of original-status claims)'
                      for r in flips.itertuples())+'.'
    save_figure(fig,'04_prompt_sensitivity_transitions',data,
        'Which original support judgments change under each prompt?',
        'Rows are original BACE judgments and columns are new judgments. Each cell shows a count and its row percentage. '
        'Both panels use the same complete paired claim cohort and color scale; this is not a confusion matrix against ground truth.',
        pattern,
        'Both flip directions are observed so that offsetting changes cannot be hidden by a small net support-rate difference.',
        'Cell counts pool claims, whereas the primary effect gives each disclosure equal weight. '
        'Automated disagreement does not identify which judgment is correct.')
