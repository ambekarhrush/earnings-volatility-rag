import argparse
import json
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(
        description="Freeze one local desk snapshot for every evaluation provider."
    )
    parser.add_argument(
        "--snapshot", help="Snapshot ID from the dashboard; defaults to initial hypothetical case"
    )
    parser.add_argument("--base", default="http://127.0.0.1:8001")
    args = parser.parse_args()
    endpoint = f"/snapshots/{args.snapshot}" if args.snapshot else "/initial"
    response = httpx.get(args.base + "/api/desk" + endpoint, timeout=20)
    response.raise_for_status()
    data = response.json()
    pack = {k: data[k] for k in ("request", "market", "analytics", "evidence")}
    path = Path(__file__).resolve().parents[1] / ".cache" / "eval-pack.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(pack, indent=2))
    print(f"Frozen snapshot {data['id']} for all providers at {path}")


if __name__ == "__main__":
    main()
