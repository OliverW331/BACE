"""Source-traceable CSV/PDF cards, resumable report extraction, and annual packs."""
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import json
import shutil
import sys

import pandas as pd

from common import ROOT, csvfile, digest, jsonl, read, rows, write
sys.path.insert(0, str(ROOT/'script/data_2_evidence'))
import csv_2_evidence as csv_builder
import pdf_2_evidence as pdf_builder

BUILD = ROOT/'evidence'
INDEX = BUILD/'canonical/indexes'
PDF_CONFIG = dict(extract_tables=True, include_table_markdown=False,
                  include_short_narrative=False, narrative_min_words=40,
                  narrative_max_words=250, narrative_min_chars=50, max_pages_per_pdf=None)
EVONIK = '060107a1-5462-4b5b-adf7-ca200f3bb587'
CORRECTIONS = {
    '79721786-0de7-4a9f-b933-d7cfe2def60b': 'Eight alleged cases do not establish eight confirmed incidents (PDF page 124).',
    'da409069-8783-4aa9-ae11-6e310c8c2808': 'Twelve dismissed employees for general compliance violations do not establish twelve corruption incidents (PDF page 124).',
    '9751e1dc-2cd3-4275-986f-dea3650914ec': 'Three terminated business relationships concern general compliance, not established corruption incidents (PDF page 124).',
    '7c966679-3964-4ebe-bc33-0e96343dca51': 'About 90 percent paid within 60 days does not establish an average of 60 days (PDF page 130).',
}


def build_csv(selected, data):
    source = data/'processed/results/esg_indicators_postprocessed.csv'
    indicators = csv_builder.load_indicator_metadata(data/'raw/datasets/indicator_metadata.csv')
    metadata = {r['company_id']:csv_builder.CompanyMeta(**{k:r[k] for k in ['company_id','company_name','company_slug','country','primary_sics_sector']}) for r in selected}
    cards, exclusions, seen = [], [], set()
    source_hash = digest(source)
    for chunk in pd.read_csv(source, chunksize=100000, low_memory=False):
        chunk = chunk[chunk.company_id.isin(metadata) & chunk.year.between(2015,2023)]
        chunk = chunk[csv_builder.bool_series(chunk.model_output_valid) & chunk.value_final.notna() & chunk.value_final.astype(str).str.strip().ne('')]
        chunk = chunk.merge(indicators,on='data_point_id',how='left',validate='many_to_one')
        for row in chunk.to_dict('records'):
            card = csv_builder.construct_csv_metric_card(row, metadata[row['company_id']], '../data/processed/results/esg_indicators_postprocessed.csv')
            if card['evidence_id'] in seen:
                raise ValueError('Duplicate source metric: '+card['evidence_id'])
            seen.add(card['evidence_id'])
            card['source_sha256'] = source_hash
            if row['company_id'] == EVONIK and int(row['year']) == 2023 and row['data_point_id'] in CORRECTIONS:
                exclusions.append({'evidence_id':card['evidence_id'],'source_value':card['value_text'],'action':'exclude_from_cards_packages_and_indexes', 'reason':CORRECTIONS[row['data_point_id']]})
                continue
            cards.append(card)
    cards.sort(key=lambda c:c['evidence_id'])
    jsonl(INDEX/'all_csv_metric_cards.jsonl',cards)
    write(BUILD/'mapping_corrections.json',{'version':'source_mapping_exclusions_v1','raw_data_modified':False,'policy':'Quarantine four verified erroneous Evonik 2023 metric cells; do not infer replacement values. Other model-extracted CSV cells remain unverified, not source-validated facts.','source_report':'../data/raw/reports_pdf/'+EVONIK+'_2023_SR.pdf','source_report_sha256':digest(data/'raw/reports_pdf'/f'{EVONIK}_2023_SR.pdf'),'exclusions':exclusions})
    print(f'CSV: {len(cards)} cards; {len(exclusions)} documented exclusions',flush=True)


def extract_one(task):
    path = BUILD/'report_cache'/ (task['report'].source_file+'.jsonl')
    meta = path.with_suffix('.meta.json')
    fingerprint = {'source_sha256':digest(task['report'].pdf_path),'config':PDF_CONFIG,
                   'extractor_sha256':digest(Path(pdf_builder.__file__))}
    if path.exists() and meta.exists():
        record = read(meta)
        if record['fingerprint'] == fingerprint and record['cards_sha256'] == digest(path):
            return record
        raise ValueError('Changed PDF cache source/config: '+path.name)
    result = pdf_builder.process_pdf_report_task(task)
    if result['failed'] or result['extraction_summary']['errors']:
        write(meta.with_suffix('.failure.json'),result['extraction_summary'])
        raise RuntimeError('PDF extraction failed: '+task['report'].source_file)
    for card in result['cards']:
        card['source_sha256'] = fingerprint['source_sha256']
        card['source_path'] = '../data/raw/reports_pdf/'+card['source_file']
    jsonl(path,result['cards'])
    record = {'source_file':task['report'].source_file,'fingerprint':fingerprint,
              'cards_sha256':digest(path),'summary':result['extraction_summary'],'origin':'local_extraction'}
    write(meta,record)
    return record


def import_legacy(tasks):
    """Copy eligible prior source cards once; no runtime dependency on old files."""
    legacy = ROOT.parent/'evidence_pilot/canonical/indexes/all_pdf_cards.jsonl'
    if not legacy.exists():
        return
    wanted = {t['report'].source_file:t for t in tasks if not (BUILD/'report_cache'/(t['report'].source_file+'.jsonl')).exists()}
    grouped = defaultdict(list)
    summaries = {p.name.replace('.extraction_summary.json','.pdf'):p
                 for p in (ROOT.parent/'evidence_pilot/canonical/companies').glob('**/*.extraction_summary.json')}
    with legacy.open() as f:
        for line in f:
            c = json.loads(line)
            if c['source_file'] in wanted and c['evidence_type'] in ('narrative','pdf_table_row'):
                grouped[c['source_file']].append(c)
    for filename, cards in grouped.items():
        task = wanted[filename]
        if filename not in summaries:
            continue
        summary = read(summaries[filename])
        if summary.get('errors') or summary.get('pages_processed') != summary.get('pages_total'):
            continue
        if len(cards) != summary['narrative_cards_written'] + summary['table_row_cards_written']:
            raise ValueError('Legacy card count differs from its extraction summary: '+filename)
        # Legacy extractor settings are unchanged; source identity is now hashed.
        fingerprint = {'source_sha256':digest(task['report'].pdf_path),'config':PDF_CONFIG,
                       'extractor_sha256':digest(Path(pdf_builder.__file__))}
        for c in cards:
            c['source_sha256'] = fingerprint['source_sha256']
            c['source_path'] = '../data/raw/reports_pdf/'+filename
        path = BUILD/'report_cache'/(filename+'.jsonl')
        jsonl(path,cards)
        with pdf_builder.fitz.open(task['report'].pdf_path) as doc:
            pages = len(doc)
        if pages != summary['pages_total']:
            raise ValueError('Source page count differs from legacy extraction: '+filename)
        record = {'source_file':filename,'fingerprint':fingerprint,'cards_sha256':digest(path),
                  'summary':summary,'legacy_summary_sha256':digest(summaries[filename]),
                  'legacy_summary_source':str(summaries[filename].relative_to(ROOT.parent)),
                  'origin':'copied_legacy_cards','legacy_index_sha256':digest(legacy),
                  'legacy_source':'evidence_pilot/canonical/indexes/all_pdf_cards.jsonl'}
        write(path.with_suffix('.meta.json'),record)
    print(f'Reused {len(grouped)} prior PDF card sets',flush=True)


def build_pdfs(selected, data):
    tasks = []
    for r in selected:
        company = pdf_builder.CompanyMeta(**{k:r[k] for k in ['company_id','company_name','company_slug','country','primary_sics_sector']})
        for year, files in sorted(r['pdf_reports'].items()):
            for filename in files:
                report = pdf_builder.parse_report_filename(data/'raw/reports_pdf'/filename)
                if report is None:
                    raise ValueError('Unsupported report filename: '+filename)
                tasks.append({'task_index':len(tasks),'report':report,'company':company,'config':PDF_CONFIG})
    import_legacy(tasks)
    results = []
    with ProcessPoolExecutor(max_workers=read(ROOT/'config/experiment.json')['runtime']['pdf_workers']) as pool:
        futures = {pool.submit(extract_one,t):t['report'].source_file for t in tasks}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f'PDF {len(results)}/{len(tasks)} {result["source_file"]}',flush=True)
    INDEX.mkdir(parents=True,exist_ok=True)
    paths = {k:INDEX/f'all_pdf_{k}_cards.jsonl' for k in ['narrative','table_row']}
    streams = {k:p.with_suffix('.tmp').open('w') for k,p in paths.items()}
    counts, seen = Counter(), set()
    try:
        for task in tasks:
            for c in rows(BUILD/'report_cache'/(task['report'].source_file+'.jsonl')):
                if c['evidence_id'] in seen:
                    raise ValueError('Duplicate PDF evidence ID')
                seen.add(c['evidence_id'])
                key = 'narrative' if c['evidence_type']=='narrative' else 'table_row'
                streams[key].write(json.dumps(c,ensure_ascii=False)+'\n')
                counts[key] += 1
    finally:
        for f in streams.values():
            f.close()
    for p in paths.values():
        p.with_suffix('.tmp').replace(p)
    write(BUILD/'pdf_build_report.json',{'counts':counts,'reports':sorted(results,key=lambda r:r['source_file']),'report_count':len(tasks)})


def build_packages(selected):
    by_company = defaultdict(lambda:defaultdict(lambda:defaultdict(list)))
    for p in sorted(INDEX.glob('all_*_cards.jsonl')):
        for c in rows(p):
            by_company[c['company_id']][c['source_year']][c['evidence_type']].append(c['evidence_id'])
    index = []
    for company in selected:
        for year in range(2019,2024):
            content = {}
            for kind in ['csv_metric','narrative','pdf_table_row']:
                years = range(year-4,year+1) if kind=='csv_metric' else range(year-4,year)
                content['pdf_narrative' if kind=='narrative' else kind] = sorted(eid for y in years for eid in by_company[company['company_id']][y][kind])
            # Availability remains independent of task content and scores.
            for y in range(year-4,year):
                if not by_company[company['company_id']][y]['narrative']:
                    raise ValueError(f'Unusable full PDF source year: {company["company_id"]} {y}')
            for y in range(year-4,year+1):
                if not by_company[company['company_id']][y]['csv_metric']:
                    raise ValueError('No usable CSV source year')
            package = {k:company[k] for k in ['company_id','company_name','company_slug','primary_sics_sector','country']}
            package.update(schema_version='evidence_package_manifest_v1',package_id=f'{company["company_id"]}__{year}',target_reporting_year=year,
                           included_source_years={'csv':list(range(year-4,year+1)),'pdf':list(range(year-4,year))},evidence_card_ids=content)
            path = BUILD/'builds/main_v1/companies'/company['company_id']/'manifests'/f'package_{year}.json'
            write(path,package)
            index.append({'company_id':company['company_id'],'target_reporting_year':year,'manifest_path':str(path.relative_to(BUILD/'builds/main_v1'))})
    csvfile(BUILD/'builds/main_v1/package_index.csv',index)
    write(BUILD/'builds/main_v1/build_config.json',{'windows':read(ROOT/'config/experiment.json')['windows'],'sample_sha256':digest(BUILD/'sample/sample.json'),'index_hashes':{p.name:digest(p) for p in INDEX.glob('*.jsonl')},'package_count':len(index)})
    print(f'Built {len(index)} annual packages',flush=True)


def prepare():
    config = read(ROOT/'config/experiment.json')
    data = (ROOT/config['data_root']).resolve()
    selected = read(BUILD/'sample/sample.json')['selected']
    build_csv(selected,data)
    build_pdfs(selected,data)
    from evidence_quality import quarantine
    quarantine()
    build_packages(selected)
    from verify_legacy_sources import verify
    verify()
    shutil.rmtree(BUILD/'report_cache')


if __name__ == '__main__':
    prepare()
