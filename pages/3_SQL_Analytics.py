"""SQL Analytics: the 25 practice questions plus a custom read-only query box."""
import re

import streamlit as st

from sql.queries import QUERIES
from utils.db_connection import DatabaseError, run_query
from utils.ui import setup_page

setup_page("SQL Analytics", "🔍")
st.title("🔍 SQL Queries & Analytics")

practice_tab, custom_tab = st.tabs(["25 practice questions", "Custom SQL"])

# --------------------------------------------------------------- practice set
with practice_tab:
    level = st.radio("Level", ["All", "Beginner", "Intermediate", "Advanced"], horizontal=True)
    options = [q for q in QUERIES if level == "All" or q["level"] == level]
    query = st.selectbox("Question", options,
                         format_func=lambda q: f"Q{q['id']}. {q['title']}  ({q['level']})")

    st.markdown(f"**Q{query['id']}.** {query['question']}")
    with st.expander("Show SQL", expanded=False):
        st.code(query["sql"].strip(), language="sql")

    try:
        result = run_query(query["sql"])
    except DatabaseError as exc:
        st.error(str(exc))
        st.stop()

    st.caption(f"{len(result):,} rows")
    st.dataframe(result, hide_index=True)

    # Quick chart when the result has a text column and a number column.
    numeric_cols = result.select_dtypes("number").columns.tolist()
    text_cols = [c for c in result.columns if c not in numeric_cols]
    if numeric_cols and text_cols and 1 < len(result) <= 40:
        with st.expander("Chart this result"):
            y = st.selectbox("Value", numeric_cols, index=len(numeric_cols) - 1,
                             key=f"chart_y_{query['id']}")
            x = text_cols[0]
            chart = result.groupby(x, sort=False)[y].sum()
            st.bar_chart(chart)

    st.download_button("⬇️ Download CSV", result.to_csv(index=False).encode("utf-8"),
                       file_name=f"q{query['id']}.csv", mime="text/csv")

# ----------------------------------------------------------------- custom SQL
READ_ONLY = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
FORBIDDEN = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|PRAGMA)\b",
                       re.IGNORECASE)

with custom_tab:
    st.write("Write your own **read-only** query (SELECT or WITH). Tables: `teams`, `venues`, "
             "`players`, `series`, `matches`, `batting_innings`, `bowling_innings`, "
             "`player_career_stats`, and the view `v_match_details`.")
    sql = st.text_area("SQL", height=180,
                       value="SELECT match_format, COUNT(*) AS matches\nFROM matches\n"
                             "GROUP BY match_format;")
    if st.button("▶ Run query"):
        if not READ_ONLY.match(sql) or FORBIDDEN.search(sql) or sql.count(";") > 1:
            st.error("Only a single SELECT/WITH query is allowed here. Use the CRUD page to "
                     "change data.")
        else:
            try:
                df = run_query(sql)
                st.caption(f"{len(df):,} rows")
                st.dataframe(df, hide_index=True)
            except DatabaseError as exc:
                st.error(str(exc))

    with st.expander("Table columns"):
        try:
            for table in ["teams", "venues", "players", "series", "matches", "batting_innings",
                          "bowling_innings", "player_career_stats"]:
                cols = run_query(f"SELECT * FROM {table} LIMIT 0").columns
                st.markdown(f"**{table}**: " + ", ".join(f"`{c}`" for c in cols))
        except DatabaseError as exc:
            st.error(str(exc))

