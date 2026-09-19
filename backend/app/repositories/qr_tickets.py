import json
import sqlite3
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["path"] = json.loads(d.pop("path_json"))
    return d


def find_active_by_path(conn: sqlite3.Connection, path: list[str]) -> dict | None:
    row = conn.execute(
        "SELECT * FROM qr_tickets WHERE status='active' AND path_json=?",
        (json.dumps(path, ensure_ascii=False),),
    ).fetchone()
    return _row_to_dict(row) if row else None


def insert(
    conn: sqlite3.Connection,
    code: str,
    run_id: int | None,
    start: str,
    end: str,
    path: list[str],
    hops: int,
    fare: float,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO qr_tickets(code, run_id, start, end, path_json, hops, fare, status, created_at)
        VALUES (?,?,?,?,?,?,?, 'active', ?)
        """,
        (code, run_id, start, end, json.dumps(path, ensure_ascii=False), hops, fare, _now()),
    )
    return int(cur.lastrowid)


def get_by_code(conn: sqlite3.Connection, code: str) -> dict | None:
    row = conn.execute("SELECT * FROM qr_tickets WHERE code=?", (code,)).fetchone()
    return _row_to_dict(row) if row else None


def list_active(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM qr_tickets WHERE status='active' ORDER BY id DESC"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def void(conn: sqlite3.Connection, ticket_id: int, reason: str) -> None:
    conn.execute(
        "UPDATE qr_tickets SET status='void', void_reason=?, voided_at=? WHERE id=?",
        (reason, _now(), ticket_id),
    )
