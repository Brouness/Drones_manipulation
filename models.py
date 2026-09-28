from typing import Optional
from enum import Enum
from dataclasses import dataclass


class ZoneType(str, Enum):
    NORMAL = "normal"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"
    PRIORITY = "priority"


def _validate_name(name: str) -> None:
    if not name:
        raise ValueError("Empty name is forbidden :)")
    if " " in name:
        raise ValueError(f"Invalid name spaces are forbidden {name}")
    if "-" in name:
        raise ValueError(f"Invalid name dashes are forbidden {name}")


@dataclass
class Zone:
    name: str
    x: int
    y: int
    color: Optional[str] = None
    zone_type: ZoneType = ZoneType.NORMAL
    max_drones: int = 1
    is_end: bool = False
    is_start: bool = False

    def __post_init__(self) -> None:
        _validate_name(self.name)
        if self.max_drones <= 0:
            raise ValueError(
                f"Max drones must be a positive integer {self.max_drones}")

    def is_blocked(self) -> bool:
        return self.zone_type is ZoneType.BLOCKED

    def capacity(self) -> Optional[int]:
        if self.is_start or self.is_end:
            return None
        return self.max_drones

    def move_cost(self) -> int:
        if self.zone_type in (ZoneType.NORMAL, ZoneType.PRIORITY):
            return 1
        if self.zone_type is ZoneType.RESTRICTED:
            return 2
        raise ValueError(
                f"Invalid zone type blocked are forbidden {self.zone_type}")


@dataclass(frozen=True)
class Connection:
    a: str
    b: str
    max_link_capacity: int = 1

    def __post_init__(self) -> None:
        _validate_name(self.a)
        _validate_name(self.b)
        if self.a == self.b:
            raise ValueError(f"Self connection is forbidden {self.a}")
        if self.max_link_capacity <= 0:
            raise ValueError(f"Max link capacity must be a valid positive integer")

    def key(self) -> tuple[str, str]:
        return tuple(sorted((self.a, self.b)))

if __name__ == "__main__":
    zone1 = Zone("zabelhachmi", 10, 10)
    zone2 = Zone("morco", 11, 11, ZoneType.RESTRICTED)
    print(zone1.move_cost())
    print(zone2.move_cost())
    edg = Connection(zone1.name, zone2.name, 10)
    print(edg.max_link_capacity, edg.key())
