"""Refresh notebook-04 artifacts without implying completion of a live experiment."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parent.parent
OUT=HERE/'outputs/evaluator_gap'
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE))
from evaluator_gap_analysis import sha,save_json

def main():
    path=OUT/'artifact_manifest.json'
    if path.exists():
        previous=json.loads(path.read_text())
        # Preserve the pre-extension delivery record once, rather than silently
        # reinterpreting its historical completion claim as this experiment's.
        if previous.get('status')=='COMPLETE_WITH_DECLARED_PENDING_VALIDATION':
            archive=OUT/'qa/history'/f'pre_prompt_extension_manifest_{sha(path)[:12]}.json'
            archive.parent.mkdir(parents=True,exist_ok=True)
            if not archive.exists():archive.write_bytes(path.read_bytes())
    readiness_path=OUT/'prompt_sensitivity/readiness.json'
    readiness=json.loads(readiness_path.read_text()) if readiness_path.exists() else {'ready':False}
    statistics_path=OUT/'prompt_sensitivity/qa/final_statistics.json'
    statistics=json.loads(statistics_path.read_text()) if statistics_path.exists() else {}
    statistics_ok=readiness['ready'] and statistics.get('status')=='PASS'
    visual_path=OUT/'prompt_sensitivity/qa/visual_review.json'
    visual=json.loads(visual_path.read_text()) if visual_path.exists() else {}
    visual_ok=visual.get('status')=='PASS'
    if visual_ok:
        for name,expected in visual.get('reviewed_png_sha256',{}).items():
            visual_ok=visual_ok and sha(ROOT/name)==expected
        visual_ok=visual_ok and len(visual.get('reviewed_png_sha256',{}))==2
    if statistics_ok:
        status=('PROMPT_RESULTS_COMPLETE_WITH_DECLARED_VALIDITY_LIMITS' if visual_ok else
                'PROMPT_STATISTICS_COMPLETE_VISUAL_REVIEW_PENDING')
    else:
        status='PROMPT_RESULTS_AWAITING_VERIFICATION' if readiness['ready'] else 'PROMPT_EXPERIMENT_IN_PROGRESS'
    paths=set(HERE.glob('*evaluator_gap*.py'))
    paths.update((HERE/'scripts').glob('*evaluator_gap*.py'))
    paths.update([HERE/'04_evaluator_gap_diagnostics.ipynb',HERE/'EVALUATOR_GAP_SPEC.md'])
    paths.update(p for p in OUT.rglob('*') if p.is_file() and p!=path
                 and '.runtime' not in p.parts and 'synthetic_layout_fixture' not in p.parts
                 and 'history' not in p.parts)
    experiment=ROOT/'BACE/experiments/prompt_sensitivity_v1'
    paths.update(p for p in experiment.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    save_json(path,{'status':status,'updated_at_utc':datetime.now(timezone.utc).isoformat(),
        'files':{str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)},
        'scope':'Notebook 04, its saved diagnostics and the controlled support-prompt extension. '
                'Raw experiment records are linked by the frozen plan and completed-run audit. '
                'Runtime caches and synthetic layout fixtures are excluded from delivered results.',
        'independent_accuracy_and_evidence_loss_validation':'COMPUTATION_PENDING'})
    print('Artifact manifest:',status)

if __name__=='__main__':main()
