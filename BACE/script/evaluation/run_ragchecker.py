"""Native RAGChecker faithfulness with a logged Azure Responses transport."""

from concurrent.futures import ThreadPoolExecutor

from external_evaluation import run


def make_evaluator(config, transport):
    from ragchecker import RAGChecker, RAGResults
    from ragchecker.container import RAGResult, RetrievedDoc
    from refchecker.checker.checker_prompts import JOINT_CHECKING_PROMPT_Q
    from refchecker.extractor.extractor_prompts import LLM_TRIPLET_EXTRACTION_PROMPT_Q

    settings = config['frameworks']['ragchecker']
    evaluator = RAGChecker(extractor_name=config['judge']['model_id'], checker_name=config['judge']['model_id'],
                           extractor_max_new_tokens=config['runtime']['max_output_tokens'],
                           batch_size_checker=settings['batch_size'], joint_check=True,
                           joint_check_num=settings['joint_check_num'])

    def evaluate(case):
        stage = 'response_claim_extraction'
        expected_by_prompt = {}
        parse_audits = []

        def validate_extraction(raw):
            claims = evaluator.extractor.parse_claims(raw, '###')
            if not claims:
                raise ValueError('Native RAGChecker extractor returned no parseable claims')
            return {'claim_count': len(claims)}

        def request(prompt):
            def validate_labels(raw):
                labels = evaluator.checker._parse_joint_checking_labels(raw)
                expected = expected_by_prompt[prompt]
                audit = {'expected_labels': expected, 'parsed_labels': labels,
                         'native_padding_needed': max(0, expected - len(labels)),
                         'native_truncation_needed': max(0, len(labels) - expected)}
                parse_audits.append(audit)
                if len(labels) != expected:
                    raise ValueError(f'Native label count mismatch: expected {expected}, got {len(labels)}')
                return audit
            return transport.complete(prompt, stage, validator=validate_extraction if stage == 'response_claim_extraction' else validate_labels)

        def batch(prompts):
            with ThreadPoolExecutor(max_workers=config['runtime']['concurrency']) as pool:
                return list(pool.map(request, prompts))

        evaluator.custom_llm_api_func = batch
        record = RAGResult(query_id=case['generation_case_id'], query=case['query'], gt_answer='',
                           response=case['response'], retrieved_context=[RetrievedDoc(doc_id=eid, text=text) for eid, text in zip(case['evidence_ids'], case['contexts'])])
        # Use the native extractor explicitly so label counts can be checked before
        # RefChecker silently pads/truncates them. evaluate() reuses these claims.
        evaluator.extract_claims([record], extract_type='response')
        stage = 'retrieved2response'
        for context in case['contexts']:
            for start in range(0, len(record.response_claims), settings['joint_check_num']):
                group = record.response_claims[start:start + settings['joint_check_num']]
                claim_text = '\n'.join(f'("{c[0]}", "{c[1]}", "{c[2]}")' for c in group)
                prompt = JOINT_CHECKING_PROMPT_Q.replace('[QUESTION]', case['query']).replace('[REFERENCE]', context).replace('[CLAIMS]', claim_text)
                expected_by_prompt[prompt] = len(group)
        evaluator.evaluate(RAGResults(results=[record]), metrics=['faithfulness'])
        claims = []
        for index, (claim, verdicts) in enumerate(zip(record.response_claims, record.retrieved2response)):
            claims.append({'claim_index': index, 'claim': claim, 'supported': 'Entailment' in verdicts,
                           'evidence_verdicts': dict(zip(case['evidence_ids'], verdicts))})
        return {'score': record.metrics['faithfulness'], 'claim_count': len(claims), 'claims': claims,
                'native_result': record.to_dict(), 'context_unit': 'individual_evidence_card',
                'parse_audit': {'checks': len(expected_by_prompt), 'label_mismatch_attempts': sum(bool(a['native_padding_needed'] or a['native_truncation_needed']) for a in parse_audits)},
                'native_prompts': {'extraction': LLM_TRIPLET_EXTRACTION_PROMPT_Q, 'checking': JOINT_CHECKING_PROMPT_Q}}
    return evaluate


if __name__ == '__main__':
    run('ragchecker', make_evaluator)
