from collections import defaultdict, deque


def _build_graph(edges: list[tuple[str, str]]) -> dict[str, set[str]]:
    g: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        g[a].add(b)
        g[b].add(a)
    return g


def shortest_path(edges: list[tuple[str, str]], start: str, end: str) -> list[str] | None:
    """Undirected graph BFS; returns the visited-station sequence (fewest hops),
    or None when unreachable. Ties resolve by neighbour insertion order."""
    g = _build_graph(edges)
    if start not in g or end not in g:
        return None
    if start == end:
        return [start]
    prev: dict[str, str] = {}
    q = deque([start])
    seen = {start}
    while q:
        cur = q.popleft()
        if cur == end:
            break
        for nxt in g[cur]:
            if nxt in seen:
                continue
            seen.add(nxt)
            prev[nxt] = cur
            q.append(nxt)
    if end not in seen:
        return None
    path = [end]
    while path[-1] != start:
        path.append(prev[path[-1]])
    path.reverse()
    return path


def shortest_hops(edges: list[tuple[str, str]], start: str, end: str) -> int | None:
    """Undirected graph BFS hop count; None if unreachable."""
    path = shortest_path(edges, start, end)
    if path is None:
        return None
    return len(path) - 1
