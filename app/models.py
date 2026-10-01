from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EvidenceItem(BaseModel):
    claim: str
    source: str
    source_date: date
    url: str | None = None


class OptionLeg(BaseModel):
    kind: Literal["call", "put"]
    strike: float = Field(gt=0)
    premium: float = Field(ge=0)
    quantity: int = 1


class EarningsCase(BaseModel):
    ticker: str
    company_name: str
    as_of: date
    earnings_date: date
    spot: float = Field(gt=0)
    days_to_expiry: int = Field(gt=0)
    risk_free_rate: float = Field(default=0.04, ge=-0.05, le=0.25)
    implied_volatility: float = Field(gt=0, le=5)
    prior_moves_pct: list[float] = Field(min_length=1)
    call: OptionLeg
    put: OptionLeg
    evidence: list[EvidenceItem] = Field(default_factory=list)
    user_view: str = "No directional view supplied."

    @model_validator(mode="after")
    def validate_chain(self):
        if self.call.kind != "call" or self.put.kind != "put":
            raise ValueError("call and put legs must have the matching option kind")
        if self.call.strike != self.put.strike:
            raise ValueError("the implied-move straddle must use a common strike")
        return self


class ScenarioRow(BaseModel):
    move_pct: float
    terminal_spot: float
    call_value: float
    put_value: float
    straddle_pnl: float


class Brief(BaseModel):
    case: EarningsCase
    implied_move_dollars: float
    implied_move_pct: float
    historical_median_abs_move_pct: float
    historical_max_abs_move_pct: float
    call_model_value: float
    put_model_value: float
    scenarios: list[ScenarioRow]
    synthesis: str
    synthesis_mode: Literal["deterministic", "openai"]
    limitations: list[str]
