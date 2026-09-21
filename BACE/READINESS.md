# BACE readiness report

Ready for main experiment: **True**

Preparation, the original 12-case engineering pilot and bounded runtime validations. This acceptance check does not execute the main study. Formal human annotations have not been performed.

## Gates

- frozen_inputs_and_environment: true
- complete_experimental_matrix: {"companies": 30, "sectors": 11, "years": 5, "tasks": 12, "cases": 1800}
- evidence_windows_and_mapping_corrections: {"packages": 150, "canonical_cards": 931448, "excluded_mapping_errors": 4, "unreadable_cards_quarantined": 44, "cross_company_or_future_leaks": 0}
- source_provenance: {"hashed_pdf_sources": 401, "freshly_verified_reused_reports": 32, "all_pages_processed": true, "raw_data_unchanged": true}
- vector_integrity: {"rows": 931448, "dimensions": 3072}
- automated_tests: true
- bounded_claim_execution: {"paired_jobs_per_stage": 8, "stages": {"candidates": {"serial_seconds": 80.776, "parallel_seconds": 46.042, "observed_speedup": 1.754}, "support": {"serial_seconds": 17.778, "parallel_seconds": 17.07, "observed_speedup": 1.041}, "diagnosis": {"serial_seconds": 21.394, "parallel_seconds": 13.691, "observed_speedup": 1.563}}, "scope": "Historical timing under the preceding two-worker implementation; not a speedup estimate for the current scheduler."}
- parallel_execution: {"case_workers": 16, "independent_branches": ["BACE", "RAGChecker", "RAGAS"], "live_stage_timings": {"candidates": 22.715, "support": 14.157, "diagnosis": 8.127}, "scope": "24 live integration jobs and offline concurrency/cancellation tests; no whole-study speedup estimate."}
- real_pilot_and_human_materials: {"real_cases": 12, "task_coverage": 12, "native_evaluators": ["BACE", "RAGChecker 0.1.9", "RAGAS 0.4.3"], "formal_human_annotations": 0}

## Unresolved critical items

None.

## Research limitations

- Native judges and claim extraction remain fallible; engineering acceptance is not evaluator validity.
- Only four previously verified CSV mapping errors are excluded; other extracted metrics have not all been independently audited.
- PDF evidence uses report-year windows, not historical publication-date cutoffs; source labels preserve measurement-year distinctions.
- Sampling conditions define the 250-company complete-source subpopulation; inference to all 600 companies requires accounting for availability selection.

## Main command

```bash
/home/muwang/master_thesis/BACE/.venv/bin/python /home/muwang/master_thesis/BACE/run.py main
```

The same command resumes completed stages after validating their recorded hashes.
