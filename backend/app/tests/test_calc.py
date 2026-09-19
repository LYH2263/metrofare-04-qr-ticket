from app.engines.fare_rules import fare_for_hops
from app.engines.graph_bfs import shortest_hops, shortest_path
from app.engines.route_quote import quote_route

EDGES = [("A1", "A2"), ("A2", "A3"), ("A2", "B1"), ("B1", "B2")]
RULES = [{"max_hops": 2, "price": 3.0}, {"max_hops": 4, "price": 4.0}, {"max_hops": None, "price": 6.0}]


def test_hops_a1_a3():
    assert shortest_hops(EDGES, "A1", "A3") == 2


def test_hops_a1_b2():
    assert shortest_hops(EDGES, "A1", "B2") == 3


def test_fare_by_hops():
    assert fare_for_hops(2, RULES) == 3.0
    assert fare_for_hops(3, RULES) == 4.0
    assert fare_for_hops(10, RULES) == 6.0


def test_quote():
    q = quote_route(EDGES, "A1", "B2", RULES)
    assert q["hops"] == 3 and q["fare"] == 4.0


def test_path_sequence():
    assert shortest_path(EDGES, "A1", "B2") == ["A1", "A2", "B1", "B2"]
    assert shortest_path(EDGES, "A1", "ZZ") is None
    assert shortest_path(EDGES, "A1", "A1") == ["A1"]


def test_quote_carries_path():
    q = quote_route(EDGES, "A1", "B2", RULES)
    assert q["reachable"] and q["path"] == ["A1", "A2", "B1", "B2"]
    bad = quote_route(EDGES, "A1", "ZZ", RULES)
    assert not bad["reachable"] and bad["path"] is None
