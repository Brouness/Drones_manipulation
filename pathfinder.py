"""Find single-drone routes through the zone graph."""

from heapq import heappop, heappush

from graph import Graph
from models import ZoneType


class Pathfinder:
    """Find a lowest-turn route through a zone graph."""

    def __init__(self, graph: Graph) -> None:
        """Create a pathfinder for the given graph."""
        self._graph = graph

    def find_path(self, start_name: str, end_name: str) -> list[str] | None:
        """Find the best route from start_name to end_name.

        The primary objective is to minimize turns. Among routes with
        the same turn cost, prefer the route that enters more priority
        zones.

        Return None if the destination is blocked or unreachable.

        Raises:
            KeyError: If the start or end zone is not in the graph.
        """
        self._graph.get_zone(start_name)
        end_zone = self._graph.get_zone(end_name)

        if end_zone.is_blocked():
            return None

        # Each label is (turns, negative priority-zone count).
        # The second value only breaks ties between equal-turn routes.
        best_label: dict[str, tuple[int, int]] = {
            start_name: (0, 0)
        }
        previous_zone: dict[str, str] = {}

        # Heap entries are (turns, negative priority count, zone name).
        frontier: list[tuple[int, int, str]] = [
            (0, 0, start_name)
        ]

        while frontier:
            turns, priority_score, current_name = heappop(frontier)
            current_label = (turns, priority_score)

            # Ignore an outdated heap entry if a better label was found.
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

                # Movement cost is based on the destination zone.
                next_turns = turns + neighbor.move_cost()

                # More priority zones improve only the tie-break score.
                priority_adjustment = (
                    -1
                    if neighbor.zone_type is ZoneType.PRIORITY
                    else 0
                )
                next_priority_score = (
                    priority_score + priority_adjustment
                )
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
        """Build the route by following predecessor links backward."""
        path: list[str] = [end_name]
        current_name = end_name

        while current_name != start_name:
            current_name = previous_zone[current_name]
            path.append(current_name)

        path.reverse()
        return path
