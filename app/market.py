"""Small, budget-aware requests to documented MarketData.app endpoints."""

from __future__ import annotations

import os
import re
import threading
import time
from datetime import UTC, datetime

import httpx

from app.desk_models import DeskRequest, MarketSnapshot, QuoteLeg


class DataUnavailable(Exception):
    pass


_cache: dict[tuple, tuple[float, dict, datetime]] = {}
_lock = threading.Lock()


def hypothetical_snapshot(request: DeskRequest, now: datetime) -> MarketSnapshot:
    a = request.assumptions
    return MarketSnapshot(
        ticker=request.ticker,
        spot=a.spot,
        spot_time=now,
        fetched_at=now,
        expiration=request.expiration,
        provider="User assumptions",
        feed="hypothetical",
        stale=False,
        call=QuoteLeg(
            symbol="HYPOTHETICAL-CALL",
            kind="call",
            strike=a.strike,
            bid=a.call_bid,
            ask=a.call_ask,
            quote_time=now,
        ),
        put=QuoteLeg(
            symbol="HYPOTHETICAL-PUT",
            kind="put",
            strike=a.strike,
            bid=a.put_bid,
            ask=a.put_ask,
            quote_time=now,
        ),
        warnings=["Option prices and spot are hypothetical inputs, not market observations."],
    )


def parse_chain(payload: dict, request: DeskRequest, now: datetime) -> MarketSnapshot:
    if payload.get("s") != "ok" or not payload.get("optionSymbol"):
        raise DataUnavailable("No option chain returned for this symbol and expiration.")
    pairs: dict[float, dict] = {}
    underlying = {}
    prefix = request.ticker + request.expiration.strftime("%y%m%d")
    for i, symbol in enumerate(payload["optionSymbol"]):
        try:
            if not re.fullmatch(re.escape(prefix) + r"[CP]\d{8}", symbol):
                continue  # Exclude adjusted roots and other expiries.
            kind = payload["side"][i]
            updated = datetime.fromtimestamp(float(payload["updated"][i]), tz=UTC)
            if (updated - now).total_seconds() > 300:
                continue
            leg = QuoteLeg(
                symbol=symbol,
                kind=kind,
                strike=payload["strike"][i],
                bid=payload["bid"][i],
                ask=payload["ask"][i],
                quote_time=updated,
                volume=payload.get("volume", [0] * len(payload["optionSymbol"]))[i] or 0,
                open_interest=payload.get("openInterest", [0] * len(payload["optionSymbol"]))[i]
                or 0,
            )
            spot = float(payload["underlyingPrice"][i])
            if spot <= 0:
                continue
            pairs.setdefault(leg.strike, {})[kind] = leg
            underlying[symbol] = spot
        except (ValueError, TypeError, KeyError, IndexError, OverflowError):
            continue
    valid = [v for v in pairs.values() if "call" in v and "put" in v]
    if not valid:
        raise DataUnavailable(
            "No valid two-sided standard call/put pair; check expiry and liquidity."
        )
    pair = min(valid, key=lambda p: abs(p["call"].strike - underlying[p["call"].symbol]))
    call, put = pair["call"], pair["put"]
    spot = underlying[call.symbol]
    if abs(spot - underlying[put.symbol]) / spot > 0.005:
        raise DataUnavailable("Call/put underlying snapshots disagree by more than 0.5%.")
    if abs((call.quote_time - put.quote_time).total_seconds()) > 900:
        raise DataUnavailable("Call and put snapshots are more than 15 minutes apart.")
    quote_time = min(call.quote_time, put.quote_time)
    age = (now - quote_time).total_seconds()
    warnings = ["MarketData.app free/trial data is 24h+ delayed. This is a dated observation."]
    if age > 36 * 3600:
        warnings.append(
            "Snapshot is over 36 hours old; weekends and closed markets can explain the age."
        )
    if (call.ask + put.ask - call.bid - put.bid) / (call.ask + put.ask) > 0.15:
        warnings.append("Wide combined spread: midpoint is not an executable purchase price.")
    if abs(call.strike - spot) / spot > 0.02:
        warnings.append(
            "Selected strike is over 2% from spot; implied-move heuristic is less reliable."
        )
    return MarketSnapshot(
        ticker=request.ticker,
        spot=spot,
        spot_time=quote_time,
        fetched_at=now,
        expiration=request.expiration,
        call=call,
        put=put,
        provider="MarketData.app",
        feed="delayed",
        stale=age > 36 * 3600,
        warnings=warnings,
    )


def get_snapshot(request: DeskRequest, now: datetime) -> MarketSnapshot:
    if request.mode == "hypothetical":
        return hypothetical_snapshot(request, now)
    token = os.getenv("MARKETDATA_TOKEN", "").strip()
    if not token:
        raise DataUnavailable("Add MARKETDATA_TOKEN to the local .env, restart, then fetch quotes.")
    key = (request.ticker, str(request.expiration))
    with _lock:
        cached = _cache.get(key)
        if cached and time.monotonic() - cached[0] < 900:
            parsed = parse_chain(cached[1], request, now)
            parsed.fetched_at = cached[2]
            return parsed
    try:
        with httpx.Client(timeout=20) as client:
            response = client.get(
                f"https://api.marketdata.app/v1/options/chain/{request.ticker}/",
                headers={"Authorization": f"Bearer {token}"},
                params={"expiration": str(request.expiration), "strikeLimit": 1},
            )
        if response.status_code in (401, 403):
            raise DataUnavailable(
                "Provider rejected the key or data entitlement. Check the account."
            )
        if response.status_code == 429:
            raise DataUnavailable(
                "Provider rate/credit limit reached. Retry later; no automatic retry."
            )
        response.raise_for_status()
        payload = response.json()
        result = parse_chain(payload, request, now)
    except (httpx.HTTPError, ValueError) as exc:
        raise DataUnavailable(
            "Market-data request failed or returned invalid data. No prices substituted."
        ) from exc
    with _lock:
        if len(_cache) >= 64:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (time.monotonic(), payload, now)
    return result
