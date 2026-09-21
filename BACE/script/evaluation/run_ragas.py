"""Native RAGAS Faithfulness with captured statement and entailment outputs."""

import asyncio

from external_evaluation import run


def make_evaluator(config, transport):
    from ragas.llms.base import InstructorBaseRagasLLM
    from ragas.metrics.collections import Faithfulness

    class ResponsesLLM(InstructorBaseRagasLLM):
        def __init__(self):
            self.outputs = {}

        def generate(self, prompt, response_model):
            def validate(raw):
                value = response_model.model_validate_json(raw)
                if response_model.__name__ == 'StatementGeneratorOutput':
                    if not value.statements:
                        raise ValueError('RAGAS returned no extracted statements')
                elif response_model.__name__ == 'NLIStatementOutput':
                    expected = self.outputs.get('StatementGeneratorOutput', {}).get('statements', [])
                    if len(value.statements) != len(expected) or any(s != v.statement for s, v in zip(expected, value.statements)):
                        raise ValueError('RAGAS verdict statements differ from extracted statements')
                    if any(v.verdict not in (0, 1) for v in value.statements):
                        raise ValueError('RAGAS verdict must be 0 or 1')
                return {'statement_count':len(value.statements)}
            result = transport.complete(prompt, response_model.__name__, response_model=response_model, validator=validate)
            self.outputs[response_model.__name__] = result.model_dump(mode='json')
            return result

        async def agenerate(self, prompt, response_model):
            return await asyncio.to_thread(self.generate, prompt, response_model)

    llm = ResponsesLLM()
    metric = Faithfulness(llm=llm)

    def evaluate(case):
        llm.outputs = {}
        score = asyncio.run(metric.ascore(user_input=case['query'], response=case['response'], retrieved_contexts=case['contexts']))
        statements = llm.outputs.get('StatementGeneratorOutput', {}).get('statements', [])
        verdicts = llm.outputs.get('NLIStatementOutput', {}).get('statements', [])
        if statements and (len(statements) != len(verdicts) or any(s != v['statement'] for s, v in zip(statements, verdicts))):
            raise ValueError('RAGAS verdict statements differ from extracted statements')
        if any(v['verdict'] not in (0, 1) for v in verdicts):
            raise ValueError('RAGAS verdict must be 0 or 1')
        return {'score': score.value, 'claim_count': len(statements),
                'claims': [{'claim_index': i, 'claim': s, 'supported': bool(v['verdict']), 'reason': v['reason']} for i, (s, v) in enumerate(zip(statements, verdicts))],
                'native_outputs': llm.outputs, 'context_unit': 'all_evidence_cards_joined',
                'parse_audit': {'statement_verdict_alignment': 'passed'}}
    return evaluate


if __name__ == '__main__':
    run('ragas', make_evaluator)
