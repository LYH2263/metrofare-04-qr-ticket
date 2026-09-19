"""QR ticket capability: issue / verify / void.

A ticket freezes the quoted journey (start, end, visited-station sequence,
hop count, payable fare) at issue time. It can only be issued against a
persisted quote run that is reachable and carries a station sequence.

Invariants:
 * at most one *active* ticket may exist for a given station sequence;
 * a failed issue never leaves a row behind (single transaction + partial
   unique index ``ux_qr_active_path``);
 * voiding writes the reason onto the ticket only and never touches the
   underlying quote run, so historical fares stay intact.
"""
import json
import sqlite3
import uuid

from app.repositories import qr_tickets as ticket_repo
from app.repositories import runs as runs_repo


class TicketError(Exception):
    """Domain error; ``status`` is the suggested HTTP status."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _new_code() -> str:
    return "QR-" + uuid.uuid4().hex[:12].upper()


def issue(conn: sqlite3.Connection, run_id: int) -> dict:
    run = runs_repo.get_by_id(conn, run_id)
    if run is None:
        raise TicketError("询价记录不存在", 404)
    if run.get("kind") != "quote":
        raise TicketError("仅可凭询价记录签发乘车码", 400)

    try:
        result = json.loads(run.get("result_json") or "{}")
        payload = json.loads(run.get("input_json") or "{}")
    except json.JSONDecodeError:
        raise TicketError("询价记录已损坏，无法签发", 400)

    if not result.get("reachable"):
        raise TicketError("本次询价不可达，不能签发", 400)
    path = result.get("path")
    if not path or not isinstance(path, list):
        raise TicketError("本次询价未给出途经站序列，不能签发", 400)
    fare = result.get("fare")
    if fare is None:
        raise TicketError("本次询价缺少应付票价，不能签发", 400)

    start = result.get("start") or payload.get("start")
    end = result.get("end") or payload.get("end")
    hops = result.get("hops")
    if hops is None:
        hops = len(path) - 1
    if start != path[0] or end != path[-1]:
        raise TicketError("途经站序列与起终点不一致，不能签发", 400)

    existing = ticket_repo.find_active_by_path(conn, path)
    if existing is not None:
        raise TicketError(
            f"该途经站序列已有有效乘车码 {existing['code']}，请先作废或发起新的起终点询价",
            409,
        )

    code = _new_code()
    try:
        # Single transaction: duplicate check and insert either both succeed
        # or leave nothing behind. The partial unique index is the hard guard.
        conn.execute("BEGIN IMMEDIATE")
        ticket_id = ticket_repo.insert(conn, code, run_id, start, end, path, int(hops), float(fare))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        dup = ticket_repo.find_active_by_path(conn, path)
        hint = f"：{dup['code']}" if dup else ""
        raise TicketError(f"该途经站序列已存在有效乘车码{hint}", 409)
    except Exception:
        conn.rollback()
        raise

    ticket = ticket_repo.get_by_code(conn, code)
    assert ticket is not None
    return ticket


def verify(conn: sqlite3.Connection, code: str) -> dict:
    ticket = ticket_repo.get_by_code(conn, code)
    if ticket is None:
        raise TicketError("乘车码不存在", 404)
    # Path and fare come straight from the frozen row, so a successful
    # verification always matches what was issued.
    return ticket


def list_active(conn: sqlite3.Connection) -> list[dict]:
    return ticket_repo.list_active(conn)


def void(conn: sqlite3.Connection, code: str, reason: str) -> dict:
    reason = (reason or "").strip()
    if not reason:
        raise TicketError("作废必须填写原因", 400)
    ticket = ticket_repo.get_by_code(conn, code)
    if ticket is None:
        raise TicketError("乘车码不存在", 404)
    if ticket["status"] != "active":
        raise TicketError("该乘车码已作废，无需重复作废", 409)
    conn.execute("BEGIN IMMEDIATE")
    try:
        ticket_repo.void(conn, ticket["id"], reason)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return ticket_repo.get_by_code(conn, code)
