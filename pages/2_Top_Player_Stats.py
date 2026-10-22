"""Top Player Stats: leaderboards from the Cricbuzz API, with a database fallback."""
import pandas as pd
import streamlit as st

from api.parsers import parse_top_stats
from utils.db_connection import DatabaseError, run_query
from utils.ui import cached_api_call, setup_page

setup_page("Top Player Stats", "🏆")
st.title("🏆 Top Player Stats")

# label -> (Cricbuzz statsType, SQL for the database fallback, value column, sort)
STATS = {
    "Most runs": ("mostRuns", "SUM(c.runs)", "runs", "DESC"),
    "Highest individual score": ("highestScore", "MAX(c.highest_score)", "highest_score", "DESC"),
    "Best batting average": ("highestAvg", "ROUND(SUM(c.runs) * 1.0 / NULLIF(SUM("
                             "CASE WHEN c.batting_average > 0 THEN c.runs / c.batting_average "
                             "END), 0), 2)", "batting_average", "DESC"),
    "Most hundreds": ("mostHundreds", "SUM(c.hundreds)", "hundreds", "DESC"),
    "Most fifties": ("mostFifties", "SUM(c.fifties)", "fifties", "DESC"),
    "Most wickets": ("mostWickets", "SUM(c.wickets)", "wickets", "DESC"),
    "Best bowling average": ("lowestAvg", "ROUND(SUM(c.bowling_average * c.wickets) * 1.0 / "
                             "NULLIF(SUM(c.wickets), 0), 2)", "bowling_average", "ASC"),
    # economy = runs / overs; runs = avg * wickets and overs = runs / economy
    "Best economy": ("lowestEcon", "ROUND(SUM(c.bowling_average * c.wickets) / NULLIF(SUM("
                     "c.bowling_average * c.wickets / c.economy), 0), 2)", "economy", "ASC"),
}
FORMAT_CODES = {"Test": "1", "ODI": "2", "T20I": "3"}

c1, c2, c3 = st.columns([2, 1, 1])
stat_label = c1.selectbox("Statistic", list(STATS))
fmt = c2.selectbox("Format", ["All formats", "Test", "ODI", "T20I"])
source = c3.radio("Source", ["Cricbuzz API", "Database"], horizontal=True)
top_n = st.slider("How many players", 5, 25, 10)

stats_type, sql_expr, value_name, order = STATS[stat_label]


def from_database():
    """Leaderboard from player_career_stats (all formats combined or one format)."""
    where = "WHERE c.format = ?" if fmt != "All formats" else ""
    params = [fmt] if fmt != "All formats" else []
    min_filter = ""
    if value_name in ("batting_average",):
        min_filter = "HAVING SUM(c.innings) >= 10"
    elif value_name in ("bowling_average", "economy"):
        min_filter = "HAVING SUM(c.wickets) >= 20"
    sql = f"""
        SELECT p.full_name AS player, p.country, SUM(c.matches) AS matches,
               {sql_expr} AS {value_name}
        FROM player_career_stats c
        JOIN players p ON p.player_id = c.player_id
        {where}
        GROUP BY p.player_id, p.full_name, p.country
        {min_filter}
        ORDER BY {value_name} {order}
        LIMIT ?"""
    return run_query(sql, params + [top_n])


df, note = None, None
if source == "Cricbuzz API":
    params = {"statsType": stats_type}
    if fmt != "All formats":
        params["matchType"] = FORMAT_CODES[fmt]
    payload, error = cached_api_call("top_stats", params=params)
    if error:
        note = f"{error} Showing database stats instead."
    else:
        headers, rows = parse_top_stats(payload)
        if rows:
            width = max(len(r) for r in rows)
            headers = list(headers)[:width] + [f"col{i}" for i in range(len(headers), width)]
            df = pd.DataFrame(rows, columns=headers).head(top_n)
        else:
            note = "The API returned no rows for this statistic. Showing database stats instead."

if df is None:
    if note:
        st.warning(note)
    try:
        df = from_database()
        st.caption("Source: SQL database (sample + saved API data)")
    except DatabaseError as exc:
        st.error(str(exc))
        st.stop()
else:
    st.caption("Source: Cricbuzz API (live)")

if df.empty:
    st.info("No data for this selection.")
    st.stop()

df.index = range(1, len(df) + 1)
left, right = st.columns([3, 2])
with left:
    st.dataframe(df)
with right:
    # Chart: first text column as labels, the last numeric column as values.
    numeric = df.apply(pd.to_numeric, errors="coerce")
    value_cols = [c for c in numeric.columns if numeric[c].notna().all()]
    label_col = next((c for c in df.columns if c not in value_cols and "id" not in str(c).lower()),
                     None)
    if value_cols and label_col:
        chart = pd.DataFrame({stat_label: numeric[value_cols[-1]].values},
                             index=df[label_col].astype(str))
        st.bar_chart(chart, horizontal=True)

st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode("utf-8"),
                   file_name=f"{stats_type}_{fmt}.csv", mime="text/csv")
