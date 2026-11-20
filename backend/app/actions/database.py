import os
import sqlite3
from pathlib import Path
from typing import Optional

from ..db.connection import (
    get_db_path as _core_get_db_path,
    get_db_connection as _core_get_db_connection,
)
from ..db.migrations import run_migrations

DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "bizpulse.db"


def get_db_path() -> str:
    """Return the configured SQLite database file path."""
    return _core_get_db_path()


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Establish and return a SQLite database connection with row factory.
    Enforces foreign keys, busy timeout, and WAL mode for high concurrency.
    """
    return _core_get_db_connection(db_path)


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initialize SQLite schema for Action Management System & Verification Engine.
    Executes ordered, tracked database migrations.
    """
    run_migrations(db_path)
