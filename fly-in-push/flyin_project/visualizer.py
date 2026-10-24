"""Render a colored, human-readable view of a simulation."""

import sys
from typing import TextIO

from graph import Graph
from models import ZoneType


class Visualizer:
    """Display movements and end-of-turn drone positions."""

    _TYPE_COLORS = {
        ZoneType.NORMAL: "36",
        ZoneType.PRIORITY: "32",
        ZoneType.RESTRICTED: "33",
        ZoneType.BLOCKED: "31",
    }

    def __init__(
        self,
        graph: Graph,
        nb_drones: int,
        start_zone: str,
        end_zone: str,
    ) -> None:
        """Create a visualizer for a parsed map and fleet."""
        self._graph = graph
        self._nb_drones = nb_drones
        self._start_zone = start_zone
        self._end_zone = end_zone

    def render(
        self,
        output_lines: list[str],
        stream: TextIO | None = None,
        color: bool | None = None,
    ) -> None:
        """Print each turn's moves and resulting drone positions.

        The output is intended for a terminal and is separate from the
        simulator's exact movement lines.
        """
        target_stream = stream if stream is not None else sys.stderr
        if color is None:
            is_tty = getattr(target_stream, "isatty", None)
            use_color = bool(is_tty and is_tty())
        else:
            use_color = color

        zone_names = set(self._graph.zone_names())
        positions: dict[int, str | None] = {}
        transit: dict[int, tuple[str, str]] = {}
        delivered: set[int] = set()
        for drone_id in range(1, self._nb_drones + 1):
            if self._start_zone == self._end_zone:
                positions[drone_id] = None
                delivered.add(drone_id)
            else:
                positions[drone_id] = self._start_zone

        if not output_lines:
            print(
                "No turns: all drones are already delivered.",
                file=target_stream,
            )
            return

        for turn_number, line in enumerate(output_lines, start=1):
            displayed_tokens: list[str] = []
            for token in line.split():
                drone_id, target = self._split_token(token)
                if target in zone_names:
                    positions[drone_id] = target
                    transit.pop(drone_id, None)
                    if target == self._end_zone:
                        delivered.add(drone_id)
                        positions[drone_id] = None
                    displayed_tokens.append(
                        self._paint(token, target, use_color)
                    )
                    continue

                endpoints = target.split("-")
                if len(endpoints) != 2:
                    displayed_tokens.append(token)
                    continue
                first, second = endpoints
                current = positions.get(drone_id)
                if current == first:
                    origin, destination = first, second
                elif current == second:
                    origin, destination = second, first
                else:
                    origin, destination = first, second
                positions[drone_id] = None
                transit[drone_id] = (origin, destination)
                displayed_tokens.append(self._paint(token, None, use_color))

            movement_text = " ".join(displayed_tokens) or "(no movement)"
            print(f"Turn {turn_number}: {movement_text}", file=target_stream)
            states = [
                self._format_state(
                    drone_id,
                    positions,
                    transit,
                    delivered,
                    use_color,
                )
                for drone_id in range(1, self._nb_drones + 1)
            ]
            print("  " + " | ".join(states), file=target_stream)

    @staticmethod
    def _split_token(token: str) -> tuple[int, str]:
        """Separate a movement token into drone number and target text."""
        drone_label, target = token.split("-", 1)
        return int(drone_label[1:]), target

    def _format_state(
        self,
        drone_id: int,
        positions: dict[int, str | None],
        transit: dict[int, tuple[str, str]],
        delivered: set[int],
        use_color: bool,
    ) -> str:
        """Format one drone's state after the displayed turn."""
        label = f"D{drone_id}"
        if drone_id in delivered:
            return self._paint(
                f"{label}: delivered",
                self._end_zone,
                use_color,
            )
        if drone_id in transit:
            origin, destination = transit[drone_id]
            text = f"{label}: in transit {origin}->{destination}"
            return self._paint(text, None, use_color)

        zone_name = positions[drone_id]
        if zone_name is None:
            return f"{label}: unknown"
        return self._paint(f"{label}: {zone_name}", zone_name, use_color)

    def _paint(
        self,
        text: str,
        zone_name: str | None,
        use_color: bool,
    ) -> str:
        """Apply an ANSI color based on the target zone type."""
        if not use_color:
            return text
        if zone_name is None:
            code = "33"
        else:
            zone = self._graph.get_zone(zone_name)
            code = self._TYPE_COLORS.get(zone.zone_type, "37")
        return f"\033[{code}m{text}\033[0m"
