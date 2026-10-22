# 🏏 Cricbuzz LiveStats: Real-Time Cricket Insights & SQL-Based Analytics

A multi-page **Streamlit** dashboard that combines live data from the **Cricbuzz Cricket API**
(via RapidAPI) with a **SQL database** to deliver live scorecards, player leaderboards,
25 analytical SQL queries and full CRUD data management.

**Skills:** Python · SQL · Streamlit · REST API · JSON · pandas · Git
**Domain:** Sports Analytics

---

## Features

| Page | What it does |
|---|---|
| **Home** (`main.py`) | Project overview, tools, navigation, folder structure, database summary |
| **Live Matches** | Live / recent / upcoming matches from the API, full scorecards (batting + bowling per innings), match status and venue; one click saves them to SQL |
| **Top Player Stats** | Most runs, highest score, best average, hundreds, fifties, most wickets, best bowling average, best economy, by format, from the API or the database, with charts and CSV download |
| **SQL Analytics** | All 25 practice questions (8 beginner, 8 intermediate, 9 advanced) with question text, SQL, results table, quick chart, CSV download, plus a safe custom read-only SQL box |
| **CRUD Operations** | Create, read, update and delete **players** and **matches** with validated forms and transactions |

**Resilient by design:** if the API is unreachable or the free quota runs out (HTTP 429), the
pages fall back to data in the database instead of crashing.

---

## Setup (Windows)

> Requires **Python 3.12–3.14**. Check with `py list`.

1. **Get the code** into a folder, e.g. `Desktop\cricbuzz_livestats`, and open it in VS Code.
2. **Create a virtual environment** (a private Python for this project). In the VS Code terminal:
   ```
   py -V:3.14 -m venv .venv --clear
   ```
3. **Install the libraries:**
   ```
   .venv\Scripts\python -m pip install -r requirements.txt
   ```
4. **Add your API key:** copy `.env.example` to `.env` and set
   `RAPIDAPI_KEY=` to your key from RapidAPI → Console → your app → Authorization.
5. **Run the app:**
   ```
   .venv\Scripts\python -m streamlit run main.py
   ```
   Your browser opens at `http://localhost:8501`. On first run the database
   (`data/cricbuzz.db`) is created and filled with sample data automatically.

*(macOS/Linux: use `python3 -m venv .venv`, then `.venv/bin/python` instead of `.venv\Scripts\python`.)*

### Optional commands
```
.venv\Scripts\python scripts\setup_database.py          # rebuild sample data
.venv\Scripts\python scripts\sync_from_api.py --scorecards 5   # pull real matches + scorecards
.venv\Scripts\python scripts\inspect_api.py recent      # save raw JSON to data\raw\ to study it
.venv\Scripts\python -m pytest -q                       # run the automated tests
```

---

## API setup

1. Sign up at [rapidapi.com](https://rapidapi.com) and subscribe to **Cricbuzz Cricket**
   (Basic / free plan).
2. Copy your key into `.env` (never into code, never into Git: `.env` is in `.gitignore`).

Endpoints used (all `GET`, defined in one place: `api/cricbuzz_client.py → ENDPOINTS`):

| Endpoint | Used for | Saved to |
|---|---|---|
| `/matches/v1/live` · `/recent` · `/upcoming` | Match lists | `teams`, `venues`, `series`, `matches` |
| `/mcenter/v1/{matchId}/scard` | Scorecards | `players`, `batting_innings`, `bowling_innings` |
| `/stats/v1/topstats/0?statsType=…` | Leaderboards | shown live (fallback: `player_career_stats`) |

Headers: `X-RapidAPI-Key`, `X-RapidAPI-Host: cricbuzz-cricket.p.rapidapi.com`.
API answers are cached for `API_CACHE_MINUTES` (default 5) to protect the free quota.
Temporary server errors (5xx) are retried 3 times with back-off; 429 (rate limit) is not.

---

## Database

**Default: SQLite** (a single file, nothing to install). Schema: `sql/schema.sql`.

```
teams ──< players
teams ──< matches >── venues
series ──< matches
matches ──< batting_innings >── players
matches ──< bowling_innings >── players
players ──< player_career_stats   (one row per player per format)
```

| Table | Key columns |
|---|---|
| `teams` | team_id (PK, Cricbuzz ID), team_name (UNIQUE), country |
| `venues` | venue_id (PK), venue_name, city, country, capacity |
| `players` | player_id (PK), full_name, country, team_id (FK), playing_role, batting_style, bowling_style, source |
| `series` | series_id (PK), series_name, host_country, match_type, start_date, total_matches |
| `matches` | match_id (PK), series_id, match_format, team1_id, team2_id, venue_id, match_date, toss_winner_id, toss_decision, winner_id, victory_margin, victory_type |
| `batting_innings` | match_id + innings_no + player_id (UNIQUE), batting_position, runs, balls, 4s, 6s, strike_rate |
| `bowling_innings` | match_id + innings_no + player_id (UNIQUE), overs, maidens, runs_conceded, wickets, economy |
| `player_career_stats` | (player_id, format) PK, matches, runs, averages, 100s, 50s, wickets, economy, catches, stumpings |

- **Normalised to 3NF:** team and venue names live in one place; matches refer to them by ID.
- **Constraints:** `NOT NULL`, `UNIQUE`, `CHECK` (valid roles/formats, wickets 0–10, team1 ≠ team2),
  foreign keys with `ON DELETE CASCADE` for innings rows.
- **Indexes** on match date, format, winner, venue, player IDs and batting position.
- **View** `v_match_details` resolves team/venue names for easier queries.

### About the sample data
The free API plan allows only a few hundred calls a month, which isn't enough history for
questions like Q25 (6+ quarters per player). So the app generates **synthetic sample data**:
real teams and grounds, **fictional players**, about 900 matches since 2020, with full scorecards.
Sample rows have `source = 'sample'`; API rows `source = 'api'`; CRUD rows `source = 'manual'`.
Venue capacities are approximate.

### Using MySQL or PostgreSQL
1. Set `DB_ENGINE=mysql` (or `postgresql`) and the `DB_*` values in `.env`.
2. Install the driver (`mysql-connector-python` or `psycopg2-binary`).
3. Run `sql/schema.sql` in your database, replacing `INTEGER PRIMARY KEY AUTOINCREMENT` with
   `INT AUTO_INCREMENT PRIMARY KEY` (MySQL) or `SERIAL PRIMARY KEY` (PostgreSQL).
4. In `sql/queries.py`, swap SQLite date functions: `date('now', '-30 days')` →
   `CURRENT_DATE - INTERVAL 30 DAY` (MySQL) / `CURRENT_DATE - INTERVAL '30 days'` (PostgreSQL),
   and `strftime('%Y', d)` → `YEAR(d)` / `EXTRACT(YEAR FROM d)`.

All connection handling is in `utils/db_connection.py`.

---

## The 25 SQL questions

Stored in `sql/queries.py`; every query is tested in `tests/test_core.py`.

| Level | Questions | Concepts |
|---|---|---|
| Beginner | Q1–Q8 | SELECT, WHERE, ORDER BY, GROUP BY, COUNT/MAX, LIMIT, date filters |
| Intermediate | Q9–Q16 | JOINs, self-joins (partnerships), CASE WHEN, HAVING, CTEs, conditional aggregation |
| Advanced | Q17–Q25 | Window functions (ROW_NUMBER, RANK, LAG), standard deviation, weighted scoring, time series |

Notes:
- **Q19/Q23 standard deviation** uses `SQRT(AVG(x*x) - AVG(x)*AVG(x))` (population std dev),
  which works on every database. `SQRT` is registered for SQLite in `db_connection.py`.
- **Q21** formula in the brief has an extra bracket; implemented as
  `wickets*2 + (50 - bowling_avg)*0.5 + (6 - economy)*2`, and only for players with wickets.
- **Q13/Q24 partnerships** are approximated as the combined runs of batters at adjacent
  positions, as the brief defines.

---

## Project structure

```
cricbuzz_livestats/
├── main.py                  # Home page / entry point
├── config.py                # settings read from .env
├── requirements.txt
├── .env.example             # template for your .env
├── pages/
│   ├── 1_Live_Matches.py
│   ├── 2_Top_Player_Stats.py
│   ├── 3_SQL_Analytics.py
│   └── 4_CRUD_Operations.py
├── api/
│   ├── cricbuzz_client.py   # HTTP client: headers, timeout, retries, errors
│   └── parsers.py           # raw JSON -> clean Python dicts
├── services/
│   ├── data_loader.py       # API -> SQL (upserts)
│   ├── crud.py              # validated create/read/update/delete
│   └── sample_data.py       # synthetic sample data generator
├── utils/
│   ├── db_connection.py     # central DB connection (SQLite/MySQL/PostgreSQL)
│   └── ui.py                # shared Streamlit helpers, API caching
├── sql/
│   ├── schema.sql           # tables, indexes, view
│   └── queries.py           # the 25 SQL questions
├── scripts/                 # setup_database, sync_from_api, inspect_api
├── tests/test_core.py       # pytest tests
└── data/                    # SQLite database (created automatically)
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python`/`pip` not recognised | Use `py -V:3.14 …` or the `.venv\Scripts\python …` commands above |
| Status 403 "not subscribed" | `.env` has the wrong key, or you're not subscribed to the free plan |
| Status 429 | Free quota used up: the app shows database data until it resets |
| Live page shows "No live matches" | Nothing is live right now; switch the sidebar to **Recent** |
| Want a clean database | Delete `data\cricbuzz.db` and rerun the app |

---

## Screenshots

_Add screenshots of each page here for your submission._

## Future improvements
- Auto-refreshing live scores
- Player detail pages from the player stats endpoints
- Match outcome prediction with machine learning
- User login and deployment to Streamlit Community Cloud
