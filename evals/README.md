# Week 1 experiment

All providers receive the same saved pack, same schema and same instructions. Variants remove evidence or add an untrusted instruction. Pydantic AI enforces output schema and valid citation IDs; Promptfoo records comparative results. No scores have been claimed or fabricated.

1. Set `DEEPSEEK_API_KEY` and `EVAL_DEEPSEEK_MODEL=deepseek-flash` in the root `.env`.
2. Start the backend on port 8001. From the repository root, run `uv run python -m evals.export_pack` (or pass the snapshot ID displayed in the UI).
3. `cd evals && npm ci`
4. Run `npm run compare` for DeepSeek only. The runner uses the root `.venv` Python; set `PROMPTFOO_PYTHON` only to override it. Missing model IDs or keys stop the run before model calls.
5. Later, add OpenAI and Anthropic credentials and run `npm run compare:all` for the full three-provider experiment.
5. `npm run view` to inspect results. Comparisons make paid model calls; dashboard browsing does not.

Human scoring is still required for source support, financial reasoning and numeric fidelity: 0 = wrong, 1 = incomplete, 2 = accurate and useful. Record missing risks, invented consensus, hypothetical/live confusion, and assertions unsupported by citations. Citation IDs alone do not verify that a cited source entails a claim. Do not publish a winner until every model's results use the same pack hash and configuration. Dollar cost is unmeasured until pricing is configured; token usage and latency are measured.
