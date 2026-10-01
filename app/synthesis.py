from app.models import EarningsCase


def deterministic_synthesis(case: EarningsCase, implied_pct: float, median_move: float) -> str:
    comparison = "above" if implied_pct > median_move else "below"
    claims = " ".join(item.claim for item in case.evidence)
    return (
        f"{case.company_name} is priced for an approximately {implied_pct:.1f}% move through "
        f"the supplied straddle, {comparison} the {median_move:.1f}% median absolute move in the "
        f"supplied history. Evidence snapshot: {claims} User assumption: {case.user_view} "
        "Before expressing a view, verify the option snapshot, expiry convention, liquidity, "
        "management guidance, and which outcome would falsify the thesis."
    )


def synthesize(case: EarningsCase, implied_pct: float, median_move: float) -> tuple[str, str]:
    # Legacy synthetic demo remains deterministic. Paid generation lives behind an explicit POST.
    return deterministic_synthesis(case, implied_pct, median_move), "deterministic"
