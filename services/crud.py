"""Create, Read, Update, Delete operations for players and matches.

Every write is validated first and runs inside a transaction
(see utils.db_connection.transaction), so a failed write never leaves
half-saved data behind.
"""
import math
from datetime import date

from utils.db_connection import execute, run_query, transaction

PLAYING_ROLES = ["Batsman", "Bowler", "All-rounder", "Wicket-keeper"]
BATTING_STYLES = ["Right-hand bat", "Left-hand bat"]
BOWLING_STYLES = ["", "Right-arm fast", "Right-arm medium", "Left-arm fast", "Left-arm medium",
                  "Right-arm offbreak", "Legbreak googly", "Slow left-arm orthodox",
                  "Left-arm wrist-spin"]
FORMATS = ["Test", "ODI", "T20I"]
STATES = ["Upcoming", "In Progress", "Complete"]


class ValidationError(ValueError):
    """Raised when form input is not acceptable."""


def _py(value):
    """Convert pandas/numpy values to plain Python (NaN -> None, int64 -> int)."""
    if value is None:
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _row_to_dict(df):
    return None if df.empty else {k: _py(v) for k, v in df.iloc[0].items()}


def _id(value):
    value = _py(value)
    return int(value) if value not in (None, "") else None


# --------------------------------------------------------------------- lookups
def list_teams():
    return run_query("SELECT team_id, team_name, country FROM teams ORDER BY team_name")


def list_venues():
    return run_query("SELECT venue_id, venue_name, city, country FROM venues ORDER BY venue_name")


# --------------------------------------------------------------------- players
def _validate_player(data):
    name = (data.get("full_name") or "").strip()
    if len(name) < 3:
        raise ValidationError("Full name must be at least 3 characters.")
    if data.get("playing_role") not in PLAYING_ROLES:
        raise ValidationError(f"Playing role must be one of: {', '.join(PLAYING_ROLES)}.")
    if not (data.get("country") or "").strip():
        raise ValidationError("Country is required.")
    return {
        "full_name": name,
        "country": data["country"].strip(),
        "team_id": _id(data.get("team_id")),
        "playing_role": data["playing_role"],
        "batting_style": data.get("batting_style") or None,
        "bowling_style": data.get("bowling_style") or None,
    }


def create_player(data):
    """Insert a new player and return the new player_id."""
    clean = _validate_player(data)
    with transaction() as conn:
        new_id = conn.execute("SELECT COALESCE(MAX(player_id), 0) + 1 FROM players").fetchone()[0]
        conn.execute("""INSERT INTO players (player_id, full_name, country, team_id, playing_role,
                                             batting_style, bowling_style, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'manual')""",
                     (new_id, clean["full_name"], clean["country"], clean["team_id"],
                      clean["playing_role"], clean["batting_style"], clean["bowling_style"]))
    return new_id


def read_players(name_filter="", country=None, role=None, limit=500):
    """Return players as a DataFrame, optionally filtered."""
    sql = """SELECT p.player_id, p.full_name, p.country, t.team_name, p.playing_role,
                    p.batting_style, p.bowling_style, p.source
             FROM players p LEFT JOIN teams t ON t.team_id = p.team_id
             WHERE p.full_name LIKE ?"""
    params = [f"%{name_filter.strip()}%"]
    if country:
        sql += " AND p.country = ?"
        params.append(country)
    if role:
        sql += " AND p.playing_role = ?"
        params.append(role)
    sql += " ORDER BY p.full_name LIMIT ?"
    params.append(int(limit))
    return run_query(sql, params)


def get_player(player_id):
    return _row_to_dict(run_query("SELECT * FROM players WHERE player_id = ?", [_id(player_id)]))


def update_player(player_id, data):
    """Update a player's details. Returns rows changed (0 if not found)."""
    clean = _validate_player(data)
    return execute("""UPDATE players
                      SET full_name = ?, country = ?, team_id = ?, playing_role = ?,
                          batting_style = ?, bowling_style = ?
                      WHERE player_id = ?""",
                   (clean["full_name"], clean["country"], clean["team_id"], clean["playing_role"],
                    clean["batting_style"], clean["bowling_style"], _id(player_id)))


def delete_player(player_id):
    """Delete a player (their innings and career rows are removed by CASCADE)."""
    return execute("DELETE FROM players WHERE player_id = ?", (_id(player_id),))


# --------------------------------------------------------------------- matches
def _validate_match(data):
    data = dict(data)
    for key in ("team1_id", "team2_id", "venue_id", "winner_id", "toss_winner_id",
                "victory_margin"):
        data[key] = _id(data.get(key))
    if not data.get("team1_id") or not data.get("team2_id"):
        raise ValidationError("Both teams are required.")
    if data["team1_id"] == data["team2_id"]:
        raise ValidationError("Team 1 and Team 2 must be different.")
    if data.get("match_format") not in FORMATS:
        raise ValidationError("Choose a match format.")
    if not isinstance(data.get("match_date"), (date, str)):
        raise ValidationError("Match date is required.")
    winner = data.get("winner_id") or None
    if winner and winner not in (data["team1_id"], data["team2_id"]):
        raise ValidationError("The winner must be one of the two teams.")
    margin = data.get("victory_margin")
    vtype = data.get("victory_type") or None
    if winner and (not margin or not vtype):
        raise ValidationError("Give a victory margin and type (runs/wickets) for the winner.")
    if vtype == "wickets" and margin and not 1 <= int(margin) <= 10:
        raise ValidationError("A win by wickets must be between 1 and 10.")
    toss_winner = data.get("toss_winner_id") or None
    if toss_winner and toss_winner not in (data["team1_id"], data["team2_id"]):
        raise ValidationError("The toss winner must be one of the two teams.")
    match_date = data["match_date"]
    return {
        "match_desc": (data.get("match_desc") or "").strip() or None,
        "match_format": data["match_format"],
        "team1_id": int(data["team1_id"]), "team2_id": int(data["team2_id"]),
        "venue_id": data.get("venue_id"),
        "match_date": match_date.isoformat() if isinstance(match_date, date) else match_date,
        "state": data.get("state") or ("Complete" if winner else "Upcoming"),
        "toss_winner_id": toss_winner,
        "toss_decision": data.get("toss_decision") or None,
        "winner_id": winner,
        "victory_margin": int(margin) if winner else None,
        "victory_type": vtype if winner else None,
    }


def _status_text(clean):
    if not clean["winner_id"]:
        return clean["state"]
    name = run_query("SELECT team_name FROM teams WHERE team_id = ?",
                     [clean["winner_id"]])["team_name"].iloc[0]
    unit = "runs" if clean["victory_type"] == "runs" else "wkts"
    return f"{name} won by {clean['victory_margin']} {unit}"


def create_match(data):
    clean = _validate_match(data)
    with transaction() as conn:
        new_id = conn.execute("SELECT COALESCE(MAX(match_id), 0) + 1 FROM matches").fetchone()[0]
        conn.execute("""INSERT INTO matches (match_id, match_desc, match_format, team1_id, team2_id,
                            venue_id, match_date, state, status, toss_winner_id, toss_decision,
                            winner_id, victory_margin, victory_type, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual')""",
                     (new_id, clean["match_desc"], clean["match_format"], clean["team1_id"],
                      clean["team2_id"], clean["venue_id"], clean["match_date"], clean["state"],
                      _status_text(clean), clean["toss_winner_id"], clean["toss_decision"],
                      clean["winner_id"], clean["victory_margin"], clean["victory_type"]))
    return new_id


def read_matches(team_id=None, match_format=None, limit=200):
    sql = "SELECT * FROM v_match_details WHERE 1 = 1"
    params = []
    if team_id:
        sql += (" AND match_id IN (SELECT match_id FROM matches "
                "WHERE team1_id = ? OR team2_id = ?)")
        params += [_id(team_id), _id(team_id)]
    if match_format:
        sql += " AND match_format = ?"
        params.append(match_format)
    sql += " ORDER BY match_date DESC, match_id DESC LIMIT ?"
    params.append(int(limit))
    return run_query(sql, params)


def get_match(match_id):
    return _row_to_dict(run_query("SELECT * FROM matches WHERE match_id = ?", [_id(match_id)]))


def update_match(match_id, data):
    clean = _validate_match(data)
    return execute("""UPDATE matches
                      SET match_desc = ?, match_format = ?, team1_id = ?, team2_id = ?,
                          venue_id = ?, match_date = ?, state = ?, status = ?,
                          toss_winner_id = ?, toss_decision = ?, winner_id = ?,
                          victory_margin = ?, victory_type = ?
                      WHERE match_id = ?""",
                   (clean["match_desc"], clean["match_format"], clean["team1_id"],
                    clean["team2_id"], clean["venue_id"], clean["match_date"], clean["state"],
                    _status_text(clean), clean["toss_winner_id"], clean["toss_decision"],
                    clean["winner_id"], clean["victory_margin"], clean["victory_type"],
                    _id(match_id)))


def delete_match(match_id):
    return execute("DELETE FROM matches WHERE match_id = ?", (_id(match_id),))
