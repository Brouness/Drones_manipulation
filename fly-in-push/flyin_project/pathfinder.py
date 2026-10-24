"""Find a lowest-turn route through the zone graph."""

from heapq import heappop, heappush

from graph import Graph
from models import ZoneType


class Pathfinder:
    """Find single-drone routes while ignoring fleet congestion."""

    def __init__(self, graph: Graph) -> None:
        """Create a pathfinder for a graph."""
        self._graph = graph

    def find_path(self, start_name: str, end_name: str) -> list[str] | None:
        """Return the best route, or None if the end is unreachable.

        Routes minimize movement turns. For equal-turn routes, routes that
        enter more priority zones are preferred.
        """
        self._graph.get_zone(start_name)
        end_zone = self._graph.get_zone(end_name)
        if end_zone.is_blocked():
            return None

        start_label = (0, 0)
        best_label: dict[str, tuple[int, int]] = {start_name: start_label}
        previous_zone: dict[str, str] = {}
        frontier: list[tuple[int, int, str]] = [
            (start_label[0], start_label[1], start_name)
        ]

        while frontier:
            turns, priority_score, current_name = heappop(frontier)
            current_label = (turns, priority_score)
            if best_label.get(current_name) != current_label:
                continue

            if current_name == end_name:
                return self._reconstruct_path(
                    start_name,
                    end_name,
                    previous_zone,
                )

            for neighbor in self._graph.neighbors(current_name):
                if neighbor.is_blocked():
                    continue

                next_turns = turns + neighbor.move_cost()
                priority_delta = (
                    -1
                    if neighbor.zone_type is ZoneType.PRIORITY
                    else 0
                )
                next_priority_score = priority_score + priority_delta
                next_label = (next_turns, next_priority_score)
                old_label = best_label.get(neighbor.name)

                if old_label is None or next_label < old_label:
                    best_label[neighbor.name] = next_label
                    previous_zone[neighbor.name] = current_name
                    heappush(
                        frontier,
                        (
                            next_turns,
                            next_priority_score,
                            neighbor.name,
                        ),
                    )

        return None

    @staticmethod
    def _reconstruct_path(
        start_name: str,
        end_name: str,
        previous_zone: dict[str, str],
    ) -> list[str]:
        """Reconstruct a route from stored predecessor links."""
        path = [end_name]
        current_name = end_name
        while current_name != start_name:
            current_name = previous_zone[current_name]
            path.append(current_name)
        path.reverse()
        return path
