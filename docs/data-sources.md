# Data and configuration

## MarketData.app

Primary source: [option-chain API documentation](https://www.marketdata.app/docs/api/options/chain/). The adapter requests `/v1/options/chain/{ticker}/` with `expiration` and `strikeLimit=1`, sending the token in the authorization header. The selected call and put must have matching standard OCC roots and strikes. Underlying price comes from the same chain snapshot, not an unrelated live stock quote.

Store your token in `MARKETDATA_TOKEN` in the root `.env`; restart the server. Credential-presence flags do not prove account entitlement. A missing key, invalid entitlement, no valid pair, exhausted credits or malformed response produces a visible error. Authenticated AAPL retrieval was verified through the running application on October 1, 2026. The returned delayed snapshot passed quote parsing, IV and payoff-bound checks; a repeated request reused the cache. This verifies that account and query, not every ticker or entitlement.

Per the provider's October 1, 2026 [pricing](https://www.marketdata.app/pricing/), Free Forever includes 100 daily credits and 24h-delayed options. The [no-card Starter trial](https://www.marketdata.app/docs/account/plans/starter-trial/) also has 24h-delayed options, not 15-minute quotes. Entitlements and pricing can change. The adapter conservatively labels all returned data delayed; it does not claim a paid account's real-time entitlement.

The small query and 15-minute process-local cache conserve credits; there is no background poller. Restarts clear the cache. Multiple server workers do not share the cache. This is not a global quota-enforcement system.

## Alpha Vantage

Primary source: [Alpha Vantage Documentation](https://www.alphavantage.co/documentation/). The adapter queries `EARNINGS_CALENDAR` (horizon=12month) for upcoming announcement dates and sessions, and `EARNINGS` for up to 12 quarters of reported vs. estimated EPS and surprise history.

Store your API key in `ALPHA_VANTAGE_API_KEY` in the root `.env`. A 6-hour process-local LRU cache protects free-tier budgets (25 requests/day, 5 requests/minute). When the key is missing or the provider hits rate limits, the application returns a clear error and falls back to user-assumed dates without interrupting pricing calculations. Dates and estimates remain indicative and subject to issuer IR confirmation.

## Issuer research

The curated pack cites Apple's [July 30, 2026 earnings release](https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/). It is a dated editorial pack, not an automatically refreshed feed. No vendor consensus, historical event returns or confirmed future earnings date has been inserted.

## EdgarTools and SEC

Set `EDGAR_IDENTITY` to your name and contact email following [EdgarTools guidance](https://edgartools.readthedocs.io/en/latest/quick-guide/). The integration fetches the latest 10-Q/10-K, selects bounded excerpts and records the accession, filing date, source URL and document hash. Do not use a fictitious identity. Network failures leave existing research intact.

Live retrieval was verified on October 1, 2026 using Apple's July 31, 2026 10-Q (accession `0000320193-26-000020`). Both the direct integration and `/api/desk/filings/AAPL` returned the SEC URL, 16,491 selected characters and a complete SHA-256 hash. The retrieved filing is held in memory and is not committed to the repository.

## Docling

The optional `documents` dependency enables local text-based PDF extraction. The app passes bytes through `DocumentStream`, disables OCR, exports Markdown and caps the excerpt. First use can download model weights and be slower. Text and Markdown use the lightweight built-in path. Publication dates on uploads are supplied by the user. Files are not retained on disk by the app; selected text is held in memory and sent to the model only when a view is generated.

## Model providers

`AI_MODEL` is an explicit Pydantic AI provider/model identifier. The default is `deepseek:deepseek-flash`. Pydantic AI accepts this provider/model combination through its OpenAI-compatible DeepSeek provider. Provider keys stay in `.env`; OpenAI and Anthropic are optional comparison providers.

DeepSeek's official pricing page was checked on October 1, 2026. It identifies `deepseek-flash` as DeepSeek-V4.1-Flash, supports JSON output, tool calls and the Responses API, and prices it below DeepSeek V4 Pro. Prices vary between peak/off-peak and cache-hit/cache-miss input, so the application does not hard-code a dollar estimate. The API documentation also warns that JSON mode can occasionally return empty content; the application therefore validates output and preserves the existing editorial brief when generation fails.

References: [DeepSeek models and pricing](https://api-docs.deepseek.com/quick_start/pricing), [DeepSeek JSON output](https://api-docs.deepseek.com/guides/json_mode), [Pydantic AI agents](https://ai.pydantic.dev/agents/), [Promptfoo Python provider](https://www.promptfoo.dev/docs/providers/python/).
