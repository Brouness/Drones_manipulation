from models import Connection, Zone

class Graph:
    def __init__(self) -> None:
        self._zones: dict[str, Zone] = {}
        self._connections: dict[tuple[str, str], Connection] = {}
        self._adjacency: dict[str, list[str]] = {}

    def add_zone(self, zone: Zone) -> None:
        if zone.name in self._zones:
            raise ValueError(f"Zone already exist duplicate zone is forbidden {zone.name}")
        self._zones[zone.name] = zone
        self._adjacency[zone.name] = []

    def _validate_zone(self, a: str, b: str) -> None:
        if a not in self._zones:
            raise KeyError(f"Uncknown zone name {a}")
        if b not in self._zones:
            raise KeyError(f"Uncknown zone name {b}")

    def _conn_key(self, a: str, b: str) -> tuple[str, str]:
        return tuple(sorted((a, b)))

    def add_connection(self, conn: Connection) -> None:
        k = conn.key()
        a = conn.a
        b = conn.b
        self._validate_zone(a, b)
        if k in self._connections:
            raise ValueError(f"Connection already exist {k}")
        self._connections[k] = conn
        self._adjacency[a].append(b)
        self._adjacency[b].append(a)

    def get_zone(self, name: str) -> Zone:
        if name not in self._zones:
            raise KeyError(f"Uncknown zone name {name}")
        zone: Zone = self._zones[name]
        return zone

    def neighbors(self, name: str) -> tuple[Zone]:
        if name not in self._zones:
            raise KeyError(f"Uncknown zone name {name}")
        my_list: list[Zone] = []
        for zone in self._adjacency[name]:
            obj_zone: Zone = self._zones[zone]
            my_list.append(obj_zone)
        return tuple(my_list)

    def get_connection(self, a: str, b: str) -> Connection:
        self._validate_zone(a, b)
        keys = self._conn_key(a, b)
        if keys not in self._connections:
            raise KeyError(f"Uncknown connection: {a}-{b}")
        connection: Connection = self._connections[keys]
        return connection
