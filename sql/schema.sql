-- =====================================================================
-- Cricbuzz LiveStats - database schema
-- Written for SQLite; uses standard SQL so it ports to MySQL/PostgreSQL
-- with minor type changes (see README).
-- =====================================================================

-- Teams (international sides). team_id matches Cricbuzz team IDs.
CREATE TABLE IF NOT EXISTS teams (
    team_id      INTEGER PRIMARY KEY,
    team_name    TEXT    NOT NULL UNIQUE,
    short_name   TEXT,
    country      TEXT
);

-- Venues (grounds)
CREATE TABLE IF NOT EXISTS venues (
    venue_id     INTEGER PRIMARY KEY,
    venue_name   TEXT    NOT NULL,
    city         TEXT,
    country      TEXT,
    capacity     INTEGER CHECK (capacity IS NULL OR capacity >= 0)
);

-- Players
CREATE TABLE IF NOT EXISTS players (
    player_id     INTEGER PRIMARY KEY,
    full_name     TEXT    NOT NULL,
    country       TEXT,
    team_id       INTEGER REFERENCES teams(team_id) ON DELETE SET NULL,
    playing_role  TEXT CHECK (playing_role IN
                    ('Batsman', 'Bowler', 'All-rounder', 'Wicket-keeper') OR playing_role IS NULL),
    batting_style TEXT,
    bowling_style TEXT,
    source        TEXT DEFAULT 'manual'      -- 'sample', 'api' or 'manual'
);

-- Series / tournaments
CREATE TABLE IF NOT EXISTS series (
    series_id     INTEGER PRIMARY KEY,
    series_name   TEXT NOT NULL,
    host_country  TEXT,
    match_type    TEXT,            -- Test / ODI / T20I / Mixed
    start_date    DATE,
    end_date      DATE,
    total_matches INTEGER
);

-- Matches
CREATE TABLE IF NOT EXISTS matches (
    match_id        INTEGER PRIMARY KEY,
    series_id       INTEGER REFERENCES series(series_id) ON DELETE SET NULL,
    match_desc      TEXT,
    match_format    TEXT CHECK (match_format IN ('Test', 'ODI', 'T20I') OR match_format IS NULL),
    team1_id        INTEGER REFERENCES teams(team_id),
    team2_id        INTEGER REFERENCES teams(team_id),
    venue_id        INTEGER REFERENCES venues(venue_id),
    match_date      DATE,
    state           TEXT,          -- Complete / In Progress / Upcoming
    status          TEXT,          -- e.g. "India won by 5 wkts"
    toss_winner_id  INTEGER REFERENCES teams(team_id),
    toss_decision   TEXT CHECK (toss_decision IN ('bat', 'bowl') OR toss_decision IS NULL),
    winner_id       INTEGER REFERENCES teams(team_id),
    victory_margin  INTEGER,
    victory_type    TEXT CHECK (victory_type IN ('runs', 'wickets') OR victory_type IS NULL),
    source          TEXT DEFAULT 'manual',
    CHECK (team1_id IS NULL OR team1_id <> team2_id)
);

-- One row per batter per innings (from scorecards)
CREATE TABLE IF NOT EXISTS batting_innings (
    batting_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id          INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    innings_no        INTEGER NOT NULL,
    player_id         INTEGER NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    team_id           INTEGER REFERENCES teams(team_id),
    batting_position  INTEGER CHECK (batting_position BETWEEN 1 AND 11),
    runs              INTEGER NOT NULL DEFAULT 0 CHECK (runs >= 0),
    balls             INTEGER NOT NULL DEFAULT 0 CHECK (balls >= 0),
    fours             INTEGER DEFAULT 0,
    sixes             INTEGER DEFAULT 0,
    strike_rate       REAL,
    is_out            INTEGER DEFAULT 1,      -- 1 = dismissed, 0 = not out
    dismissal         TEXT,
    UNIQUE (match_id, innings_no, player_id)
);

-- One row per bowler per innings
CREATE TABLE IF NOT EXISTS bowling_innings (
    bowling_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id       INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    innings_no     INTEGER NOT NULL,
    player_id      INTEGER NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    team_id        INTEGER REFERENCES teams(team_id),
    overs          REAL    NOT NULL DEFAULT 0 CHECK (overs >= 0),
    maidens        INTEGER DEFAULT 0,
    runs_conceded  INTEGER NOT NULL DEFAULT 0,
    wickets        INTEGER NOT NULL DEFAULT 0 CHECK (wickets BETWEEN 0 AND 10),
    economy        REAL,
    UNIQUE (match_id, innings_no, player_id)
);

-- Career summary per player per format (from player stats endpoints)
CREATE TABLE IF NOT EXISTS player_career_stats (
    player_id        INTEGER NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    format           TEXT    NOT NULL CHECK (format IN ('Test', 'ODI', 'T20I')),
    matches          INTEGER DEFAULT 0,
    innings          INTEGER DEFAULT 0,
    runs             INTEGER DEFAULT 0,
    highest_score    INTEGER DEFAULT 0,
    batting_average  REAL,
    strike_rate      REAL,
    hundreds         INTEGER DEFAULT 0,
    fifties          INTEGER DEFAULT 0,
    wickets          INTEGER DEFAULT 0,
    bowling_average  REAL,
    economy          REAL,
    catches          INTEGER DEFAULT 0,
    stumpings        INTEGER DEFAULT 0,
    PRIMARY KEY (player_id, format)
);

-- ---------------------------------------------------------------------
-- Indexes on columns used in WHERE / JOIN / ORDER BY
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_players_country   ON players(country);
CREATE INDEX IF NOT EXISTS idx_players_role      ON players(playing_role);
CREATE INDEX IF NOT EXISTS idx_matches_date      ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_format    ON matches(match_format);
CREATE INDEX IF NOT EXISTS idx_matches_winner    ON matches(winner_id);
CREATE INDEX IF NOT EXISTS idx_matches_venue     ON matches(venue_id);
CREATE INDEX IF NOT EXISTS idx_bat_player        ON batting_innings(player_id);
CREATE INDEX IF NOT EXISTS idx_bat_match_innings ON batting_innings(match_id, innings_no, batting_position);
CREATE INDEX IF NOT EXISTS idx_bowl_player       ON bowling_innings(player_id);
CREATE INDEX IF NOT EXISTS idx_bowl_match        ON bowling_innings(match_id);
CREATE INDEX IF NOT EXISTS idx_series_start      ON series(start_date);

-- ---------------------------------------------------------------------
-- A reusable view: every match with team and venue names resolved
-- ---------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_match_details AS
SELECT m.match_id,
       m.match_desc,
       m.match_format,
       m.match_date,
       m.state,
       m.status,
       t1.team_name AS team1,
       t2.team_name AS team2,
       v.venue_name,
       v.city,
       v.country    AS venue_country,
       w.team_name  AS winner,
       m.victory_margin,
       m.victory_type,
       tw.team_name AS toss_winner,
       m.toss_decision,
       m.source
FROM matches m
LEFT JOIN teams  t1 ON t1.team_id = m.team1_id
LEFT JOIN teams  t2 ON t2.team_id = m.team2_id
LEFT JOIN venues v  ON v.venue_id = m.venue_id
LEFT JOIN teams  w  ON w.team_id  = m.winner_id
LEFT JOIN teams  tw ON tw.team_id = m.toss_winner_id;
