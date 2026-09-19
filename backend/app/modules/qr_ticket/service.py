import json
import secrets
import sqlite3
from datetime import datetime, timezone

from app.modules.qr_ticket import repository as repo
from app.repositories import runs as runs_repo


class TicketError(Exception):
    """Domain error; the router layer maps status_code to an HTTP response."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_dict(row: dict) -> dict:
    return {
        "code": row["code"],
        "run_id": row["run_id"],
        "start": row["start_code"],
        "end": row["end_code"],
        "path": json.loads(row["path_json"]),
        "hops": row["hops"],
        "fare": row["fare"],
        "status": row["status"],
        "created_at": row["created_at"],
        "voided_at": row["voided_at"],
        "void_reason": row["void_reason"],
    }


def issue(conn: sqlite3.Connection, run_id: int) -> dict:
    """Issue a QR ticket from a persisted successful quote run.

    Only a reachable quote that carries a via-station sequence is issuable.
    A run yields at most one ticket; a via-station sequence may hold at most
    one valid ticket — issuing again requires a fresh successful quote.
    On any failure nothing is committed, so no valid ticket is left behind.
    """
    run = runs_repo.get_by_id(conn, run_id)
    if run is None or run["kind"] != "quote":
        raise TicketError("询价记录不存在", 404)
    result = json.loads(run["result_json"])
    path = result.get("path")
    if not result.get("reachable") or not isinstance(path, list) or not path:
        raise TicketError("该询价不可达或缺少途经站序列，不能签发", 400)
    if result.get("fare") is None or result.get("hops") is None:
        raise TicketError("该询价缺少票价或站数，不能签发", 400)
    if repo.get_by_run(conn, run_id):
        raise TicketError("该询价已签发过乘车码，请重新询价后再签", 409)
    path_json = json.dumps(path, ensure_ascii=False)
    clash = repo.find_valid_by_path(conn, path_json)
    if clash:
        raise TicketError(f"同一途经站序列已存在有效乘车码 {clash['code']}，不能重复签发", 409)
    last_err: sqlite3.IntegrityError | None = None
    for _ in range(3):  # retry only covers a random code collision
        code = "QR-" + secrets.token_hex(5).upper()
        try:
            repo.insert(
                conn,
                code=code,
                run_id=run_id,
                start=result["start"],
                end=result["end"],
                path_json=path_json,
                hops=int(result["hops"]),
                fare=float(result["fare"]),
                created_at=_now(),
            )
            conn.commit()
            return _to_dict(repo.get_by_code(conn, code))
        except sqlite3.IntegrityError as e:
            conn.rollback()
            last_err = e
    raise TicketError("签发冲突：该询价或途经站序列已存在乘车码", 409) from last_err


def verify(conn: sqlite3.Connection, code: str) -> dict:
    """Verify by code. A valid ticket returns the frozen path and fare."""
    row = repo.get_by_code(conn, code)
    if row is None:
        raise TicketError("乘车码不存在", 404)
    ticket = _to_dict(row)
    return {"valid": row["status"] == "valid", "ticket": ticket}


def void(conn: sqlite3.Connection, code: str, reason: str | None) -> dict:
    """Void a ticket; reason is mandatory. The source quote run is untouched."""
    reason = (reason or "").strip()
    if not reason:
        raise TicketError("作废原因必填", 400)
    row = repo.get_by_code(conn, code)
    if row is None:
        raise TicketError("乘车码不存在", 404)
    if row["status"] != "valid":
        raise TicketError("该乘车码已是作废状态", 409)
    repo.mark_voided(conn, code, reason, _now())
    conn.commit()
    return _to_dict(repo.get_by_code(conn, code))


def get(conn: sqlite3.Connection, code: str) -> dict:
    """Read by code — works for voided tickets too, so the reason stays readable."""
    row = repo.get_by_code(conn, code)
    if row is None:
        raise TicketError("乘车码不存在", 404)
    return _to_dict(row)


def list_tickets(conn: sqlite3.Connection, include_voided: bool = False, limit: int = 100) -> list[dict]:
    """Default listing hides voided tickets."""
    return [_to_dict(r) for r in repo.list_tickets(conn, include_voided, limit)]
