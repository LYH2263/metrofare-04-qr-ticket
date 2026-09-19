import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS qr_tickets(
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    run_id INTEGER NOT NULL,
    start_code TEXT NOT NULL,
    end_code TEXT NOT NULL,
    path_json TEXT NOT NULL,
    hops INTEGER NOT NULL,
    fare REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'valid',
    created_at TEXT NOT NULL,
    voided_at TEXT,
    void_reason TEXT
);
-- one successful issuance per quote run: re-issuing requires a fresh quote
CREATE UNIQUE INDEX IF NOT EXISTS ux_qr_tickets_run ON qr_tickets(run_id);
-- at most one valid ticket per via-station sequence
CREATE UNIQUE INDEX IF NOT EXISTS ux_qr_tickets_valid_path
    ON qr_tickets(path_json) WHERE status='valid';
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def insert(conn: sqlite3.Connection, *, code: str, run_id: int, start: str, end: str,
           path_json: str, hops: int, fare: float, created_at: str) -> int:
    """Insert a valid ticket. Caller commits (or rolls back on failure)."""
    cur = conn.execute(
        "INSERT INTO qr_tickets(code, run_id, start_code, end_code, path_json, hops, fare, status, created_at)"
        " VALUES (?,?,?,?,?,?,?,'valid',?)",
        (code, run_id, start, end, path_json, hops, fare, created_at),
    )
    return int(cur.lastrowid)


def get_by_code(conn: sqlite3.Connection, code: str) -> dict | None:
    row = conn.execute("SELECT * FROM qr_tickets WHERE code=?", (code,)).fetchone()
    return dict(row) if row else None


def get_by_run(conn: sqlite3.Connection, run_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM qr_tickets WHERE run_id=?", (run_id,)).fetchone()
    return dict(row) if row else None


def find_valid_by_path(conn: sqlite3.Connection, path_json: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM qr_tickets WHERE path_json=? AND status='valid'", (path_json,)
    ).fetchone()
    return dict(row) if row else None


def list_tickets(conn: sqlite3.Connection, include_voided: bool = False, limit: int = 100) -> list[dict]:
    if include_voided:
        q = "SELECT * FROM qr_tickets ORDER BY id DESC LIMIT ?"
        return [dict(r) for r in conn.execute(q, (limit,)).fetchall()]
    q = "SELECT * FROM qr_tickets WHERE status='valid' ORDER BY id DESC LIMIT ?"
    return [dict(r) for r in conn.execute(q, (limit,)).fetchall()]


def mark_voided(conn: sqlite3.Connection, code: str, reason: str, voided_at: str) -> int:
    cur = conn.execute(
        "UPDATE qr_tickets SET status='voided', void_reason=?, voided_at=?"
        " WHERE code=? AND status='valid'",
        (reason, voided_at, code),
    )
    return cur.rowcount
