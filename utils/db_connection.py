"""Centralised database connection handling.

Every other module gets its database connection from here, so switching
from SQLite to MySQL or PostgreSQL only means changing the .env file.

SQL in this project is written with ``?`` placeholders (SQLite style).
For MySQL/PostgreSQL they are converted to ``%s`` automatically.
"""
import logging
import math
import sqlite3
from contextlib import contextmanager

import pandas as pd

import config

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Raised when a database operation fails, with a readable message."""


def _sqlite_connection():
    """Open the SQLite file and add the helper functions the queries need."""
    config.SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.SQLITE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    # Some SQLite builds lack maths functions; register the ones we use.
    conn.create_function("SQRT", 1, lambda x: math.sqrt(x) if x is not None and x >= 0 else None)
    conn.create_function("POWER", 2, lambda x, y: None if x is None or y is None else x ** y)
    return conn


def _mysql_connection():
    import mysql.connector  # pip install mysql-connector-python

    return mysql.connector.connect(
        host=config.DB_HOST, port=config.DB_PORT, database=config.DB_NAME,
        user=config.DB_USER, password=config.DB_PASSWORD,
    )


def _postgres_connection():
    import psycopg2  # pip install psycopg2-binary

    return psycopg2.connect(
        host=config.DB_HOST, port=config.DB_PORT, dbname=config.DB_NAME,
        user=config.DB_USER, password=config.DB_PASSWORD,
    )


_FACTORIES = {
    "sqlite": _sqlite_connection,
    "mysql": _mysql_connection,
    "postgresql": _postgres_connection,
}


def get_connection():
    """Return a new DB-API connection for the engine set in DB_ENGINE."""
    factory = _FACTORIES.get(config.DB_ENGINE)
    if factory is None:
        raise DatabaseError(f"Unsupported DB_ENGINE '{config.DB_ENGINE}'. "
                            f"Use one of: {', '.join(_FACTORIES)}")
    try:
        return factory()
    except Exception as exc:  # driver-specific errors differ per engine
        raise DatabaseError(f"Could not connect to the {config.DB_ENGINE} database: {exc}") from exc


def _adapt(sql):
    """Convert ? placeholders to %s for MySQL/PostgreSQL drivers."""
    return sql if config.DB_ENGINE == "sqlite" else sql.replace("?", "%s")


@contextmanager
def transaction():
    """Context manager: commits on success, rolls back on any error."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.exception("Transaction rolled back")
        raise DatabaseError(str(exc)) from exc
    finally:
        conn.close()


def run_query(sql, params=None):
    """Run a SELECT and return the result as a pandas DataFrame."""
    conn = get_connection()
    try:
        return pd.read_sql_query(_adapt(sql), conn, params=params or ())
    except Exception as exc:
        raise DatabaseError(f"Query failed: {exc}") from exc
    finally:
        conn.close()


def execute(sql, params=None):
    """Run one INSERT/UPDATE/DELETE inside a transaction. Returns rows affected."""
    with transaction() as conn:
        cur = conn.cursor()
        cur.execute(_adapt(sql), params or ())
        return cur.rowcount


def execute_many(sql, rows):
    """Run the same statement for many rows in one transaction."""
    if not rows:
        return 0
    with transaction() as conn:
        cur = conn.cursor()
        cur.executemany(_adapt(sql), rows)
        return cur.rowcount


def init_schema():
    """Create all tables, indexes and views from sql/schema.sql (safe to rerun)."""
    script = config.SCHEMA_FILE.read_text(encoding="utf-8")
    if config.DB_ENGINE == "sqlite":
        with transaction() as conn:
            conn.executescript(script)
    else:
        raise DatabaseError("Auto schema creation is SQLite-only. For MySQL/PostgreSQL, "
                            "run sql/schema.sql manually (see README).")


def table_counts():
    """Return {table_name: row_count} for the main tables."""
    tables = ["teams", "venues", "players", "series", "matches",
              "batting_innings", "bowling_innings", "player_career_stats"]
    counts = {}
    for name in tables:
        try:
            counts[name] = int(run_query(f"SELECT COUNT(*) AS n FROM {name}")["n"].iloc[0])
        except DatabaseError:
            counts[name] = 0
    return counts


def database_ready():
    """True if the schema exists and has match data."""
    try:
        return table_counts().get("matches", 0) > 0
    except DatabaseError:
        return False
