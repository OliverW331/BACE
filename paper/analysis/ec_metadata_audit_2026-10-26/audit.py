"""Read-only forensic audit of ESRS metadata in frozen main-study ECs.

Run with the system Python; no project imports, API calls, or artifact mutation.
All output is confined to this directory. Counts are text-pattern flags, not
human adjudications of every claim's semantic fidelity.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
CASES = ROOT / 'BACE/results/main_v1/cases'
INPUTS = []
MISSING_INPUTS = []
REF = re.compile(r'\bESRS\b|\bdisclosure requirements?\b|\b[ESG]\d[-–]\d{1,2}\b', re.I)
EXACT = ['under ESRS S1 disclosure requirement S1-14',
         'under ESRS G1 disclosure requirement G1-6']


def rows(path):
    if not path.exists():
        MISSING_INPUTS.append(str(path.relative_to(ROOT)))
        return
    h = hashlib.sha256()
    count = 0
    with path.open('rb') as stream:
        for line in stream:
            h.update(line)
            if line.strip():
                count += 1
                yield json.loads(line)
    INPUTS.append({'path': str(path.relative_to(ROOT)), 'sha256': h.hexdigest(),
                   'rows': count, 'bytes': path.stat().st_size})


def dump(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def write_csv(name, records, fields):
    with (OUT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(records)


def main():
    canonical = {}
    card_counts = Counter()
    for row in rows(ROOT / 'BACE/evidence/canonical/indexes/all_csv_metric_cards.jsonl'):
        canonical[row['evidence_id']] = row
        card_counts[row.get('standard') or 'MISSING'] += 1
    print('Loaded canonical CSV cards', sum(card_counts.values()), flush=True)
    counts = defaultdict(Counter)
    stage_cases = defaultdict(set)
    stage_available = Counter()
    unique_flagged = defaultdict(set)
    consistency = defaultdict(lambda: [set(), set()])
    downstream = Counter()
    examples = {}
    missing = []
    flags = []
    case_records = []
    exposure = Counter()
    transitions = Counter()
    case_dirs = sorted(p for p in CASES.iterdir() if p.is_dir())
    stages = [('direct', 'extraction/direct/ec_claim_occurrences.jsonl'),
              ('integrated', 'extraction/integrated/ec_claim_occurrences.jsonl'),
              ('atomic', 'extraction/atomic/ec_claim_occurrences.jsonl'),
              ('dedup', 'bace/dedup/ec_claims.jsonl')]
    for index, case in enumerate(case_dirs, 1):
        inp = list(rows(case / 'inputs/generation_cases.jsonl'))[0]
        task = inp['task_id']
        family = task.split('-')[0]
        current = {'generation_case_id': case.name, 'task_id': task}
        visible = {c['evidence_id']: c for c in inp['prompt_evidence'] if c.get('shown_in_prompt')}
        for c in visible.values():
            if c['evidence_type'] == 'csv_metric':
                source = canonical[c['evidence_id']]
                exposure['csv_card_occurrences'] += 1
                exposure['csv_card_occurrences_with_explicit_ESRS_metadata'] += bool(REF.search(c['retrieval_text']))
                exposure['csv_card_text_matches_canonical'] += c['retrieval_text'] == source['retrieval_text']
                exposure['csv_card_requirement_differs_from_task'] += source['discl_req'] != task.split('_')[0]
        previous_flags = None
        flagged_ids = set()
        ec_lookup = {}
        for stage, rel in stages:
            p = case / rel
            current[stage + '_total'] = None
            current[stage + '_reference_flags'] = None
            if not p.exists():
                missing.append(str(p.relative_to(ROOT)))
                continue
            stage_available[stage] += 1
            stage_flagged = set()
            current[stage + '_total'] = 0
            current[stage + '_reference_flags'] = 0
            for r in rows(p):
                text = r.get('ec_text', r.get('claim_text', ''))
                ids = r.get('evidence_card_ids') or [r['evidence_id']]
                kinds = sorted(set('csv_metric' if eid in canonical else visible.get(eid, {}).get('evidence_type', 'UNKNOWN') for eid in ids))
                kind = '+'.join(kinds)
                standards = sorted(set(canonical[eid].get('standard') or 'MISSING' for eid in ids if eid in canonical))
                standard = '+'.join(standards) or 'PDF'
                ref = bool(REF.search(text))
                exact = any(s in text for s in EXACT)
                buckets = [('all', 'ALL'), ('evidence_type', kind), ('source_standard', standard), ('task_family', family)]
                for dimension, group in buckets:
                    count = counts[(stage, dimension, group)]
                    count['total'] += 1
                    count['reference_flags'] += ref
                    count['exact_user_phrases'] += exact
                current[stage + '_total'] += 1
                current[stage + '_reference_flags'] += ref
                if ref:
                    stage_cases[stage].add(case.name)
                    stage_flagged.update(ids)
                    unique_flagged[stage].update(ids)
                if stage == 'dedup':
                    ec_lookup[r['ec_id']] = r
                    for eid in ids:
                        if eid in canonical:
                            consistency[eid][int(ref)].add(case.name)
                    if ref:
                        flagged_ids.add(r['ec_id'])
                        flags.append({'generation_case_id': case.name, 'task_id': task,
                                      'ec_id': r['ec_id'], 'source_standard': standard,
                                      'evidence_type': kind, 'evidence_ids': '|'.join(ids),
                                      'exact_user_phrase': exact, 'ec_text': text})
                        key = standard if standard not in examples else None
                        if 'G1-6' in text and 'intertek__2019__g1_2' in case.name:
                            key = 'Intertek_G1_6'
                        if 'S1-14' in text and 'mowi__2023__s1_14' in case.name:
                            key = 'Mowi_S1_14'
                        if key:
                            examples[key] = {'case': case.name, 'ec': r,
                                             'cards': [canonical[eid] if eid in canonical else visible.get(eid) for eid in ids]}
            if previous_flags is not None:
                transitions[stage + '_newly_flagged_case_card_pairs'] += len(stage_flagged - previous_flags)
                transitions[stage + '_no_longer_flagged_case_card_pairs'] += len(previous_flags - stage_flagged)
            previous_flags = stage_flagged
        downstream['cases'] += 1
        downstream['cases_with_candidate_file'] += (case / 'bace/candidates/dc_candidate_ecs.jsonl').exists()
        downstream['cases_with_support_file'] += (case / 'bace/support/dc_support_sets.jsonl').exists()
        selected_flags = set()
        support_flags = set()
        for row in rows(case / 'bace/candidates/dc_candidate_ecs.jsonl'):
            downstream['candidate_dc_records'] += 1
            overlap = flagged_ids.intersection(row['candidate_ec_ids'])
            downstream['candidate_dc_records_with_flagged_ec'] += bool(overlap)
            selected_flags.update(overlap)
        for row in rows(case / 'bace/support/dc_support_sets.jsonl'):
            downstream['support_dc_records'] += 1
            used = False
            for support in row['support_sets']:
                downstream['support_sets'] += 1
                overlap = flagged_ids.intersection(support['ec_claim_ids'])
                downstream['support_sets_with_flagged_ec'] += bool(overlap)
                support_flags.update(overlap)
                used |= bool(overlap)
            downstream['support_dc_records_with_flagged_ec'] += used
        downstream['flagged_ecs_selected_as_candidates'] += len(selected_flags)
        downstream['flagged_ecs_in_support_sets'] += len(support_flags)
        downstream['cases_with_flagged_candidate_ec'] += bool(selected_flags)
        downstream['cases_with_flagged_support_ec'] += bool(support_flags)
        current['flagged_ecs_selected_as_candidates'] = len(selected_flags)
        current['flagged_ecs_in_support_sets'] = len(support_flags)
        case_records.append(current)
        if index % 150 == 0:
            print('Audited cases', index, '/', len(case_dirs), flush=True)

    inconsistent = [{'evidence_id': eid, 'standard': canonical[eid]['standard'],
                     'cases_without_reference': len(v[0]), 'cases_with_reference': len(v[1]),
                     'example_case_without': sorted(v[0])[0], 'example_case_with': sorted(v[1])[0]}
                    for eid, v in consistency.items() if v[0] and v[1]]
    summary = {
        'access_date': '2026-10-26', 'completed_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'All main_v1 case directories; four saved EC stages; canonical CSV cards; candidate and support records.',
        'counting_unit': 'Stage rows are case-level claim occurrences (or case-level deduplicated ECs), not independent source observations. Reference flags search claim_text/ec_text only, excluding quotations and provenance. Multiple source standards/types form their own combined category.',
        'reference_regex': REF.pattern, 'exact_phrases': EXACT,
        'case_count': len(case_dirs), 'missing_stage_files': missing,
        'available_cases_by_stage': dict(stage_available), 'missing_downstream_files': MISSING_INPUTS,
        'canonical_csv_cards_by_standard': dict(card_counts),
        'prompt_exposure': dict(exposure),
        'flagged_cases_by_stage': {k: len(v) for k, v in stage_cases.items()},
        'unique_flagged_evidence_cards_by_stage': {k: len(v) for k, v in unique_flagged.items()},
        'stage_transition_case_card_flags': dict(transitions),
        'counts': [{'stage': k[0], 'dimension': k[1], 'group': k[2], **dict(v)} for k, v in sorted(counts.items())],
        'downstream': dict(downstream),
        'csv_evidence_ids_represented_in_final_ec': len(consistency),
        'csv_evidence_ids_with_both_flagged_and_unflagged_final_claims': len(inconsistent),
        'limitations': ['Text flags are a reproducible screen, not a semantic error count.',
                       'An EC appearing in a support set does not show its ESRS phrase changed the verdict.',
                       'Same-card wording differences may include legitimate contextual variation; no new model run was performed.',
                       'Corporate Sustainability Tracker measurements were not revalidated against every original corporate PDF.']}
    dump('summary.json', summary)
    dump('examples.json', examples)
    dump('input_manifest.json', {'files': INPUTS, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    write_csv('case_counts.csv', case_records, list(case_records[0]))
    write_csv('flagged_final_ec.csv', flags, list(flags[0]))
    write_csv('same_card_variation.csv', inconsistent, list(inconsistent[0]))
    print(json.dumps({k: summary[k] for k in ['case_count','flagged_cases_by_stage','downstream','csv_evidence_ids_with_both_flagged_and_unflagged_final_claims']}), flush=True)


if __name__ == '__main__':
    main()
