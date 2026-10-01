"""Budget-aware Alpha Vantage earnings calendar and EPS history adapter."""

from __future__ import annotations

import csv
import io
import os
import threading
import time
from datetime import UTC, date, datetime

import httpx
from pydantic import BaseModel, ConfigDict

from app.market import DataUnavailable


class EarningsEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: str
    report_date: date
    fiscal_date_ending: date | None = None
    estimate: float | None = None
    currency: str | None = None
    session: str | None = None


class EarningsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fiscal_date_ending: date
    reported_date: date
    reported_eps: float | None = None
    estimated_eps: float | None = None
    surprise: float | None = None
    surprise_percentage: float | None = None


class EarningsProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    provider: str = "Alpha Vantage"
    fetched_at: str
    next_event: EarningsEvent | None
    history: list[EarningsResult]
    note: str


_cache: dict[str, tuple[float, EarningsProfile]] = {}
_lock = threading.Lock()


def _number(value: object) -> float | None:
    if value in (None, "", "None", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_calendar(raw: str, symbol: str, today: date | None = None) -> EarningsEvent | None:
    rows = list(csv.DictReader(io.StringIO(raw)))
    check_date = today or datetime.now(UTC).date()
    candidates = []
    for row in rows:
        try:
            event = EarningsEvent(
                symbol=row["symbol"].upper(),
                name=row.get("name", ""),
                report_date=row["reportDate"],
                fiscal_date_ending=row.get("fiscalDateEnding") or None,
                estimate=_number(row.get("estimate")),
                currency=row.get("currency") or None,
                session=row.get("timeOfTheDay") or None,
            )
            if event.symbol == symbol and event.report_date >= check_date:
                candidates.append(event)
        except (KeyError, ValueError):
            continue
    return min(candidates, key=lambda item: item.report_date) if candidates else None


def parse_history(payload: dict, symbol: str) -> list[EarningsResult]:
    if payload.get("symbol", "").upper() != symbol:
        raise DataUnavailable("Earnings history did not match the requested ticker.")
    output = []
    for row in payload.get("quarterlyEarnings", [])[:12]:
        try:
            output.append(
                EarningsResult(
                    fiscal_date_ending=row["fiscalDateEnding"],
                    reported_date=row["reportedDate"],
                    reported_eps=_number(row.get("reportedEPS")),
                    estimated_eps=_number(row.get("estimatedEPS")),
                    surprise=_number(row.get("surprise")),
                    surprise_percentage=_number(row.get("surprisePercentage")),
                )
            )
        except (KeyError, ValueError):
            continue
    return output


def _provider_error(response: httpx.Response) -> None:
    if response.status_code in (401, 403):
        raise DataUnavailable("Alpha Vantage rejected the API key.")
    if response.status_code == 429:
        raise DataUnavailable("Alpha Vantage rate limit reached. Retry later.")
    response.raise_for_status()
    text = response.text.lstrip()
    if text.startswith("{"):
        payload = response.json()
        message = payload.get("Note") or payload.get("Information") or payload.get("Error Message")
        if message:
            raise DataUnavailable(f"Alpha Vantage: {message}")


def get_earnings_profile(symbol: str) -> EarningsProfile:
    symbol = symbol.upper()
    with _lock:
        cached = _cache.get(symbol)
        if cached and time.monotonic() - cached[0] < 6 * 3600:
            return cached[1]
    key = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
    if not key:
        raise DataUnavailable("Add ALPHA_VANTAGE_API_KEY to .env and restart.")
    try:
        with httpx.Client(timeout=20) as client:
            calendar = client.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "EARNINGS_CALENDAR",
                    "symbol": symbol,
                    "horizon": "12month",
                    "apikey": key,
                },
            )
            _provider_error(calendar)
            history = client.get(
                "https://www.alphavantage.co/query",
                params={"function": "EARNINGS", "symbol": symbol, "apikey": key},
            )
            _provider_error(history)
            profile = EarningsProfile(
                symbol=symbol,
                fetched_at=datetime.now(UTC).date().isoformat(),
                next_event=parse_calendar(calendar.text, symbol),
                history=parse_history(history.json(), symbol),
                note="Calendar dates and estimates can change; verify with issuer investor relations.",
            )
    except (httpx.HTTPError, ValueError) as exc:
        raise DataUnavailable("Earnings-data request failed or returned invalid data.") from exc
    with _lock:
        if len(_cache) >= 64:
            _cache.pop(next(iter(_cache)))
        _cache[symbol] = (time.monotonic(), profile)
    return profile
