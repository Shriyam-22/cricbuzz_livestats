"""Generate realistic *synthetic* sample data.

Why: the free Cricbuzz API plan allows only a few hundred calls a month,
which is not enough history for the advanced SQL questions (e.g. Q25 needs
6+ quarters of data per player). The brief asks for "sample data", so we
generate a consistent, reproducible dataset. Player names are fictional;
teams and grounds are real. Real API data is added on top by data_loader.py.

All sample rows are marked with source = 'sample'.
"""
import random
from datetime import date, timedelta

from utils.db_connection import execute, execute_many, init_schema, transaction

SEED = 42

# Cricbuzz team IDs, so API data joins to the same teams.
TEAMS = [
    (2, "India", "IND", "India"),
    (4, "Australia", "AUS", "Australia"),
    (9, "England", "ENG", "England"),
    (3, "Pakistan", "PAK", "Pakistan"),
    (11, "South Africa", "RSA", "South Africa"),
    (13, "New Zealand", "NZ", "New Zealand"),
    (5, "Sri Lanka", "SL", "Sri Lanka"),
    (6, "Bangladesh", "BAN", "Bangladesh"),
    (10, "West Indies", "WI", "West Indies"),
    (96, "Afghanistan", "AFG", "Afghanistan"),
]

# Approximate capacities, for sample purposes.
VENUES = [
    (9001, "Narendra Modi Stadium", "Ahmedabad", "India", 132000),
    (9002, "Eden Gardens", "Kolkata", "India", 68000),
    (9003, "Wankhede Stadium", "Mumbai", "India", 33108),
    (9004, "M. Chinnaswamy Stadium", "Bengaluru", "India", 40000),
    (9005, "Melbourne Cricket Ground", "Melbourne", "Australia", 100024),
    (9006, "Sydney Cricket Ground", "Sydney", "Australia", 48000),
    (9007, "Optus Stadium", "Perth", "Australia", 60000),
    (9008, "Adelaide Oval", "Adelaide", "Australia", 53583),
    (9009, "Lord's", "London", "England", 31100),
    (9010, "Old Trafford", "Manchester", "England", 26000),
    (9011, "Gaddafi Stadium", "Lahore", "Pakistan", 27000),
    (9012, "National Stadium", "Karachi", "Pakistan", 34228),
    (9013, "Newlands", "Cape Town", "South Africa", 25000),
    (9014, "The Wanderers", "Johannesburg", "South Africa", 34000),
    (9015, "Eden Park", "Auckland", "New Zealand", 50000),
    (9016, "R. Premadasa Stadium", "Colombo", "Sri Lanka", 35000),
    (9017, "Shere Bangla National Stadium", "Dhaka", "Bangladesh", 25000),
    (9018, "Kensington Oval", "Bridgetown", "West Indies", 28000),
    (9019, "Sharjah Cricket Stadium", "Sharjah", "Afghanistan", 27000),  # AFG home base
    (9020, "Arun Jaitley Stadium", "Delhi", "India", 41820),
]

FIRST_NAMES = ["Arjun", "Rohan", "Kabir", "Liam", "Oliver", "Jack", "Hamza", "Bilal", "Ethan",
               "Kieran", "Noah", "Kasun", "Dinesh", "Tamim", "Rafi", "Jason", "Shai", "Rashid",
               "Ibrahim", "Sam", "Harry", "Mitchell", "Aiden", "Tom", "Babar", "Zain", "Dev",
               "Nikhil", "Callum", "Pathum", "Litton", "Akeal", "Farid", "Marco", "Lewis", "Imad"]
LAST_NAMES = ["Sharma", "Mehta", "Rao", "Clarke", "Walsh", "Hughes", "Khan", "Ahmed", "Taylor",
              "Brooks", "Pieterse", "Naidoo", "Fernando", "Perera", "Hossain", "Rahman", "Holder",
              "Joseph", "Zadran", "Nabi", "Curran", "Stokes", "Marsh", "Green", "Latham", "Young",
              "Iyer", "Kapoor", "Jansen", "Mendis", "Das", "Charles", "Malik", "Bavuma", "Patel"]

FORMAT_OVERS = {"ODI": 50, "T20I": 20, "Test": 90}  # Test: overs per innings cap (simplified)


def _make_players(rng):
    """15 players per team: 5 batsmen, 1 keeper, 3 all-rounders, 6 bowlers."""
    players = []
    pid = 900001
    roles = (["Batsman"] * 5 + ["Wicket-keeper"] + ["All-rounder"] * 3 + ["Bowler"] * 6)
    used = set()
    for team_id, team_name, _, country in TEAMS:
        for role in roles:
            while True:
                name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
                if name not in used:
                    used.add(name)
                    break
            bat_style = rng.choice(["Right-hand bat"] * 3 + ["Left-hand bat"])
            if role in ("Bowler", "All-rounder"):
                bowl_style = rng.choice(["Right-arm fast", "Right-arm medium", "Left-arm fast",
                                         "Right-arm offbreak", "Legbreak googly",
                                         "Slow left-arm orthodox"])
            else:
                bowl_style = rng.choice([None, None, "Right-arm offbreak"])
            # Hidden skill numbers drive the random scores.
            bat_skill = {"Batsman": rng.uniform(30, 48), "Wicket-keeper": rng.uniform(25, 40),
                         "All-rounder": rng.uniform(22, 36), "Bowler": rng.uniform(5, 14)}[role]
            bowl_skill = {"Bowler": rng.uniform(0.9, 1.3), "All-rounder": rng.uniform(0.6, 1.0),
                          "Batsman": 0.0, "Wicket-keeper": 0.0}[role]
            players.append(dict(player_id=pid, full_name=name, country=country, team_id=team_id,
                                playing_role=role, batting_style=bat_style,
                                bowling_style=bowl_style, bat_skill=bat_skill,
                                bowl_skill=bowl_skill))
            pid += 1
    return players


def _batting_card(rng, xi, fmt, innings_no):
    """Return (rows, total_runs, wickets_lost) for one innings."""
    order = sorted(xi, key=lambda p: -p["bat_skill"])
    # Keep openers/keeper near the top, bowlers at the bottom.
    rows, total, wickets = [], 0, 0
    max_balls = FORMAT_OVERS[fmt] * 6
    balls_used = 0
    sr_base = {"T20I": 1.35, "ODI": 0.9, "Test": 0.55}[fmt]
    for pos, p in enumerate(order, start=1):
        if wickets >= 10 or balls_used >= max_balls:
            break
        mean = p["bat_skill"] * (1.1 if pos <= 4 else 0.85)
        if fmt == "T20I":
            mean *= 0.7
        cap = {"ODI": 185, "T20I": 120, "Test": 260}[fmt]
        runs = min(cap, max(0, int(rng.expovariate(1 / max(mean, 3)))))
        sr = max(30.0, rng.gauss(sr_base * 100, 18))
        balls = max(1, int(round(runs * 100 / sr))) if runs else rng.randint(1, 8)
        balls = min(balls, max_balls - balls_used) or 1
        runs = min(runs, int(balls * 3))
        balls_used += balls
        last_batter = pos == len(order)
        out = 0 if (last_batter or balls_used >= max_balls or rng.random() < 0.08) else 1
        wickets += out
        total += runs
        rows.append(dict(player_id=p["player_id"], team_id=p["team_id"], position=pos, runs=runs,
                         balls=balls, fours=runs // 9, sixes=runs // 25 if fmt != "Test" else runs // 60,
                         sr=round(runs * 100 / balls, 2), is_out=out,
                         dismissal=rng.choice(["caught", "bowled", "lbw", "run out", "stumped"])
                         if out else "not out"))
    total += rng.randint(3, 18)  # extras
    return rows, total, min(wickets, 10)


def _bowling_card(rng, xi, fmt, runs_conceded, wickets):
    """Split overs, runs and wickets across 5 bowlers."""
    bowlers = sorted([p for p in xi if p["bowl_skill"] > 0], key=lambda p: -p["bowl_skill"])[:5]
    if len(bowlers) < 5:
        bowlers += sorted(xi, key=lambda p: p["bat_skill"])[:5 - len(bowlers)]
    quota = {"ODI": 10, "T20I": 4, "Test": 25}[fmt]
    total_overs = {"ODI": 50, "T20I": 20, "Test": rng.randint(70, 110)}[fmt]
    weights = [b["bowl_skill"] + 0.2 for b in bowlers]
    rows = []
    overs_left, runs_left, wkts_left = total_overs, runs_conceded, wickets
    for i, b in enumerate(bowlers):
        last = i == len(bowlers) - 1
        overs = overs_left if last else min(quota, max(1, round(total_overs * weights[i] / sum(weights))))
        overs = max(1, min(overs, overs_left)) if overs_left > 0 else 1
        overs_left -= overs
        share = overs / total_overs
        runs = runs_left if last else max(0, int(runs_conceded * share * rng.uniform(0.75, 1.25)))
        runs = max(0, min(runs, runs_left))
        runs_left -= runs
        wk = wkts_left if last else min(wkts_left, int(round(wickets * weights[i] / sum(weights)
                                                              * rng.uniform(0.5, 1.6))))
        wkts_left -= wk
        rows.append(dict(player_id=b["player_id"], team_id=b["team_id"], overs=float(overs),
                         maidens=rng.randint(0, 2 if fmt != "T20I" else 0), runs=runs,
                         wickets=wk, econ=round(runs / overs, 2) if overs else None))
    return rows


def seed_sample_data(reset=True, n_matches=900):
    """Create schema and fill it with sample data. Returns a summary dict."""
    rng = random.Random(SEED)
    init_schema()
    if reset:
        # Remove only sample rows; API and manually added rows are kept.
        with transaction() as conn:
            conn.execute("DELETE FROM matches WHERE source = 'sample'")   # cascades to innings
            conn.execute("DELETE FROM series WHERE series_id BETWEEN 90001 AND 99999")
            conn.execute("DELETE FROM players WHERE source = 'sample'")

    # Teams/venues: insert if missing, otherwise fill in the details.
    execute_many("""INSERT INTO teams VALUES (?, ?, ?, ?)
                    ON CONFLICT(team_id) DO UPDATE SET country = excluded.country""", TEAMS)
    execute_many("""INSERT INTO venues VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(venue_id) DO UPDATE SET country = excluded.country,
                                                       capacity = excluded.capacity""", VENUES)

    players = _make_players(rng)
    execute_many(
        "INSERT OR REPLACE INTO players (player_id, full_name, country, team_id, playing_role, "
        "batting_style, bowling_style, source) VALUES (?, ?, ?, ?, ?, ?, ?, 'sample')",
        [(p["player_id"], p["full_name"], p["country"], p["team_id"], p["playing_role"],
          p["batting_style"], p["bowling_style"]) for p in players])
    by_team = {}
    for p in players:
        by_team.setdefault(p["team_id"], []).append(p)
    venues_by_country = {}
    for v in VENUES:
        venues_by_country.setdefault(v[3], []).append(v[0])
    team_country = {t[0]: t[3] for t in TEAMS}
    team_name = {t[0]: t[1] for t in TEAMS}

    # Matches spread from Jan 2020 up to yesterday, so "last 30 days" has results.
    start, end = date(2020, 1, 5), date.today() - timedelta(days=1)
    span = (end - start).days
    dates = sorted(start + timedelta(days=rng.randint(0, span)) for _ in range(n_matches))
    dates[-6:] = [end - timedelta(days=d) for d in (25, 18, 12, 7, 3, 1)]
    dates.sort()

    series_rows, match_rows, bat_rows, bowl_rows = [], [], [], []
    series_id = 90001
    i = 0
    match_id = 9000001
    while i < len(dates):
        # Group 3-5 consecutive matches into one bilateral series.
        size = rng.randint(3, 5)
        chunk = dates[i:i + size]
        i += size
        t1, t2 = rng.sample([t[0] for t in TEAMS], 2)
        host = team_country[t1]
        fmt = rng.choices(["ODI", "T20I", "Test"], weights=[40, 35, 25])[0]
        sname = f"{team_name[t2]} tour of {host} {chunk[0].year} ({fmt})"
        series_rows.append((series_id, sname, host, fmt, chunk[0].isoformat(),
                            chunk[-1].isoformat(), len(chunk)))
        for n, d in enumerate(chunk, start=1):
            home_venues = venues_by_country.get(host) or [v[0] for v in VENUES]
            venue = rng.choice(home_venues) if rng.random() < 0.85 else rng.choice(VENUES)[0]
            toss_winner = rng.choice([t1, t2])
            decision = rng.choice(["bat", "bowl"])
            first = toss_winner if decision == "bat" else (t2 if toss_winner == t1 else t1)
            second = t2 if first == t1 else t1
            xi_first = rng.sample(by_team[first], 11)
            xi_second = rng.sample(by_team[second], 11)
            n_innings = 4 if fmt == "Test" else 2
            totals = {first: 0, second: 0}
            last_wickets = 0
            for inn in range(1, n_innings + 1):
                bat_team, xi_bat, xi_bowl = ((first, xi_first, xi_second) if inn % 2 == 1
                                             else (second, xi_second, xi_first))
                card, total, wkts = _batting_card(rng, xi_bat, fmt, inn)
                # Home advantage: a small boost for the host side.
                if team_country[bat_team] == host:
                    total += rng.randint(0, 15)
                totals[bat_team] += total
                last_wickets = wkts
                for r in card:
                    bat_rows.append((match_id, inn, r["player_id"], r["team_id"], r["position"],
                                     r["runs"], r["balls"], r["fours"], r["sixes"], r["sr"],
                                     r["is_out"], r["dismissal"]))
                for b in _bowling_card(rng, xi_bowl, fmt, total, wkts):
                    bowl_rows.append((match_id, inn, b["player_id"], b["team_id"], b["overs"],
                                      b["maidens"], b["runs"], b["wickets"], b["econ"]))
            if totals[second] > totals[first]:
                winner, vtype, margin = second, "wickets", max(1, 10 - last_wickets)
            else:
                winner, vtype = first, "runs"
                margin = max(1, totals[first] - totals[second])
            # Recent matches: keep a couple "Upcoming"/"In Progress" for the live page demo.
            status = f"{team_name[winner]} won by {margin} {'runs' if vtype == 'runs' else 'wkts'}"
            match_rows.append((match_id, series_id, f"{n}{_suffix(n)} {fmt}", fmt, first, second,
                               venue, d.isoformat(), "Complete", status, toss_winner, decision,
                               winner, margin, vtype))
            match_id += 1
        series_id += 1

    execute_many("INSERT OR REPLACE INTO series VALUES (?, ?, ?, ?, ?, ?, ?)", series_rows)
    execute_many(
        "INSERT OR REPLACE INTO matches (match_id, series_id, match_desc, match_format, team1_id, "
        "team2_id, venue_id, match_date, state, status, toss_winner_id, toss_decision, winner_id, "
        "victory_margin, victory_type, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
        "'sample')", match_rows)
    execute_many(
        "INSERT OR REPLACE INTO batting_innings (match_id, innings_no, player_id, team_id, "
        "batting_position, runs, balls, fours, sixes, strike_rate, is_out, dismissal) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", bat_rows)
    execute_many(
        "INSERT OR REPLACE INTO bowling_innings (match_id, innings_no, player_id, team_id, overs, "
        "maidens, runs_conceded, wickets, economy) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", bowl_rows)

    rebuild_career_stats(rng)
    return {"players": len(players), "series": len(series_rows), "matches": len(match_rows),
            "batting_rows": len(bat_rows), "bowling_rows": len(bowl_rows)}


def rebuild_career_stats(rng=None):
    """Recalculate player_career_stats from the innings tables."""
    rng = rng or random.Random(SEED)
    with transaction() as conn:
        conn.execute("DELETE FROM player_career_stats")
        conn.execute("""
            INSERT INTO player_career_stats
                (player_id, format, matches, innings, runs, highest_score, batting_average,
                 strike_rate, hundreds, fifties, wickets, bowling_average, economy)
            SELECT p.player_id, f.fmt,
                   COALESCE(bat.matches, bowl.matches, 0),
                   COALESCE(bat.innings, 0), COALESCE(bat.runs, 0), COALESCE(bat.hs, 0),
                   CASE WHEN bat.outs > 0 THEN ROUND(1.0 * bat.runs / bat.outs, 2) END,
                   CASE WHEN bat.balls > 0 THEN ROUND(100.0 * bat.runs / bat.balls, 2) END,
                   COALESCE(bat.hundreds, 0), COALESCE(bat.fifties, 0),
                   COALESCE(bowl.wkts, 0),
                   CASE WHEN bowl.wkts > 0 THEN ROUND(1.0 * bowl.runs / bowl.wkts, 2) END,
                   CASE WHEN bowl.overs > 0 THEN ROUND(bowl.runs / bowl.overs, 2) END
            FROM players p
            CROSS JOIN (SELECT 'Test' AS fmt UNION ALL SELECT 'ODI' UNION ALL SELECT 'T20I') f
            LEFT JOIN (
                SELECT b.player_id, m.match_format AS fmt,
                       COUNT(DISTINCT b.match_id) AS matches, COUNT(*) AS innings,
                       SUM(b.runs) AS runs, MAX(b.runs) AS hs, SUM(b.balls) AS balls,
                       SUM(b.is_out) AS outs,
                       SUM(CASE WHEN b.runs >= 100 THEN 1 ELSE 0 END) AS hundreds,
                       SUM(CASE WHEN b.runs BETWEEN 50 AND 99 THEN 1 ELSE 0 END) AS fifties
                FROM batting_innings b JOIN matches m ON m.match_id = b.match_id
                GROUP BY b.player_id, m.match_format
            ) bat ON bat.player_id = p.player_id AND bat.fmt = f.fmt
            LEFT JOIN (
                SELECT w.player_id, m.match_format AS fmt,
                       COUNT(DISTINCT w.match_id) AS matches, SUM(w.wickets) AS wkts,
                       SUM(w.runs_conceded) AS runs, SUM(w.overs) AS overs
                FROM bowling_innings w JOIN matches m ON m.match_id = w.match_id
                GROUP BY w.player_id, m.match_format
            ) bowl ON bowl.player_id = p.player_id AND bowl.fmt = f.fmt
            WHERE bat.player_id IS NOT NULL OR bowl.player_id IS NOT NULL
        """)
        # Fielding numbers are not in scorecards; approximate them per match.
        rows = conn.execute("""SELECT c.player_id, c.format, c.matches, p.playing_role
                               FROM player_career_stats c JOIN players p USING (player_id)""").fetchall()
        updates = []
        for pid, fmt, m, role in rows:
            keeper = role == "Wicket-keeper"
            catches = int(m * (rng.uniform(0.9, 1.4) if keeper else rng.uniform(0.2, 0.5)))
            stumpings = int(m * rng.uniform(0.1, 0.3)) if keeper and fmt != "Test" else (
                int(m * 0.05) if keeper else 0)
            updates.append((catches, stumpings, pid, fmt))
        conn.executemany("UPDATE player_career_stats SET catches = ?, stumpings = ? "
                         "WHERE player_id = ? AND format = ?", updates)


def _suffix(n):
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


if __name__ == "__main__":
    print(seed_sample_data())
