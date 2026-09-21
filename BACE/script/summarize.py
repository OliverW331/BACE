"""Verify completed runs, summarize native denominators, and prepare blind review."""
from collections import Counter, defaultdict
import json
import random
import re
import sys
from statistics import mean

from common import ROOT, csvfile, digest, jsonl, read, rows, write
sys.path.insert(0,str(ROOT/'script/evaluation'))
sys.path.insert(0,str(ROOT/'script/human_validation'))
sys.path.insert(0,str(ROOT/'script/generation'))
from external_evaluation import adapt_case
from metrics import bace_metrics, external_metrics
from run_w2_generation import deterministic_word_count
from generation_claims import build_dc_jobs, build_ec_jobs
from lineage_audit import audit_extraction
import prepare_materials as human


def review_quote_locations(claim, disclosure, blocks):
    """Expose only verbatim excerpts, retaining every sampled claim for review.

    Extractors sometimes quote noncontiguous table rows. Locate their literal
    lines separately; never label a reconstructed table as a verbatim quote.
    Missing or invented quotations fall back to the full disclosure, without
    changing the sample or treating localization as a fidelity verdict.
    """
    reported = sorted({q for p in claim['dc_provenance'] for q in p.get('source_quotes',[]) if q.strip()})
    excerpts, unresolved, segmented = set(), [], False
    for quote in reported:
        if quote in disclosure:
            excerpts.add(quote)
        else:
            lines = [line.strip() for line in quote.splitlines() if line.strip()]
            if len(lines)>1 and all(line in disclosure for line in lines):
                excerpts.update(lines)
                segmented = True
            else:
                unresolved.append(quote)
    quotes = sorted(excerpts)
    locations = [{'quote':q,'start':m.start(),'end':m.end()} for q in quotes for m in re.finditer(re.escape(q),disclosure)]
    fallback = not reported or bool(unresolved)
    refs = [b['ref'] for b in blocks if fallback or any(q['start']<b['end'] and b['start']<q['end'] for q in locations)]
    status = {'mode':'full_disclosure' if fallback else 'verbatim_line_segments' if segmented else 'exact',
              'unresolved_quote_count':len(unresolved),'quote_locations':locations}
    return quotes,refs,status


def human_packet(run, reviewed):
    """Uniform samples work even when a case has no inferred/unsupported claims."""
    materials, mappings = [], []
    for i,(case,response,adapted,base,claims) in enumerate(reviewed,1):
        cid = case['generation_case_id']
        blocks = human.paragraphs(response['generated_text'])
        units = []
        pools = [('claim_support',sorted(claims,key=lambda c:c['dc_id']),5),
                 ('ec_source_audit',[c for c in case['prompt_evidence'] if c['shown_in_prompt']],2),
                 ('dc_source_audit',blocks,2)]
        for kind,pool,quota in pools:
            selected = human.rng(20260916,cid,kind).sample(pool,min(quota,len(pool)))
            for target in selected:
                refs,quotes = [],[]
                if kind=='claim_support':
                    text = target['dc_text']
                    quotes,refs,localization = review_quote_locations(target,response['generated_text'],blocks)
                    private = {'dc_id':target['dc_id'],'quote_localization':localization}
                elif kind=='ec_source_audit':
                    text,refs = target['retrieval_text'],[target['prompt_label']]
                    private = {'evidence_id':target['evidence_id']}
                else:
                    text,refs = target['text'],[target['ref']]
                    private = {'start':target['start'],'end':target['end']}
                unit = {'unit_id':f'HV{len(mappings)+1:06d}','unit_type':kind,'target_text':text,'source_refs':refs,'source_quotes':quotes}
                units.append(unit)
                mappings.append({'unit_id':unit['unit_id'],'generation_case_id':cid,'unit_type':kind,
                                 'population_count':len(pool),'sample_count':len(selected),'inclusion_probability':len(selected)/len(pool),**private})
        materials.append({'case_id':f'C{i:04d}','company_name':case['company_name'],'reporting_year':case['target_reporting_year'],
                          'task':case['task_title'],'disclosure_text':response['generated_text'],
                          'paragraphs':[{'ref':b['ref'],'text':b['text']} for b in blocks],
                          'evidence':[{'label':label,'context':context} for label,context in zip(adapted['prompt_labels'],adapted['contexts'])],'units':units})
    guide = human.render_instructions(materials)
    guide = guide.replace('## Evidence boundary',
        '## Locating extracted claims\n\nOnly verbatim source excerpts are displayed. Noncontiguous table quotations are shown as separate literal lines. If a quotation cannot be located, the references cover the full disclosure. Retain the sampled claim and assess its fidelity using the original disclosure; excerpt availability is not a correctness label.\n\n## Evidence boundary',1)
    files = {'instructions.md':guide,
             'materials.jsonl':''.join(json.dumps(m,ensure_ascii=False,sort_keys=True)+'\n' for m in materials),
             'reviewer_a.csv':human.csv_text(materials),'reviewer_b.csv':human.csv_text(materials),
             'adjudicated.csv':human.csv_text(materials,adjudication=True)}
    manifest = {'schema_version':'bace_human_materials_v1','access':'COORDINATOR ONLY','seed':20260916,
                'case_count':len(reviewed),'human_annotations':0,
                'sampling':'Within each case, simple random sample without replacement of up to five DCs, two prompt-visible cards, and two disclosure paragraphs. No support-label quotas or sample replacement. Inclusion probabilities recorded per unit.',
                'units':mappings,'source_run_manifest_sha256':digest(run/'manifest.json'),
                'postprocessing_freeze_sha256':digest(ROOT/'config/freeze.json'),
                'pristine_output_sha256':{k:human.digest(v) for k,v in files.items()}}
    files['sample_manifest.json'] = human.json_text(manifest)
    human.write_packet(run/'human_validation',files)
    return manifest


def summarize(run, quiet=False):
    from acceptance import validate_run_freeze
    validate_run_freeze(read(run/'manifest.json')['freeze_sha256'])
    execution = read(run/'execution_status.json')
    planned = read(run/'manifest.json')['case_ids']
    if execution['status'] not in ('finalizing','complete') or execution.get('failures') or set(execution['completed_case_ids'])!=set(planned):
        raise ValueError('A comparison requires every selected case to finish')
    sectors = {r['company_id']:r['primary_sics_sector'] for r in read(ROOT/'evidence/sample/sample.json')['selected']}
    comparison,reviewed = [],[]
    source_files = {}
    for cid in planned:
        base = run/'cases'/cid
        expected_receipts = {'generation','direct','integrated','atomic','dedup','candidates','support','diagnosis','ragchecker','ragas'}
        state = read(base/'state.json')
        if state.get('status')!='complete' or set(state['stages']) != expected_receipts:
            raise ValueError('Missing or unexpected completed stage receipts: '+cid)
        source_files[str((base/'state.json').relative_to(ROOT))] = digest(base/'state.json')
        for receipt in state['stages'].values():
            for name,expected in receipt['artifacts'].items():
                if digest(ROOT/name)!=expected:
                    raise ValueError('Completed output changed: '+name)
        case = rows(base/'inputs/generation_cases.jsonl')[0]
        outputs = rows(base/'generation/generated_disclosures.jsonl')
        if len(outputs)!=1 or not outputs[0]['length_within_requested_range']:
            raise ValueError('Generation is missing, duplicated or outside length bounds')
        response = outputs[0]
        actual_words = deterministic_word_count(response['generated_text'])
        if not 300 <= actual_words <= 500 or actual_words != response['generated_word_count']:
            raise ValueError('Disclosure word count does not match the frozen length contract')
        adapted = adapt_case(case,response)
        lineage_files = {}
        for task,jobs in [('ec',build_ec_jobs([case])),('dc',build_dc_jobs([case],{cid:response}))]:
            audit_extraction(base/'extraction/atomic',cid,task,jobs[0],lineage_files)
        b = base/'bace'
        dc = rows(b/'dedup/dc_claims.jsonl')
        result = {'generation_case_id':cid,'company_id':case['company_id'],'company_name':case['company_name'],
                  'sector':sectors[case['company_id']],'year':case['target_reporting_year'],'task_id':case['task_id'],
                  'standard':case['task_id'].split('-')[0].upper(),'word_count':response['generated_word_count'],
                  'visible_evidence_count':len(adapted['contexts'])}
        result.update(bace_metrics(rows(b/'dedup/ec_claims.jsonl'),dc,rows(b/'support/dc_support_sets.jsonl'),
                                   rows(b/'diagnosis/dc_unsupported_diagnoses.jsonl'),rows(b/'candidates/dc_candidate_ecs.jsonl')))
        for framework in ['ragchecker','ragas']:
            native = rows(base/'evaluation'/framework/'results.jsonl')[-1]
            result.update(external_metrics(native,framework,adapted))
        comparison.append(result)
        reviewed.append((case,response,adapted,base,dc))
    analysis = run/'analysis'
    csvfile(analysis/'comparison.csv',comparison)
    metrics = ['bace_support_rate_all_dc','bace_eccr','bace_inference_rate','ragchecker_faithfulness','ragas_faithfulness']
    groups = []
    for dimension in ['standard','task_id','sector','year']:
        grouped = defaultdict(list)
        for r in comparison:
            grouped[r[dimension]].append(r)
        for name,group in sorted(grouped.items()):
            groups.append({'dimension':dimension,'group':name,'case_count':len(group),
                           **{m:mean([r[m] for r in group if r[m] is not None]) if any(r[m] is not None for r in group) else None for m in metrics}})
    csvfile(analysis/'group_summary.csv',groups)
    summary = {'status':'complete','scope':read(run/'manifest.json')['scope'],'case_count':len(comparison),
               'postprocessing_freeze_sha256':digest(ROOT/'config/freeze.json'),
               'task_counts':dict(Counter(r['task_id'] for r in comparison)),
               'macro_means':{m:mean([r[m] for r in comparison if r[m] is not None]) if any(r[m] is not None for r in comparison) else None for m in metrics},
               'native_denominators':{f:sum(r[f+'_claim_count'] for r in comparison) for f in ['ragchecker','ragas']},
               'bace_total_dc':sum(r['bace_dc_count'] for r in comparison),
               'micro_rates':{'bace':sum(r['bace_supported_direct']+r['bace_supported_inferred'] for r in comparison)/sum(r['bace_dc_count'] for r in comparison),
                              **{f:sum(r[f+'_supported'] for r in comparison)/sum(r[f+'_claim_count'] for r in comparison) for f in ['ragchecker','ragas']}},
               'interpretation':'Engineering completion and native score summaries. Frameworks have different claim denominators; these scores are not evaluator accuracy or thesis conclusions.',
               'source_files':source_files}
    write(analysis/'summary.json',summary)
    human_packet(run,reviewed)
    if not quiet:
        print(f'Validated {len(comparison)} cases; summary and blank human-review materials prepared',flush=True)
    return summary
