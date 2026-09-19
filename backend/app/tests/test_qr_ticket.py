import json
import sqlite3

import pytest

from app.modules import qr_ticket

SCHEMA = """
CREATE TABLE calc_runs(
    id INTEGER PRIMARY KEY, kind TEXT, input_json TEXT, result_json TEXT, created_at TEXT);
CREATE TABLE qr_tickets(
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE,
    run_id INTEGER,
    start TEXT,
    end TEXT,
    path_json TEXT,
    hops INTEGER,
    fare REAL,
    status TEXT NOT NULL DEFAULT 'active',
    void_reason TEXT,
    created_at TEXT,
    voided_at TEXT);
CREATE UNIQUE INDEX ux_qr_active_path ON qr_tickets(path_json) WHERE status='active';
"""

EDGES = [("A1", "A2"), ("A2", "A3"), ("A2", "B1"), ("B1", "B2")]
PATH_A1_B2 = ["A1", "A2", "B1", "B2"]


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    yield c
    c.close()


def add_run(c, kind="quote", payload=None, result=None) -> int:
    cur = c.execute(
        "INSERT INTO calc_runs(kind, input_json, result_json, created_at) VALUES (?,?,?,'t')",
        (
            kind,
            json.dumps(payload or {"start": "A1", "end": "B2"}),
            json.dumps(result or {"start": "A1", "end": "B2", "hops": 3, "path": PATH_A1_B2,
                                  "fare": 4.0, "reachable": True}),
        ),
    )
    c.commit()
    return int(cur.lastrowid)


def test_issue_freezes_journey(conn):
    run_id = add_run(conn)
    t = qr_ticket.issue(conn, run_id)
    assert t["status"] == "active"
    assert t["start"] == "A1" and t["end"] == "B2"
    assert t["path"] == PATH_A1_B2
    assert t["hops"] == 3 and t["fare"] == 4.0
    assert t["code"].startswith("QR-")
    assert t["void_reason"] is None


def test_verify_returns_issued_path_and_fare(conn):
    t = qr_ticket.issue(conn, add_run(conn))
    v = qr_ticket.verify(conn, t["code"])
    assert v["path"] == PATH_A1_B2 and v["fare"] == 4.0


def test_duplicate_path_is_rejected(conn):
    qr_ticket.issue(conn, add_run(conn))
    with pytest.raises(qr_ticket.TicketError) as ei:
        qr_ticket.issue(conn, add_run(conn))  # another run, same sequence
    assert ei.value.status == 409
    # failure leaves no extra ticket behind
    assert len(qr_ticket.list_active(conn)) == 1


def test_new_od_after_void_is_allowed(conn):
    first = qr_ticket.issue(conn, add_run(conn))
    qr_ticket.void(conn, first["code"], "行程取消")
    second = qr_ticket.issue(conn, add_run(conn))
    assert second["id"] != first["id"]
    assert [t["id"] for t in qr_ticket.list_active(conn)] == [second["id"]]


def test_void_requires_reason(conn):
    t = qr_ticket.issue(conn, add_run(conn))
    with pytest.raises(qr_ticket.TicketError):
        qr_ticket.void(conn, t["code"], "   ")
    assert qr_ticket.verify(conn, t["code"])["status"] == "active"


def test_voided_hidden_from_list_but_readable_by_code(conn):
    t = qr_ticket.issue(conn, add_run(conn))
    qr_ticket.void(conn, t["code"], "临时改道")
    assert qr_ticket.list_active(conn) == []
    gone = qr_ticket.verify(conn, t["code"])
    assert gone["status"] == "void" and gone["void_reason"] == "临时改道"


def test_void_does_not_touch_quote_run(conn):
    run_id = add_run(conn)
    t = qr_ticket.issue(conn, run_id)
    qr_ticket.void(conn, t["code"], "放弃出行")
    run = conn.execute("SELECT result_json FROM calc_runs WHERE id=?", (run_id,)).fetchone()
    assert json.loads(run["result_json"])["fare"] == 4.0


def test_unreachable_run_cannot_issue(conn):
    run_id = add_run(conn, result={"start": "A1", "end": "X9", "hops": None,
                                   "path": None, "fare": None, "reachable": False})
    with pytest.raises(qr_ticket.TicketError):
        qr_ticket.issue(conn, run_id)
    assert qr_ticket.list_active(conn) == []


def test_run_without_path_cannot_issue(conn):
    run_id = add_run(conn, result={"start": "A1", "end": "B2", "hops": 3, "fare": 4.0,
                                   "reachable": True})
    with pytest.raises(qr_ticket.TicketError):
        qr_ticket.issue(conn, run_id)


def test_unknown_run_and_code(conn):
    with pytest.raises(qr_ticket.TicketError) as ei:
        qr_ticket.issue(conn, 999)
    assert ei.value.status == 404
    with pytest.raises(qr_ticket.TicketError) as ei:
        qr_ticket.verify(conn, "QR-NOPE")
    assert ei.value.status == 404
