import json
import sqlite3

import pytest

from app.engines.route_quote import quote_route
from app.modules import qr_ticket
from app.modules.qr_ticket import TicketError
from app.repositories import runs as runs_repo

EDGES = [("A1", "A2"), ("A2", "A3"), ("A2", "B1"), ("B1", "B2")]
RULES = [{"max_hops": 2, "price": 3.0}, {"max_hops": 4, "price": 4.0}, {"max_hops": None, "price": 6.0}]


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE calc_runs(id INTEGER PRIMARY KEY, kind TEXT, input_json TEXT, result_json TEXT, created_at TEXT)"
    )
    qr_ticket.ensure_schema(conn)
    return conn


def _quote_run(conn: sqlite3.Connection, start: str, end: str, result: dict | None = None) -> int:
    res = result if result is not None else quote_route(EDGES, start, end, RULES)
    return runs_repo.insert(conn, "quote", {"start": start, "end": end}, res)


def _ticket_rows(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) c FROM qr_tickets").fetchone()["c"]


def test_issue_freezes_fields():
    conn = _conn()
    rid = _quote_run(conn, "A1", "B2")
    t = qr_ticket.issue(conn, rid)
    assert t["code"].startswith("QR-")
    assert t["run_id"] == rid
    assert t["start"] == "A1" and t["end"] == "B2"
    assert t["path"] == ["A1", "A2", "B1", "B2"]
    assert t["hops"] == 3 and t["fare"] == 4.0
    assert t["status"] == "valid"
    assert t["void_reason"] is None and t["voided_at"] is None


def test_issue_rejects_unreachable_and_leaves_no_ticket():
    conn = _conn()
    rid = _quote_run(conn, "A1", "ZZ")  # unreachable: no path, no fare
    with pytest.raises(TicketError) as e:
        qr_ticket.issue(conn, rid)
    assert e.value.status_code == 400
    assert _ticket_rows(conn) == 0
    assert qr_ticket.list_tickets(conn, include_voided=True) == []


def test_issue_rejects_quote_without_path():
    conn = _conn()
    legacy = {"start": "A1", "end": "A3", "hops": 2, "fare": 3.0, "reachable": True}  # no path field
    rid = _quote_run(conn, "A1", "A3", result=legacy)
    with pytest.raises(TicketError) as e:
        qr_ticket.issue(conn, rid)
    assert e.value.status_code == 400
    assert _ticket_rows(conn) == 0


def test_issue_rejects_unknown_run():
    conn = _conn()
    with pytest.raises(TicketError) as e:
        qr_ticket.issue(conn, 999)
    assert e.value.status_code == 404


def test_same_run_cannot_issue_twice():
    conn = _conn()
    rid = _quote_run(conn, "A1", "B2")
    qr_ticket.issue(conn, rid)
    with pytest.raises(TicketError) as e:
        qr_ticket.issue(conn, rid)
    assert e.value.status_code == 409
    assert _ticket_rows(conn) == 1


def test_same_sequence_with_valid_ticket_rejected_even_after_new_quote():
    conn = _conn()
    rid1 = _quote_run(conn, "A1", "B2")
    qr_ticket.issue(conn, rid1)
    rid2 = _quote_run(conn, "A1", "B2")  # fresh quote, same via-station sequence
    with pytest.raises(TicketError) as e:
        qr_ticket.issue(conn, rid2)
    assert e.value.status_code == 409
    assert _ticket_rows(conn) == 1


def test_after_void_new_quote_can_issue_but_old_run_cannot():
    conn = _conn()
    rid1 = _quote_run(conn, "A1", "B2")
    t1 = qr_ticket.issue(conn, rid1)
    qr_ticket.void(conn, t1["code"], "乘客取消")
    with pytest.raises(TicketError) as e:
        qr_ticket.issue(conn, rid1)  # old run already consumed
    assert e.value.status_code == 409
    rid2 = _quote_run(conn, "A1", "B2")  # new successful quote of the same OD
    t2 = qr_ticket.issue(conn, rid2)
    assert t2["status"] == "valid" and t2["code"] != t1["code"]


def test_different_sequences_can_hold_valid_tickets():
    conn = _conn()
    t1 = qr_ticket.issue(conn, _quote_run(conn, "A1", "A3"))
    t2 = qr_ticket.issue(conn, _quote_run(conn, "A1", "B2"))
    assert {t["code"] for t in qr_ticket.list_tickets(conn)} == {t1["code"], t2["code"]}


def test_verify_returns_frozen_path_and_fare():
    conn = _conn()
    t = qr_ticket.issue(conn, _quote_run(conn, "A1", "B2"))
    v = qr_ticket.verify(conn, t["code"])
    assert v["valid"] is True
    assert v["ticket"]["path"] == ["A1", "A2", "B1", "B2"]
    assert v["ticket"]["fare"] == 4.0


def test_verify_unknown_code():
    conn = _conn()
    with pytest.raises(TicketError) as e:
        qr_ticket.verify(conn, "QR-NOPE")
    assert e.value.status_code == 404


def test_void_requires_reason():
    conn = _conn()
    t = qr_ticket.issue(conn, _quote_run(conn, "A1", "B2"))
    for bad in ("", "   ", None):
        with pytest.raises(TicketError) as e:
            qr_ticket.void(conn, t["code"], bad)
        assert e.value.status_code == 400
    assert qr_ticket.verify(conn, t["code"])["valid"] is True  # still valid


def test_void_hides_from_default_list_but_reason_stays_readable():
    conn = _conn()
    t = qr_ticket.issue(conn, _quote_run(conn, "A1", "B2"))
    v = qr_ticket.void(conn, t["code"], "重复出票")
    assert v["status"] == "voided" and v["void_reason"] == "重复出票"
    assert qr_ticket.list_tickets(conn) == []  # default list hides voided
    assert [x["code"] for x in qr_ticket.list_tickets(conn, include_voided=True)] == [t["code"]]
    got = qr_ticket.get(conn, t["code"])  # by code the reason is still readable
    assert got["status"] == "voided" and got["void_reason"] == "重复出票"
    checked = qr_ticket.verify(conn, t["code"])
    assert checked["valid"] is False and checked["ticket"]["void_reason"] == "重复出票"


def test_void_twice_rejected():
    conn = _conn()
    t = qr_ticket.issue(conn, _quote_run(conn, "A1", "B2"))
    qr_ticket.void(conn, t["code"], "第一次作废")
    with pytest.raises(TicketError) as e:
        qr_ticket.void(conn, t["code"], "第二次作废")
    assert e.value.status_code == 409


def test_void_unknown_code():
    conn = _conn()
    with pytest.raises(TicketError) as e:
        qr_ticket.void(conn, "QR-NOPE", "原因")
    assert e.value.status_code == 404


def test_void_does_not_modify_quote_run_fare():
    conn = _conn()
    rid = _quote_run(conn, "A1", "B2")
    before = runs_repo.get_by_id(conn, rid)["result_json"]
    t = qr_ticket.issue(conn, rid)
    qr_ticket.void(conn, t["code"], "测试作废")
    after = runs_repo.get_by_id(conn, rid)["result_json"]
    assert after == before
    assert json.loads(after)["fare"] == 4.0
