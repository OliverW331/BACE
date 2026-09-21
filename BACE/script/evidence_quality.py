"""Quarantine unreadable extraction output before embedding or retrieval."""
from collections import Counter
import json
import unicodedata

import tiktoken

from common import ROOT, digest, write


def unusable_reason(text, encoder):
    visible = [c for c in text if not c.isspace()]
    unmapped = sum(unicodedata.category(c)=='Co' or c=='\ufffd' for c in visible)
    if unmapped >= 10 and unmapped/max(1,len(visible)) > 0.05:
        return 'unmapped_font_glyphs', {'unmapped_characters':unmapped,'visible_characters':len(visible)}
    # UTF-8 bytes bound token count; tokenize only potentially oversized cards.
    if len(text.encode('utf-8')) >= 8192:
        tokens = len(encoder.encode(text,disallowed_special=()))
        if tokens > 8191:
            return 'over_embedding_token_limit', {'token_count':tokens}
    return None, {}


def quarantine():
    encoder = tiktoken.get_encoding('cl100k_base')
    root = ROOT/'evidence'
    excluded, counts = [], Counter()
    existing = root/'quality_exclusions.json'
    previous = {r['evidence_id']:r for r in json.loads(existing.read_text())['excluded']} if existing.exists() else {}
    for path in sorted((root/'canonical/indexes').glob('all_*_cards.jsonl')):
        temp = path.with_suffix('.quality.tmp')
        with path.open() as source,temp.open('w') as target:
            for line in source:
                card = json.loads(line)
                reason,details = unusable_reason(card['retrieval_text'],encoder)
                if reason:
                    previous[card['evidence_id']] = {'evidence_id':card['evidence_id'],'company_id':card['company_id'],
                        'source_file':card['source_file'],'source_year':card['source_year'],'evidence_type':card['evidence_type'],
                        'page_start':card.get('page_start'),'page_end':card.get('page_end'),'reason':reason,**details}
                else:
                    target.write(line)
                    counts[card['evidence_type']] += 1
        temp.replace(path)
    excluded = sorted(previous.values(),key=lambda r:r['evidence_id'])
    report = {'version':'unreadable_extraction_quarantine_v1',
              'policy':'Exclude entire cards with at least ten unmapped private-use/replacement glyphs comprising more than 5% of non-whitespace characters, or more than 8191 cl100k_base tokens. Do not truncate text, invent font mappings, or substitute claims. Apply identically across companies and tasks before generation. Raw report caches and source PDFs remain available for audit.',
              'excluded':excluded,'excluded_count':len(excluded),'retained_counts':dict(counts),
              'by_reason':dict(Counter(r['reason'] for r in excluded)),
              'by_company_year':dict(Counter(f"{r['company_id']}:{r['source_year']}" for r in excluded))}
    write(existing,report)
    print({'quality_excluded_cards':len(excluded),'retained_cards':dict(counts)},flush=True)
    return report
