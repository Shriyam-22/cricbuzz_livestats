"""Live Matches: ongoing / recent / upcoming matches and full scorecards."""
import pandas as pd
import streamlit as st

from api.cricbuzz_client import CricbuzzAPIError
from api.parsers import parse_match_list, parse_scorecard
from services.data_loader import sync_matches, sync_scorecard
from utils.db_connection import DatabaseError, run_query
from utils.ui import cached_api_call, setup_page

setup_page("Live Matches", "📺")
st.title("📺 Live Matches")

with st.sidebar:
    feed = st.radio("Show", ["Live", "Recent", "Upcoming"], index=0)
    if st.button("🔄 Refresh from API"):
        cached_api_call.clear()
        st.rerun()

endpoint = feed.lower()
payload, error = cached_api_call(endpoint)
matches = parse_match_list(payload) if payload else []

# ---------------------------------------------------------------- fallbacks
if error:
    st.warning(f"{error}\n\nShowing the most recent matches stored in the database instead.")
elif not matches:
    st.info(f"No {feed.lower()} matches from the API right now.")
    if feed == "Live":
        alt_payload, alt_error = cached_api_call("recent")
        matches = parse_match_list(alt_payload) if alt_payload else []
        if matches:
            st.caption("Showing recent matches instead.")

if not matches:
    try:
        recent = run_query("""SELECT match_date, match_desc, match_format, team1, team2,
                                     venue_name, city, status
                              FROM v_match_details
                              ORDER BY match_date DESC, match_id DESC LIMIT 20""")
        st.subheader("Latest matches in the database")
        st.dataframe(recent, hide_index=True)
    except DatabaseError as exc:
        st.error(str(exc))
    st.stop()

# ------------------------------------------------------------ match picker
types = sorted({m["match_type"] for m in matches if m["match_type"]})
chosen_types = st.multiselect("Match type", types, default=types)
matches = [m for m in matches if m["match_type"] in chosen_types] or matches

st.metric(f"{feed} matches", len(matches))
labels = {
    m["match_id"]: f"{m['team1_short'] or m['team1']} vs {m['team2_short'] or m['team2']}"
                   f" · {m['match_desc'] or ''} · {m['series_name'] or ''}"
    for m in matches
}
match_id = st.selectbox("Choose a match", list(labels), format_func=labels.get)
match = next(m for m in matches if m["match_id"] == match_id)

# ------------------------------------------------------------- match header
st.subheader(f"{match['team1']} vs {match['team2']}")
st.caption(f"{match['series_name'] or ''} · {match['match_desc'] or ''} · "
           f"{match['match_format'] or ''}")
c1, c2, c3 = st.columns(3)
c1.metric(match["team1_short"] or match["team1"], match["team1_score"] or "-")
c2.metric(match["team2_short"] or match["team2"], match["team2_score"] or "-")
c3.metric("State", match["state"] or "-")
st.write(f"**Status:** {match['status'] or '-'}")
st.write(f"**Venue:** {match['venue'] or '-'}, {match['city'] or ''}  ·  "
         f"**Date:** {match['start_date'] or '-'}")

# --------------------------------------------------------------- scorecard
st.divider()
st.subheader("Scorecard")
if match["state"] and match["state"].lower() in ("upcoming", "preview"):
    st.info("Scorecard will be available once the match starts.")
else:
    card_payload, card_error = cached_api_call("scorecard", match_id=match_id)
    if card_error:
        st.warning(card_error)
    else:
        innings = parse_scorecard(card_payload)
        if not innings:
            st.info("No scorecard data yet for this match.")
            with st.expander("Raw API response (for debugging)"):
                st.json(card_payload)
        else:
            tabs = st.tabs([f"{inn['team'] or 'Innings'} · {inn['runs']}/{inn['wickets']}"
                            f" ({inn['overs'] or '-'})" for inn in innings])
            for tab, inn in zip(tabs, innings):
                with tab:
                    st.markdown("**Batting**")
                    bat = pd.DataFrame(inn["batters"])
                    if not bat.empty:
                        bat = bat[["name", "dismissal", "runs", "balls", "fours", "sixes",
                                   "strike_rate"]].rename(columns={
                                       "name": "Batter", "dismissal": "Dismissal", "runs": "R",
                                       "balls": "B", "fours": "4s", "sixes": "6s",
                                       "strike_rate": "SR"})
                    st.dataframe(bat, hide_index=True)
                    st.markdown("**Bowling**")
                    bowl = pd.DataFrame(inn["bowlers"])
                    if not bowl.empty:
                        bowl = bowl[["name", "overs", "maidens", "runs", "wickets",
                                     "economy"]].rename(columns={
                                         "name": "Bowler", "overs": "O", "maidens": "M",
                                         "runs": "R", "wickets": "W", "economy": "Econ"})
                    st.dataframe(bowl, hide_index=True)

# -------------------------------------------------------------- save to DB
st.divider()
st.subheader("Save to database")
st.caption("Stores these matches (and this scorecard) in SQL so they appear in the analytics "
           "and CRUD pages. Uses 1 to 2 API calls.")
if st.button("💾 Save matches and this scorecard"):
    try:
        saved = sync_matches(which=endpoint if not error else "recent")
        msg = f"Saved {saved} international matches."
        if match["match_type"].lower() == "international" and match["state"] != "Upcoming":
            counts = sync_scorecard(match_id)
            msg += (f" Scorecard: {counts['batting_rows']} batting and "
                    f"{counts['bowling_rows']} bowling rows.")
        st.success(msg)
    except (CricbuzzAPIError, DatabaseError, ValueError) as exc:
        st.error(f"Could not save: {exc}")
