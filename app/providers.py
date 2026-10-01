import json
from pathlib import Path

from app.models import EarningsCase

DATA_DIR = Path(__file__).parent / "data"


class SnapshotCaseProvider:
    """Dated, reproducible fixtures. Live providers will implement the same contract."""

    def get(self, ticker: str) -> EarningsCase:
        path = DATA_DIR / f"{ticker.upper()}.json"
        if not path.exists():
            raise KeyError(f"No snapshot is available for {ticker.upper()}")
        return EarningsCase.model_validate(json.loads(path.read_text()))

    def available(self) -> list[str]:
        return sorted(path.stem for path in DATA_DIR.glob("*.json"))
