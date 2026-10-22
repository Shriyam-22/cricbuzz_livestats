"""Cricbuzz LiveStats - Home page and app entry point.

Run with:  streamlit run main.py
"""
import streamlit as st

from utils.db_connection import table_counts
from utils.ui import setup_page

setup_page("Home")

st.title("🏏 Cricbuzz LiveStats")
st.subheader("Real-time cricket insights and SQL-based analytics")
st.write(
    "A cricket analytics dashboard that combines **live data from the Cricbuzz API** with a "
    "**SQL database**. Follow live matches, explore top player stats, run 25 analytical SQL "
    "queries, and manage records with full CRUD operations."
)

# --- Database at a glance ----------------------------------------------------
counts = table_counts()
cols = st.columns(4)
cols[0].metric("Matches", f"{counts['matches']:,}")
cols[1].metric("Players", f"{counts['players']:,}")
cols[2].metric("Batting innings", f"{counts['batting_innings']:,}")
cols[3].metric("Venues", f"{counts['venues']:,}")

st.divider()

# --- Navigation --------------------------------------------------------------
st.header("Pages")
nav = st.columns(2)
with nav[0]:
    st.page_link("pages/1_Live_Matches.py", label="Live Matches", icon="📺")
    st.caption("Ongoing, recent and upcoming matches from the Cricbuzz API, with full "
               "scorecards, batter and bowler details, match status and venue.")
    st.page_link("pages/2_Top_Player_Stats.py", label="Top Player Stats", icon="🏆")
    st.caption("Most runs, highest scores, most wickets, best economy and more, by format.")
with nav[1]:
    st.page_link("pages/3_SQL_Analytics.py", label="SQL Analytics", icon="🔍")
    st.caption("All 25 practice questions (beginner to advanced) plus your own custom "
               "read-only SQL.")
    st.page_link("pages/4_CRUD_Operations.py", label="CRUD Operations", icon="🛠️")
    st.caption("Add, view, update and delete players and matches with validated forms.")

st.divider()

# --- About ------------------------------------------------------------------
left, right = st.columns(2)
with left:
    st.header("Tools used")
    st.markdown(
        "- **Python**: application logic\n"
        "- **Streamlit**: multi-page web interface\n"
        "- **SQLite** (default) / MySQL / PostgreSQL: data storage\n"
        "- **Cricbuzz Cricket API** via RapidAPI: live data (REST + JSON)\n"
        "- **requests**: API calls with retries and timeouts\n"
        "- **pandas**: tables and query results\n"
        "- **python-dotenv**: keeps the API key out of the code"
    )
    st.header("About the data")
    st.info(
        "The database starts with **synthetic sample data** (real teams and grounds, "
        "fictional players, ~900 matches since 2020) so every SQL question has enough history. "
        "Real API data is added on top when you click **Save to database** on the Live Matches "
        "page. Sample rows are marked `source = 'sample'`, API rows `source = 'api'`."
    )
with right:
    st.header("Folder structure")
    st.code(
        """cricbuzz_livestats/
├── main.py              # this Home page (entry point)
├── config.py            # settings from .env
├── pages/               # one file per Streamlit page
├── api/                 # Cricbuzz API client + JSON parsers
├── services/            # data loading, CRUD, sample data
├── utils/               # db_connection.py, UI helpers
├── sql/                 # schema.sql + the 25 queries
├── data/                # SQLite database file
├── scripts/             # setup / sync scripts
└── tests/               # automated tests""",
        language="text",
    )
    st.header("How to use")
    st.markdown(
        "1. Put your RapidAPI key in `.env` as `RAPIDAPI_KEY=...`\n"
        "2. Run `streamlit run main.py`\n"
        "3. Pick a page from the sidebar\n\n"
        "Full setup steps are in **README.md** in the project folder."
    )

with st.expander("Reset sample data"):
    st.write("Rebuilds all sample rows. Data you added manually or from the API is kept.")
    if st.button("Reset sample data", type="secondary"):
        from services.sample_data import seed_sample_data

        with st.spinner("Rebuilding..."):
            summary = seed_sample_data()
        st.success(f"Done: {summary['matches']} matches, {summary['players']} players.")
