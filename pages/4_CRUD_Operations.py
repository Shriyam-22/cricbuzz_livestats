"""CRUD Operations: add, view, update and delete players and matches."""
from datetime import date

import streamlit as st

from services import crud
from utils.db_connection import DatabaseError
from utils.ui import setup_page

setup_page("CRUD Operations", "🛠️")
st.title("🛠️ CRUD Operations")
st.caption("Create, Read, Update and Delete records. Every change is validated and saved in a "
           "transaction, so a failed save never leaves half-written data.")

entity = st.radio("Work with", ["Players", "Matches"], horizontal=True)

try:
    teams = crud.list_teams()
    venues = crud.list_venues()
except DatabaseError as exc:
    st.error(str(exc))
    st.stop()

team_names = dict(zip(teams["team_id"], teams["team_name"]))
team_country = dict(zip(teams["team_id"], teams["country"]))
venue_names = dict(zip(venues["venue_id"], venues["venue_name"] + ", " + venues["city"].fillna("")))
team_ids = list(team_names)


def _index(options, value, default=0):
    return options.index(value) if value in options else default


# =============================================================== PLAYER FORM
def player_form(key, existing=None):
    """Draw the player form. Returns the entered data, or None until submitted."""
    existing = existing or {}
    with st.form(key, clear_on_submit=existing == {}):
        name = st.text_input("Full name *", value=existing.get("full_name") or "", key=f"{key}_w1")
        c1, c2 = st.columns(2)
        team_options = [None] + team_ids
        team_id = c1.selectbox("Team", team_options,
                               index=_index(team_options, existing.get("team_id")),
                               format_func=lambda t: "-" if t is None else team_names[t], key=f"{key}_w2")
        country = c2.text_input("Country *", value=existing.get("country") or "",
                                help="Leave blank to use the team's country.", key=f"{key}_w3")
        role = c1.selectbox("Playing role *", crud.PLAYING_ROLES,
                            index=_index(crud.PLAYING_ROLES, existing.get("playing_role")), key=f"{key}_w4")
        bat = c2.selectbox("Batting style", crud.BATTING_STYLES,
                           index=_index(crud.BATTING_STYLES, existing.get("batting_style")), key=f"{key}_w5")
        bowl = st.selectbox("Bowling style", crud.BOWLING_STYLES,
                            index=_index(crud.BOWLING_STYLES, existing.get("bowling_style") or ""), key=f"{key}_w6")
        submitted = st.form_submit_button("Save player", type="primary")
    if not submitted:
        return None
    if not country.strip() and team_id:
        country = team_country.get(team_id) or ""
    return {"full_name": name, "team_id": team_id, "country": country, "playing_role": role,
            "batting_style": bat, "bowling_style": bowl}


def choose_player(key):
    search = st.text_input("Search player by name", key=f"{key}_search")
    found = crud.read_players(search, limit=200)
    if found.empty:
        st.info("No players match that search.")
        return None
    labels = {r.player_id: f"{r.full_name} ({r.country or '-'}, {r.playing_role or '-'})"
              for r in found.itertuples()}
    return st.selectbox("Player", list(labels), format_func=labels.get, key=f"{key}_pick")


# ================================================================ MATCH FORM
def match_form(key, existing=None):
    existing = existing or {}
    with st.form(key, clear_on_submit=existing == {}):
        desc = st.text_input("Description", value=existing.get("match_desc") or "",
                             placeholder="e.g. 2nd ODI", key=f"{key}_w7")
        c1, c2, c3 = st.columns(3)
        t1 = c1.selectbox("Team 1 *", team_ids, format_func=team_names.get,
                          index=_index(team_ids, existing.get("team1_id")), key=f"{key}_w8")
        t2 = c2.selectbox("Team 2 *", team_ids, format_func=team_names.get,
                          index=_index(team_ids, existing.get("team2_id"), 1), key=f"{key}_w9")
        fmt = c3.selectbox("Format *", crud.FORMATS,
                           index=_index(crud.FORMATS, existing.get("match_format"), 1), key=f"{key}_w10")
        venue_options = [None] + list(venue_names)
        venue = c1.selectbox("Venue", venue_options,
                             index=_index(venue_options, existing.get("venue_id")),
                             format_func=lambda v: "-" if v is None else venue_names[v], key=f"{key}_w11")
        default_date = date.fromisoformat(existing["match_date"]) if existing.get(
            "match_date") else date.today()
        match_date = c2.date_input("Match date *", value=default_date, key=f"{key}_w12")
        state = c3.selectbox("State", crud.STATES,
                             index=_index(crud.STATES, existing.get("state"), 2), key=f"{key}_w13")
        st.markdown("**Toss and result** (choose teams from Team 1 / Team 2)")
        d1, d2, d3, d4 = st.columns(4)
        result_options = [None] + team_ids
        toss = d1.selectbox("Toss winner", result_options,
                            index=_index(result_options, existing.get("toss_winner_id")),
                            format_func=lambda t: "-" if t is None else team_names[t], key=f"{key}_w14")
        decision_options = [None, "bat", "bowl"]
        decision = d2.selectbox("Toss decision", decision_options,
                                index=_index(decision_options, existing.get("toss_decision")),
                                format_func=lambda d: d or "-", key=f"{key}_w15")
        winner = d3.selectbox("Winner", result_options,
                              index=_index(result_options, existing.get("winner_id")),
                              format_func=lambda t: "-" if t is None else team_names[t], key=f"{key}_w16")
        vtype_options = [None, "runs", "wickets"]
        vtype = d4.selectbox("Won by", vtype_options,
                             index=_index(vtype_options, existing.get("victory_type")),
                             format_func=lambda v: v or "-", key=f"{key}_w17")
        margin = st.number_input("Victory margin", min_value=0, max_value=1000, step=1,
                                 value=int(existing.get("victory_margin") or 0), key=f"{key}_w18")
        submitted = st.form_submit_button("Save match", type="primary")
    if not submitted:
        return None
    return {"match_desc": desc, "team1_id": t1, "team2_id": t2, "match_format": fmt,
            "venue_id": venue, "match_date": match_date, "state": state,
            "toss_winner_id": toss, "toss_decision": decision, "winner_id": winner,
            "victory_type": vtype, "victory_margin": margin or None}


def choose_match(key):
    found = crud.read_matches(limit=300)
    if found.empty:
        st.info("No matches yet.")
        return None
    labels = {r.match_id: f"{r.match_date} · {r.team1} vs {r.team2} · {r.match_desc or ''} "
                          f"[{r.source}]" for r in found.itertuples()}
    return st.selectbox("Match (latest 300)", list(labels), format_func=labels.get,
                        key=f"{key}_pick")


def run_safely(action, success_message):
    """Run a CRUD call and show a friendly message instead of a crash."""
    try:
        result = action()
        st.success(success_message.format(result=result))
        return result
    except crud.ValidationError as exc:
        st.error(f"Please fix: {exc}")
    except DatabaseError as exc:
        st.error(f"Database error: {exc}")
    return None


create_tab, read_tab, update_tab, delete_tab = st.tabs(
    ["➕ Create", "📄 Read", "✏️ Update", "🗑️ Delete"])

# ==================================================================== PLAYERS
if entity == "Players":
    with create_tab:
        st.subheader("Add a new player")
        data = player_form("create_player")
        if data:
            run_safely(lambda: crud.create_player(data), "Player added with ID {result}.")

    with read_tab:
        st.subheader("View players")
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Name contains")
        countries = sorted({c for c in teams["country"].dropna()})
        country = c2.selectbox("Country", [None] + countries, format_func=lambda c: c or "All")
        role = c3.selectbox("Role", [None] + crud.PLAYING_ROLES, format_func=lambda r: r or "All")
        df = crud.read_players(name, country, role)
        st.caption(f"{len(df)} players")
        st.dataframe(df, hide_index=True)

    with update_tab:
        st.subheader("Edit a player")
        pid = choose_player("upd_player")
        if pid:
            current = crud.get_player(pid)
            data = player_form(f"update_player_{pid}", current)
            if data:
                run_safely(lambda: crud.update_player(pid, data), "Player updated.")

    with delete_tab:
        st.subheader("Delete a player")
        st.warning("Deleting a player also deletes their batting, bowling and career rows.")
        pid = choose_player("del_player")
        if pid:
            confirm = st.checkbox("Yes, I want to delete this player", key="del_player_ok")
            if st.button("Delete player", type="primary", disabled=not confirm):
                run_safely(lambda: crud.delete_player(pid), "Deleted ({result} row).")

# ==================================================================== MATCHES
else:
    with create_tab:
        st.subheader("Add a new match")
        data = match_form("create_match")
        if data:
            run_safely(lambda: crud.create_match(data), "Match added with ID {result}.")

    with read_tab:
        st.subheader("View matches")
        c1, c2 = st.columns(2)
        team = c1.selectbox("Team", [None] + team_ids,
                            format_func=lambda t: "All" if t is None else team_names[t])
        fmt = c2.selectbox("Format", [None] + crud.FORMATS, format_func=lambda f: f or "All")
        df = crud.read_matches(team, fmt)
        st.caption(f"{len(df)} matches (latest first, up to 200)")
        st.dataframe(df, hide_index=True)

    with update_tab:
        st.subheader("Edit a match")
        mid = choose_match("upd_match")
        if mid:
            current = crud.get_match(mid)
            data = match_form(f"update_match_{mid}", current)
            if data:
                run_safely(lambda: crud.update_match(mid, data), "Match updated.")

    with delete_tab:
        st.subheader("Delete a match")
        st.warning("Deleting a match also deletes its batting and bowling rows.")
        mid = choose_match("del_match")
        if mid:
            confirm = st.checkbox("Yes, I want to delete this match", key="del_match_ok")
            if st.button("Delete match", type="primary", disabled=not confirm):
                run_safely(lambda: crud.delete_match(mid), "Deleted ({result} row).")
