"""Render source-bound claim groups without regenerating shared qualifiers.

Native model output remains authoritative for auditing what was extracted.
This module only composes declared context/stems with each atomic completion;
it does not infer facts, resolve references, or decide semantic correctness.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


class ContextContractError(ValueError):
    pass


def _text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ContextContractError(f'{field} must be a {"possibly empty " if allow_empty else "nonempty "}string')
    return value.strip()


def _strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ContextContractError(f'{field} must be a string array')
    return list(value)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def render_groups(groups: Any, attribution: str = '') -> list[dict[str, Any]]:
    if not isinstance(groups, list):
        raise ContextContractError('claim_groups must be an array')
    attribution = _text(attribution, 'source_attribution', allow_empty=True)
    rendered = []
    for group_index, group in enumerate(groups):
        if not isinstance(group, dict):
            raise ContextContractError('claim group must be an object')
        context = _text(group.get('context'), 'context', allow_empty=True)
        stem = _text(group.get('stem'), 'stem', allow_empty=True)
        shared_quotes = _strings(group.get('source_quotes'), 'group source_quotes')
        shared_unknowns = _strings(group.get('unresolved_context'), 'group unresolved_context')
        children = group.get('claims')
        if not isinstance(children, list) or not children:
            raise ContextContractError('each group must contain at least one claim')
        for child_index, child in enumerate(children):
            if not isinstance(child, dict):
                raise ContextContractError('claim completion must be an object')
            completion = _text(child.get('completion'), 'completion', allow_empty=True)
            if not stem and not completion:
                raise ContextContractError('stem and completion cannot both be empty')
            quotes = _strings(child.get('source_quotes'), 'claim source_quotes')
            unknowns = _strings(child.get('unresolved_context'), 'claim unresolved_context')
            prefixes = [v.rstrip(' ,;:') for v in (attribution, context) if v]
            claim_text = ', '.join(prefixes + [' '.join(v for v in (stem, completion) if v)])
            if not claim_text.endswith(('.', '?', '!')):
                claim_text += '.'
            rendered.append({
                'claim_text': claim_text,
                'source_quotes': _unique(shared_quotes + quotes),
                'unresolved_context': _unique(shared_unknowns + unknowns),
                'context_resolutions': [],
                'context_binding': {
                    'group_index': group_index, 'child_index': child_index,
                    'source_attribution': attribution, 'context': context,
                    'stem': stem, 'completion': completion,
                },
            })
    return rendered


def canonicalize(task: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Return a separate legacy-compatible view, retaining the native groups."""
    if task == 'ec':
        results = payload.get('evidence_results')
        if not isinstance(results, list):
            raise ContextContractError('evidence_results must be an array')
        return {'evidence_results': [
            {'prompt_label': r['prompt_label'],
             'claims': render_groups(r['claim_groups'], r['source_attribution']),
             'unextracted_spans': deepcopy(r['unextracted_spans'])}
            for r in results
        ]}
    if task == 'dc':
        claims = render_groups(payload.get('claim_groups'))
        reason = payload.get('no_claim_reason')
        if bool(claims) != (reason is None):
            raise ContextContractError('no_claim_reason must be null exactly when claims exist')
        return {'claims': claims, 'no_claim_reason': reason,
                'unextracted_spans': deepcopy(payload['unextracted_spans'])}
    raise ContextContractError(f'Unknown task: {task}')
