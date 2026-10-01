# Strategy before implementation · v0.2

Give a discretionary trader a sourced earnings view, observable option prices, and a transparent hypothetical trade. Start with Apple research. Support other US tickers for quotes without substituting Apple evidence.

## Decisions
- MarketData.app Free Forever is the primary provider: 100 daily credits, 24h+ delayed actual options, with a no-card trial. Ask for one expiry and nearest strike; cache requests. Authenticated AAPL retrieval and the running application API were verified on October 1, 2026, including quote timestamps, IV recovery, payoff bounds and cache reuse. Raw provider data is not committed.
- Cboe scraping rejected because its terms prohibit automated extraction. Alpaca's free modified indicative quotes do not fit actual option-pricing analysis. Tradier remains a possible future adapter.
- EdgarTools retrieves filings using the configured contact identity; Docling extracts uploaded documents.
- Authenticated SEC retrieval was verified on October 1, 2026 through both the library and running API using Apple's July 31, 2026 10-Q. The result retained the accession number, filing date, `sec.gov` URL, selected passages, and SHA-256 hash. Raw filing text is not committed.
- Pydantic AI enforces structured, cited opinion. Models are configurable; paid model calls require an explicit Generate action.
- DeepSeek Flash is the default opinion model because it is currently the lowest-priced DeepSeek API model and supports JSON output, tools, and the Responses API. OpenAI and Anthropic remain optional comparison providers rather than runtime requirements.
- Alpha Vantage EARNINGS_CALENDAR and quarterly EARNINGS provide optional upcoming report dates and historical EPS surprises. 6-hour process cache protects free tier rate limits (25 req/day, 5 req/min). If unavailable, user-supplied assumptions remain the fallback.
- React, shadcn/ui and Recharts form the desk. Promptfoo compares configured models using one frozen evidence pack.

## Output contract
Real evidence is dated and linked. Hypothetical prices stay labelled throughout exports. Missing credentials never trigger fake live data. Pricing runs in Python. Opinion states evidence, counterargument and invalidation. Earnings dates are verified through Alpha Vantage when configured, or marked user assumptions unless independently confirmed.

## Sequence and verification
Typed snapshot and quote validation → ingestion → analytics/opinion → dashboard → evaluation and visual README. Test bad/stale timestamps, crossed quotes, event/expiry ordering, missing keys, citations, API failure and numerical bounds. Alpha Vantage contract tests cover calendar CSV parsing, EPS surprise extraction, rate limit responses, cache TTL and ticker validation. Build React and inspect responsive behavior where browser access exists. Report contract tests separately from authenticated live tests.
