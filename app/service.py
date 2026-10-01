from app.analytics import black_scholes, historical_stats, implied_move, scenario_table
from app.models import Brief, EarningsCase
from app.synthesis import synthesize


def build_brief(case: EarningsCase) -> Brief:
    move_dollars, move_pct = implied_move(case)
    median_move, max_move = historical_stats(case)
    years = case.days_to_expiry / 365
    call_value = black_scholes(
        spot=case.spot,
        strike=case.call.strike,
        years=years,
        rate=case.risk_free_rate,
        volatility=case.implied_volatility,
        kind="call",
    )
    put_value = black_scholes(
        spot=case.spot,
        strike=case.put.strike,
        years=years,
        rate=case.risk_free_rate,
        volatility=case.implied_volatility,
        kind="put",
    )
    width = max(round(move_pct), 1)
    moves = sorted({-2 * width, -width, 0, width, 2 * width})
    synthesis, mode = synthesize(case, move_pct, median_move)
    return Brief(
        case=case,
        implied_move_dollars=round(move_dollars, 2),
        implied_move_pct=round(move_pct, 2),
        historical_median_abs_move_pct=round(median_move, 2),
        historical_max_abs_move_pct=round(max_move, 2),
        call_model_value=round(call_value, 2),
        put_model_value=round(put_value, 2),
        scenarios=scenario_table(case, moves),
        synthesis=synthesis,
        synthesis_mode=mode,
        limitations=[
            "The demo uses a synthetic, dated snapshot rather than live executable quotes.",
            "The simple straddle heuristic does not isolate the event variance from ordinary volatility.",
            "Scenario P&L assumes expiry immediately after the event and excludes fees, spreads, and skew changes.",
            "The brief supports a decision; it does not predict the earnings outcome or recommend a trade.",
        ],
    )
