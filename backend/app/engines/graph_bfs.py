from collections import defaultdict, deque


def shortest_path(edges: list[tuple[str, str]], start: str, end: str) -> list[str] | None:
    """Undirected BFS shortest path as a station sequence; None if unreachable.

    Neighbors are visited in sorted order so the sequence is deterministic
    across runs (the same start/end always yields the same path).
    """
    if start == end:
        return [start]
    g: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        g[a].add(b)
        g[b].add(a)
    if start not in g or end not in g:
        return None
    prev: dict[str, str | None] = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        for nxt in sorted(g[cur]):
            if nxt in prev:
                continue
            prev[nxt] = cur
            if nxt == end:
                path = [end]
                while path[-1] != start:
                    path.append(prev[path[-1]])
                path.reverse()
                return path
            q.append(nxt)
    return None


def shortest_hops(edges: list[tuple[str, str]], start: str, end: str) -> int | None:
    """Undirected graph BFS hop count; None if unreachable."""
    path = shortest_path(edges, start, end)
    return None if path is None else len(path) - 1
