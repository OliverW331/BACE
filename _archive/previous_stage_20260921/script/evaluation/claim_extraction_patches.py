"""Apply source-grounded edits without regenerating unaffected flat claims."""
from copy import deepcopy
import re


class PatchContractError(ValueError):
    pass


def report_attribution(source_label):
    # A year explicitly printed in the visible report filename is attribution,
    # not an event/measurement year. Tracker source years are handled in claims.
    match = re.search(r'_(\d{4})_(?:AR|SR)\.pdf\b', source_label)
    return f'According to the {match.group(1)} report' if match else ''


def apply_unit(draft_claims, edits, additions, attribution=''):
    owners = {}
    for edit in edits:
        indexes = edit['replace_indices']
        if not indexes or len(set(indexes)) != len(indexes):
            raise PatchContractError('An edit must identify distinct existing claim indexes')
        for index in indexes:
            if type(index) is not int or index < 1 or index > len(draft_claims) or index in owners:
                raise PatchContractError('Replacement index out of range or edited twice')
            owners[index] = edit
    final = []
    for index, original in enumerate(draft_claims, 1):
        edit = owners.get(index)
        if edit is None:
            final.append(deepcopy(original))
        elif index == min(edit['replace_indices']):
            final.extend(deepcopy(edit['claims']))
    final.extend(deepcopy(additions))
    for claim in final:
        if not isinstance(claim.get('claim_text'), str) or not claim['claim_text'].strip():
            raise PatchContractError('Empty claim')
        claim.setdefault('unresolved_context', [])
        if attribution:
            claim['claim_text'] = attribution + ', ' + claim['claim_text']
    return final


def canonicalize(task, patch, draft, attributions=None):
    attributions = attributions or {}
    if task == 'ec':
        original = draft['evidence_results']
        if [r['prompt_label'] for r in patch['evidence_results']] != [r['prompt_label'] for r in original]:
            raise PatchContractError('Missing, duplicate or reordered evidence labels')
        return {'evidence_results': [
            {'prompt_label': old['prompt_label'],
             'claims': apply_unit(old['claims'], new['edits'], new['additions'], attributions.get(old['prompt_label'], '')),
             'unextracted_spans': deepcopy(new['unextracted_spans'])}
            for old,new in zip(original, patch['evidence_results'])]}
    claims = apply_unit(draft['claims'], patch['edits'], patch['additions'])
    reason = patch['no_claim_reason']
    if bool(claims) != (reason is None):
        raise PatchContractError('No-claim reason contradicts patched claims')
    return {'claims': claims, 'no_claim_reason': reason, 'unextracted_spans': deepcopy(patch['unextracted_spans'])}
