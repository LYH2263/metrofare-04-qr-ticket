from app.engines.fare_rules import fare_for_hops
from app.engines.graph_bfs import shortest_path


def quote_route(edges: list[tuple[str, str]], start: str, end: str, rules: list[dict]) -> dict:
    path = shortest_path(edges, start, end)
    if path is None:
        return {"start": start, "end": end, "hops": None, "fare": None, "path": None, "reachable": False}
    hops = len(path) - 1
    fare = fare_for_hops(hops, rules)
    return {"start": start, "end": end, "hops": hops, "fare": fare, "path": path, "reachable": True}
