# RepoLens AI Evaluation Report (v0.5.0)

- Timestamp: `20260313T171631Z`
- Total cases: `10`
- Passed cases: `3`
- Pass rate: `0.3`
- Refusal correctness: `0.9`
- Citation correctness: `0.6`
- Relevance proxy score: `0.758`
- Avg latency: `211.25 ms`

## Per Mode

- `onboarding`: pass `2/6` (0.333)
- `debug`: pass `1/2` (0.5)
- `release`: pass `0/2` (0.0)

## Per Category

- `small_python_app`: pass `1/3` (0.333)
- `api_service`: pass `0/2` (0.0)
- `frontend_or_ui_repo`: pass `1/1` (1.0)
- `infra_or_devops_repo`: pass `0/2` (0.0)
- `noisy_large_repo`: pass `1/1` (1.0)
- `ml_repo`: pass `0/1` (0.0)

## Failures

- `setup_local_run` (onboarding/small_python_app): LLM answer generation requires GEMINI_API_KEY.
- `architecture_overview` (onboarding/small_python_app): LLM answer generation requires GEMINI_API_KEY.
- `api_health_endpoint` (onboarding/api_service): LLM answer generation requires GEMINI_API_KEY.
- `debug_trace_flow` (debug/api_service): LLM answer generation requires GEMINI_API_KEY.
- `deployment_artifacts` (release/infra_or_devops_repo): LLM answer generation requires GEMINI_API_KEY.
- `release_summary` (release/infra_or_devops_repo): LLM answer generation requires GEMINI_API_KEY.
- `ml_training_refusal` (onboarding/ml_repo): LLM answer generation requires GEMINI_API_KEY.
