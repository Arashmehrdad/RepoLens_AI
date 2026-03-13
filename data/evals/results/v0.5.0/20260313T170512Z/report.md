# RepoLens AI Evaluation Report (v0.5.0)

- Timestamp: `20260313T170512Z`
- Total cases: `10`
- Passed cases: `2`
- Pass rate: `0.2`
- Refusal correctness: `0.8`
- Citation correctness: `0.5`
- Relevance proxy score: `0.658`
- Avg latency: `1731.22 ms`

## Per Mode

- `onboarding`: pass `1/6` (0.167)
- `debug`: pass `1/2` (0.5)
- `release`: pass `0/2` (0.0)

## Per Category

- `small_python_app`: pass `1/3` (0.333)
- `api_service`: pass `0/2` (0.0)
- `frontend_or_ui_repo`: pass `0/1` (0.0)
- `infra_or_devops_repo`: pass `0/2` (0.0)
- `noisy_large_repo`: pass `1/1` (1.0)
- `ml_repo`: pass `0/1` (0.0)

## Failures

- `setup_local_run` (onboarding/small_python_app): LLM answer generation failed.
- `architecture_overview` (onboarding/small_python_app): LLM answer generation failed.
- `api_health_endpoint` (onboarding/api_service): LLM answer generation failed.
- `debug_trace_flow` (debug/api_service): LLM answer generation failed.
- `ui_api_base_url` (onboarding/frontend_or_ui_repo): refusal/citation/confidence mismatch
- `deployment_artifacts` (release/infra_or_devops_repo): LLM answer generation failed.
- `release_summary` (release/infra_or_devops_repo): LLM answer generation failed.
- `ml_training_refusal` (onboarding/ml_repo): LLM answer generation failed.
