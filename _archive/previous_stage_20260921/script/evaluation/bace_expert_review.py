"""Source-grounded assistant adjudication tools; no model calls or automatic verdicts.

Print one complete case for manual review, then save explicit per-claim
annotations. All classifications require an annotation; there is no default
agreement rule. Original BACE outputs remain immutable.

This is an unblinded, end-to-end source-grounding audit by the assistant, not
an independent human gold standard and not a controlled retest of the support
judge on its original candidate ECs. The extracted DC is the primary target;
disclosure context clarifies referents and exposes extraction changes. Raw
prompt-visible evidence, including report/table context, determines support.
Source assertions are not independently verified against real-world truth.

Direct support includes faithful paraphrase, ordinary rounding and reunion
of explicitly connected source statements. Inferred support requires a
reasoning step without an added substantive fact. Explicit dates, metric
definitions, entities, boundaries and modalities must be preserved. A report
publication year does not automatically expire a generic definition or method.
Packet-scoped absence can be inferred after inspecting the complete packet;
absence across an entire annual report cannot be inferred from retrieved
fragments. Materially ambiguous readings receive an uncertain verdict.

Diagnosis labels follow the frozen BACE precedence, conditional on the claim
remaining unsupported. The separate end-to-end diagnosis-validity column also
counts a diagnosis as invalid when the expert finds the claim supported.
Native minimal support sets are inspected but not exhaustively re-enumerated.
"""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'evidence_pilot/evaluation/external_comparison/pilot_v2'
CSV = RUN / 'expert_claim_review.csv'
PLAN = json.loads((RUN / 'plan.json').read_text())
CLASSES = {'D':'supported_direct', 'I':'supported_inferred', 'U':'unsupported',
           'A':'uncertain', 'T':'supported_type_uncertain'}
LABELS = {'ND':'non_disclosure_statement', 'CON':'contradiction', 'CF':'evidence_conflation',
          'BND':'factual_boundary_distortion', 'INF':'inferential_inflation', 'NOV':'unsupported_novelty',
          'NA':'not_applicable', 'A':'uncertain'}


def rows(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def case(number):
    cid = PLAN['cases'][number - 1]['generation_case_id']
    short = cid.split('stratified_by_evidence_type_n10__')[1]
    base = RUN / 'bace' / short
    source = next(r for r in rows(ROOT / PLAN['generation_cases']) if r['generation_case_id']==cid)
    disclosure = next(r for r in rows(ROOT / PLAN['generated_disclosures']) if r['generation_case_id']==cid)
    dc = rows(base / 'dedup/dc_claims.jsonl')
    def position(r):
        starts=[s['start'] for p in r['dc_provenance'] for s in p['source_spans'] if s.get('start') is not None]
        return min(starts) if starts else 10**9
    dc.sort(key=lambda r:(position(r),r['dc_text'],r['dc_id']))
    ec = rows(base / 'dedup/ec_claims.jsonl')
    eids={r['ec_id']:f'E{i:03d}' for i,r in enumerate(ec,1)}
    ecmap={r['ec_id']:r for r in ec}
    support={r['dc_claim_id']:r['support_sets'] for r in rows(base / 'support/dc_support_sets.jsonl')}
    diagnosis={r['dc_claim_id']:r for r in rows(base / 'diagnosis/dc_unsupported_diagnoses.jsonl')}
    candidates={r['dc_claim_id']:r['candidate_ec_ids'] for r in rows(base / 'candidates/dc_candidate_ecs.jsonl')}
    return cid,source,disclosure,dc,ec,ecmap,eids,support,diagnosis,candidates


def bace_class(sets):
    return 'U' if not sets else ('D' if any(s['support_type']=='direct' for s in sets) else 'I')


def show(number, mode='all'):
    cid,source,disclosure,dc,ec,ecmap,eids,support,diagnosis,candidates=case(number)
    print(f'CASE {number}: {cid}')
    if mode in ('all','source'):
        print('FULL GENERATED DISCLOSURE\n'+disclosure['generated_text'])
        print('\nALL PROMPT-VISIBLE EVIDENCE')
        for card in source['prompt_evidence']:
            if card['shown_in_prompt']:
                print(f"\n{card['prompt_label']} | {card['source_label']}\n{card['retrieval_text']}")
    if mode in ('all','claims'):
        print('\nDISCLOSURE CLAIMS, NATIVE SUPPORT AND DIAGNOSIS')
        for i,d in enumerate(dc,1):
            sets=support[d['dc_id']]
            desc='; '.join(s['support_type']+':'+','.join(eids[e] for e in s['ec_claim_ids']) for s in sets)
            print(f"\n{i:02d} [{bace_class(sets)}] {d['dc_text']}\nSETS {desc}")
            if d['dc_id'] in diagnosis:
                diag=diagnosis[d['dc_id']]
                print('DIAG '+diag['unsupported_label']+' | '+diag['rationale'])
                print('CAND '+','.join(eids[e] for e in candidates[d['dc_id']]))
    if mode in ('all','ec'):
        print('\nEXTRACTED EVIDENCE CLAIMS')
        for e in ec:
            labels=sorted({p['prompt_label'] for p in e['ec_provenance']})
            print(eids[e['ec_id']]+' ['+','.join(labels)+'] '+e['ec_text'])


def save(number, annotations):
    """Annotations: number -> [class, diagnosis, evidence labels, stage, reason, rationale verdict]."""
    cid,source,disclosure,dc,ec,ecmap,eids,support,diagnosis,candidates=case(number)
    assert set(annotations)==set(range(1,len(dc)+1)), ('Explicit annotations required for every claim',number)
    existing=[]
    if CSV.exists():
        with CSV.open(newline='', encoding='utf-8-sig') as stream: existing=list(csv.DictReader(stream))
    assert not any(r['generation_case_id']==cid for r in existing), 'Case already adjudicated'
    for i,d in enumerate(dc,1):
        verdict,label,labels,stage,reason,rationale=annotations[i]
        assert verdict in CLASSES and label in LABELS
        assert len(reason)>30 and labels and stage
        assert rationale in ('correct','incorrect','incomplete','uncertain','not_applicable')
        old=bace_class(support[d['dc_id']]); olddiag=diagnosis.get(d['dc_id'])
        status_correct='uncertain' if verdict=='A' else ('yes' if (old!='U')==(verdict!='U') else 'no')
        classification_correct='uncertain' if verdict in ('A','T') else ('yes' if old==verdict else 'no')
        if olddiag is None: diagnosis_correct='not_applicable'
        elif verdict in ('A','T') or label=='A': diagnosis_correct='uncertain'
        elif verdict!='U': diagnosis_correct='no'
        else: diagnosis_correct='yes' if olddiag['unsupported_label']==LABELS[label] else 'no'
        diagnosis_applicable = ('not_generated' if olddiag is None else
                                'uncertain' if verdict=='A' else
                                'yes' if verdict=='U' else 'no_expert_supported')
        conditional_label = ('not_applicable' if olddiag is None or verdict in ('D','I','T')
                             else diagnosis_correct)
        linked=[]
        for s in support[d['dc_id']]:
            linked.append({'support_type':s['support_type'],'ecs':[{'ec_id':e,'ec_text':ecmap[e]['ec_text'],
                'evidence_labels':sorted({p['prompt_label'] for p in ecmap[e]['ec_provenance']})} for e in s['ec_claim_ids']]})
        record={'case_no':number,'claim_no':i,'generation_case_id':cid,'company':source['company_name'],
                'reporting_year':source['target_reporting_year'],'task':source['task_id'],
                'dc_id':d['dc_id'],'dc_text':d['dc_text'],
                'disclosure_source_quotes':json.dumps(sorted({s['quote'] for p in d['dc_provenance'] for s in p['source_spans']}),ensure_ascii=False),
                'bace_support_class':CLASSES[old],'expert_support_class':CLASSES[verdict],
                'support_status_correct':status_correct,'support_classification_correct':classification_correct,
                'bace_unsupported_label':olddiag['unsupported_label'] if olddiag else '',
                'expert_unsupported_label':LABELS[label],
                'unsupported_diagnosis_applicable':diagnosis_applicable,
                'diagnosis_label_correct_given_unsupported':conditional_label,
                'unsupported_diagnosis_valid_end_to_end':diagnosis_correct,
                'bace_diagnosis_rationale':olddiag['rationale'] if olddiag else '',
                'diagnosis_rationale_assessment':rationale,'review_evidence_labels':labels,
                'likely_issue_stage_or_caveat':stage,'expert_review_reason':reason,
                'bace_support_sets_with_ec_text':json.dumps(linked,ensure_ascii=False),
                'assessment_basis':'Full prompt-visible raw evidence and the disclosure context; native ECs/support sets and diagnoses inspected.',
                'review_standard':'bace_expert_source_audit_v1',
                'audit_scope':'End-to-end source grounding; not a controlled retest on identical candidate EC input.',
                'reviewer_type':'Codex assistant source-grounded review; unblinded; not independent human ground truth',
                'source_cases_file':PLAN['generation_cases'],'source_disclosures_file':PLAN['generated_disclosures']}
        existing.append(record)
    existing.sort(key=lambda r:(int(r['case_no']),int(r['claim_no'])))
    temporary=CSV.with_suffix('.csv.tmp')
    with temporary.open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(existing[0]));writer.writeheader();writer.writerows(existing)
    temporary.replace(CSV)
    print(f'Saved case {number}: {len(dc)} explicit judgments; {len(existing)} reviewed claims total.')


if __name__=='__main__':
    show(int(sys.argv[1]),sys.argv[2] if len(sys.argv)>2 else 'all')
