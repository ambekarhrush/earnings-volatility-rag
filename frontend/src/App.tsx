import { useEffect, useState } from "react";
import {
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Line,
  ComposedChart,
} from "recharts";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronRight,
  CircleHelp,
  FlaskConical,
  Layers3,
  Loader2,
  PanelLeft,
  Radio,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";
import { Button } from "./components/ui/button";
import type {
  Assumptions,
  Brief,
  EarningsProfile,
  Evidence,
  ModelRun,
  Request,
  Status,
} from "./types";

const money = (v: number | null, digits = 2) =>
  v === null
    ? "—"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: digits,
      }).format(v);
const pct = (v: number | null) => (v === null ? "—" : `${v.toFixed(1)}%`);
const stamp = (s: string) =>
  new Date(s).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(
    `/api/desk${path}`,
    body === undefined
      ? undefined
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Check your inputs: dates, quote spreads, and numeric ranges.",
    );
  return data;
}

export default function App() {
  const [brief, setBrief] = useState<Brief | null>(null);
  const [draft, setDraft] = useState<Request | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [tab, setTab] = useState("overview");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [run, setRun] = useState<ModelRun | null>(null);
  const [attachments, setAttachments] = useState<Evidence[]>([]);
  const [pubDate, setPubDate] = useState(new Date().toISOString().slice(0, 10));
  const [mobileNav, setMobileNav] = useState(false);
  useEffect(() => {
    Promise.all([api<Brief>("/initial"), api<Status>("/status")])
      .then(([b, s]) => {
        setBrief(b);
        setDraft(b.request);
        setStatus(s);
      })
      .catch((e) => setError(String(e.message)));
  }, []);
  const dirty =
    draft && brief && JSON.stringify(draft) !== JSON.stringify(brief.request);
  function update(key: keyof Request, value: unknown) {
    setDraft((d) => (d ? { ...d, [key]: value } : d));
  }
  function assumption(key: keyof Assumptions, value: number) {
    setDraft((d) =>
      d ? { ...d, assumptions: { ...d.assumptions, [key]: value } } : d,
    );
  }
  async function rebuild() {
    if (!draft) return;
    setBusy("brief");
    setError("");
    try {
      const b = await api<Brief>("/brief", draft);
      setBrief(b);
      setRun(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function generate() {
    if (!brief) return;
    setBusy("ai");
    setError("");
    try {
      setRun(await api<ModelRun>(`/snapshots/${brief.id}/opinion`, {}));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function attach(file: File) {
    setBusy("upload");
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("published", pubDate);
      const res = await fetch("/api/desk/documents", {
        method: "POST",
        body: form,
      });
      const doc = await res.json();
      if (!res.ok) throw new Error(doc.detail);
      setAttachments((a) => [...a.filter((x) => x.id !== doc.id), doc]);
      setDraft((d) =>
        d
          ? { ...d, document_ids: [...new Set([...d.document_ids, doc.id])] }
          : d,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function filing() {
    if (!draft) return;
    setBusy("filing");
    setError("");
    try {
      const doc = await api<Evidence>(`/filings/${draft.ticker}`, {});
      setAttachments((a) => [...a.filter((x) => x.id !== doc.id), doc]);
      setDraft((d) =>
        d
          ? { ...d, document_ids: [...new Set([...d.document_ids, doc.id])] }
          : d,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function fetchCalendar() {
    if (!draft) return;
    setBusy("calendar");
    setError("");
    try {
      const profile = await api<EarningsProfile>(`/earnings/${draft.ticker}`);
      if (profile.next_event) {
        update("event_date", profile.next_event.report_date);
        if (profile.next_event.session) {
          const sess = profile.next_event.session.toLowerCase();
          if (sess.includes("before") || sess.includes("bmo")) {
            update("event_session", "before_open");
          } else if (sess.includes("after") || sess.includes("amc")) {
            update("event_session", "after_close");
          }
        }
      } else {
        setError(
          `No upcoming earnings event found for ${draft.ticker} in Alpha Vantage calendar.`,
        );
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  function download() {
    if (!brief) return;
    const file = new Blob(
      [JSON.stringify({ ...brief, model_run: run }, null, 2)],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(file);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${brief.request.ticker}-${brief.market.feed}-brief.json`;
    a.click();
    URL.revokeObjectURL(url);
  }
  if (!brief || !draft)
    return (
      <main className="loading">
        <span className="brand-mark">e.</span>
        <h1>Opening your research desk</h1>
        <p>{error || "Loading the evidence pack and scenario engine…"}</p>
        {error && <Button onClick={() => location.reload()}>Try again</Button>}
      </main>
    );
  const analytics = brief.analytics,
    market = brief.market,
    opinion = run?.opinion ?? brief.opinion;
  const nav = [
    ["overview", "The brief", Layers3],
    ["evidence", "Evidence room", BookOpen],
    ["experiment", "Model lab", FlaskConical],
    ["method", "Method & sources", ShieldCheck],
  ] as const;
  return (
    <div className="shell">
      <aside className={`sidebar ${mobileNav ? "mobile-open" : ""}`}>
        <a href="/" className="brand">
          <span className="brand-mark">e.</span>
          <span>
            earnings<span className="brand-light">desk</span>
          </span>
        </a>
        <div className="workspace-tag">
          <span className="dot" /> PERSONAL RESEARCH WORKSPACE
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {nav.map(([id, label, Icon]) => (
            <button
              key={id}
              className={tab === id ? "active" : ""}
              onClick={() => {
                setTab(id);
                setMobileNav(false);
              }}
            >
              <Icon size={18} />
              {label}
              {tab === id && <ChevronRight size={15} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="small-label">RESEARCH QUESTION / 001</span>
          <p>
            What has to happen
            <br />
            to justify the premium?
          </p>
          <div className="mini-rule" />
          <span>
            Evidence first.
            <br />
            Your judgment, made explicit.
          </span>
        </div>
        <div className="sidebar-bottom">
          <span className="avatar">HR</span>
          <div>
            Personal desk<small>Local workspace · v0.2</small>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="mobile-menu"
              onClick={() => setMobileNav(!mobileNav)}
              aria-label="Toggle navigation"
            >
              <PanelLeft size={18} />
            </button>
            Research <ChevronRight size={13} />
            <strong>Earnings options</strong>
          </div>
          <div className="top-actions">
            <span className="connection">
              <span className={`dot ${status?.marketdata ? "" : "muted"}`} />
              {status?.marketdata
                ? "Provider key configured"
                : "Connect market data"}
            </span>
            <span className="connection">
              <span className={`dot ${status?.earnings ? "" : "muted"}`} />
              {status?.earnings ? "Calendar active" : "Calendar key optional"}
            </span>
            <a
              href="https://www.marketdata.app/pricing/"
              target="_blank"
              rel="noreferrer"
              title="Market-data free plan"
            >
              <CircleHelp size={17} />
            </a>
          </div>
        </header>
        <main className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">EARNINGS OPTIONS, MADE LEGIBLE</div>
              <h1>
                See the event.
                <br className="mobile-break" /> Understand the risk.
              </h1>
              <p>
                Evidence, market pricing and a conditional point of view—brought
                together in one precise brief.
              </p>
            </div>
            <Button variant="outline" onClick={download}>
              <ArrowDownToLine />
              Export brief
            </Button>
          </div>
          <section className="context-bar">
            <div className="company-mark">
              {brief.request.ticker.slice(0, 1)}
            </div>
            <div className="company">
              <strong>
                {brief.request.ticker} <span>{brief.company}</span>
              </strong>
              <small>EQUITY OPTIONS · USD · LONG STRADDLE</small>
            </div>
            <div className="context-separator" />
            <div className="event">
              <small>SCENARIO EVENT</small>
              <strong>
                {brief.request.event_date}{" "}
                <span>
                  {brief.request.event_session === "after_close"
                    ? "After close"
                    : "Before open"}
                </span>
              </strong>
            </div>
            <span
              className={`badge ${brief.event_note?.includes("Alpha Vantage") ? "neutral" : "amber"}`}
              title={brief.event_note}
            >
              {brief.event_note?.includes("Alpha Vantage")
                ? "Alpha Vantage calendar date"
                : "User-assumed date"}
            </span>
            <div className="context-spacer" />
            <span
              className={`badge ${market.feed === "hypothetical" ? "neutral" : "amber"}`}
            >
              <Radio size={12} />
              {market.feed === "hypothetical"
                ? "Hypothetical prices"
                : market.stale
                  ? "Delayed · stale snapshot"
                  : "24h+ delayed feed"}
            </span>
          </section>
          {error && (
            <div role="alert" className="error-message">
              {error}
              <button onClick={() => setError("")} aria-label="Dismiss error">
                ×
              </button>
            </div>
          )}
          {dirty && (
            <div className="pending" role="status">
              Inputs changed. The charts still show the last built snapshot.
              <Button size="sm" onClick={rebuild} disabled={!!busy}>
                Apply changes <ArrowRight />
              </Button>
            </div>
          )}
          <div className="tab-strip" role="tablist">
            {nav.map(([id, label]) => (
              <button
                key={id}
                role="tab"
                aria-selected={tab === id}
                onClick={() => setTab(id)}
                className={tab === id ? "selected" : ""}
              >
                {label}
                {id === "evidence" && <span>{brief.evidence.length}</span>}
              </button>
            ))}
            <span className="snapshot-stamp">
              {market.feed === "hypothetical" ? "Built" : "Quote as of"}{" "}
              {stamp(analytics.quote_at)}
            </span>
          </div>
          {tab === "overview" && (
            <>
              <section className="metric-grid">
                <Metric
                  label="STRADDLE MOVE PROXY"
                  value={`±${analytics.implied_move_pct.toFixed(2)}%`}
                  detail={`${money(analytics.midpoint_straddle)} midpoint · whole expiry`}
                  accent
                />
                <Metric
                  label="PURCHASE PREMIUM"
                  value={money(analytics.ask_straddle)}
                  detail="Per share · buying both legs at ask"
                />
                <Metric
                  label="MAXIMUM LOSS"
                  value={money(analytics.max_loss)}
                  detail={`${brief.request.assumptions.contracts} straddle(s) · 100 shares each · fees included`}
                />
                <Metric
                  label="EXPIRY BREAKEVENS"
                  value={`${money(analytics.breakeven_low, 1)} / ${money(analytics.breakeven_high, 1)}`}
                  detail="Opening costs included"
                  compact
                />
              </section>
              <div className="dashboard-grid">
                <section className="panel payoff">
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">01 / THE TRADE</span>
                      <h2>The shape of your risk</h2>
                      <p>
                        A long straddle needs movement. Direction alone is not
                        enough.
                      </p>
                    </div>
                    <span className="badge neutral">
                      {market.feed === "hypothetical"
                        ? "Scenario"
                        : "Dated quotes"}
                    </span>
                  </div>
                  <div className="chart-legend">
                    <span>
                      <i className="legend-line green" />
                      At expiry
                    </span>
                    <span>
                      <i className="legend-line dashed" />
                      After event · {brief.request.assumptions.iv_crush_pct}% IV
                      reduction
                    </span>
                  </div>
                  <div className="chart-box">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart
                        data={analytics.curve}
                        margin={{ top: 15, right: 20, left: 10, bottom: 8 }}
                      >
                        <defs>
                          <linearGradient
                            id="payoff-fill"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                          >
                            <stop
                              offset="0%"
                              stopColor="#2997ff"
                              stopOpacity={0.2}
                            />
                            <stop
                              offset="100%"
                              stopColor="#2997ff"
                              stopOpacity={0}
                            />
                          </linearGradient>
                        </defs>
                        <CartesianGrid
                          vertical={false}
                          stroke="#e5e9e2"
                          strokeDasharray="3 4"
                        />
                        <XAxis
                          dataKey="move_pct"
                          type="number"
                          domain={["dataMin", "dataMax"]}
                          tickFormatter={(v) => `${v > 0 ? "+" : ""}${v}%`}
                          tickLine={false}
                          axisLine={false}
                          tick={{ fontSize: 11, fill: "#758077" }}
                        />
                        <YAxis
                          tickFormatter={(v) => `$${v}`}
                          tickLine={false}
                          axisLine={false}
                          tick={{ fontSize: 11, fill: "#758077" }}
                          width={60}
                        />
                        <Tooltip
                          contentStyle={{
                            border: "1px solid #dbe3d9",
                            borderRadius: 10,
                            fontSize: 12,
                          }}
                          formatter={(v, name) => [
                            money(Number(v)),
                            name === "expiry_pnl" ? "At expiry" : "After event",
                          ]}
                          labelFormatter={(v) =>
                            `Stock move: ${Number(v).toFixed(1)}%`
                          }
                        />
                        <ReferenceLine
                          y={0}
                          stroke="#8d9c91"
                          strokeDasharray="5 4"
                        />
                        <ReferenceLine x={0} stroke="#d8e0d6" />
                        <Area
                          type="linear"
                          dataKey="expiry_pnl"
                          stroke="#0071e3"
                          strokeWidth={2.5}
                          fill="url(#payoff-fill)"
                          isAnimationActive={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="post_event_pnl"
                          stroke="#bf5af2"
                          strokeDasharray="5 5"
                          strokeWidth={2}
                          dot={false}
                          isAnimationActive={false}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="chart-caption">
                    <span>P&amp;L across the selected contracts</span>
                    <span>
                      Underlying move relative to {money(market.spot)}
                    </span>
                  </div>
                  <div className="chart-insight">
                    <Activity size={18} />
                    <p>{analytics.pricing_read}</p>
                  </div>
                </section>
                <section className="panel opinion">
                  <div className="panel-heading">
                    <span className="eyebrow">02 / THE DESK VIEW</span>
                    <span className="badge green">
                      {run ? "AI interpretation" : "Editorial view"}
                    </span>
                  </div>
                  <h2>{opinion.headline}</h2>
                  {opinion.rationale.map((claim, i) => (
                    <div className="opinion-claim" key={i}>
                      <p>{claim.text}</p>
                      <div>
                        {claim.evidence_ids.map((id) => (
                          <button
                            key={id}
                            className="source-ref"
                            onClick={() => setTab("evidence")}
                          >
                            {id === "CALCULATIONS"
                              ? "Calculations"
                              : id.replace("AAPL-Q3-", "")}{" "}
                            <ArrowUpRight size={10} />
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                  <div className="opinion-section">
                    <span className="small-label">THE COUNTERARGUMENT</span>
                    <p>{opinion.counterargument}</p>
                  </div>
                  <div className="opinion-section">
                    <span className="small-label">WHAT CHANGES THIS VIEW</span>
                    <p>{opinion.invalidation}</p>
                  </div>
                  <div className="opinion-footer">
                    <span>
                      <span className="dot muted" />
                      {opinion.confidence} conviction · conditional
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={generate}
                      disabled={!!busy || !!dirty || !status?.ai_model}
                    >
                      {busy === "ai" ? (
                        <Loader2 className="spin" />
                      ) : (
                        <Sparkles />
                      )}
                      Generate AI view
                    </Button>
                  </div>
                  {!status?.ai_model && (
                    <small className="hint">
                      Configure a model and key in .env to generate an AI view.
                    </small>
                  )}
                </section>
              </div>
              <div className="lower-grid">
                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">03 / SCENARIO LAB</span>
                      <h2>What if the volatility disappears?</h2>
                    </div>
                    <FlaskConical size={20} />
                  </div>
                  <p className="muted-copy">
                    Post-event theoretical P&amp;L · change both the stock move
                    and the IV drop.
                  </p>
                  <div className="heatmap-wrap">
                    <table className="heatmap">
                      <thead>
                        <tr>
                          <th>IV reduction ↓</th>
                          {[-10, -5, 0, 5, 10].map((v) => (
                            <th key={v}>
                              {v > 0 ? "+" : ""}
                              {v}% move
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {analytics.heatmap.map((row) => (
                          <tr key={row.crush_pct}>
                            <th>{row.crush_pct}%</th>
                            {row.scenarios.map((cell) => (
                              <td
                                key={cell.move_pct}
                                className={
                                  cell.post_event_pnl === null
                                    ? ""
                                    : cell.post_event_pnl >= 0
                                      ? "gain"
                                      : "loss"
                                }
                              >
                                {money(cell.post_event_pnl, 0)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="panel-footnote">
                    European pricing approximation · sale spreads and exit fees
                    excluded
                  </div>
                </section>
                <section className="panel thesis-panel">
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">04 / YOUR JUDGMENT</span>
                      <h2>Write the disagreement.</h2>
                    </div>
                    <BookOpen size={20} />
                  </div>
                  <label htmlFor="thesis" className="muted-copy">
                    What do you believe that might not be in the price?
                  </label>
                  <textarea
                    id="thesis"
                    value={draft.thesis}
                    maxLength={4000}
                    onChange={(e) => update("thesis", e.target.value)}
                    rows={4}
                  />
                  <div className="thesis-bottom">
                    <span>User assumption · included in the evidence pack</span>
                    <Button
                      size="sm"
                      onClick={rebuild}
                      disabled={!!busy || !dirty}
                    >
                      Update brief <ArrowRight />
                    </Button>
                  </div>
                </section>
              </div>
              <section className="panel controls">
                <div className="panel-heading">
                  <div>
                    <span className="eyebrow">BUILD YOUR SCENARIO</span>
                    <h2>Make the assumptions explicit.</h2>
                  </div>
                  <Settings2 size={20} />
                </div>
                <div className="input-grid">
                  <label>
                    Ticker
                    <div className="icon-input">
                      <Search size={14} />
                      <input
                        aria-label="Ticker"
                        value={draft.ticker}
                        onChange={(e) =>
                          update("ticker", e.target.value.toUpperCase())
                        }
                        maxLength={10}
                      />
                    </div>
                  </label>
                  <label>
                    Quote source
                    <select
                      value={draft.mode}
                      onChange={(e) => update("mode", e.target.value)}
                    >
                      <option value="hypothetical">Hypothetical inputs</option>
                      <option value="marketdata">
                        MarketData.app · delayed
                      </option>
                    </select>
                  </label>
                  <div className="field-group">
                    <div className="label-with-action">
                      <label htmlFor="assumed-earnings-date">
                        Assumed earnings date
                      </label>
                      {status?.earnings && (
                        <button
                          type="button"
                          className="link-button"
                          disabled={busy === "calendar"}
                          onClick={fetchCalendar}
                          title="Fetch scheduled earnings date from Alpha Vantage"
                        >
                          {busy === "calendar"
                            ? "Checking…"
                            : "Lookup calendar"}
                        </button>
                      )}
                    </div>
                    <input
                      id="assumed-earnings-date"
                      type="date"
                      value={draft.event_date}
                      onChange={(e) => update("event_date", e.target.value)}
                    />
                  </div>
                  <label>
                    Session
                    <select
                      value={draft.event_session}
                      onChange={(e) => update("event_session", e.target.value)}
                    >
                      <option value="after_close">After close</option>
                      <option value="before_open">Before open</option>
                    </select>
                  </label>
                  <label>
                    Option expiration
                    <input
                      type="date"
                      value={draft.expiration}
                      onChange={(e) => update("expiration", e.target.value)}
                    />
                  </label>
                  <NumberInput
                    label="Straddle contracts"
                    value={draft.assumptions.contracts}
                    min={1}
                    max={1000}
                    step={1}
                    change={(v) => assumption("contracts", v)}
                  />
                </div>
                {draft.mode === "hypothetical" && (
                  <div className="input-grid hypothetical-inputs">
                    {(
                      [
                        ["spot", "Assumed stock price"],
                        ["strike", "Strike"],
                        ["call_bid", "Call bid"],
                        ["call_ask", "Call ask"],
                        ["put_bid", "Put bid"],
                        ["put_ask", "Put ask"],
                      ] as const
                    ).map(([key, label]) => (
                      <NumberInput
                        key={key}
                        label={label}
                        value={draft.assumptions[key]}
                        min={0.01}
                        change={(v) => assumption(key, v)}
                      />
                    ))}
                  </div>
                )}
                <div className="slider-grid">
                  <label>
                    Expected absolute move{" "}
                    <strong>±{draft.assumptions.expected_move_pct}%</strong>
                    <input
                      type="range"
                      min={0}
                      max={30}
                      step={0.5}
                      value={draft.assumptions.expected_move_pct}
                      onChange={(e) =>
                        assumption("expected_move_pct", +e.target.value)
                      }
                    />
                  </label>
                  <label>
                    Post-event IV reduction{" "}
                    <strong>{draft.assumptions.iv_crush_pct}%</strong>
                    <input
                      type="range"
                      min={0}
                      max={95}
                      step={5}
                      value={draft.assumptions.iv_crush_pct}
                      onChange={(e) =>
                        assumption("iv_crush_pct", +e.target.value)
                      }
                    />
                  </label>
                  <NumberInput
                    label="Assumed risk-free rate (%)"
                    value={draft.assumptions.rate * 100}
                    min={-5}
                    max={30}
                    step={0.1}
                    change={(v) => assumption("rate", v / 100)}
                  />
                  <NumberInput
                    label="Assumed dividend yield (%)"
                    value={draft.assumptions.dividend_yield * 100}
                    min={0}
                    max={30}
                    step={0.1}
                    change={(v) => assumption("dividend_yield", v / 100)}
                  />
                  <NumberInput
                    label="Opening fee / contract ($)"
                    value={draft.assumptions.fee_per_contract}
                    min={0}
                    max={100}
                    change={(v) => assumption("fee_per_contract", v)}
                  />
                </div>
                <div className="controls-bottom">
                  <p>
                    {draft.mode === "marketdata"
                      ? "Requires your free provider API key. One expiry and nearest strike only; repeated requests cached for 15 minutes."
                      : "Illustrative $100 reference price. These input values are not Apple market quotes."}
                  </p>
                  <Button onClick={rebuild} disabled={!!busy}>
                    {busy === "brief" ? (
                      <Loader2 className="spin" />
                    ) : (
                      <RefreshCw />
                    )}
                    {draft.mode === "marketdata"
                      ? "Fetch quotes & build"
                      : "Recalculate scenario"}
                  </Button>
                </div>
              </section>
            </>
          )}
          {tab === "evidence" && (
            <>
              <div className="section-intro">
                <h2>Follow every claim to its source.</h2>
                <p>
                  The issuer evidence is real. Scenario prices and dates remain
                  explicit assumptions until verified.
                </p>
              </div>
              {brief.fundamentals.length > 0 && (
                <div className="fundamentals">
                  {brief.fundamentals.map((m) => (
                    <Metric
                      key={m.label}
                      label={m.label}
                      value={m.value}
                      detail={m.detail}
                    />
                  ))}
                </div>
              )}
              {brief.earnings?.history && brief.earnings.history.length > 0 && (
                <div className="panel quote-table" style={{ margin: "20px 0" }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 12,
                    }}
                  >
                    <div>
                      <span className="badge neutral">Alpha Vantage</span>
                      <strong style={{ marginLeft: 8 }}>
                        Quarterly EPS surprise history
                      </strong>
                    </div>
                    <small className="timestamp">
                      Fetched {brief.earnings.fetched_at}
                    </small>
                  </div>
                  <table>
                    <thead>
                      <tr>
                        <th>Quarter ending</th>
                        <th>Reported date</th>
                        <th>Reported EPS</th>
                        <th>Estimated EPS</th>
                        <th>Surprise</th>
                        <th>Surprise %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {brief.earnings.history.map((row) => (
                        <tr key={row.fiscal_date_ending}>
                          <td>{row.fiscal_date_ending}</td>
                          <td>{row.reported_date}</td>
                          <td>
                            {row.reported_eps !== null
                              ? `$${row.reported_eps.toFixed(2)}`
                              : "—"}
                          </td>
                          <td>
                            {row.estimated_eps !== null
                              ? `$${row.estimated_eps.toFixed(2)}`
                              : "—"}
                          </td>
                          <td
                            style={{
                              color:
                                row.surprise !== null && row.surprise >= 0
                                  ? "#174c3d"
                                  : "#c62828",
                              fontWeight: 500,
                            }}
                          >
                            {row.surprise !== null
                              ? `${row.surprise >= 0 ? "+" : ""}${row.surprise.toFixed(2)}`
                              : "—"}
                          </td>
                          <td
                            style={{
                              color:
                                row.surprise_percentage !== null &&
                                row.surprise_percentage >= 0
                                  ? "#174c3d"
                                  : "#c62828",
                              fontWeight: 500,
                            }}
                          >
                            {pct(row.surprise_percentage)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <small
                    style={{ color: "#657369", display: "block", marginTop: 8 }}
                  >
                    {brief.earnings.note}
                  </small>
                </div>
              )}
              <div className="evidence-grid">
                {brief.evidence.map((e, i) => (
                  <article className="panel evidence-card" key={e.id}>
                    <div className="panel-heading">
                      <span className="source-number">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="badge neutral">
                        {e.kind === "issuer" ? "Issuer disclosure" : e.kind}
                      </span>
                    </div>
                    <h2>{e.title}</h2>
                    <p>
                      {e.text.length > 1200
                        ? e.text.slice(0, 1200) + "…"
                        : e.text}
                    </p>
                    <div className="evidence-bottom">
                      <small>
                        {e.source}
                        <br />
                        {e.published} · {e.id}
                      </small>
                      {e.url && (
                        <a
                          href={e.url}
                          target="_blank"
                          rel="noreferrer"
                          aria-label={`Open source for ${e.title}`}
                        >
                          <ArrowUpRight size={18} />
                        </a>
                      )}
                    </div>
                    {e.text.length > 1200 && (
                      <details>
                        <summary>Read extracted text</summary>
                        <pre>{e.text}</pre>
                      </details>
                    )}
                  </article>
                ))}
              </div>
              <section className="panel ingestion">
                <h2>Expand the evidence pack</h2>
                <p>
                  Attach a filing or your own source document, then apply
                  changes to rebuild the brief. Uploaded content is kept in this
                  local session.
                </p>
                <div className="ingestion-actions">
                  <label>
                    Document publication date
                    <input
                      type="date"
                      value={pubDate}
                      onChange={(e) => setPubDate(e.target.value)}
                    />
                  </label>
                  <label className="upload-button">
                    <Upload size={16} />
                    {busy === "upload"
                      ? "Extracting…"
                      : "Upload PDF / TXT / MD"}
                    <input
                      disabled={!!busy}
                      type="file"
                      accept=".pdf,.txt,.md"
                      onChange={(e) => {
                        if (e.target.files?.[0]) void attach(e.target.files[0]);
                        e.target.value = "";
                      }}
                    />
                  </label>
                  <Button
                    variant="outline"
                    disabled={!!busy || !status?.edgar}
                    onClick={filing}
                  >
                    {busy === "filing" ? (
                      <Loader2 className="spin" />
                    ) : (
                      <BookOpen />
                    )}
                    Fetch latest SEC filing
                  </Button>
                </div>
                <small className="hint">
                  SEC retrieval requires EDGAR_IDENTITY. PDF extraction requires
                  the optional Docling dependency; text works immediately.
                </small>
                {attachments.map((e) => (
                  <div className="attachment" key={e.id}>
                    <Check size={14} />
                    {e.title}
                    <small>{e.id}</small>
                    <button
                      aria-label={`Remove ${e.title}`}
                      onClick={() => {
                        setAttachments((a) => a.filter((x) => x.id !== e.id));
                        update(
                          "document_ids",
                          draft.document_ids.filter((id) => id !== e.id),
                        );
                      }}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </section>
            </>
          )}
          {tab === "experiment" && (
            <>
              <div className="section-intro">
                <h2>Same evidence. Different minds.</h2>
                <p>
                  Compare model interpretations against a frozen evidence pack.
                  The experiment starts with measurements, not a leaderboard.
                </p>
              </div>
              <section className="panel experiment-panel">
                <div className="panel-heading">
                  <div>
                    <span className="eyebrow">WEEKLY EXPERIMENT / 01</span>
                    <h2>Can a model challenge the margin thesis?</h2>
                  </div>
                  <span className="badge neutral">
                    {run ? "Single run recorded" : "Comparison not run"}
                  </span>
                </div>
                <p>
                  Use Promptfoo to run OpenAI, Anthropic and DeepSeek against
                  this exact pack. Check schema, citation IDs, missing-data
                  behavior, numerical claims, latency and tokens. Citation-ID
                  validity alone does not establish factual support.
                </p>
                <div className="experiment-cards">
                  {["OpenAI", "Anthropic", "DeepSeek"].map((name) => (
                    <article key={name}>
                      <FlaskConical size={22} />
                      <h3>{name}</h3>
                      <span>Configure model + API key</span>
                      <strong>Not benchmarked</strong>
                    </article>
                  ))}
                </div>
                <div className="hash-row">
                  <span>EVIDENCE SHA-256</span>
                  <code>{brief.experiment.evidence_hash}</code>
                </div>
                <pre className="code-block">
                  uv run python -m evals.export_pack --snapshot {brief.id}
                  {"\n"}cd evals && npm ci{"\n"}npm run compare
                </pre>
                <Button
                  onClick={generate}
                  disabled={!!busy || !!dirty || !status?.ai_model}
                >
                  <Sparkles />
                  Generate one configured model view
                </Button>
                {run && (
                  <div className="run-result">
                    <h3>{run.model}</h3>
                    <p>
                      {run.latency_seconds}s · {run.input_tokens} input tokens ·{" "}
                      {run.output_tokens} output tokens
                    </p>
                    <p>{run.validation}</p>
                    <small>
                      Cost not estimated. This run is not a comparative
                      benchmark.
                    </small>
                  </div>
                )}
              </section>
            </>
          )}
          {tab === "method" && (
            <>
              <div className="section-intro">
                <h2>Inspect the machinery.</h2>
                <p>
                  A small, auditable workflow. Every result comes with the
                  assumptions that produced it.
                </p>
              </div>
              <section className="panel method-panel">
                <div className="pipeline">
                  {[
                    "Evidence + dated quotes",
                    "Validated snapshot",
                    "Python calculations",
                    "Cited interpretation",
                  ].map((s, i) => (
                    <div key={s}>
                      <span>0{i + 1}</span>
                      <strong>{s}</strong>
                      {i < 3 && <ArrowRight size={16} />}
                    </div>
                  ))}
                </div>
                <h2>Calculation notes</h2>
                <ul>
                  {analytics.limitations.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
                <h2>Market-data quality</h2>
                <ul>
                  {market.warnings.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
                <div className="quote-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Contract</th>
                        <th>Bid</th>
                        <th>Ask</th>
                        <th>Model IV</th>
                        <th>Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(["call", "put"] as const).map((side) => (
                        <tr key={side}>
                          <td>{market[side].symbol}</td>
                          <td>{money(market[side].bid)}</td>
                          <td>{money(market[side].ask)}</td>
                          <td>
                            {pct(
                              analytics[`iv_${side}`] === null
                                ? null
                                : analytics[`iv_${side}`]! * 100,
                            )}
                          </td>
                          <td>{stamp(market[side].quote_time)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <h2>Connections</h2>
                <p>{status?.feed_note}</p>
                <p>
                  MarketData.app:{" "}
                  {status?.marketdata
                    ? "key configured (entitlement checked on fetch)"
                    : "key needed"}{" "}
                  · EdgarTools:{" "}
                  {status?.edgar ? "identity configured" : "identity needed"} ·
                  Model: {status?.ai_model || "not configured"}
                </p>
                <p className="method-links">
                  <a
                    href="https://www.marketdata.app/docs/api/options/chain/"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Provider API <ArrowUpRight size={13} />
                  </a>
                  <a
                    href="https://edgartools.readthedocs.io/"
                    target="_blank"
                    rel="noreferrer"
                  >
                    EdgarTools <ArrowUpRight size={13} />
                  </a>
                  <a href="/docs" target="_blank" rel="noreferrer">
                    This API <ArrowUpRight size={13} />
                  </a>
                </p>
              </section>
            </>
          )}
          <footer>
            <span>
              <ShieldCheck size={14} /> Research interpretation · hypothetical
              trades · verify event timing
            </span>
            <span>
              Snapshot {brief.id.slice(0, 8)}{" "}
              <span className="footer-dot">·</span>{" "}
              {market.feed === "hypothetical"
                ? `${brief.evidence.length ? "Sourced evidence" : "No company evidence"} / assumed prices`
                : `${brief.evidence.length ? "Sourced evidence" : "No company evidence"} / delayed quotes`}
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  detail,
  accent = false,
  compact = false,
}: {
  label: string;
  value: string;
  detail: string;
  accent?: boolean;
  compact?: boolean;
}) {
  return (
    <article className={`metric ${accent ? "accent" : ""}`}>
      <span className="small-label">{label}</span>
      <strong className={compact ? "compact" : ""}>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}
function NumberInput({
  label,
  value,
  min = 0,
  max = 100000,
  step = 0.01,
  change,
}: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  change: (v: number) => void;
}) {
  return (
    <label>
      {label}
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={Number.isFinite(value) ? value : ""}
        onChange={(e) => change(e.target.valueAsNumber)}
      />
    </label>
  );
}
