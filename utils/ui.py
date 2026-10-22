"""Shared Streamlit helpers used by every page."""
import streamlit as st

import config
from api.cricbuzz_client import CricbuzzAPIError, CricbuzzClient
from utils.db_connection import DatabaseError, database_ready, init_schema

CACHE_SECONDS = config.API_CACHE_MINUTES * 60


def setup_page(title, icon="🏏"):
    """Set the page title and make sure the database exists (first run)."""
    st.set_page_config(page_title=f"{title} | Cricbuzz LiveStats", page_icon=icon, layout="wide")
    ensure_database()
    with st.sidebar:
        st.caption("Cricbuzz LiveStats")
        if CricbuzzClient().is_configured:
            st.success("API key loaded", icon="🔑")
        else:
            st.warning("No API key: live pages will use database data", icon="🔑")


def ensure_database():
    """Create the schema and load sample data the very first time the app runs."""
    if st.session_state.get("_db_checked"):
        return
    try:
        if not database_ready():
            from services.sample_data import seed_sample_data

            with st.spinner("First run: creating the database and loading sample data..."):
                init_schema()
                seed_sample_data()
        st.session_state["_db_checked"] = True
    except DatabaseError as exc:
        st.error(f"Database problem: {exc}")
        st.stop()


@st.cache_data(ttl=CACHE_SECONDS, show_spinner="Fetching from Cricbuzz...")
def cached_api_call(endpoint_name, params=None, **path_values):
    """Call the API once and reuse the answer for a few minutes (saves quota).

    Returns (data, error_message). Errors are returned, not raised, so pages
    can fall back to database data.
    """
    try:
        return CricbuzzClient().get(endpoint_name, params=params, **path_values), None
    except CricbuzzAPIError as exc:
        return None, str(exc)
