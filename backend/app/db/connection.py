import os
import time
import random
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Callable, Any, Generator

logger = logging.getLogger("bizpulse.db.connection")

DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "bizpulse.db"


def get_db_path() -> str:
    """Return the configured SQLite database file path."""
    return os.getenv("DATABASE_PATH", str(DEFAULT_DB_PATH))


def get_db_connection(
    db_path: Optional[str] = None,
    timeout: float = 15.0,
) -> sqlite3.Connection:
    """
    Establish and return a robust SQLite database connection with row factory.
    Enforces:
    - PRAGMA foreign_keys = ON (referential integrity)
    - PRAGMA journal_mode = WAL (high concurrent read/write concurrency)
    - PRAGMA synchronous = NORMAL (safe and performant in WAL mode)
    - PRAGMA busy_timeout = 15000 (wait up to 15 seconds before raising lock error)
    """
    path = db_path or get_db_path()
    if path != ":memory:":
        parent_dir = Path(path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        path,
        timeout=timeout,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row

    # Execute reliability pragmas
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)};")

    if path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")

    return conn


def execute_with_retry(
    conn: sqlite3.Connection,
    operation: Callable[[], Any],
    max_retries: int = 3,
    initial_delay: float = 0.05,
) -> Any:
    """
    Execute a database operation with exponential backoff on transient
    sqlite3.OperationalError (database is locked / table is locked).
    """
    attempt = 0
    delay = initial_delay
    last_error: Optional[Exception] = None

    while attempt < max_retries:
        try:
            return operation()
        except sqlite3.OperationalError as e:
            err_msg = str(e).lower()
            if "locked" in err_msg or "busy" in err_msg:
                attempt += 1
                last_error = e
                jitter = random.uniform(0.5, 1.5)
                sleep_time = delay * jitter
                logger.warning(
                    f"SQLite concurrency lock detected (attempt {attempt}/{max_retries}). "
                    f"Retrying in {sleep_time:.3f}s: {e}"
                )
                time.sleep(sleep_time)
                delay *= 2
            else:
                raise
        except Exception:
            raise

    if last_error:
        raise last_error


@contextmanager
def db_transaction(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager providing an explicit atomic database transaction.
    - Automatically begins transaction.
    - Commits on successful block completion.
    - Automatically rolls back on any exception.
    - Always closes connection on exit.
    """
    conn = get_db_connection(db_path)
    try:
        with conn:
            yield conn
    except Exception as e:
        logger.error(f"Transaction failed and was rolled back: {e}")
        raise
    finally:
        conn.close()
