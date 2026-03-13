# RepoLens AI Evaluation Report (v0.5.0)

- Timestamp: `20260313T170222Z`
- Total cases: `10`
- Passed cases: `4`
- Pass rate: `0.4`
- Refusal correctness: `0.8`
- Citation correctness: `0.5`
- Relevance proxy score: `0.733`
- Avg latency: `3371.03 ms`

## Per Mode

- `onboarding`: pass `3/6` (0.5)
- `debug`: pass `1/2` (0.5)
- `release`: pass `0/2` (0.0)

## Per Category

- `small_python_app`: pass `2/3` (0.667)
- `api_service`: pass `1/2` (0.5)
- `frontend_or_ui_repo`: pass `0/1` (0.0)
- `infra_or_devops_repo`: pass `0/2` (0.0)
- `noisy_large_repo`: pass `1/1` (1.0)
- `ml_repo`: pass `0/1` (0.0)

## Failures

- `architecture_overview` (onboarding/small_python_app): LLM output was not safely grounded enough to return directly.
- `debug_trace_flow` (debug/api_service): refusal/citation/confidence mismatch
- `ui_api_base_url` (onboarding/frontend_or_ui_repo): refusal/citation/confidence mismatch
- `deployment_artifacts` (release/infra_or_devops_repo): refusal/citation/confidence mismatch
- `release_summary` (release/infra_or_devops_repo): LLM output was not safely grounded enough to return directly.
- `ml_training_refusal` (onboarding/ml_repo): LLM answer generation failed.
