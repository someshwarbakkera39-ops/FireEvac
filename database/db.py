"""
SQLite Database Connection Manager & Query Utilities
Blueprint Section 11 Implementation
"""

import os
import sqlite3
from flask import g

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "digital_twin.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

def get_db():
    """Returns a thread-local SQLite connection with dictionary row access."""
    try:
        # Check if in Flask app context
        if "db" not in g:
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db
    except RuntimeError:
        # Outside application context (CLI or standalone script)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

def close_db(e=None):
    """Closes the active database connection for the current request."""
    try:
        db = g.pop("db", None)
        if db is not None:
            db.close()
    except RuntimeError:
        pass

def init_db():
    """Initializes SQLite schema tables."""
    conn = get_db()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    # Ensure migration columns
    try:
        conn.execute("ALTER TABLE occupancy_sim ADD COLUMN scanned_qr TEXT")
    except Exception:
        pass
    try:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_occ_sim_occupant_id ON occupancy_sim(occupant_id)")
    except Exception:
        pass
    conn.commit()

def query_db(query, args=(), one=False):
    """Executes a SELECT query and returns a list of dictionaries (or a single dictionary)."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    res = [dict(row) for row in rv]
    return (res[0] if res else None) if one else res

def execute_db(query, args=()):
    """Executes an INSERT, UPDATE, or DELETE query and commits."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    conn.commit()
    last_id = cur.lastrowid
    affected = cur.rowcount
    cur.close()
    return {"lastrowid": last_id, "rowcount": affected}

def execute_many(query, seq_of_args):
    """Executes a batch query within a single transaction."""
    conn = get_db()
    cur = conn.cursor()
    cur.executemany(query, seq_of_args)
    conn.commit()
    cur.close()

