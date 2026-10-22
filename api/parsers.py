"""Turn raw Cricbuzz JSON into simple Python lists/dicts.

The API's JSON is deeply nested and its key names differ slightly between
API versions (e.g. "scoreCard" vs "scorecard"). These functions look for
several possible key names, so the rest of the app stays simple.
"""
import re
from datetime import datetime, timezone


def pick(data, *keys, default=None):
    """Return the first key found in a dict, ignoring upper/lower case."""
    if not isinstance(data, dict):
        return default
    lowered = {str(k).lower(): v for k, v in data.items()}
    for key in keys:
        if key.lower() in lowered and lowered[key.lower()] not in (None, ""):
            return lowered[key.lower()]
    return default


def to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def to_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def epoch_ms_to_date(value):
    """Cricbuzz sends dates as milliseconds since 1970, e.g. '1729166400000'."""
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        return None


def normalise_format(fmt):
    fmt = (fmt or "").upper()
    if fmt == "TEST":
        return "Test"
    if fmt == "ODI":
        return "ODI"
    if fmt in ("T20", "T20I"):
        return "T20I"
    return None


# --------------------------------------------------------------------- matches
def parse_match_list(payload):
    """Flatten live/recent/upcoming responses into one list of match dicts."""
    matches = []
    for type_block in pick(payload, "typeMatches", default=[]) or []:
        match_type = pick(type_block, "matchType", default="")
        for series_block in pick(type_block, "seriesMatches", default=[]) or []:
            wrapper = pick(series_block, "seriesAdWrapper", default=None)
            if not wrapper:
                continue  # ad blocks have no matches
            for item in pick(wrapper, "matches", default=[]) or []:
                info = pick(item, "matchInfo", default={}) or {}
                score = pick(item, "matchScore", default={}) or {}
                team1 = pick(info, "team1", default={}) or {}
                team2 = pick(info, "team2", default={}) or {}
                venue = pick(info, "venueInfo", default={}) or {}
                matches.append({
                    "match_id": to_int(pick(info, "matchId")),
                    "match_type": match_type,
                    "series_id": to_int(pick(info, "seriesId", default=pick(wrapper, "seriesId"))),
                    "series_name": pick(info, "seriesName", default=pick(wrapper, "seriesName")),
                    "match_desc": pick(info, "matchDesc"),
                    "match_format": pick(info, "matchFormat"),
                    "start_date": epoch_ms_to_date(pick(info, "startDate")),
                    "state": pick(info, "state"),
                    "status": pick(info, "status"),
                    "team1_id": to_int(pick(team1, "teamId")),
                    "team1": pick(team1, "teamName"),
                    "team1_short": pick(team1, "teamSName"),
                    "team2_id": to_int(pick(team2, "teamId")),
                    "team2": pick(team2, "teamName"),
                    "team2_short": pick(team2, "teamSName"),
                    "venue_id": to_int(pick(venue, "id")),
                    "venue": pick(venue, "ground"),
                    "city": pick(venue, "city"),
                    "team1_score": format_team_score(pick(score, "team1Score")),
                    "team2_score": format_team_score(pick(score, "team2Score")),
                })
    return matches


def format_team_score(team_score):
    """{'inngs1': {'runs': 250, 'wickets': 6, 'overs': 49.6}} -> '250/6 (49.6)'."""
    if not isinstance(team_score, dict):
        return ""
    parts = []
    for key in sorted(team_score):
        inn = team_score[key]
        if isinstance(inn, dict) and "runs" in inn:
            text = f"{inn.get('runs', 0)}/{inn.get('wickets', 0)}"
            if inn.get("overs") is not None:
                text += f" ({inn['overs']})"
            parts.append(text)
    return " & ".join(parts)


RESULT_PATTERN = re.compile(r"^(?P<team>.+?) won by (?:an innings and )?(?P<margin>\d+) "
                            r"(?P<kind>runs?|wkts?|wickets?)", re.IGNORECASE)


def parse_result(status):
    """'India won by 5 wkts' -> ('India', 5, 'wickets'); otherwise (None, None, None)."""
    match = RESULT_PATTERN.match(status or "")
    if not match:
        return None, None, None
    kind = "runs" if match["kind"].lower().startswith("run") else "wickets"
    return match["team"].strip(), int(match["margin"]), kind


# ------------------------------------------------------------------ scorecards
def _as_list(value):
    """Batter lists come either as a list or as {'bat_1': {...}, 'bat_2': {...}}."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value[k] for k in sorted(value, key=lambda k: to_int(re.sub(r"\D", "", k), 0))]
    return []


def parse_scorecard(payload):
    """Return a list of innings: team, score, batters and bowlers."""
    innings_list = pick(payload, "scorecard", "scoreCard", default=[]) or []
    result = []
    for idx, inn in enumerate(innings_list, start=1):
        bat_team = pick(inn, "batTeamDetails", default={}) or {}
        score_details = pick(inn, "scoreDetails", default={}) or {}
        batters_raw = (pick(inn, "batsman", "batsmen", default=None)
                       or pick(bat_team, "batsmenData", default=[]))
        bowl_team = pick(inn, "bowlTeamDetails", default={}) or {}
        bowlers_raw = pick(inn, "bowler", "bowlers", default=None) or pick(bowl_team, "bowlersData",
                                                                          default=[])
        batters = []
        for pos, b in enumerate(_as_list(batters_raw), start=1):
            balls = to_int(pick(b, "balls"))
            runs = to_int(pick(b, "runs"))
            dismissal = pick(b, "outDesc", "outdec", "outDec", default="")
            if not balls and not runs and not dismissal:
                continue  # did not bat
            batters.append({
                "player_id": to_int(pick(b, "batId", "id")),
                "name": pick(b, "batName", "name"),
                "position": pos,
                "runs": runs, "balls": balls,
                "fours": to_int(pick(b, "fours")), "sixes": to_int(pick(b, "sixes")),
                "strike_rate": to_float(pick(b, "strikeRate", "strkrate", "strkRate")),
                "dismissal": dismissal or "not out",
            })
        bowlers = []
        for b in _as_list(bowlers_raw):
            bowlers.append({
                "player_id": to_int(pick(b, "bowlerId", "bowlId", "id")),
                "name": pick(b, "bowlName", "name"),
                "overs": to_float(pick(b, "overs"), 0.0),
                "maidens": to_int(pick(b, "maidens")),
                "runs": to_int(pick(b, "runs")),
                "wickets": to_int(pick(b, "wickets")),
                "economy": to_float(pick(b, "economy")),
            })
        result.append({
            "innings_no": to_int(pick(inn, "inningsId", "inningsid"), idx),
            "team_id": to_int(pick(inn, "batTeamId", default=pick(bat_team, "batTeamId"))),
            "team": pick(inn, "batTeamName", "batteamname", default=pick(bat_team, "batTeamName")),
            "runs": to_int(pick(inn, "score", default=pick(score_details, "runs"))),
            "wickets": to_int(pick(inn, "wickets", default=pick(score_details, "wickets"))),
            "overs": pick(inn, "overs", default=pick(score_details, "overs")),
            "batters": batters,
            "bowlers": bowlers,
        })
    return result


# ------------------------------------------------------------------- top stats
def parse_top_stats(payload):
    """{'headers': [...], 'values': [{'values': [...]}]} -> (headers, rows)."""
    headers = pick(payload, "headers", default=[]) or []
    rows = [pick(v, "values", default=[]) for v in pick(payload, "values", default=[]) or []]
    # The first column is usually the player id; keep it but rename it.
    if headers and rows and len(rows[0]) == len(headers) + 1:
        headers = ["Player ID"] + list(headers)
    return headers, rows
