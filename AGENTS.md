# Working agreement

Strategize before changes: inspect current code, identify the decision, record scope and checks in docs/build-strategy.md, then implement.

Never label assumptions as observed market data. Prices and calculations stay outside model output. Preserve timestamps and evidence IDs. Read provider terms before adding feeds. Keep credentials in environment variables. No paid model calls on dashboard GET requests. Test changed backend behavior and build the frontend after frontend changes.
