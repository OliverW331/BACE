# Evidence-chain sensitivity

The three current conditions share targets, judge criteria, model settings and
the native BACE support-set schema. Only the supplied evidence units vary.
Historical BACE judgments are a descriptive reference. Read `PROTOCOL.md` for
the paired estimands, missingness rules and limits of mechanism attribution.

Preparation uses saved artifacts only:

```bash
PYTHONDONTWRITEBYTECODE=1 BACE/.venv/bin/python -B BACE/experiments/evidence_chain_v1/prepare_inputs.py
PYTHONDONTWRITEBYTECODE=1 BACE/.venv/bin/python -B BACE/experiments/evidence_chain_v1/freeze.py --criterion bace
PYTHONDONTWRITEBYTECODE=1 BACE/.venv/bin/python -B BACE/experiments/evidence_chain_v1/check_replay.py
```

Run the frozen technical gate, then the full cohort:

```bash
PYTHONDONTWRITEBYTECODE=1 BACE/.venv/bin/python -B BACE/experiments/evidence_chain_v1/run.py --mode pilot --workers 8
PYTHONDONTWRITEBYTECODE=1 BACE/.venv/bin/python -B BACE/experiments/evidence_chain_v1/run.py --mode full --workers 48
```

The runner uses a separate lock and durable call journals. Resume with the same
full command only after verifying that its recorded process is no longer live.
Recorded successes and exhausted failures are never retried on resume.

Monitor without affecting execution:

```bash
watch -n 10 cat /home/muwang/master_thesis/BACE/results/evidence_chain_v1/status.json
```

`input_plan.json` and `results/evidence_chain_v1/qa/input_sizes.csv` record exact
inventory and character counts. Character counts are not tokenizer counts or
price estimates. No source text is truncated. Review packets and final statistics
must distinguish automated disagreements from independently validated losses.
