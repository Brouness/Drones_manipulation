from heapq import heappop, heappush

from graph import Graph
from models import ZoneType


class Pathfinder:
    """Find a lowest-turn route through a zone graph."""

    def __init__(self, graph: Graph) -> None:
        """Store the graph that this pathfinder will search."""
        self._graph = graph

    def find_path(self, start_name: str, end_name: str) -> list[str] | None:
        """Return a best route, or None when no route exists."""
        # Raises KeyError if either name is not in the graph.
        self._graph.get_zone(start_name)
        self._graph.get_zone(end_name)

        # The first value is total turns.
        # The second is negative priority-zone count, used only for ties.
        best_label: dict[str, tuple[int, int]] = {
            start_name: (0, 0)
        }
        previous_zone: dict[str, str] = {}

        # Heap entries are: turns, negative priority count, zone name.
        frontier: list[tuple[int, int, str]] = [
            (0, 0, start_name)
        ]

        while frontier:
            turns, priority_score, current_name = heappop(frontier)
            current_label = (turns, priority_score)

            # A cheaper route may have been found after this entry was queued.
            if best_label.get(current_name) != current_label:
                continue

            if current_name == end_name:
                path: list[str] = [end_name]

                while path[-1] != start_name:
                    path.append(previous_zone[path[-1]])

                path.reverse()
                return path

            for neighbor in self._graph.neighbors(current_name):
                # A blocked zone cannot be entered or passed through.
                if neighbor.is_blocked():
                    continue

                # Movement cost depends on the destination zone.
                next_turns = turns + neighbor.move_cost()

                # Among routes with the same turn cost, prefer more
                # priority zones. Negative means more is better.
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
    