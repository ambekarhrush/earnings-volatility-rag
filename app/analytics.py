import math
from statistics import median

from app.models import EarningsCase, ScenarioRow


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def black_scholes(
    *, spot: float, strike: float, years: float, rate: float, volatility: float, kind: str
) -> float:
    if years <= 0:
        return max(spot - strike, 0.0) if kind == "call" else max(strike - spot, 0.0)
    root_t = math.sqrt(years)
    d1 = (math.log(spot / strike) + (rate + 0.5 * volatility**2) * years) / (volatility * root_t)
    d2 = d1 - volatility * root_t
    if kind == "call":
        return spot * _normal_cdf(d1) - strike * math.exp(-rate * years) * _normal_cdf(d2)
    return strike * math.exp(-rate * years) * _normal_cdf(-d2) - spot * _normal_cdf(-d1)


def implied_move(case: EarningsCase) -> tuple[float, float]:
    dollars = case.call.premium + case.put.premium
    return dollars, dollars / case.spot * 100


def scenario_table(case: EarningsCase, moves: list[float]) -> list[ScenarioRow]:
    premium = case.call.premium + case.put.premium
    strike = case.call.strike
    rows = []
    for move in moves:
        terminal = case.spot * (1 + move / 100)
        call_value = max(terminal - strike, 0)
        put_value = max(strike - terminal, 0)
        rows.append(
            ScenarioRow(
                move_pct=move,
                terminal_spot=round(terminal, 2),
                call_value=round(call_value, 2),
                put_value=round(put_value, 2),
                straddle_pnl=round(call_value + put_value - premium, 2),
            )
        )
    return rows


def historical_stats(case: EarningsCase) -> tuple[float, float]:
    absolute_moves = [abs(move) for move in case.prior_moves_pct]
    return median(absolute_moves), max(absolute_moves)
