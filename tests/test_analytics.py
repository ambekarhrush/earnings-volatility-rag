import pytest

from app.analytics import black_scholes, implied_move, scenario_table
from app.providers import SnapshotCaseProvider


@pytest.fixture
def case():
    return SnapshotCaseProvider().get("ACME")


def test_implied_move_uses_atm_straddle(case):
    dollars, percent = implied_move(case)
    assert dollars == 8.0
    assert percent == 8.0


def test_black_scholes_put_call_parity():
    call = black_scholes(spot=100, strike=100, years=0.25, rate=0.04, volatility=0.3, kind="call")
    put = black_scholes(spot=100, strike=100, years=0.25, rate=0.04, volatility=0.3, kind="put")
    assert call - put == pytest.approx(100 - 100 * __import__("math").exp(-0.04 * 0.25))


def test_straddle_scenario_is_symmetric_at_strike(case):
    rows = scenario_table(case, [-8, 0, 8])
    assert rows[0].straddle_pnl == rows[2].straddle_pnl == 0
    assert rows[1].straddle_pnl == -8
