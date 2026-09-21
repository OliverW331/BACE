"""Select companies using source availability only, before model evaluation."""
from collections import Counter, defaultdict
import csv
import hashlib
import random
import re

import pandas as pd

from common import ROOT, csvfile, digest, read, write


def allocate(counts, size):
    """One per nonempty sector, then Hamilton allocation of remaining slots."""
    if size < len(counts) or size > sum(counts.values()):
        raise ValueError('Sample size cannot represent every eligible sector')
    remaining = size - len(counts)
    weights = {k: v - 1 for k, v in counts.items()}
    denominator = sum(weights.values())
    exact = {k: remaining * v / denominator if denominator else 0 for k, v in weights.items()}
    quotas = {k: 1 + int(v) for k, v in exact.items()}
    for k in sorted(counts, key=lambda k: (-(exact[k] - int(exact[k])), k))[:size-sum(quotas.values())]:
        quotas[k] += 1
    return quotas


def select():
    config = read(ROOT/'config/experiment.json')
    data = (ROOT/config['data_root']).resolve()
    out = ROOT/'evidence/sample'
    companies_path = data/'raw/datasets/companies.csv'
    metric_path = data/'processed/results/esg_indicators_postprocessed.csv'
    companies = pd.read_csv(companies_path).sort_values(['firm', 'year'], kind='stable')
    # Classification is the latest observed classification at or before 2023.
    companies = companies[companies.year <= 2023].groupby('firm', sort=True).tail(1)
    valid = defaultdict(Counter)
    for chunk in pd.read_csv(metric_path, chunksize=100000, usecols=['company_id','year','model_output_valid','value_final'], dtype=str):
        keep = chunk.model_output_valid.str.lower().isin(['true','1','yes','y','t']) & chunk.value_final.notna() & chunk.value_final.str.strip().ne('')
        for (cid, year), n in chunk[keep].groupby(['company_id','year']).size().items():
            valid[cid][int(year)] += int(n)
    available = defaultdict(lambda: defaultdict(list))
    invalid = []
    for p in sorted((data/'raw/reports_pdf').glob('*.pdf')):
        match = re.fullmatch(r'(.+)_(\d{4})_(.+)\.pdf', p.name)
        if not match:
            continue
        cid, year, kind = match.groups()
        if not 2015 <= int(year) <= 2022:
            continue
        with p.open('rb') as f:
            header = f.read(1024)
        if b'%PDF-' not in header:
            invalid.append(p.name)
        else:
            available[cid][int(year)].append(p.name)
    frame = []
    for item in companies.to_dict('records'):
        cid = item['firm']
        missing_csv = [y for y in range(2015,2024) if not valid[cid][y]]
        missing_pdf = [y for y in range(2015,2023) if not available[cid][y]]
        sector = item['primary_sics_sector'] if pd.notna(item['primary_sics_sector']) else ''
        frame.append({'company_id':cid,'company_name':item['name'],'company_slug':re.sub('[^a-z0-9]+','_',item['name'].lower()).strip('_'),
                      'primary_sics_sector':sector,'country':item['country'],'classification_year':int(item['year']),
                      'eligible':not missing_csv and not missing_pdf and bool(sector),
                      'missing_csv_years':missing_csv,'missing_pdf_years':missing_pdf,
                      'csv_valid_counts':{str(y):valid[cid][y] for y in range(2015,2024)},
                      'pdf_reports':{str(y):available[cid][y] for y in range(2015,2023)}})
    groups = defaultdict(list)
    for r in frame:
        if r['eligible']:
            groups[r['primary_sics_sector']].append(r)
    counts = {k:len(v) for k,v in sorted(groups.items())}
    quotas = allocate(counts, 30)
    selected, reserves = [], {}
    for sector, group in sorted(groups.items()):
        ordered = sorted(group, key=lambda r:r['company_id'])
        seed = int(hashlib.sha256(f"{config['sampling']['seed']}:{sector}".encode()).hexdigest(),16)
        random.Random(seed).shuffle(ordered)
        selected.extend(ordered[:quotas[sector]])
        reserves[sector] = [r['company_id'] for r in ordered[quotas[sector]:]]
    selected.sort(key=lambda r:(r['primary_sics_sector'],r['company_id']))
    manifest = {'version':'stratified_source_availability_v1','seed':config['sampling']['seed'],
                'selection_uses_experiment_scores':False,'source_hashes':{str(companies_path):digest(companies_path),str(metric_path):digest(metric_path)},
                'policy':config['sampling'],'eligible_counts':counts,'quotas':quotas,'population_count':len(frame),
                'eligible_count':sum(counts.values()),'selected':selected,'reserve_order':reserves,'invalid_pdf_headers':invalid}
    if (out/'sample.json').exists() and read(out/'sample.json') != manifest:
        raise ValueError('Frozen sample differs; use a new experiment version instead of overwriting')
    write(out/'sample.json',manifest)
    write(out/'sampling_frame.json',frame)
    csvfile(out/'selected_companies.csv', [{k:r[k] for k in ['company_id','company_name','company_slug','primary_sics_sector','country']} for r in selected])
    print({'population':len(frame),'eligible':sum(counts.values()),'quotas':quotas,'selected':len(selected)},flush=True)
    return manifest


if __name__ == '__main__':
    select()
