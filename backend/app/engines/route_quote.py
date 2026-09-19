from app.engines.fare_rules import fare_for_hops
from app.engines.graph_bfs import shortest_path


def quote_route(edges: list[tuple[str, str]], start: str, end: str, rules: list[dict]) -> dict:
    path = shortest_path(edges, start, end)
    if path is None:
        return {"start": start, "end": end, "hops": None, "path": None, "fare": None, "reachable": False}
    fare = fare_for_hops(len(path) - 1, rules)
    return {"start": start, "end": end, "hops": len(path) - 1, "path": path, "fare": fare, "reachable": True}
