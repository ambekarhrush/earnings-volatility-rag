# Earnings Desk product brief

The user is a discretionary equity-options trader preparing for one earnings event. The completed workflow is: inspect dated evidence, write a thesis, obtain a valid quote pair or supply explicit hypothetical inputs, compare conditional P&L, challenge the view and export the brief.

## Acceptance criteria

1. No-key startup displays real company evidence with labelled hypothetical prices.
2. Real data mode either returns a dated provider observation or a useful error; it never fabricates a quote.
3. Charts and table share deterministic ask-based entry and fee conventions.
4. Editing inputs does not silently mix old outputs with new assumptions.
5. AI generation is explicit and references a frozen pack, with checked citation IDs.
6. User evidence can be attached without being treated as system instructions.
7. Exports retain source dates, assumptions and data-mode labels.
8. The comparison harness evaluates all providers using identical pack hashes.

## Deliberate scope

One long standard-contract straddle. Real curated research starts with AAPL; other companies require their own evidence. Historical event distributions, consensus and trade execution remain outside this release; upcoming dates can be looked up via Alpha Vantage or entered as explicit user assumptions. Quote timestamp does not imply executability. Every opinion is conditional and states what would overturn it.

## Practitioner review

Ask a trader: is the pricing convention clear, which disclosure changes the view, which necessary expectation is missing, and what would prevent using the result before earnings? Record concrete misses and update the same test cases.
