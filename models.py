from enum import Enum


class ZoneType(Enum):
    NORMAL: str = "Normal"
    BLOCKED: str = "Blocked"
    RESTRICTED: str = "Restricted"
    PRIORITY: str = "Priority"


class Zone:

    def __init__(self, name: str, x: int, y: int,
                 zone_type: ZoneType = ZoneType.normal,
                 color: str | None = None,
                 max_drones: int = 1, is_start: bool = False,
                 is_end: bool = False
                 ) -> None:
        self.name: str = name
        self.x: int = x
        self.y: int = y
        self.zone_type: str = zone_type
        self.color: str = color
        self.max_drones: int = max_drones
        self.is_start: bool = is_start
        self.is_end: bool = is_end

    def capacity(self) -> int | None:
        if self.is_start:
            return None
        elif self.is_end:
            return None
        return self.max_drones

    def move_cost(self) -> int:
        if self.zone_type == "Normal":
            return 1
        elif self.zone_type == "Resticted":
            return 2
        else:
            raise ValueError(f"invalid or blocked zone {self.zone_type}")

    def is_blocked(self) -> bool:
        if self.zone_type == "Blocked":
            return True
        return False


class Connection:

    def __init__(self, a: str, b: str, max_link_capacity: int = 1) -> None:
        self.a: str = a
        self.b: str = b
        self.max_link = max_link_capacity

    def key(self) -> tuple[str, str]:
        return (self.a, self.b)

