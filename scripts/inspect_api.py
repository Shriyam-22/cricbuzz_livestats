"""Save a raw API response to data/raw/ so you can study its JSON structure.

Examples (from the project folder):
    python scripts/inspect_api.py recent
    python scripts/inspect_api.py scorecard --match-id 170723
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.cricbuzz_client import ENDPOINTS, CricbuzzAPIError, CricbuzzClient  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endpoint", choices=sorted(ENDPOINTS))
    parser.add_argument("--match-id")
    parser.add_argument("--player-id")
    parser.add_argument("--venue-id")
    args = parser.parse_args()

    path_values = {k: v for k, v in {"match_id": args.match_id, "player_id": args.player_id,
                                     "venue_id": args.venue_id}.items() if v}
    try:
        data = CricbuzzClient().get(args.endpoint, **path_values)
    except (CricbuzzAPIError, KeyError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    out = ROOT / "data" / "raw" / f"{args.endpoint}{'_' + '_'.join(path_values.values()) if path_values else ''}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved {out} - top-level keys: {list(data)[:10] if isinstance(data, dict) else type(data)}")
