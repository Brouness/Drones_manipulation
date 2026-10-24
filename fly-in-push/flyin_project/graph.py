"""Undirected graph of zones and connections."""

from models import Connection, Zone


class Graph:
    """Store zones, connections, and zone adjacency."""

    def __init__(self) -> None:
        """Create an empty graph."""
        self._zones: dict[str, Zone] = {}
        self._connections: dict[tuple[str, str], Connection] = {}
        self._adjacency: dict[str, list[str]] = {}

    def add_zone(self, zone: Zone) -> None:
        """Add a uniquely named zone to the graph."""
        if zone.name in self._zones:
            raise ValueError(f"Duplicate zone: {zone.name}")
        self._zones[zone.name] = zone
        self._adjacency[zone.name] = []

    def _validate_zone(self, a: str, b: str) -> None:
        """Ensure both endpoint names are present in the graph."""
        if a not in self._zones:
            raise KeyError(f"Unknown zone: {a}")
        if b not in self._zones:
            raise KeyError(f"Unknown zone: {b}")

    @staticmethod
    def _conn_key(a: str, b: str) -> tuple[str, str]:
        """Build a direction-independent connection key."""
        first, second = sorted((a, b))
        return first, second

    def add_connection(self, conn: Connection) -> None:
        """Add a unique connection between previously added zones."""
        self._validate_zone(conn.a, conn.b)
        key = conn.key()
        if key in self._connections:
            raise ValueError(f"Duplicate connection: {conn.a}-{conn.b}")
        self._connections[key] = conn
        self._adjacency[conn.a].append(conn.b)
        self._adjacency[conn.b].append(conn.a)

    def get_zone(self, name: str) -> Zone:
        """Return a zone by name or raise KeyError."""
        try:
            return self._zones[name]
        except KeyError as error:
            raise KeyError(f"Unknown zone: {name}") from error

    def zone_names(self) -> tuple[str, ...]:
        """Return zone names in declaration order."""
        return tuple(self._zones)

    def neighbors(self, name: str) -> tuple[Zone, ...]:
        """Return adjacent zones in declaration order."""
        if name not in self._zones:
            raise KeyError(f"Unknown zone: {name}")
        return tuple(self._zones[other] for other in self._adjacency[name])

    def get_connection(self, a: str, b: str) -> Connection:
        """Return the undirected connection between two adjacent zones."""
        self._validate_zone(a, b)
        key = self._conn_key(a, b)
        try:
            return self._connections[key]
        except KeyError as error:
            raise KeyError(f"Unknown connection: {a}-{b}") from error
