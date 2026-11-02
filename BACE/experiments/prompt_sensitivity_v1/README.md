# Support-prompt sensitivity run

See [PROTOCOL.md](PROTOCOL.md) for the estimands, intervention, repeat sample,
missingness and interpretation limits. [plan.json](plan.json) contains the
verified cohort, exact input caches and selections. [freeze.json](freeze.json)
was created before new model calls. The two original-to-adapted prompt diffs
are [RAGAS-style](ragas_style.diff) and [RAGChecker-style](ragchecker_style.diff).

The inputs cover 1,798 disclosures, 30 companies and 94,955 DCs per full
condition. Of these, 1,911 have no candidate EC and remain deterministic
unsupported. Each full condition schedules 93,044 model jobs, before native
retries. The repeat control contains 60 disclosures, 3,106 DCs and 3,048 model
jobs. These are planned counts from `plan.json`, not completed observations.

Run commands from the repository root, using the existing environment without
installing packages:

```bash
PYTHONDONTWRITEBYTECODE=1 BACE/.venv/bin/python -B BACE/experiments/prompt_sensitivity_v1/check_replay.py
PYTHONDONTWRITEBYTECODE=1 BACE/.venv/bin/python -B BACE/experiments/prompt_sensitivity_v1/run.py --mode pilot --workers 8
PYTHONDONTWRITEBYTECODE=1 BACE/.venv/bin/python -B BACE/experiments/prompt_sensitivity_v1/run.py --mode full --workers 48
```

`prepare.py` is intentionally one-shot. Do not run it again after freezing.
The full run requires a passed technical pilot. The replay uses the native
support executor, parser, Responses transport and retry rules. Credentials
are loaded by that executor as for the authorized main experiment; they are
never copied into analysis artifacts. The deployment must match the original.

Calls are appended under `BACE/results/prompt_sensitivity_v1/runs/`. A local
status JSON records the PID and process marker, but process liveness must be
verified against the actual process. Successful or exhausted failed jobs are
not retried by restarting the scheduler; this prevents response selection and
unbounded repeated retries. Interrupted jobs with no recorded outcome remain
pending. Persistent deployment/authentication/transport errors stop scheduling.

The notebook imports `evaluator_gap_prompt_sensitivity.py` and reads saved
results only. While a full run is incomplete it displays completion counts
and an explicit pending status, without partial primary score estimates.
Final exported analyses live under
`BACE/analysis/outputs/evaluator_gap/prompt_sensitivity/`.
