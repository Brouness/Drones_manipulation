"""Data models for zones and connections."""

from dataclasses import dataclass
from enum import Enum


class ZoneType(str, Enum):
    """Kinds of zones and their movement behavior."""

    NORMAL = "normal"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"
    PRIORITY = "priority"


def _validate_name(name: str) -> None:
    """Reject empty names and characters forbidden by the map format."""
    if not name:
        raise ValueError("Empty name is forbidden")
    if " " in name:
        raise ValueError(f"Spaces are forbidden in names: {name}")
    if "-" in name:
        raise ValueError(f"Dashes are forbidden in names: {name}")


@dataclass
class Zone:
    """A named place on the map."""

    name: str
    x: int
    y: int
    color: str | None = None
    zone_type: ZoneType = ZoneType.NORMAL
    max_drones: int = 1
    is_end: bool = False
    is_start: bool = False

    def __post_init__(self) -> None:
        """Validate values that do not depend on parsing context."""
        _validate_name(self.name)
        if self.max_drones <= 0:
            raise ValueError(
                f"Max drones must be positive: {self.max_drones}"
            )

    def is_blocked(self) -> bool:
        """Return whether drones may not enter this zone."""
        return self.zone_type is ZoneType.BLOCKED

    def capacity(self) -> int | None:
        """Return the occupancy limit, or None for unlimited zones."""
        if self.is_start or self.is_end:
            return None
        return self.max_drones

    def move_cost(self) -> int:
        """Return the cost to enter this zone in simulation turns."""
        if self.zone_type in (ZoneType.NORMAL, ZoneType.PRIORITY):
            return 1
        if self.zone_type is ZoneType.RESTRICTED:
            return 2
        raise ValueError(
            f"A blocked zone cannot be entered: {self.name}"
        )


@dataclass(frozen=True)
class Connection:
    """An undirected link between two zones."""

    a: str
    b: str
    max_link_capacity: int = 1

    def __post_init__(self) -> None:
        """Validate endpoints and connection capacity."""
        _validate_name(self.a)
        _validate_name(self.b)
        if self.a == self.b:
            raise ValueError(f"Self-connections are forbidden: {self.a}")
        if self.max_link_capacity <= 0:
            raise ValueError("Connection capacity must be positive")

    def key(self) -> tuple[str, str]:
        """Return a direction-independent key for this connection."""
        first, second = sorted((self.a, self.b))
        return first, second
