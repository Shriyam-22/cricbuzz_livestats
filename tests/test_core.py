"""Automated tests. Run with:  python -m pytest -q

They use a temporary database, so your real data/cricbuzz.db is never touched.
"""
import os
import tempfile

os.environ["SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

import pytest  # noqa: E402

from api.parsers import parse_match_list, parse_result, parse_scorecard  # noqa: E402
from services import crud  # noqa: E402
from services.sample_data import seed_sample_data  # noqa: E402
from sql.queries import QUERIES  # noqa: E402
from utils.db_connection import run_query  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def database():
    seed_sample_data()


# ------------------------------------------------------------------ parsers
def test_parse_result():
    assert parse_result("India won by 5 wkts") == ("India", 5, "wickets")
    assert parse_result("Australia won by 32 runs") == ("Australia", 32, "runs")
    assert parse_result("England won by an innings and 12 runs") == ("England", 12, "runs")
    assert parse_result("Match drawn") == (None, None, None)


def test_parse_match_list_skips_ads():
    payload = {"typeMatches": [{"matchType": "International", "seriesMatches": [
        {"adDetail": {}},
        {"seriesAdWrapper": {"seriesId": 1, "seriesName": "S", "matches": [
            {"matchInfo": {"matchId": 10, "team1": {"teamId": 2, "teamName": "India"},
                           "team2": {"teamId": 4, "teamName": "Australia"},
                           "startDate": "1700000000000", "venueInfo": {"id": 3}}}]}}]}]}
    matches = parse_match_list(payload)
    assert len(matches) == 1
    assert matches[0]["match_id"] == 10
    assert matches[0]["start_date"] == "2023-11-14"


def test_parse_scorecard_both_shapes():
    new = {"scorecard": [{"inningsid": 1, "batsman": [
        {"id": 1, "name": "A", "runs": 50, "balls": 40, "outdec": "not out"}], "bowler": []}]}
    old = {"scoreCard": [{"inningsId": 1, "batTeamDetails": {"batsmenData": {
        "bat_1": {"batId": 1, "batName": "A", "runs": 50, "balls": 40, "outDesc": "b X"}}}}]}
    for payload in (new, old):
        innings = parse_scorecard(payload)
        assert innings[0]["batters"][0]["runs"] == 50


# ------------------------------------------------------------------ queries
@pytest.mark.parametrize("query", QUERIES, ids=lambda q: f"Q{q['id']}")
def test_every_query_runs_and_returns_rows(query):
    df = run_query(query["sql"])
    assert not df.empty, f"Q{query['id']} returned no rows"


def test_there_are_25_queries():
    assert [q["id"] for q in QUERIES] == list(range(1, 26))


# --------------------------------------------------------------------- CRUD
def test_player_crud_cycle():
    pid = crud.create_player({"full_name": "Test Player", "country": "India",
                              "team_id": 2, "playing_role": "Batsman"})
    assert crud.get_player(pid)["full_name"] == "Test Player"
    crud.update_player(pid, {"full_name": "Renamed Player", "country": "India",
                             "playing_role": "Bowler"})
    assert crud.get_player(pid)["playing_role"] == "Bowler"
    assert crud.delete_player(pid) == 1
    assert crud.get_player(pid) is None


def test_player_validation():
    with pytest.raises(crud.ValidationError):
        crud.create_player({"full_name": "x", "country": "India", "playing_role": "Batsman"})
    with pytest.raises(crud.ValidationError):
        crud.create_player({"full_name": "Valid Name", "country": "India",
                            "playing_role": "Captain"})


def test_match_validation():
    base = {"team1_id": 2, "team2_id": 4, "match_format": "ODI", "match_date": "2026-01-01"}
    with pytest.raises(crud.ValidationError):
        crud.create_match({**base, "team2_id": 2})                       # same team twice
    with pytest.raises(crud.ValidationError):
        crud.create_match({**base, "winner_id": 3, "victory_margin": 5,
                           "victory_type": "runs"})                      # winner not playing
    with pytest.raises(crud.ValidationError):
        crud.create_match({**base, "winner_id": 2, "victory_margin": 12,
                           "victory_type": "wickets"})                   # > 10 wickets


def test_deleting_match_cascades_to_innings():
    match_id = int(run_query("SELECT match_id FROM matches LIMIT 1")["match_id"].iloc[0])
    crud.delete_match(match_id)
    left = run_query("SELECT COUNT(*) AS n FROM batting_innings WHERE match_id = ?", [match_id])
    assert left["n"].iloc[0] == 0
