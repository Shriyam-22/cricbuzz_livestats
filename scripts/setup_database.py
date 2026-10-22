"""Create the database and load sample data.

Run from the project folder:  python scripts/setup_database.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from services.sample_data import seed_sample_data  # noqa: E402
from utils.db_connection import table_counts  # noqa: E402

if __name__ == "__main__":
    print(f"Database: {config.SQLITE_PATH}")
    summary = seed_sample_data()
    print(f"Loaded sample data: {summary}")
    for table, count in table_counts().items():
        print(f"  {table:<22}{count:>8,}")
