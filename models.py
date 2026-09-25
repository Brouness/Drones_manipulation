from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ZoneType(Enum):
    """Supported zone types. """

    NORMAL = "Normal"
    BLOCKED = "Blocked"
    RESTRICTED = "Restricted"
    PRIORITY = "Priority"


def _validate_name(name: str) -> None:
    if not name:
        raise ValueError("Zone name must not be empty")
    elif " " in name:
        raise ValueError(f"invalid zone name {name}: spaces are forbidden")
    elif "-" in name:
        raise ValueError(f"invalid zone name {name}: dashes are forbidden")


@dataclass(frozen=True, slots=True)
class Zone:
    """A node of the network graph."""

    name: str
    x: int
    y: int
    color: Optional[str]
    max_drones: int
    is_start: bool
    is_end: bool
    zone_type: ZoneType = ZoneType.NORMAL

    def __post_init__(self) -> None:
        _validate_name(self.name)

        if self.max_drones <= 0:
            raise ValueError("max_drones must be a positive integer")

    def capacity(self) -> int | None:
        """Return None for unlimited capacity (start/end), else max_drones."""
        if self.is_start or self.is_end:
            return None
        return self.max_drones

    def move_cost(self) -> int:
        """
        Turn cose to Enter this zone (depends on destination zone type).
        normal/priority -> 1
        restricted -> 2
        blocked -> forbiden
        """
        if self.zone_type in (ZoneType.NORMAL, ZoneType.PRIORITY):
            return 1
        elif self.zone_type is ZoneType.RESTRICTED:
            return 2
        raise ValueError("Blocked zones cannot be entered")

    def is_blocked(self) -> bool:
        if self.zone_type == "Blocked":
            return True
        return False


@dataclass(frozen=True, slots=True)
class Connection:
    """A bidirectional edge between two zones."""

    a: str
    b: str
    max_link_capacity: int = 1

    def __post__init__(self) -> None:
        _validate_name(self.a)
        _validate_name(self.b)
        if self.a == self.b:
            raise ValueError("self-connection is not allowed")
        if self.max_link_capacity <= 0:
            raise ValueError("max_link_capacity must be a positive integer")

    def key(self) -> tuple:
        """canonikal key so a-b and b-a are treated as the same connection."""
        return tuple(sorted((self.a, self.b)))
