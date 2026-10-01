"""European approximation for transparent hypothetical scenarios, in USD."""

from __future__ import annotations

import math
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.desk_models import DeskRequest, MarketSnapshot

NY = ZoneInfo("America/New_York")


def _normal_cdf(x: float) -> float:
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def price(
    spot: float,
    strike: float,
    years: float,
    rate: float,
    vol: float,
    kind: str,
    dividend: float = 0.0,
) -> float:
    if years <= 0:
        return max(spot - strike, 0.0) if kind == "call" else max(strike - spot, 0.0)
    if min(spot, strike, vol) <= 0:
        raise ValueError("Spot, strike and volatility must be positive.")
    d1 = (math.log(spot / strike) + (rate - dividend + vol * vol / 2.0) * years) / (
        vol * math.sqrt(years)
    )
    d2 = d1 - vol * math.sqrt(years)
    s, k = spot * math.exp(-dividend * years), strike * math.exp(-rate * years)
    return (
        s * _normal_cdf(d1) - k * _normal_cdf(d2)
        if kind == "call"
        else k * _normal_cdf(-d2) - s * _normal_cdf(-d1)
    )


def solve_iv(
    premium: float,
    spot: float,
    strike: float,
    years: float,
    rate: float,
    kind: str,
    dividend: float = 0.0,
) -> float:
    low, high = 0.0001, 5.0
    if years <= 0 or not (
        price(spot, strike, years, rate, low, kind, dividend)
        < premium
        < price(spot, strike, years, rate, high, kind, dividend)
    ):
        raise ValueError(
            "Premium is outside model bounds; IV and post-event valuation unavailable."
        )
    for _ in range(80):
        mid = (low + high) / 2.0
        if price(spot, strike, years, rate, mid, kind, dividend) < premium:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def analyze(snapshot: MarketSnapshot, request: DeskRequest) -> dict:
    a, call, put = request.assumptions, snapshot.call, snapshot.put
    expiry = datetime.combine(request.expiration, time(16), NY)
    reaction_date = request.event_date + timedelta(days=request.event_session == "after_close")
    while reaction_date.weekday() >= 5:
        reaction_date += timedelta(days=1)
    reaction = datetime.combine(reaction_date, time(9, 30), NY)
    if reaction >= expiry:
        raise ValueError("Selected expiry precedes the assumed earnings reaction.")
    quote_time = min(snapshot.spot_time, call.quote_time, put.quote_time)
    if reaction <= quote_time:
        raise ValueError(
            "Snapshot is after the event reaction; it cannot support a pre-earnings brief."
        )
    years = (expiry - quote_time).total_seconds() / (365 * 86400)
    remaining = (expiry - reaction).total_seconds() / (365 * 86400)
    mid = (call.bid + call.ask + put.bid + put.ask) / 2
    debit = call.ask + put.ask
    fees = 2 * a.fee_per_contract / 100
    entry = debit + fees
    scale = 100 * a.contracts
    ivs = {}
    errors = []
    for leg in (call, put):
        try:
            ivs[leg.kind] = solve_iv(
                (leg.bid + leg.ask) / 2,
                snapshot.spot,
                leg.strike,
                years,
                a.rate,
                leg.kind,
                a.dividend_yield,
            )
        except ValueError as exc:
            ivs[leg.kind] = None
            errors.append(str(exc))
    width = min(60, max(12, mid / snapshot.spot * 250, a.expected_move_pct * 1.5))

    def value(move, crush):
        terminal = snapshot.spot * (1 + move / 100)
        expiry_pnl = (abs(terminal - call.strike) - entry) * scale
        post_pnl = None
        if all(v is not None for v in ivs.values()):
            post_value = sum(
                price(
                    terminal,
                    leg.strike,
                    remaining,
                    a.rate,
                    ivs[leg.kind] * (1 - crush / 100),
                    leg.kind,
                    a.dividend_yield,
                )
                for leg in (call, put)
            )
            post_pnl = round((post_value - entry) * scale, 2)
        return {
            "move_pct": round(move, 2),
            "spot": round(terminal, 2),
            "expiry_pnl": round(expiry_pnl, 2),
            "post_event_pnl": post_pnl,
        }

    curve = [value(-width + 2 * width * i / 80, a.iv_crush_pct) for i in range(81)]
    moves = [-10, -5, 0, 5, 10]
    heatmap = [
        {"crush_pct": crush, "scenarios": [value(move, crush) for move in moves]}
        for crush in [0, 25, 50, 75]
    ]
    low, high = call.strike - entry, call.strike + entry
    return {
        "midpoint_straddle": round(mid, 4),
        "ask_straddle": round(debit, 4),
        "implied_move_pct": round(mid / snapshot.spot * 100, 4),
        "max_loss": round(entry * scale, 2),
        "contracts": a.contracts,
        "breakeven_low": round(low, 4) if low > 0 else None,
        "breakeven_high": round(high, 4),
        "iv_call": ivs["call"],
        "iv_put": ivs["put"],
        "spread_pct": round((debit - call.bid - put.bid) / debit * 100, 2),
        "curve": curve,
        "heatmap": heatmap,
        "assumed_move_scenarios": [
            value(-a.expected_move_pct, a.iv_crush_pct),
            value(a.expected_move_pct, a.iv_crush_pct),
        ],
        "reaction_at": reaction.isoformat(),
        "quote_at": quote_time.isoformat(),
        "pricing_read": (
            f"Buying at the supplied asks risks ${entry * scale:,.2f} across {a.contracts} straddle(s). "
            f"The midpoint move proxy is {mid / snapshot.spot * 100:.2f}%. "
            f"Your assumed move is ±{a.expected_move_pct:.1f}%; inspect both outcomes against the breakevens."
        ),
        "limitations": list(dict.fromkeys(errors))
        + [
            "Expiry payoff includes opening fees and purchase at asks; post-event P&L uses theoretical mid-values, without exit fees or spreads.",
            "European Black–Scholes approximation: constant dividend yield; no American early exercise, discrete dividends or volatility-skew dynamics.",
            "IV crush and stock move are user scenarios, not forecasts. Straddle premium spans all time to expiry, not just earnings.",
            "Event date is user-supplied. Reaction rolls weekends only; exchange holidays and early closes require manual review.",
            "No historical earnings-move distribution or consensus dataset is attached; no cheap/rich volatility conclusion is justified.",
        ],
    }
