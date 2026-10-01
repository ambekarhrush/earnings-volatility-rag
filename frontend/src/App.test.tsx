import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import type { Brief } from "./types";
import research from "../../app/data/AAPL-research.json";

// DOM workflow tests deliberately stub charts: chart rendering needs an actual browser.
vi.mock("recharts", () =>
  Object.fromEntries(
    [
      "Area",
      "CartesianGrid",
      "XAxis",
      "YAxis",
      "Tooltip",
      "ResponsiveContainer",
      "ReferenceLine",
      "Line",
      "ComposedChart",
    ].map((name) => [name, () => null]),
  ),
);

const fixture: Brief = {
  id: "test-snapshot",
  company: "Apple Inc.",
  created_at: "2026-10-01T16:00:00Z",
  request: {
    ticker: "AAPL",
    mode: "hypothetical",
    event_date: "2026-10-29",
    event_session: "after_close",
    expiration: "2026-10-30",
    thesis: "Check recurring margin.",
    document_ids: [],
    assumptions: {
      spot: 100,
      strike: 100,
      call_bid: 4.1,
      call_ask: 4.3,
      put_bid: 3.7,
      put_ask: 3.9,
      rate: 0.04,
      dividend_yield: 0,
      iv_crush_pct: 45,
      expected_move_pct: 6,
      contracts: 1,
      fee_per_contract: 0.65,
    },
  },
  market: {
    spot: 100,
    spot_time: "2026-10-01T16:00:00Z",
    fetched_at: "2026-10-01T16:00:00Z",
    expiration: "2026-10-30",
    provider: "User assumptions",
    feed: "hypothetical",
    stale: false,
    warnings: ["Hypothetical inputs"],
    call: {
      symbol: "HYPOTHETICAL-CALL",
      strike: 100,
      bid: 4.1,
      ask: 4.3,
      quote_time: "2026-10-01T16:00:00Z",
      volume: 0,
      open_interest: 0,
    },
    put: {
      symbol: "HYPOTHETICAL-PUT",
      strike: 100,
      bid: 3.7,
      ask: 3.9,
      quote_time: "2026-10-01T16:00:00Z",
      volume: 0,
      open_interest: 0,
    },
  },
  analytics: {
    midpoint_straddle: 8,
    ask_straddle: 8.2,
    implied_move_pct: 8,
    max_loss: 821.3,
    breakeven_low: 91.787,
    breakeven_high: 108.213,
    iv_call: 0.36,
    iv_put: 0.35,
    spread_pct: 4.88,
    curve: [],
    heatmap: [],
    assumed_move_scenarios: [],
    reaction_at: "2026-10-30T09:30:00-04:00",
    quote_at: "2026-10-01T16:00:00Z",
    pricing_read: "Buying the ask includes opening fees.",
    limitations: ["European approximation."],
  },
  evidence: research.evidence,
  opinion: research.editorial,
  opinion_mode: "editorial",
  fundamentals: research.metrics,
  event_note: "User-assumed date.",
  experiment: { status: "not_run", evidence_hash: "fixture-hash" },
};
const fetched = vi.fn();
beforeEach(() => {
  fetched.mockReset();
  fetched.mockImplementation(async (url: string, options?: RequestInit) => {
    const json = url.endsWith("/status")
      ? {
          marketdata: false,
          edgar: false,
          earnings: true,
          ai_model: null,
          feed_note: "24h+ delayed",
        }
      : url.includes("/earnings/")
        ? {
            symbol: "AAPL",
            provider: "Alpha Vantage",
            fetched_at: "2026-10-01",
            next_event: {
              symbol: "AAPL",
              name: "Apple Inc",
              report_date: "2026-11-05",
              estimate: 1.6,
              currency: "USD",
              session: "after close",
            },
            history: [
              {
                fiscal_date_ending: "2026-06-30",
                reported_date: "2026-07-30",
                reported_eps: 1.4,
                estimated_eps: 1.35,
                surprise: 0.05,
                surprise_percentage: 3.7,
              },
            ],
            note: "Verify with IR.",
          }
        : url.endsWith("/brief")
          ? {
              ...fixture,
              request: JSON.parse(String(options?.body)),
              analytics: { ...fixture.analytics, max_loss: 1642.6 },
            }
          : fixture;
    return { ok: true, json: async () => structuredClone(json) };
  });
  vi.stubGlobal("fetch", fetched);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("research desk interactions", () => {
  it("labels assumptions and makes no model call on load", async () => {
    render(<App />);
    await screen.findByText("Hypothetical prices");
    expect(screen.getByText("±8.00%")).toBeTruthy();
    expect(
      (
        screen.getByRole("button", {
          name: "Generate AI view",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    expect(fetched.mock.calls.every(([url]) => !url.includes("/opinion"))).toBe(
      true,
    );
  });
  it("keeps calculated values on the old snapshot until changes are applied", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Hypothetical prices");
    const contracts = screen.getByRole("spinbutton", {
      name: "Straddle contracts",
    });
    await user.clear(contracts);
    await user.type(contracts, "2");
    expect(screen.getByText(/1 straddle\(s\)/)).toBeTruthy();
    expect(screen.getByText(/Inputs changed/)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Apply changes" }));
    await waitFor(() =>
      expect(screen.queryByText(/Inputs changed/)).toBeNull(),
    );
    expect(screen.getByText(/2 straddle\(s\)/)).toBeTruthy();
    expect(screen.getByText("$1,642.60")).toBeTruthy();
  });
  it("opens real source links in the evidence room", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Hypothetical prices");
    await user.click(screen.getByRole("tab", { name: /Evidence room/ }));
    expect(
      screen
        .getByRole("link", { name: "Open source for Growth remains strong" })
        .getAttribute("href"),
    ).toContain("apple.com/newsroom");
    expect(screen.getByText("Expand the evidence pack")).toBeTruthy();
  });
  it("preserves the previous brief when provider fetching fails", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Hypothetical prices");
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Quote source" }),
      "marketdata",
    );
    fetched.mockImplementationOnce(async () => ({
      ok: false,
      json: async () => ({ detail: "Add MARKETDATA_TOKEN to .env." }),
    }));
    await user.click(
      screen.getByRole("button", { name: "Fetch quotes & build" }),
    );
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByText("Hypothetical prices")).toBeTruthy();
    expect(screen.getByText("±8.00%")).toBeTruthy();
  });
  it("looks up upcoming earnings date and fills draft when button clicked", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Hypothetical prices");
    const lookupBtn = await screen.findByText("Lookup calendar");
    await user.click(lookupBtn);
    await waitFor(() => {
      const dateInput = screen.getByLabelText(
        /Assumed earnings date/,
      ) as HTMLInputElement;
      expect(dateInput.value).toBe("2026-11-05");
    });
    expect(screen.getByText(/Inputs changed/)).toBeTruthy();
  });
  it("renders quarterly EPS surprise history when present in evidence room", async () => {
    const user = userEvent.setup();
    const fixtureWithEarnings: Brief = {
      ...fixture,
      earnings: {
        symbol: "AAPL",
        provider: "Alpha Vantage",
        fetched_at: "2026-10-01",
        next_event: null,
        history: [
          {
            fiscal_date_ending: "2026-06-30",
            reported_date: "2026-07-30",
            reported_eps: 1.4,
            estimated_eps: 1.35,
            surprise: 0.05,
            surprise_percentage: 3.7,
          },
        ],
        note: "IR confirmation recommended.",
      },
    };
    fetched.mockImplementation(async (url: string) => {
      const json = url.endsWith("/status")
        ? {
            marketdata: false,
            edgar: false,
            earnings: true,
            ai_model: null,
            feed_note: "",
          }
        : fixtureWithEarnings;
      return { ok: true, json: async () => structuredClone(json) };
    });
    render(<App />);
    await screen.findByText("Hypothetical prices");
    await user.click(screen.getByRole("tab", { name: /Evidence room/ }));
    expect(
      await screen.findByText("Quarterly EPS surprise history"),
    ).toBeTruthy();
    expect(screen.getByText("+0.05")).toBeTruthy();
    expect(screen.getByText("3.7%")).toBeTruthy();
    expect(screen.getByText("$1.40")).toBeTruthy();
  });
});
