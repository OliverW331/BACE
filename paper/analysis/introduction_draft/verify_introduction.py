"""Verify the reviewed Introduction against source records and its compiled PDF.

Checks are mechanical safeguards for manually reviewed evidence, not an automated
semantic review or an independent validation of the research. No experiment
artifact, manuscript prose or bibliography is changed by this script.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PROJECT = ROOT / 'paper/manuscript'
INPUTS = {}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(relative):
    p = ROOT / relative
    INPUTS[relative] = sha(p)
    return p.read_text()

def load(relative):
    return json.loads(read(relative))

def canonical(s):
    return re.sub(r'\W', '', unicodedata.normalize('NFKC', s))

def citekeys(s):
    return [k for g in re.findall(r'\\cite\{([^}]+)\}', s) for k in g.split(',')]

def block(s, name):
    return s.split('% BEGIN_' + name + '\n')[1].split('% END_' + name)[0]

def words(s):
    s = re.sub(r'(?m)^%.*$', '', s)
    s = re.sub(r'\\(?:cite|ref)\{[^}]+\}', '', s)
    s = re.sub(r'\\(?:sub)?section\*?\{[^}]+\}', '', s)
    s = re.sub(r'\\\[.*?\\\]|\\\(.*?\\\)', '', s, flags=re.S)
    s = re.sub(r'\\(?:[A-Za-z]+)\*?(?:\[[^]]*\])?', '', s)
    s = s.replace('~', ' ').replace('---', ' ').replace('--', '–')
    return re.findall(r"[\w]+(?:[.,'’–-][\w]+)*", s)

def main():
    tex = read('paper/manuscript/main.tex')
    intro = block(tex, 'INTRODUCTION')
    draft = load('paper/analysis/introduction_draft/draft_record.json')
    assert hashlib.sha256(intro.encode()).hexdigest() == draft['introduction_sha256']
    paragraphs = dict(re.findall(r'% (I\d\d)\n(.*?)(?=\n% I\d\d|\Z)', intro, re.S))
    assert list(paragraphs) == [f'I{i:02}' for i in range(1,7)]
    assert not re.search(r'\\(?:sub)?section', intro)
    assert not any(s in intro for s in ['DRAFT\\_PENDING', 'UNVERIFIED', 'AUTHOR\\_INPUT'])
    occurrences = load('paper/analysis/introduction_draft/citation_occurrences.json')
    assert citekeys(intro) == [r['citation_key'] for r in occurrences]
    for pid,p in paragraphs.items():
        assert hashlib.sha256(p.encode()).hexdigest() == draft['paragraph_sha256'][pid]
        assert citekeys(p) == [r['citation_key'] for r in occurrences if r['location'] == pid]
    for r in occurrences:
        assert r['claim'] in paragraphs[r['location']]
        assert r['verdict'] == 'DIRECT'
        original = re.sub(r'\s+', ' ', read(r['fulltext_path']))
        assert all(f in original for f in r['verified_excerpt_fragments'])
        for field in ['fulltext_path','original_pdf','retrieval_record']:
            path = ROOT / r[field]
            INPUTS[r[field]] = sha(path)
            assert INPUTS[r[field]] == r['source_hashes'][path.name]
        assert r['locator'] and r['source_version'] and r['limits']
    library = read('paper/references.bib')
    entries = {re.match(r'@\w+\{([^,]+),',p).group(1):p.rstrip() for p in re.split(r'(?=^@\w+\{)',library,flags=re.M) if p.startswith('@')}
    allkeys = citekeys(tex)
    assert read('paper/manuscript/references.bib') == '\n\n'.join(entries[k] for k in dict.fromkeys(allkeys)) + '\n'
    assert len(allkeys)==13 and len(set(allkeys))==10
    # Verify the recorded bibliography addition is retained by the dated library
    # builder without rerunning that builder or altering its historical outputs.
    additions = read('paper/literature/additional_references.bib').strip()
    assert additions == entries['esrs2023']
    builder = read('paper/literature/build_audit_artifacts.py')
    compile(builder, 'build_audit_artifacts.py', 'exec')
    assert 'additional_references.bib' in builder
    methods = load('paper/analysis/methods_draft/provenance.json')
    assert methods['status']=='PASS'
    # Verify the exact saved result and its upstream input hashes before using
    # the ledger. Methods verification has freshly checked the frozen settings.
    facts = load('paper/analysis/methods_draft/verified_method_facts.json')
    for relative,record in methods['input_files'].items():
        path = ROOT/relative
        assert sha(path) == record['sha256'], relative
    ledger = load('paper/analysis/introduction_draft/numeric_ledger.json')
    for r in ledger:
        if r['status']=='COMPUTED_VERIFIED':
            assert r['value']==facts['cohort'][r['result_locator'].split('.')[-1]]
            assert r['printed_value'] in paragraphs['I06']
    assert facts['cohort']['completed']==facts['cohort']['paired']==1798
    assert facts['cohort']['planned']==30*5*12==1800
    assert facts['configuration']['human.status']=='prepared_not_annotated'
    baseline=load('paper/analysis/introduction_draft/baseline.json')
    for name,digest in baseline['preserved_blocks'].items():
        assert hashlib.sha256(block(tex,name).encode()).hexdigest()==digest
    for relative,digest in baseline['figures'].items():
        INPUTS[relative]=sha(ROOT/relative)
        assert INPUTS[relative]==digest
    assert [hashlib.sha256(s.encode()).hexdigest() for s in re.findall(r'\\begin\{figure\}.*?\\end\{figure\}',tex,re.S)]==baseline['figure_environments_sha256']
    pdf=PROJECT/'main.pdf'
    rendered=subprocess.check_output(['pdftotext','-enc','UTF-8',str(pdf),'-'],text=True)
    normalized=canonical(re.sub(r'(?m)^\s*\d+\s*$', '',rendered))
    checks={}
    for pid,p in paragraphs.items():
        parts=re.split(r'\\cite\{[^}]+\}',p)
        chunks=[canonical(s.replace('--','–')) for s in parts if len(canonical(s))>=25]
        assert chunks and all(c in normalized for c in chunks), pid
        checks[pid]={'status':'PASS','rendered_prose_fragments':len(chunks),'source':'paper/manuscript/main.tex','word_count':len(words(p))}
    # Numerically verify emitted citation labels in the BibTeX/LaTeX artifacts.
    aux=read('paper/manuscript/build/main.aux')
    bbl=read('paper/manuscript/build/main.bbl')
    bibitems=re.findall(r'\\bibitem\[.*?\]\{([^}]+)\}',bbl,re.S)
    assert bibitems==list(dict.fromkeys(allkeys))
    for i,key in enumerate(bibitems,1):
        assert re.search(r'\\bibcite\{'+re.escape(key)+r'\}\{\{'+str(i)+r'\}',aux),key
    counts={name.lower():len(words(block(tex,name))) for name in ['INTRODUCTION','RESULTS','METHODS']}
    counts['drafted_main_text']=counts['introduction']+counts['results']
    counts['main_text_guideline']=3500
    counts['remaining_before_discussion']=3500-counts['drafted_main_text']
    counts['rule']='Regex prose-word estimate, excluding paragraph IDs, headings, citation/reference commands and displayed/inline math. Hyphenated words and year ranges count as one. Not a publisher word count; Discussion is pending.'
    (OUT/'word_counts.json').write_text(json.dumps(counts,indent=2)+'\n')
    build=load('paper/manuscript/build/build_manifest.json')
    assert build['main_pdf_sha256']==sha(pdf)
    log=read('paper/manuscript/build/main.log')
    assert not re.search(r'Warning:|Overfull \\[hv]box|Missing character:|^!',log,re.M)
    record={'status':'PASS','checked_at_utc':datetime.now(timezone.utc).isoformat(),'command':f'{sys.executable} paper/analysis/introduction_draft/verify_introduction.py','script_sha256':sha(Path(__file__)),'inputs':INPUTS,'paragraph_checks':checks,'citation_occurrences':len(occurrences),'whole_manuscript_citation_occurrences':len(allkeys),'unique_references':len(set(allkeys)),'numeric_records':len(ledger),'preserved_results_methods':True,'preserved_figure_artwork_and_legends':True,'bibliography_order':'PASS','word_counts':counts,'pdf_sha256':sha(pdf),'limits':'Mechanical integration checks plus previously recorded source reading. Not independent human validation, final editorial review or submission approval.'}
    (OUT/'provenance.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ['status','citation_occurrences','unique_references','preserved_results_methods','preserved_figure_artwork_and_legends','word_counts']}))

if __name__=='__main__':
    main()
