"""Create a capacity-aware turn schedule for the drone fleet."""

from dataclasses import dataclass
from heapq import heappop, heappush

from graph import Graph
from pathfinder import Pathfinder
from simulator import Move


class SchedulingError(ValueError):
    """Report when no valid schedule can be constructed."""


@dataclass(frozen=True)
class _Action:
    """One wait or one zone-to-zone movement in a drone plan."""

    kind: str
    source: str
    destination: str
    start_time: int
    end_time: int
    connection_key: tuple[str, str] | None = None


class Scheduler:
    """Plan movements using time-expanded capacity reservations.

    Drones are planned one at a time. For each drone, a shortest-arrival
    search considers both movement and waiting while respecting the paths
    already reserved for earlier drones. This is a prioritized heuristic:
    it creates valid concurrent schedules, but does not guarantee a
    globally optimal fleet schedule.
    """

    def __init__(
        self,
        graph: Graph,
        nb_drones: int,
        start_zone: str,
        end_zone: str,
    ) -> None:
        """Create a scheduler for the given graph and fleet."""
        if nb_drones <= 0:
            raise ValueError("nb_drones must be positive")

        self._graph = graph
        self._nb_drones = nb_drones
        self._start_zone = start_zone
        self._end_zone = end_zone
        self._pathfinder = Pathfinder(graph)
        self._zone_reservations: dict[tuple[str, int], int] = {}
        self._connection_reservations: dict[
            tuple[tuple[str, str], int], int
        ] = {}

        self._graph.get_zone(start_zone)
        self._graph.get_zone(end_zone)

    def create_schedule(self) -> list[list[Move]]:
        """Return a legal, turn-indexed schedule for every drone.

        The returned outer list has one entry per simulation turn. An
        empty inner list means no drone starts a move on that turn; it can
        still be needed for automatic arrivals from restricted transit.
        """
        self._zone_reservations = {}
        self._connection_reservations = {}

        if self._start_zone == self._end_zone:
            return []

        static_path = self._pathfinder.find_path(
            self._start_zone,
            self._end_zone,
        )
        if static_path is None:
            raise SchedulingError(
                f"no route from {self._start_zone} to {self._end_zone}"
            )

        moves_by_turn: dict[int, list[Move]] = {}
        final_arrival_time = 0

        for drone_id in range(1, self._nb_drones + 1):
            actions, arrival_time = self._find_plan()
            self._reserve_plan(actions)
            final_arrival_time = max(final_arrival_time, arrival_time)

            for action in actions:
                if action.kind == "move":
                    departure_turn = action.start_time + 1
                    moves_by_turn.setdefault(departure_turn, []).append(
                        Move(drone_id, action.destination)
                    )

        schedule: list[list[Move]] = []
        for turn in range(1, final_arrival_time + 1):
            turn_moves = moves_by_turn.get(turn, [])
            schedule.append(sorted(turn_moves, key=lambda move: move.drone_id))
        return schedule

    def _find_plan(self) -> tuple[list[_Action], int]:
        """Find the earliest feasible time-expanded route for one drone."""
        start_state = (self._start_zone, 0)
        frontier: list[tuple[int, int, str]] = [
            (0, 0, self._start_zone)
        ]
        best_priority_score: dict[tuple[str, int], int] = {
            start_state: 0
        }
        previous: dict[
            tuple[str, int],
            tuple[tuple[str, int], _Action],
        ] = {}
        goal_state: tuple[str, int] | None = None
        horizon = self._search_horizon()

        while frontier:
            current_time, current_zone = heappop(frontier)
            current_state = (current_zone, current_time)
            if current_zone == self._end_zone:
                goal_state = current_state
                break
            if current_time >= horizon:
                continue

            wait_state = (current_zone, current_time + 1)
            if (
                wait_state not in visited
                and self._zone_has_room(current_zone, current_time + 1)
            ):
                visited.add(wait_state)
                previous[wait_state] = (
                    current_state,
                    _Action(
                        kind="wait",
                        source=current_zone,
                        destination=current_zone,
                        start_time=current_time,
                        end_time=current_time + 1,
                    ),
                )
                heappush(frontier, (current_time + 1, current_zone))

            for neighbor in self._graph.neighbors(current_zone):
                if neighbor.is_blocked():
                    continue

                movement_cost = neighbor.move_cost()
                arrival_time = current_time + movement_cost
                if arrival_time > horizon:
                    continue

                connection = self._graph.get_connection(
                    current_zone,
                    neighbor.name,
                )
                if not self._connection_has_room(
                    connection.key(),
                    connection.max_link_capacity,
                    current_time + 1,
                    arrival_time,
                ):
                    continue
                if not self._zone_has_room(neighbor.name, arrival_time):
                    continue

                next_state = (neighbor.name, arrival_time)
                if next_state in visited:
                    continue

                visited.add(next_state)
                previous[next_state] = (
                    current_state,
                    _Action(
                        kind="move",
                        source=current_zone,
                        destination=neighbor.name,
                        start_time=current_time,
                        end_time=arrival_time,
                        connection_key=connection.key(),
                    ),
                )
                heappush(frontier, (arrival_time, neighbor.name))

        if goal_state is None:
            raise SchedulingError(
                "could not find a capacity-safe route within "
                "the search horizon"
            )

        actions: list[_Action] = []
        current_state = goal_state
        while current_state != start_state:
            parent_state, action = previous[current_state]
            actions.append(action)
            current_state = parent_state
        actions.reverse()
        return actions, goal_state[1]

    def _search_horizon(self) -> int:
        """Bound the time-expanded search after existing reservations."""
        reserved_turns = [
            turn
            for _, turn in self._zone_reservations
        ]
        reserved_turns.extend(
            turn
            for _, turn in self._connection_reservations
        )
        last_reserved_turn = max(reserved_turns, default=0)
        simple_path_cost = 2 * max(0, len(self._graph.zone_names()) - 1)
        return last_reserved_turn + simple_path_cost

    def _zone_has_room(self, zone_name: str, turn: int) -> bool:
        """Check whether one more drone fits at a zone after this turn."""
        capacity = self._graph.get_zone(zone_name).capacity()
        if capacity is None:
            return True
        present = self._zone_reservations.get((zone_name, turn), 0)
        return present + 1 <= capacity

    def _connection_has_room(
        self,
        key: tuple[str, str],
        capacity: int,
        first_turn: int,
        last_turn: int,
    ) -> bool:
        """Check link capacity on every turn of a traversal."""
        for turn in range(first_turn, last_turn + 1):
            using = self._connection_reservations.get((key, turn), 0)
            if using + 1 > capacity:
                return False
        return True

    def _reserve_plan(self, actions: list[_Action]) -> None:
        """Commit one drone's planned zone and connection reservations."""
        for action in actions:
            if action.kind == "wait":
                self._reserve_zone(action.destination, action.end_time)
                continue

            if action.connection_key is None:
                raise SchedulingError("movement plan is missing a connection")
            for turn in range(action.start_time + 1, action.end_time + 1):
                reservation_key = (action.connection_key, turn)
                self._connection_reservations[reservation_key] = (
                    self._connection_reservations.get(reservation_key, 0) + 1
                )

            self._reserve_zone(action.destination, action.end_time)

    def _reserve_zone(self, zone_name: str, turn: int) -> None:
        """Reserve occupancy for a capacity-limited zone and turn."""
        if self._graph.get_zone(zone_name).capacity() is None:
            return
        key = (zone_name, turn)
        self._zone_reservations[key] = self._zone_reservations.get(key, 0) + 1
