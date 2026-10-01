from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agent import generate_opinion
from app.desk_models import DeskRequest, Evidence
from app.earnings import EarningsProfile, get_earnings_profile
from app.market import DataUnavailable, get_snapshot
from app.research import latest_filing, parse_document, research_pack
from app.risk import analyze

router = APIRouter(prefix="/api/desk", tags=["Earnings desk"])
_snapshots: dict[str, dict] = {}
_documents: dict[str, Evidence] = {}
_earnings: dict[str, EarningsProfile] = {}
_lock = threading.Lock()


def store_bounded(store, key, value, limit=64):
    with _lock:
        if len(store) >= limit and key not in store:
            store.pop(next(iter(store)))
        store[key] = value


@router.get("/status")
def status():
    return {
        "marketdata": bool(os.getenv("MARKETDATA_TOKEN", "").strip()),
        "edgar": bool(os.getenv("EDGAR_IDENTITY", "").strip()),
        "earnings": bool(os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()),
        "ai_model": os.getenv("AI_MODEL", "").strip() or None,
        "feed_note": "Free/trial: 24h+ delayed. Fetch at most one expiry/nearest strike; 15-minute cache.",
        "research_tickers": ["AAPL"],
    }


@router.get("/initial")
def initial():
    event = datetime.now(UTC).date() + timedelta(days=28)
    while event.weekday() >= 4:
        event += timedelta(days=1)
    expiry = event + timedelta(days=1)
    while expiry.weekday() != 4:
        expiry += timedelta(days=1)
    request = DeskRequest(
        event_date=event,
        expiration=expiry,
        thesis="Recurring profitability matters more to my view than a one-off margin benefit.",
    )
    return build(request)


@router.post("/brief")
def build(request: DeskRequest):
    now = datetime.now(UTC)
    if request.event_date < now.date() or request.expiration <= now.date():
        raise HTTPException(
            422, "Use a future earnings event and expiration for this current-data workflow."
        )
    if request.expiration > now.date() + timedelta(days=730):
        raise HTTPException(422, "Choose an expiration within two years.")
    try:
        market = get_snapshot(request, now)
        analytics = analyze(market, request)
        research = research_pack(request.ticker)
        evidence = [e for e in research.evidence if e.published <= market.spot_time.date()]
        for doc_id in dict.fromkeys(request.document_ids):
            with _lock:
                doc = _documents.get(doc_id)
            if doc is None:
                raise ValueError("Attached document expired from memory. Upload it again.")
            if doc.published > market.spot_time.date():
                raise ValueError(
                    "Document was published after the quote snapshot. Use a newer snapshot."
                )
            evidence.append(doc)
        pack = {
            "ticker": request.ticker,
            "request": request.model_dump(mode="json"),
            "market": market.model_dump(mode="json"),
            "analytics": analytics,
            "evidence": [e.model_dump(mode="json") for e in evidence],
        }
        snapshot_id = hashlib.sha256(json.dumps(pack, sort_keys=True).encode()).hexdigest()[:20]
        output = {
            **pack,
            "id": snapshot_id,
            "company": research.company,
            "fundamentals": research.metrics,
            "opinion": research.editorial.model_dump(),
            "opinion_mode": "editorial",
            "created_at": now.isoformat(),
            "event_note": "User-assumed date; verify with issuer IR.",
            "experiment": {
                "status": "not_run",
                "models": [],
                "evidence_hash": hashlib.sha256(
                    json.dumps(pack["evidence"], sort_keys=True).encode()
                ).hexdigest(),
            },
        }
        with _lock:
            earnings = _earnings.get(request.ticker)
        if earnings:
            output["earnings"] = earnings.model_dump(mode="json")
            if earnings.next_event and earnings.next_event.report_date == request.event_date:
                output["event_note"] = "Alpha Vantage calendar date; verify with issuer IR."
        if not evidence:
            output["opinion"] = research_pack("UNKNOWN").editorial.model_dump()
            output["fundamentals"] = []
        store_bounded(_snapshots, snapshot_id, output)
        return output
    except DataUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def get_saved(snapshot_id: str):
    with _lock:
        saved = _snapshots.get(snapshot_id)
    if saved is None:
        raise HTTPException(404, "Snapshot expired from this local session. Rebuild the brief.")
    return saved


@router.get("/earnings/{ticker}")
def earnings(ticker: str):
    import re

    ticker = ticker.upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9.]{0,9}", ticker):
        raise HTTPException(422, "Invalid ticker.")
    try:
        profile = get_earnings_profile(ticker)
        with _lock:
            _earnings[ticker] = profile
        return profile
    except DataUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/snapshots/{snapshot_id}")
def snapshot(snapshot_id: str):
    return get_saved(snapshot_id)


@router.post("/snapshots/{snapshot_id}/opinion")
def opinion(snapshot_id: str):
    saved = get_saved(snapshot_id)
    try:
        result = generate_opinion(
            {k: saved[k] for k in ("request", "market", "analytics", "evidence")}
        )
        return {
            **result,
            "snapshot_id": snapshot_id,
            "evidence_hash": saved["experiment"]["evidence_hash"],
        }
    except DataUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/documents")
def upload(file: Annotated[UploadFile, File()], published: Annotated[date, Form()]):
    try:
        content = file.file.read(8 * 1024 * 1024 + 1)
        document = parse_document(content, file.filename or "upload.txt", published)
        store_bounded(_documents, document.id, document, limit=24)
        return document
    except DataUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        file.file.close()


@router.post("/filings/{ticker}")
def filing(ticker: str):
    import re

    if not re.fullmatch(r"[A-Z][A-Z0-9.]{0,9}", ticker):
        raise HTTPException(422, "Invalid ticker.")
    try:
        document = latest_filing(ticker)
        store_bounded(_documents, document.id, document, limit=24)
        return document
    except DataUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
