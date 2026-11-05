# Earnings Volatility & Options Desk

*Local application with hypothetical default quotes · Prepared 5 November 2026*

## The research question

Can issuer evidence, an event scenario and an auditable option payoff live in one research workspace?

## Approach

React/FastAPI combines a curated AAPL evidence pack, optional SEC ingestion, delayed quotes and Black-Scholes scenarios. A saved snapshot separates assumptions, deterministic numbers and model opinion; citation IDs and structured output are checked.

## Evidence and result

The example includes a sourced AAPL evidence pack and hypothetical prices. A previous authenticated AAPL retrieval is documented. On 5 November 2026, 42 backend tests passed and one failed because its October event fixture had expired; provider benchmarks remain unrun.

## Scope and limitations

Initial editorial analysis is authored, not a model run. Source/citation validity does not prove factual support. Event variance, historical move distributions, American exercise and exit frictions are incomplete. Storage and deployment are single-user local. The date-sensitive test failure must be addressed for a current automated demonstration.

## Explore the project

Build frontend, start uvicorn on port 8001, inspect the hypothetical pack, edit assumptions and export a snapshot. The live provider and paid-model paths are optional.

## Sources and evidence

[tests/test_earnings.py](../tests/test_earnings.py) · [docs/architecture.md](../docs/architecture.md) · [evals/README.md](../evals/README.md)

---

Hrush Ambekar · Research snapshot reviewed 5 November 2026. See linked source files for full methodology, figures and reproducibility.
