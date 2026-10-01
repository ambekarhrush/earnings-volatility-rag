from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")


class Evidence(StrictModel):
    id: str
    title: str
    text: str
    source: str
    published: date
    url: str | None = None
    kind: Literal["issuer", "filing", "upload"] = "issuer"
    sha256: str | None = None


class Assumptions(StrictModel):
    spot: float = Field(default=100, gt=0, le=100000)
    strike: float = Field(default=100, gt=0, le=100000)
    call_bid: float = Field(default=4.1, gt=0, le=100000)
    call_ask: float = Field(default=4.3, gt=0, le=100000)
    put_bid: float = Field(default=3.7, gt=0, le=100000)
    put_ask: float = Field(default=3.9, gt=0, le=100000)
    rate: float = Field(default=0.04, ge=-0.05, le=0.3)
    dividend_yield: float = Field(default=0, ge=0, le=0.3)
    iv_crush_pct: float = Field(default=45, ge=0, le=95)
    expected_move_pct: float = Field(default=6, ge=0, le=50)
    contracts: int = Field(default=1, ge=1, le=1000)
    fee_per_contract: float = Field(default=0.65, ge=0, le=100)

    @model_validator(mode="after")
    def no_crossed_quotes(self):
        if self.call_ask < self.call_bid or self.put_ask < self.put_bid:
            raise ValueError("Ask must be at least bid for each option leg.")
        return self


class DeskRequest(StrictModel):
    ticker: str = Field(default="AAPL", pattern=r"^[A-Z][A-Z0-9.]{0,9}$")
    mode: Literal["hypothetical", "marketdata"] = "hypothetical"
    event_date: date
    event_session: Literal["after_close", "before_open"] = "after_close"
    expiration: date
    thesis: str = Field(default="", max_length=4000)
    assumptions: Assumptions = Field(default_factory=Assumptions)
    document_ids: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def expiry_includes_event(self):
        if self.expiration < self.event_date or (
            self.expiration == self.event_date and self.event_session == "after_close"
        ):
            raise ValueError("Expiration must include the earnings reaction session.")
        return self


class QuoteLeg(StrictModel):
    symbol: str
    kind: Literal["call", "put"]
    strike: float = Field(gt=0)
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    quote_time: datetime
    open_interest: int = Field(default=0, ge=0)
    volume: int = Field(default=0, ge=0)

    @field_validator("quote_time")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("Quote timestamp must include timezone.")
        return value

    @model_validator(mode="after")
    def two_sided(self):
        if self.ask < self.bid:
            raise ValueError("Crossed option quote.")
        return self


class MarketSnapshot(StrictModel):
    ticker: str
    spot: float = Field(gt=0)
    spot_time: datetime
    fetched_at: datetime
    expiration: date
    call: QuoteLeg
    put: QuoteLeg
    provider: str
    feed: Literal["hypothetical", "delayed"]
    stale: bool
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_pair(self):
        if self.call.strike != self.put.strike:
            raise ValueError("Straddle legs must share a strike.")
        for value in (self.spot_time, self.fetched_at):
            if value.tzinfo is None:
                raise ValueError("Market timestamps must include timezone.")
        return self


class OpinionClaim(StrictModel):
    text: str
    evidence_ids: list[str] = Field(min_length=1)


class Opinion(StrictModel):
    headline: str
    stance: Literal["watch", "investigate_long_vol", "insufficient_data"]
    rationale: list[OpinionClaim] = Field(min_length=1, max_length=5)
    counterargument: str
    invalidation: str
    questions: list[str] = Field(min_length=1, max_length=5)
    confidence: Literal["low", "medium"]


class ResearchPack(StrictModel):
    ticker: str
    company: str
    evidence: list[Evidence]
    editorial: Opinion
    metrics: list[dict] = Field(default_factory=list)
