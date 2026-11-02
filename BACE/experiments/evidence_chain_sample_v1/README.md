# Sampled evidence-chain amendment

The author chose 90 complete disclosures: one per company and E/S/G stratum.
Read `PROTOCOL.md`, `selection.csv` and `plan.json` for the outcome-independent
selection, fixed inputs, exact counts, missingness and inferential limits.
The interrupted full run is preserved separately. This version reuses selected
saved calls verbatim, never reruns recorded failures, and schedules only missing
calls from the frozen sample. No new extraction or prompt modification occurs.

Prepare and validate with the unchanged native environment:

```bash
PYTHONDONTWRITEBYTECODE=1 BACE/.venv/bin/python -B BACE/experiments/evidence_chain_sample_v1/prepare.py
PYTHONDONTWRITEBYTECODE=1 BACE/.venv/bin/python -B BACE/experiments/evidence_chain_sample_v1/check_replay.py
PYTHONDONTWRITEBYTECODE=1 BACE/.venv/bin/python -B BACE/experiments/evidence_chain_sample_v1/verify_sample.py
```

After the checks pass, run the sample and its local postprocessor:

```bash
PYTHONDONTWRITEBYTECODE=1 BACE/.venv/bin/python -B BACE/experiments/evidence_chain_sample_v1/run.py --mode full --workers 48
PYTHONDONTWRITEBYTECODE=1 BACE/.venv/bin/python -B BACE/experiments/evidence_chain_sample_v1/finish.py
```

`full` here means all jobs in the 90-disclosure sample, not the original frame.
The two commands run as separate processes. Only resume after verifying the
recorded process identity and that the previous worker is no longer running.
SIGTERM or SIGINT stops new scheduling and retains in-flight results before exit.

```bash
watch -n 10 cat /home/muwang/master_thesis/BACE/results/evidence_chain_sample_v1/status.json
```

The postprocessor audits raw records and calculates saved-data statistics;
notebook integration and independent review are separate completion stages.
