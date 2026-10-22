"""The 25 SQL practice questions from the project brief.

Each entry has: id, level, title, question (from the brief) and sql.
Queries are written in SQLite syntax. Date functions (date(), strftime())
are the only SQLite-specific parts; see README for MySQL/PostgreSQL notes.
"""

QUERIES = [
    # ------------------------------------------------------------------ BEGINNER
    {
        "id": 1, "level": "Beginner", "title": "Players who represent India",
        "question": "Find all players who represent India. Display their full name, playing "
                    "role, batting style, and bowling style.",
        "sql": """
SELECT full_name, playing_role, batting_style, bowling_style
FROM players
WHERE country = 'India'
ORDER BY playing_role, full_name;""",
    },
    {
        "id": 2, "level": "Beginner", "title": "Matches in the last 30 days",
        "question": "Show all cricket matches that were played in the last 30 days. Include the "
                    "match description, both team names, venue name with city, and the match "
                    "date. Sort by most recent matches first.",
        "sql": """
SELECT match_desc,
       team1,
       team2,
       venue_name || ', ' || city AS venue,
       match_date
FROM v_match_details
WHERE match_date >= date('now', '-30 days')
  AND match_date <= date('now')
ORDER BY match_date DESC;""",
    },
    {
        "id": 3, "level": "Beginner", "title": "Top 10 ODI run scorers",
        "question": "List the top 10 highest run scorers in ODI cricket. Show player name, total "
                    "runs scored, batting average, and number of centuries.",
        "sql": """
SELECT p.full_name,
       c.runs            AS total_runs,
       c.batting_average,
       c.hundreds        AS centuries
FROM player_career_stats c
JOIN players p ON p.player_id = c.player_id
WHERE c.format = 'ODI'
ORDER BY c.runs DESC
LIMIT 10;""",
    },
    {
        "id": 4, "level": "Beginner", "title": "Venues with capacity over 50,000",
        "question": "Display all cricket venues that have a seating capacity of more than 50,000 "
                    "spectators. Order by largest capacity first.",
        "sql": """
SELECT venue_name, city, country, capacity
FROM venues
WHERE capacity > 50000
ORDER BY capacity DESC;""",
    },
    {
        "id": 5, "level": "Beginner", "title": "Total wins per team",
        "question": "Calculate how many matches each team has won. Display teams with most wins "
                    "first.",
        "sql": """
SELECT t.team_name,
       COUNT(m.match_id) AS total_wins
FROM teams t
LEFT JOIN matches m ON m.winner_id = t.team_id
GROUP BY t.team_id, t.team_name
ORDER BY total_wins DESC;""",
    },
    {
        "id": 6, "level": "Beginner", "title": "Players per playing role",
        "question": "Count how many players belong to each playing role.",
        "sql": """
SELECT playing_role,
       COUNT(*) AS player_count
FROM players
WHERE playing_role IS NOT NULL
GROUP BY playing_role
ORDER BY player_count DESC;""",
    },
    {
        "id": 7, "level": "Beginner", "title": "Highest individual score per format",
        "question": "Find the highest individual batting score achieved in each cricket format "
                    "(Test, ODI, T20I).",
        "sql": """
SELECT m.match_format AS format,
       MAX(b.runs)    AS highest_score
FROM batting_innings b
JOIN matches m ON m.match_id = b.match_id
GROUP BY m.match_format
ORDER BY highest_score DESC;""",
    },
    {
        "id": 8, "level": "Beginner", "title": "Series that started in 2024",
        "question": "Show all cricket series that started in the year 2024. Include series name, "
                    "host country, match type, start date, and total number of matches planned.",
        "sql": """
SELECT series_name, host_country, match_type, start_date, total_matches
FROM series
WHERE start_date >= '2024-01-01'
  AND start_date <  '2025-01-01'
ORDER BY start_date;""",
    },
    # -------------------------------------------------------------- INTERMEDIATE
    {
        "id": 9, "level": "Intermediate", "title": "All-rounders: 1000+ runs and 50+ wickets",
        "question": "Find all-rounder players who have scored more than 1000 runs AND taken more "
                    "than 50 wickets in their career. Display player name, total runs, total "
                    "wickets, and the cricket format.",
        "sql": """
SELECT p.full_name, c.runs AS total_runs, c.wickets AS total_wickets, c.format
FROM player_career_stats c
JOIN players p ON p.player_id = c.player_id
WHERE p.playing_role = 'All-rounder'
  AND c.runs > 1000
  AND c.wickets > 50
ORDER BY c.runs + c.wickets * 20 DESC;""",
    },
    {
        "id": 10, "level": "Intermediate", "title": "Last 20 completed matches",
        "question": "Get details of the last 20 completed matches. Show match description, both "
                    "team names, winning team, victory margin, victory type, and venue name.",
        "sql": """
SELECT match_desc, team1, team2, winner, victory_margin, victory_type, venue_name, match_date
FROM v_match_details
WHERE state = 'Complete'
  AND winner IS NOT NULL
ORDER BY match_date DESC, match_id DESC
LIMIT 20;""",
    },
    {
        "id": 11, "level": "Intermediate", "title": "Runs across formats",
        "question": "For players who have played at least 2 different formats, show their total "
                    "runs in Test, ODI and T20I, along with their overall batting average.",
        "sql": """
SELECT p.full_name,
       SUM(CASE WHEN c.format = 'Test' THEN c.runs ELSE 0 END) AS test_runs,
       SUM(CASE WHEN c.format = 'ODI'  THEN c.runs ELSE 0 END) AS odi_runs,
       SUM(CASE WHEN c.format = 'T20I' THEN c.runs ELSE 0 END) AS t20i_runs,
       -- overall average = total runs / total dismissals (dismissals = runs / average)
       ROUND(SUM(c.runs) * 1.0 /
             NULLIF(SUM(CASE WHEN c.batting_average > 0 THEN c.runs / c.batting_average END), 0),
             2) AS overall_average
FROM player_career_stats c
JOIN players p ON p.player_id = c.player_id
WHERE c.innings > 0
GROUP BY p.player_id, p.full_name
HAVING COUNT(DISTINCT c.format) >= 2
ORDER BY SUM(c.runs) DESC;""",
    },
    {
        "id": 12, "level": "Intermediate", "title": "Home vs away wins",
        "question": "Analyze each team's performance at home versus away (home = venue country "
                    "matches the team's country). Count wins in both conditions.",
        "sql": """
WITH team_matches AS (
    SELECT match_id, team1_id AS team_id FROM matches
    UNION ALL
    SELECT match_id, team2_id AS team_id FROM matches
)
SELECT t.team_name,
       SUM(CASE WHEN v.country =  t.country THEN 1 ELSE 0 END) AS home_matches,
       SUM(CASE WHEN v.country =  t.country AND m.winner_id = t.team_id THEN 1 ELSE 0 END) AS home_wins,
       SUM(CASE WHEN v.country <> t.country THEN 1 ELSE 0 END) AS away_matches,
       SUM(CASE WHEN v.country <> t.country AND m.winner_id = t.team_id THEN 1 ELSE 0 END) AS away_wins
FROM team_matches tm
JOIN matches m ON m.match_id = tm.match_id
JOIN teams   t ON t.team_id  = tm.team_id
JOIN venues  v ON v.venue_id = m.venue_id
GROUP BY t.team_id, t.team_name
ORDER BY home_wins + away_wins DESC;""",
    },
    {
        "id": 13, "level": "Intermediate", "title": "100+ run partnerships",
        "question": "Identify batting partnerships where two consecutive batsmen (adjacent "
                    "batting positions) scored a combined 100 or more runs in the same innings.",
        "sql": """
SELECT p1.full_name AS batter_1,
       p2.full_name AS batter_2,
       a.runs + b.runs AS partnership_runs,
       a.innings_no,
       a.match_id
FROM batting_innings a
JOIN batting_innings b
  ON  b.match_id = a.match_id
  AND b.innings_no = a.innings_no
  AND b.batting_position = a.batting_position + 1
JOIN players p1 ON p1.player_id = a.player_id
JOIN players p2 ON p2.player_id = b.player_id
WHERE a.runs + b.runs >= 100
ORDER BY partnership_runs DESC;""",
    },
    {
        "id": 14, "level": "Intermediate", "title": "Bowling at each venue",
        "question": "For bowlers who have played at least 3 matches at the same venue (bowling at "
                    "least 4 overs in each), calculate average economy, total wickets and matches.",
        "sql": """
SELECT p.full_name AS bowler,
       v.venue_name,
       COUNT(DISTINCT w.match_id)  AS matches_played,
       SUM(w.wickets)              AS total_wickets,
       ROUND(AVG(w.economy), 2)    AS avg_economy
FROM bowling_innings w
JOIN matches m ON m.match_id = w.match_id
JOIN venues  v ON v.venue_id = m.venue_id
JOIN players p ON p.player_id = w.player_id
WHERE w.overs >= 4
GROUP BY w.player_id, p.full_name, v.venue_id, v.venue_name
HAVING COUNT(DISTINCT w.match_id) >= 3
ORDER BY avg_economy ASC;""",
    },
    {
        "id": 15, "level": "Intermediate", "title": "Performers in close matches",
        "question": "A close match is decided by < 50 runs OR < 5 wickets. For these, calculate "
                    "each player's average runs, close matches played, and close matches their "
                    "team won when they batted.",
        "sql": """
WITH close_matches AS (
    SELECT match_id, winner_id
    FROM matches
    WHERE (victory_type = 'runs'    AND victory_margin < 50)
       OR (victory_type = 'wickets' AND victory_margin < 5)
)
SELECT p.full_name,
       ROUND(AVG(b.runs), 2)                 AS avg_runs,
       COUNT(DISTINCT b.match_id)            AS close_matches_played,
       COUNT(DISTINCT CASE WHEN cm.winner_id = b.team_id THEN b.match_id END) AS close_matches_won
FROM batting_innings b
JOIN close_matches cm ON cm.match_id = b.match_id
JOIN players p        ON p.player_id = b.player_id
GROUP BY b.player_id, p.full_name
HAVING COUNT(DISTINCT b.match_id) >= 5
ORDER BY avg_runs DESC
LIMIT 25;""",
    },
    {
        "id": 16, "level": "Intermediate", "title": "Yearly batting since 2020",
        "question": "For matches since 2020, show each player's average runs per match and average "
                    "strike rate for each year (players with at least 5 matches that year).",
        "sql": """
SELECT p.full_name,
       strftime('%Y', m.match_date)                            AS year,
       COUNT(DISTINCT b.match_id)                              AS matches,
       ROUND(SUM(b.runs) * 1.0 / COUNT(DISTINCT b.match_id), 2) AS avg_runs_per_match,
       ROUND(AVG(b.strike_rate), 2)                            AS avg_strike_rate
FROM batting_innings b
JOIN matches m ON m.match_id = b.match_id
JOIN players p ON p.player_id = b.player_id
WHERE m.match_date >= '2020-01-01'
GROUP BY b.player_id, p.full_name, strftime('%Y', m.match_date)
HAVING COUNT(DISTINCT b.match_id) >= 5
ORDER BY p.full_name, year;""",
    },
    # ------------------------------------------------------------------ ADVANCED
    {
        "id": 17, "level": "Advanced", "title": "Does winning the toss help?",
        "question": "What percentage of matches are won by the toss winner, broken down by toss "
                    "decision (bat first or bowl first)?",
        "sql": """
SELECT toss_decision,
       COUNT(*)                                                   AS matches,
       SUM(CASE WHEN winner_id = toss_winner_id THEN 1 ELSE 0 END) AS toss_winner_won,
       ROUND(100.0 * SUM(CASE WHEN winner_id = toss_winner_id THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                                  AS win_percentage
FROM matches
WHERE toss_winner_id IS NOT NULL
  AND winner_id IS NOT NULL
GROUP BY toss_decision;""",
    },
    {
        "id": 18, "level": "Advanced", "title": "Most economical limited-overs bowlers",
        "question": "Find the most economical bowlers in ODI and T20 cricket (at least 10 matches "
                    "and at least 2 overs per match on average). Show economy and wickets.",
        "sql": """
SELECT p.full_name AS bowler,
       COUNT(DISTINCT w.match_id)                       AS matches,
       ROUND(SUM(w.overs) / COUNT(DISTINCT w.match_id), 2) AS overs_per_match,
       SUM(w.wickets)                                   AS total_wickets,
       ROUND(SUM(w.runs_conceded) / SUM(w.overs), 2)    AS economy_rate
FROM bowling_innings w
JOIN matches m ON m.match_id = w.match_id
JOIN players p ON p.player_id = w.player_id
WHERE m.match_format IN ('ODI', 'T20I')
GROUP BY w.player_id, p.full_name
HAVING COUNT(DISTINCT w.match_id) >= 10
   AND SUM(w.overs) / COUNT(DISTINCT w.match_id) >= 2
ORDER BY economy_rate ASC
LIMIT 20;""",
    },
    {
        "id": 19, "level": "Advanced", "title": "Most consistent batsmen",
        "question": "Calculate average runs and standard deviation of runs per player (innings "
                    "with 10+ balls faced, since 2022). Lower standard deviation = more consistent.",
        "sql": """
SELECT p.full_name,
       COUNT(*)                AS innings,
       ROUND(AVG(b.runs), 2)   AS avg_runs,
       -- population standard deviation: sqrt(mean of squares - square of mean)
       ROUND(SQRT(AVG(b.runs * b.runs) - AVG(b.runs) * AVG(b.runs)), 2) AS std_dev_runs
FROM batting_innings b
JOIN matches m ON m.match_id = b.match_id
JOIN players p ON p.player_id = b.player_id
WHERE b.balls >= 10
  AND m.match_date >= '2022-01-01'
GROUP BY b.player_id, p.full_name
HAVING COUNT(*) >= 10 AND AVG(b.runs) >= 20
ORDER BY std_dev_runs ASC
LIMIT 20;""",
    },
    {
        "id": 20, "level": "Advanced", "title": "Matches and averages by format",
        "question": "Show the count of Test, ODI and T20 matches for each player with their batting "
                    "average in each. Only players with 20+ total matches.",
        "sql": """
SELECT p.full_name,
       SUM(CASE WHEN c.format = 'Test' THEN c.matches ELSE 0 END)        AS test_matches,
       MAX(CASE WHEN c.format = 'Test' THEN c.batting_average END)        AS test_avg,
       SUM(CASE WHEN c.format = 'ODI'  THEN c.matches ELSE 0 END)        AS odi_matches,
       MAX(CASE WHEN c.format = 'ODI'  THEN c.batting_average END)        AS odi_avg,
       SUM(CASE WHEN c.format = 'T20I' THEN c.matches ELSE 0 END)        AS t20i_matches,
       MAX(CASE WHEN c.format = 'T20I' THEN c.batting_average END)        AS t20i_avg,
       SUM(c.matches)                                                     AS total_matches
FROM player_career_stats c
JOIN players p ON p.player_id = c.player_id
GROUP BY p.player_id, p.full_name
HAVING SUM(c.matches) >= 20
ORDER BY total_matches DESC;""",
    },
    {
        "id": 21, "level": "Advanced", "title": "Weighted player ranking",
        "question": "Rank players per format using: batting = runs*0.01 + avg*0.5 + SR*0.3; "
                    "bowling = wickets*2 + (50-bowl avg)*0.5 + (6-economy)*2; "
                    "fielding = catches*3 + stumpings*5.",
        "sql": """
WITH scores AS (
    SELECT p.full_name,
           c.format,
           c.runs * 0.01 + COALESCE(c.batting_average, 0) * 0.5
                         + COALESCE(c.strike_rate, 0) * 0.3                 AS batting_points,
           -- bowling points only count for players who have taken wickets
           CASE WHEN c.wickets > 0
                THEN c.wickets * 2 + (50 - c.bowling_average) * 0.5 + (6 - c.economy) * 2
                ELSE 0 END                                                AS bowling_points,
           c.catches * 3 + c.stumpings * 5                                AS fielding_points
    FROM player_career_stats c
    JOIN players p ON p.player_id = c.player_id
),
ranked AS (
    SELECT *,
           ROUND(batting_points + bowling_points + fielding_points, 2) AS total_score,
           RANK() OVER (PARTITION BY format
                        ORDER BY batting_points + bowling_points + fielding_points DESC) AS rank_in_format
    FROM scores
)
SELECT format, rank_in_format, full_name,
       ROUND(batting_points, 2)  AS batting_points,
       ROUND(bowling_points, 2)  AS bowling_points,
       fielding_points,
       total_score
FROM ranked
WHERE rank_in_format <= 10
ORDER BY format, rank_in_format;""",
    },
    {
        "id": 22, "level": "Advanced", "title": "Head-to-head analysis",
        "question": "For team pairs with 5+ matches in the last 3 years: total matches, wins each, "
                    "average victory margin, wins batting first vs chasing, win percentage.",
        "sql": """
WITH recent AS (
    SELECT m.*,
           CASE WHEN m.team1_id < m.team2_id THEN m.team1_id ELSE m.team2_id END AS team_a,
           CASE WHEN m.team1_id < m.team2_id THEN m.team2_id ELSE m.team1_id END AS team_b,
           -- who batted first: toss winner if they chose to bat, otherwise the other side
           CASE WHEN m.toss_decision = 'bat' THEN m.toss_winner_id
                WHEN m.toss_winner_id = m.team1_id THEN m.team2_id
                ELSE m.team1_id END AS batted_first_id
    FROM matches m
    WHERE m.match_date >= date('now', '-3 years')
      AND m.winner_id IS NOT NULL
)
SELECT ta.team_name AS team_a,
       tb.team_name AS team_b,
       COUNT(*) AS matches,
       SUM(CASE WHEN winner_id = team_a THEN 1 ELSE 0 END) AS team_a_wins,
       SUM(CASE WHEN winner_id = team_b THEN 1 ELSE 0 END) AS team_b_wins,
       ROUND(AVG(CASE WHEN winner_id = team_a AND victory_type = 'runs'    THEN victory_margin END), 1) AS a_avg_win_by_runs,
       ROUND(AVG(CASE WHEN winner_id = team_a AND victory_type = 'wickets' THEN victory_margin END), 1) AS a_avg_win_by_wkts,
       ROUND(AVG(CASE WHEN winner_id = team_b AND victory_type = 'runs'    THEN victory_margin END), 1) AS b_avg_win_by_runs,
       ROUND(AVG(CASE WHEN winner_id = team_b AND victory_type = 'wickets' THEN victory_margin END), 1) AS b_avg_win_by_wkts,
       SUM(CASE WHEN winner_id = team_a AND batted_first_id = team_a THEN 1 ELSE 0 END) AS a_wins_batting_first,
       SUM(CASE WHEN winner_id = team_a AND batted_first_id <> team_a THEN 1 ELSE 0 END) AS a_wins_chasing,
       SUM(CASE WHEN winner_id = team_b AND batted_first_id = team_b THEN 1 ELSE 0 END) AS b_wins_batting_first,
       SUM(CASE WHEN winner_id = team_b AND batted_first_id <> team_b THEN 1 ELSE 0 END) AS b_wins_chasing,
       ROUND(100.0 * SUM(CASE WHEN winner_id = team_a THEN 1 ELSE 0 END) / COUNT(*), 1) AS team_a_win_pct,
       ROUND(100.0 * SUM(CASE WHEN winner_id = team_b THEN 1 ELSE 0 END) / COUNT(*), 1) AS team_b_win_pct
FROM recent r
JOIN teams ta ON ta.team_id = r.team_a
JOIN teams tb ON tb.team_id = r.team_b
GROUP BY team_a, team_b, ta.team_name, tb.team_name
HAVING COUNT(*) >= 5
ORDER BY matches DESC;""",
    },
    {
        "id": 23, "level": "Advanced", "title": "Recent form and momentum",
        "question": "For each player's last 10 innings: average of last 5 vs last 10, strike rate "
                    "trend, scores of 50+, consistency (std dev), and a form category.",
        "sql": """
WITH numbered AS (
    SELECT b.player_id, b.runs, b.strike_rate,
           ROW_NUMBER() OVER (PARTITION BY b.player_id
                              ORDER BY m.match_date DESC, b.match_id DESC, b.innings_no DESC) AS rn
    FROM batting_innings b
    JOIN matches m ON m.match_id = b.match_id
),
last10 AS (
    SELECT player_id,
           AVG(CASE WHEN rn <= 5 THEN runs END)         AS avg_last5,
           AVG(runs)                                     AS avg_last10,
           AVG(CASE WHEN rn <= 5 THEN strike_rate END)  AS sr_last5,
           AVG(strike_rate)                              AS sr_last10,
           SUM(CASE WHEN runs >= 50 THEN 1 ELSE 0 END)  AS fifties_plus,
           SQRT(AVG(runs * runs) - AVG(runs) * AVG(runs)) AS std_dev
    FROM numbered
    WHERE rn <= 10
    GROUP BY player_id
    HAVING COUNT(*) = 10
)
SELECT p.full_name,
       ROUND(avg_last5, 1)  AS avg_last_5,
       ROUND(avg_last10, 1) AS avg_last_10,
       ROUND(sr_last5, 1)   AS sr_last_5,
       ROUND(sr_last10, 1)  AS sr_last_10,
       fifties_plus,
       ROUND(std_dev, 1)    AS consistency_std_dev,
       CASE WHEN avg_last5 >= 45 AND fifties_plus >= 3 THEN 'Excellent Form'
            WHEN avg_last5 >= 30 OR  fifties_plus >= 2 THEN 'Good Form'
            WHEN avg_last5 >= 15                       THEN 'Average Form'
            ELSE 'Poor Form' END AS form_category
FROM last10 l
JOIN players p ON p.player_id = l.player_id
ORDER BY avg_last5 DESC;""",
    },
    {
        "id": 24, "level": "Advanced", "title": "Best batting pairs",
        "question": "For pairs who batted at consecutive positions in 5+ partnerships: average "
                    "partnership, partnerships over 50, highest, success rate. Rank them.",
        "sql": """
WITH pairs AS (
    SELECT CASE WHEN a.player_id < b.player_id THEN a.player_id ELSE b.player_id END AS p1,
           CASE WHEN a.player_id < b.player_id THEN b.player_id ELSE a.player_id END AS p2,
           a.runs + b.runs AS partnership
    FROM batting_innings a
    JOIN batting_innings b
      ON  b.match_id = a.match_id
      AND b.innings_no = a.innings_no
      AND b.batting_position = a.batting_position + 1
)
SELECT pl1.full_name AS batter_1,
       pl2.full_name AS batter_2,
       COUNT(*)                                            AS partnerships,
       ROUND(AVG(partnership), 1)                          AS avg_partnership,
       SUM(CASE WHEN partnership > 50 THEN 1 ELSE 0 END)   AS fifty_plus,
       MAX(partnership)                                    AS highest,
       ROUND(100.0 * SUM(CASE WHEN partnership > 50 THEN 1 ELSE 0 END) / COUNT(*), 1) AS success_rate_pct,
       RANK() OVER (ORDER BY AVG(partnership) DESC)        AS pair_rank
FROM pairs
JOIN players pl1 ON pl1.player_id = pairs.p1
JOIN players pl2 ON pl2.player_id = pairs.p2
GROUP BY p1, p2, pl1.full_name, pl2.full_name
HAVING COUNT(*) >= 5
ORDER BY pair_rank
LIMIT 25;""",
    },
    {
        "id": 25, "level": "Advanced", "title": "Career trajectory by quarter",
        "question": "Track quarterly average runs and strike rate, compare each quarter to the "
                    "previous one, and classify career phase (Ascending / Declining / Stable). "
                    "Players with 6+ quarters and 3+ matches per quarter.",
        "sql": """
WITH quarterly AS (
    SELECT b.player_id,
           strftime('%Y', m.match_date) || '-Q' ||
               ((CAST(strftime('%m', m.match_date) AS INTEGER) - 1) / 3 + 1) AS quarter,
           COUNT(DISTINCT b.match_id) AS matches,
           AVG(b.runs)                AS avg_runs,
           AVG(b.strike_rate)         AS avg_sr
    FROM batting_innings b
    JOIN matches m ON m.match_id = b.match_id
    GROUP BY b.player_id, quarter
    HAVING COUNT(DISTINCT b.match_id) >= 3
),
compared AS (
    SELECT q.*,
           LAG(avg_runs) OVER (PARTITION BY player_id ORDER BY quarter) AS prev_avg,
           CASE WHEN LAG(avg_runs) OVER (PARTITION BY player_id ORDER BY quarter) IS NULL THEN NULL
                WHEN avg_runs > LAG(avg_runs) OVER (PARTITION BY player_id ORDER BY quarter) * 1.10 THEN 'Improving'
                WHEN avg_runs < LAG(avg_runs) OVER (PARTITION BY player_id ORDER BY quarter) * 0.90 THEN 'Declining'
                ELSE 'Stable' END AS trend,
           ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY quarter)      AS q_first,
           ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY quarter DESC) AS q_last
    FROM quarterly q
),
summary AS (
    SELECT player_id,
           COUNT(*)                                                AS quarters,
           SUM(CASE WHEN trend = 'Improving' THEN 1 ELSE 0 END)   AS improving,
           SUM(CASE WHEN trend = 'Declining' THEN 1 ELSE 0 END)   AS declining,
           MAX(CASE WHEN q_first = 1 THEN avg_runs END)           AS first_q_avg,
           MAX(CASE WHEN q_last  = 1 THEN avg_runs END)           AS last_q_avg,
           ROUND(AVG(avg_sr), 1)                                  AS avg_strike_rate
    FROM compared
    GROUP BY player_id
    HAVING COUNT(*) >= 6
)
SELECT p.full_name,
       s.quarters,
       ROUND(s.first_q_avg, 1) AS first_quarter_avg,
       ROUND(s.last_q_avg, 1)  AS latest_quarter_avg,
       s.avg_strike_rate,
       s.improving AS quarters_improving,
       s.declining AS quarters_declining,
       CASE WHEN s.last_q_avg > s.first_q_avg * 1.15 AND s.improving >= s.declining THEN 'Career Ascending'
            WHEN s.last_q_avg < s.first_q_avg * 0.85 AND s.declining >= s.improving THEN 'Career Declining'
            ELSE 'Career Stable' END AS career_phase
FROM summary s
JOIN players p ON p.player_id = s.player_id
ORDER BY s.quarters DESC, p.full_name;""",
    },
]

QUERIES_BY_ID = {q["id"]: q for q in QUERIES}
