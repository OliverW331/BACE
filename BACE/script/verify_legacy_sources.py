"""Independently re-extract reused reports to verify current source text/location."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from common import ROOT, digest, read, rows, write
from prepare_evidence import PDF_CONFIG, pdf_builder

FIELDS = ('evidence_id','company_id','source_type','evidence_type','source_year',
          'document_type','source_file','page_start','page_end','section_heading',
          'heading_path','original_text','retrieval_text')


def verify_one(task):
    fresh = pdf_builder.process_pdf_report_task(task)
    filename = task['report'].source_file
    cached = rows(ROOT/'evidence/report_cache'/(filename+'.jsonl'))
    def project(cards):
        return {c['evidence_id']:{k:c.get(k) for k in FIELDS} for c in cards}
    old,new = project(cached),project(fresh['cards'])
    differences = sorted(k for k in old.keys() | new.keys() if old.get(k)!=new.get(k))
    return {'source_file':filename,'source_sha256':digest(task['report'].pdf_path),
            'cached_cards':len(old),'fresh_cards':len(new),'differing_card_ids':differences,
            'pages_processed':fresh['extraction_summary']['pages_processed'],
            'pages_total':fresh['extraction_summary']['pages_total'],
            'errors':fresh['extraction_summary']['errors'],'passed':not differences and not fresh['failed']}


def verify():
    config = read(ROOT/'config/experiment.json')
    selected = {c['company_id']:c for c in read(ROOT/'evidence/sample/sample.json')['selected']}
    data = (ROOT/config['data_root']).resolve()
    tasks = []
    for record in read(ROOT/'evidence/pdf_build_report.json')['reports']:
        if record.get('origin')!='copied_legacy_cards':
            continue
        report = pdf_builder.parse_report_filename(data/'raw/reports_pdf'/record['source_file'])
        company = selected[report.company_id]
        tasks.append({'task_index':len(tasks),'report':report,
                      'company':pdf_builder.CompanyMeta(**{k:company[k] for k in ['company_id','company_name','company_slug','country','primary_sics_sector']}),
                      'config':PDF_CONFIG})
    checked = []
    with ProcessPoolExecutor(max_workers=config['runtime']['pdf_workers']) as pool:
        for f in as_completed([pool.submit(verify_one,t) for t in tasks]):
            checked.append(f.result())
            print(f"Verified reused report {len(checked)}/{len(tasks)}: {checked[-1]['passed']}",flush=True)
    if not all(r['passed'] for r in checked):
        raise ValueError('Reused evidence differs from fresh source extraction')
    report = read(ROOT/'evidence/pdf_build_report.json')
    verified = {r['source_file'] for r in checked}
    for item in report['reports']:
        if item['source_file'] in verified:
            item['source_reextraction_verified'] = True
    write(ROOT/'evidence/pdf_build_report.json',report)


if __name__=='__main__':
    verify()
