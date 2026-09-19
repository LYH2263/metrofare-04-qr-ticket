from app.db import connect
from app.engines.route_quote import quote_route
from app.modules import qr_ticket
from app.repositories import edges as edges_repo
from app.repositories import fare_rules as rules_repo
from app.repositories import qr_tickets as tickets_repo
from app.repositories import runs as runs_repo
from app.repositories import settings as settings_repo
from app.repositories import stations as stations_repo


class MetroService:
    def __init__(self):
        self._conn = connect()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def stations(self):
        return stations_repo.list_all(self._conn)

    def station(self, code: str):
        return stations_repo.get_by_code(self._conn, code)

    def edges(self):
        return [{"a": a, "b": b} for a, b in edges_repo.list_pairs(self._conn)]

    def fare_rules(self):
        return rules_repo.list_ordered(self._conn)

    def settings(self):
        return settings_repo.get_map(self._conn)

    def quote(self, start: str, end: str, persist: bool):
        edges = edges_repo.list_pairs(self._conn)
        rules = rules_repo.as_calc_rules(self._conn)
        result = quote_route(edges, start, end, rules)
        run_id = None
        if persist and result.get("reachable"):
            run_id = runs_repo.insert(self._conn, "quote", {"start": start, "end": end}, result)
        return {"run_id": run_id, **result}

    def history(self, limit=50):
        return runs_repo.list_recent(self._conn, limit)

    def issue_ticket(self, run_id: int):
        return qr_ticket.issue(self._conn, run_id)

    def verify_ticket(self, code: str):
        return qr_ticket.verify(self._conn, code)

    def tickets(self):
        return tickets_repo.list_active(self._conn)

    def void_ticket(self, code: str, reason: str):
        return qr_ticket.void(self._conn, code, reason)

    def dashboard(self):
        st = stations_repo.list_all(self._conn)
        clean = [s for s in st if "种子" not in s["name"]]
        dirty = [s for s in st if "种子" in s["name"]]
        return {
            "station_count": len(st),
            "edge_count": len(edges_repo.list_pairs(self._conn)),
            "clean_stations": len(clean),
            "dirty_stations": len(dirty),
        }
