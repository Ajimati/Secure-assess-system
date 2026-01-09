

import sqlite3
from pathlib import Path
import datetime

# Default location of the SQLite database file (project root)
DB_PATH = Path(__file__).resolve().parents[1] / "access.db"


def init_db(path: str | Path | None = None):
    # Create the database file (if needed) and create simple tables.
    # Keep the schema tiny so beginners can read it easily.
    dbfile = Path(path) if path else DB_PATH
    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    # Users table stores basic info and a link to the trained face model
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        model_path TEXT,
        pin_salt TEXT,
        pin_hash TEXT,
        created_at TEXT
    )
    """
    )
    # Logs table stores each access attempt (who, when, scores, decision)
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        timestamp TEXT,
        face_score REAL,
        pin_score REAL,
        decision TEXT,
        reason TEXT
    )
    """
    )
    conn.commit()
    conn.close()


def _connect(path: str | Path | None = None):
    # Small helper to open a SQLite connection. Tests or tools may pass
    # a different path for convenience.
    return sqlite3.connect(Path(path) if path else DB_PATH)


def add_user(name: str, model_path: str, pin_salt: str, pin_hash: str):
    # Insert or replace a user record. We store salt+hash, not raw PIN.
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO users (name, model_path, pin_salt, pin_hash, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, str(model_path), pin_salt, pin_hash, datetime.datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_user_by_name(name: str):
    # Return a single user row or None if not found.
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id, name, model_path, pin_salt, pin_hash, created_at FROM users WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row


def list_users():
    # Return a short list of users (id, name, model_path)
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id, name, model_path FROM users")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_users():
    # Return all user rows with sensitive fields needed for matching/verify
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id, name, model_path, pin_salt, pin_hash FROM users")
    rows = cur.fetchall()
    conn.close()
    return rows


def save_log(user_id: int | None, name: str, face_score: float, pin_score: float, decision: str, reason: str):
    # Insert a log row into the DB. We also append the same info to a CSV
    # file so beginners can open it in Excel or a text editor.
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logs (user_id, name, timestamp, face_score, pin_score, decision, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, name, datetime.datetime.utcnow().isoformat(), face_score, pin_score, decision, reason),
    )
    conn.commit()
    conn.close()

    # Also append to CSV log for easy external analysis. This is optional
    # and will not break the main functionality if it fails.
    try:
        logs_dir = Path(__file__).resolve().parents[1] / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        csv_path = logs_dir / "access_log.csv"
        header = not csv_path.exists()
        line = f"{datetime.datetime.utcnow().isoformat()},{user_id or ''},{name},{face_score},{pin_score},{decision},{reason}\n"
        with open(csv_path, "a", encoding="utf-8") as f:
            if header:
                f.write("timestamp,user_id,name,face_score,pin_score,decision,reason\n")
            f.write(line)
    except Exception:
        # Don't let logging failures break the main flow
        pass


if __name__ == "__main__":
    init_db()
    print("Initialized DB at:", DB_PATH)
