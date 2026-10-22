"""Move data from the Cricbuzz API into the SQL database.

API JSON -> parsers.py (clean dicts) -> SQL upserts here.
Upsert = insert a new row, or update it if the ID already exists.
"""
import logging

from api.cricbuzz_client import CricbuzzClient
from api.parsers import normalise_format, parse_match_list, parse_result, parse_scorecard
from services.sample_data import rebuild_career_stats
from utils.db_connection import init_schema, transaction

logger = logging.getLogger(__name__)

UPSERT_TEAM = """
INSERT INTO teams (team_id, team_name, short_name) VALUES (?, ?, ?)
ON CONFLICT(team_id) DO UPDATE SET team_name = excluded.team_name,
                                   short_name = excluded.short_name"""

UPSERT_VENUE = """
INSERT INTO venues (venue_id, venue_name, city) VALUES (?, ?, ?)
ON CONFLICT(venue_id) DO UPDATE SET venue_name = excluded.venue_name, city = excluded.city"""

UPSERT_SERIES = """
INSERT INTO series (series_id, series_name) VALUES (?, ?)
ON CONFLICT(series_id) DO UPDATE SET series_name = excluded.series_name"""

UPSERT_MATCH = """
INSERT INTO matches (match_id, series_id, match_desc, match_format, team1_id, team2_id, venue_id,
                     match_date, state, status, winner_id, victory_margin, victory_type, source)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'api')
ON CONFLICT(match_id) DO UPDATE SET
    state = excluded.state, status = excluded.status, winner_id = excluded.winner_id,
    victory_margin = excluded.victory_margin, victory_type = excluded.victory_type"""

UPSERT_PLAYER = """
INSERT INTO players (player_id, full_name, team_id, source) VALUES (?, ?, ?, 'api')
ON CONFLICT(player_id) DO UPDATE SET full_name = excluded.full_name"""


def sync_matches(client=None, which="recent", international_only=True):
    """Fetch live/recent/upcoming matches and save them. Returns rows saved."""
    client = client or CricbuzzClient()
    payload = client.get(which)
    matches = parse_match_list(payload)
    if international_only:
        matches = [m for m in matches if (m["match_type"] or "").lower() == "international"]
    init_schema()
    saved = 0
    with transaction() as conn:
        for m in matches:
            if not m["match_id"] or not m["team1_id"] or not m["team2_id"]:
                continue
            conn.execute(UPSERT_TEAM, (m["team1_id"], m["team1"], m["team1_short"]))
            conn.execute(UPSERT_TEAM, (m["team2_id"], m["team2"], m["team2_short"]))
            if m["venue_id"]:
                conn.execute(UPSERT_VENUE, (m["venue_id"], m["venue"], m["city"]))
            if m["series_id"]:
                conn.execute(UPSERT_SERIES, (m["series_id"], m["series_name"]))
            winner_name, margin, vtype = parse_result(m["status"])
            winner_id = {m["team1"]: m["team1_id"], m["team2"]: m["team2_id"]}.get(winner_name)
            conn.execute(UPSERT_MATCH, (
                m["match_id"], m["series_id"] or None, m["match_desc"],
                normalise_format(m["match_format"]), m["team1_id"], m["team2_id"],
                m["venue_id"] or None, m["start_date"], m["state"], m["status"],
                winner_id, margin, vtype))
            saved += 1
    logger.info("Saved %s %s matches", saved, which)
    return saved


def sync_scorecard(match_id, client=None, rebuild_stats=True):
    """Fetch one match scorecard and save batting/bowling rows. Returns counts."""
    client = client or CricbuzzClient()
    innings = parse_scorecard(client.scorecard(match_id))
    bat_count = bowl_count = 0
    with transaction() as conn:
        exists = conn.execute("SELECT 1 FROM matches WHERE match_id = ?", (match_id,)).fetchone()
        if not exists:
            raise ValueError(f"Match {match_id} is not in the database. Sync matches first.")
        teams = conn.execute("SELECT team1_id, team2_id FROM matches WHERE match_id = ?",
                             (match_id,)).fetchone()
        for inn in innings:
            bat_team = inn["team_id"] or None
            bowl_team = None
            if bat_team and teams:
                bowl_team = teams[1] if bat_team == teams[0] else teams[0]
            for b in inn["batters"]:
                if not b["player_id"]:
                    continue
                conn.execute(UPSERT_PLAYER, (b["player_id"], b["name"], bat_team))
                conn.execute("""
                    INSERT OR REPLACE INTO batting_innings
                        (match_id, innings_no, player_id, team_id, batting_position, runs, balls,
                         fours, sixes, strike_rate, is_out, dismissal)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                             (match_id, inn["innings_no"], b["player_id"], bat_team,
                              min(b["position"], 11), b["runs"], b["balls"], b["fours"], b["sixes"],
                              b["strike_rate"], 0 if "not out" in b["dismissal"].lower() else 1,
                              b["dismissal"]))
                bat_count += 1
            for w in inn["bowlers"]:
                if not w["player_id"]:
                    continue
                conn.execute(UPSERT_PLAYER, (w["player_id"], w["name"], bowl_team))
                conn.execute("""
                    INSERT OR REPLACE INTO bowling_innings
                        (match_id, innings_no, player_id, team_id, overs, maidens, runs_conceded,
                         wickets, economy)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                             (match_id, inn["innings_no"], w["player_id"], bowl_team, w["overs"],
                              w["maidens"], w["runs"], w["wickets"], w["economy"]))
                bowl_count += 1
    if rebuild_stats and (bat_count or bowl_count):
        rebuild_career_stats()
    return {"batting_rows": bat_count, "bowling_rows": bowl_count}
