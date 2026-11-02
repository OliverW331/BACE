"""Audit every historical source and cache three evidence layers without model calls."""
from collections import defaultdict
import csv
import json
from pathlib import Path

from common import (EXP, ROOT, BACE, RESULTS, SOURCE_EXP, read, rows, sha,
                    write, now, rank, native, external)


def main():
    if (EXP/'freeze.json').exists():
        raise RuntimeError('Already frozen; do not overwrite inputs.')
    if any(RESULTS.glob('runs/*/calls.jsonl')):
        raise RuntimeError('Model records already exist.')
    source = read(SOURCE_EXP/'plan.json')
    source_freeze = read(SOURCE_EXP/'freeze.json')
    assert sha(SOURCE_EXP/'plan.json') == source_freeze['files'][str((SOURCE_EXP/'plan.json').relative_to(ROOT))]
    hashes = {}
    def record(path, expected=None):
        path = Path(path)
        key = str(path.relative_to(ROOT))
        digest = sha(path)
        if expected is not None:
            assert digest == expected, key
        if key in source_freeze['files']:
            assert digest == source_freeze['files'][key], key
        hashes[key] = digest
        return digest
    record(SOURCE_EXP/'plan.json')
    record(SOURCE_EXP/'freeze.json')
    config, _, _, _, _ = native.load_and_validate_configuration(
        BACE/'config/evaluation/configs/generation_claim_support_config.json')
    cases, sizes = [], []
    company_jobs = defaultdict(list)
    for index, previous in enumerate(source['cases'], 1):
        cid = previous['generation_case_id']
        base = BACE/'results/main_v1/cases'/cid
        support_path = base/'bace/support/claim_support_run_manifest.json'
        support = read(support_path)
        record(support_path)
        source_paths = support['run_identity']['inputs']
        for info in source_paths.values():
            record(info['path'], info['sha256'])
        generation_path = Path(source_paths['generation_cases']['path'])
        generation = list(rows(generation_path))
        assert len(generation) == 1 and generation[0]['generation_case_id'] == cid
        generation = generation[0]
        output_path = base/'generation/generated_disclosures.jsonl'
        baseline_path = base/'evaluation/ragas/manifest.json'
        baseline = read(baseline_path)
        record(baseline_path)
        assert baseline['status'] == 'complete'
        record(generation_path, baseline['identity']['source_hashes']['generation_cases'])
        record(output_path, baseline['identity']['source_hashes']['generated_disclosures'])
        outputs = list(rows(output_path))
        assert len(outputs) == 1
        adapted = external.adapt_case(generation, outputs[0])
        visible = [c for c in generation['prompt_evidence'] if c['shown_in_prompt']]
        assert len({c['evidence_id'] for c in visible}) == len(visible)
        card_by_id = {c['evidence_id']:c for c in visible}
        dedup_manifest_path = base/'bace/dedup/semantic_dedup_run_manifest.json'
        dedup_manifest = read(dedup_manifest_path)
        record(dedup_manifest_path)
        occurrences_path = Path(dedup_manifest['run_identity']['inputs']['ec']['path'])
        record(occurrences_path, dedup_manifest['run_identity']['inputs']['ec']['sha256'])
        occurrences = {x['ec_occurrence_id']:x for x in rows(occurrences_path)}
        ec_rows = sorted(rows(source_paths['ec_claims']['path']), key=lambda x:x['ec_id'])
        ec_alias, original_by_alias = native.make_temporary_ids(
            [x['ec_id'] for x in ec_rows], prefix='ec', minimum_width=3)
        assert len(ec_alias) == len(ec_rows)
        linked_occurrences = set()
        for ec in ec_rows:
            assert ec['generation_case_id'] == cid
            assert set(ec['evidence_card_ids']) <= set(card_by_id)
            assert set(ec['ec_occurrence_ids']) <= set(occurrences)
            linked_occurrences.update(ec['ec_occurrence_ids'])
            for provenance in ec['ec_provenance']:
                original = occurrences[provenance['ec_occurrence_id']]
                assert provenance['claim_text'] == original['claim_text']
                card = card_by_id[provenance['evidence_id']]
                assert provenance['retrieval_text_hash'] == card['retrieval_text_hash']
                assert original['evidence_id'] == card['evidence_id']
        # Omitted occurrence IDs are retained as an audit statistic, never hidden.
        original_cache = ROOT/previous['cache_path']
        record(original_cache, previous['cache_sha256'])
        jobs = list(rows(original_cache))
        assert len(jobs) == previous['claims']
        dc_rows = {x['dc_id']:x for x in rows(source_paths['dc_claims']['path'])}
        selections = {x['dc_claim_id']:x for x in rows(source_paths['candidate_selections']['path'])}
        raw_units = [{'unit_id':f'card_{i:03d}', 'alias':f'ec_{i:03d}',
                      'evidence_id':eid, 'prompt_label':label, 'text':text}
                     for i,(eid,label,text) in enumerate(zip(adapted['evidence_ids'],
                         adapted['prompt_labels'],adapted['contexts']),1)]
        all_input = [{'ec_claim_id':ec_alias[x['ec_id']], 'ec_text':x['ec_text']} for x in ec_rows]
        by_alias = {x['ec_claim_id']:x for x in all_input}
        raw_chars = sum(len(x['text']) for x in raw_units)
        all_chars = sum(len(x['ec_text']) for x in all_input)
        for saved in jobs:
            job = saved['job']
            assert job['generation_case_id'] == cid
            assert job['dynamic_input']['dc_claim']['dc_text'] == dc_rows[job['dc_id']]['dc_text']
            assert job['ec_original_by_alias'] == original_by_alias
            assert set(job['call_identity']['candidate_ec_ids']) == set(selections[job['dc_id']]['candidate_ec_ids'])
            assert job['dynamic_input']['ec_claims'] == [by_alias[a] for a in job['candidate_ec_aliases']]
            assert job['request_parameters'] == source['model']['request_parameters']
            sizes.append({'generation_case_id':cid,'company_id':previous['company_id'],
                'dc_id':job['dc_id'],'raw_units':len(raw_units),'all_ec_units':len(all_input),
                'candidate_units':len(job['candidate_ec_aliases']),
                'raw_text_characters':raw_chars,'all_ec_text_characters':all_chars,
                'candidate_text_characters':sum(len(x['ec_text']) for x in job['dynamic_input']['ec_claims'])})
            if job['requires_model']:
                company_jobs[previous['company_id']].append((cid,job['dc_id']))
        destination = RESULTS/'inputs'/f'{cid}.json'
        write(destination, {'generation_case_id':cid,'raw_units':raw_units,'all_ec_input':all_input,
            'dc_jobs':jobs,'raw_context_hash':adapted['context_hash'],
            'lineage_paths':{'generation_cases':str(generation_path.relative_to(ROOT)),
                'ec_claims':str(Path(source_paths['ec_claims']['path']).relative_to(ROOT)),
                'ec_occurrences':str(occurrences_path.relative_to(ROOT))}})
        cases.append({k:previous[k] for k in ['generation_case_id','company_id','company_name','year','task','claims','zero_candidates']} |
            {'cache_path':str(destination.relative_to(ROOT)),'cache_sha256':sha(destination),
             'raw_units':len(raw_units),'all_ec_units':len(all_input),
             'extracted_occurrences':len(occurrences),'linked_occurrences':len(linked_occurrences),
             'unlinked_occurrences':len(set(occurrences)-linked_occurrences),
             'raw_text_characters':raw_chars,'all_ec_text_characters':all_chars})
        if index % 100 == 0:
            print(f'Checked {index}/{len(source["cases"])} disclosures',flush=True)
    assert len(sizes) == source['counts']['claims_per_full_condition']
    pilot = {min(v,key=lambda x:rank('pilot','|'.join(x))) for v in company_jobs.values()}
    # Add input-size extremes to the technical gate, without reading outcomes.
    for field in ['raw_text_characters','all_ec_text_characters','candidate_units']:
        largest = max(sizes,key=lambda x:(x[field],rank('largest',x['generation_case_id']+'|'+x['dc_id'])))
        pilot.add((largest['generation_case_id'],largest['dc_id']))
    input_dir = RESULTS/'qa'
    input_dir.mkdir(parents=True,exist_ok=True)
    for name,records in [('input_sizes',sizes),('case_inventory',cases)]:
        with (input_dir/f'{name}.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(records[0]))
            writer.writeheader(); writer.writerows(records)
    report={'status':'INPUTS_PREPARED_NO_MODEL_CALLS','created_at_utc':now(),
        'cases':cases,'source_hashes':hashes,'model':source['model'],
        'model_key':source['model_key'],'deployment_name':source['deployment_name'],
        'counts':{'disclosures':len(cases),'companies':len(company_jobs),'claims_per_condition':len(sizes),
            'planned_records':3*len(sizes),'zero_candidates':sum(x['zero_candidates'] for x in cases),
            'unlinked_occurrences':sum(x['unlinked_occurrences'] for x in cases)},
        'pilot_jobs':[{'generation_case_id':c,'dc_id':d} for c,d in sorted(pilot)],
        'source_plan_sha256':sha(SOURCE_EXP/'plan.json'),
        'input_size_summary':{field:{'minimum':min(x[field] for x in sizes),
            'maximum':max(x[field] for x in sizes),'mean':sum(x[field] for x in sizes)/len(sizes)}
            for field in ['raw_units','all_ec_units','candidate_units','raw_text_characters','all_ec_text_characters','candidate_text_characters']}}
    write(EXP/'input_plan.json',report)
    print(json.dumps({'counts':report['counts'],'input_size_summary':report['input_size_summary'],
                      'pilot_claims':len(pilot)},indent=2),flush=True)

if __name__ == '__main__':
    main()
