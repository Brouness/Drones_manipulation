from models import Connection, ZoneType, Zone, dataclass


@dataclass
class Graph:
    _zones: dict[str, Zone] = {}
    _connections: dict[tuple[str, str], Connection] = {}
    _adjacency: dict[str, list[str]] = {}

    def add_zone(self, zone: Zone) -> None:
        if zone.name in self._zones:
            raise ValueError(f"Zone already exist duplicate zone is forbidden {zone.name}")
        self._zones[zone.name] = zone

    def add_connection(self, conn: Connection) -> None:
        self._connections[conn.key()] = conn

    def add_adjacency(self, ) -> None:
        