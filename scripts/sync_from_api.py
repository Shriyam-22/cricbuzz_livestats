"""Pull real data from the Cricbuzz API into the database.

Run from the project folder:  python scripts/sync_from_api.py --scorecards 5

Each scorecard costs one API call, so keep --scorecards small on the free plan.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.cricbuzz_client import CricbuzzAPIError, CricbuzzClient  # noqa: E402
from services.data_loader import sync_matches, sync_scorecard  # noqa: E402
from utils.db_connection import run_query  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecards", type=int, default=3,
                        help="How many completed API matches to fetch scorecards for")
    args = parser.parse_args()

    client = CricbuzzClient()
    try:
        for feed in ("recent", "live"):
            print(f"{feed:>7}: saved {sync_matches(client, feed)} international matches")
        todo = run_query("""SELECT m.match_id FROM matches m
                            WHERE m.source = 'api' AND m.state = 'Complete'
                              AND NOT EXISTS (SELECT 1 FROM batting_innings b
                                              WHERE b.match_id = m.match_id)
                            ORDER BY m.match_date DESC LIMIT ?""", [args.scorecards])
        for match_id in todo["match_id"]:
            counts = sync_scorecard(int(match_id), client, rebuild_stats=False)
            print(f"  scorecard {match_id}: {counts}")
        if len(todo):
            from services.sample_data import rebuild_career_stats
            rebuild_career_stats()
        print("Done.")
    except CricbuzzAPIError as exc:
        print(f"API error: {exc}")
        sys.exit(1)
