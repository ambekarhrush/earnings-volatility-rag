export type Assumptions = {
  spot: number;
  strike: number;
  call_bid: number;
  call_ask: number;
  put_bid: number;
  put_ask: number;
  rate: number;
  dividend_yield: number;
  iv_crush_pct: number;
  expected_move_pct: number;
  contracts: number;
  fee_per_contract: number;
};
export type Request = {
  ticker: string;
  mode: "hypothetical" | "marketdata";
  event_date: string;
  event_session: "after_close" | "before_open";
  expiration: string;
  thesis: string;
  assumptions: Assumptions;
  document_ids: string[];
};
export type Evidence = {
  id: string;
  title: string;
  text: string;
  source: string;
  published: string;
  url: string | null;
  kind: string;
};
export type Opinion = {
  headline: string;
  stance: string;
  rationale: { text: string; evidence_ids: string[] }[];
  counterargument: string;
  invalidation: string;
  questions: string[];
  confidence: string;
};
export type Scenario = {
  move_pct: number;
  spot: number;
  expiry_pnl: number;
  post_event_pnl: number | null;
};
export type Quote = {
  symbol: string;
  strike: number;
  bid: number;
  ask: number;
  quote_time: string;
  volume: number;
  open_interest: number;
};
export type Brief = {
  id: string;
  company: string;
  request: Request;
  market: {
    spot: number;
    spot_time: string;
    fetched_at: string;
    expiration: string;
    provider: string;
    feed: string;
    stale: boolean;
    warnings: string[];
    call: Quote;
    put: Quote;
  };
  analytics: {
    midpoint_straddle: number;
    ask_straddle: number;
    implied_move_pct: number;
    max_loss: number;
    breakeven_low: number | null;
    breakeven_high: number;
    iv_call: number | null;
    iv_put: number | null;
    spread_pct: number;
    curve: Scenario[];
    heatmap: { crush_pct: number; scenarios: Scenario[] }[];
    assumed_move_scenarios: Scenario[];
    reaction_at: string;
    quote_at: string;
    pricing_read: string;
    limitations: string[];
  };
  evidence: Evidence[];
  opinion: Opinion;
  opinion_mode: string;
  fundamentals: { label: string; value: string; detail: string }[];
  event_note: string;
  earnings?: EarningsProfile;
  experiment: { status: string; evidence_hash: string };
  created_at: string;
};
export type EarningsEvent = {
  symbol: string;
  name: string;
  report_date: string;
  fiscal_date_ending: string | null;
  estimate: number | null;
  currency: string | null;
  session: string | null;
};
export type EarningsResult = {
  fiscal_date_ending: string;
  reported_date: string;
  reported_eps: number | null;
  estimated_eps: number | null;
  surprise: number | null;
  surprise_percentage: number | null;
};
export type EarningsProfile = {
  symbol: string;
  provider: string;
  fetched_at: string;
  next_event: EarningsEvent | null;
  history: EarningsResult[];
  note: string;
};
export type Status = {
  marketdata: boolean;
  edgar: boolean;
  earnings: boolean;
  ai_model: string | null;
  feed_note: string;
};
export type ModelRun = {
  opinion: Opinion;
  model: string;
  latency_seconds: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number | null;
  validation: string;
  snapshot_id: string;
  evidence_hash: string;
};
