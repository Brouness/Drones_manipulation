"""Validate and simulate a turn-by-turn drone schedule."""

from dataclasses import dataclass
from enum import Enum

from graph import Graph
from models import Connection


class SimulationError(ValueError):
    """Represent an invalid or incomplete simulation schedule."""


class DroneStatus(Enum):
    """Represent the main states a drone can be in."""

    AT_ZONE = "at_zone"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"


@dataclass(frozen=True)
class Move:
    """Request that one drone move to an adjacent zone this turn."""

    drone_id: int
    destination_zone: str


@dataclass(frozen=True)
class DroneState:
    """Represent one drone's state at a turn boundary."""

    status: DroneStatus
    zone_name: str | None = None
    connection_key: tuple[str, str] | None = None
    destination_zone: str | None = None


class Simulator:
    """Simulate and validate a schedule for a drone fleet."""

    def __init__(
        self,
        graph: Graph,
        nb_drones: int,
        start_zone: str,
        end_zone: str,
    ) -> None:
        """Create a simulator for a map and its drone fleet."""
        if nb_drones <= 0:
            raise ValueError("nb_drones must be positive")

        self._graph = graph
        self._nb_drones = nb_drones
        self._start_zone = start_zone
        self._end_zone = end_zone
        self._graph.get_zone(start_zone)
        self._graph.get_zone(end_zone)

    def run(self, schedule: list[list[Move]]) -> list[str]:
        """Run a schedule and return one movement line per turn.

        Drones omitted from a turn wait. Drones already in restricted
        transit arrive automatically on the next turn.
        """
        states: dict[int, DroneState] = {}
        for drone_id in range(1, self._nb_drones + 1):
            if self._start_zone == self._end_zone:
                states[drone_id] = DroneState(
                    status=DroneStatus.DELIVERED,
                )
            else:
                states[drone_id] = DroneState(
                    status=DroneStatus.AT_ZONE,
                    zone_name=self._start_zone,
                )

        output_lines: list[str] = []
        for turn_number, moves in enumerate(schedule, start=1):
            all_delivered = all(
                state.status is DroneStatus.DELIVERED
                for state in states.values()
            )
            if all_delivered:
                if moves:
                    raise SimulationError(
                        f"turn {turn_number}: moves were scheduled after "
                        "all drones were delivered"
                    )
                break

            states, output_line = self._simulate_turn(
                states,
                moves,
                turn_number,
            )
            output_lines.append(output_line)

        undelivered = [
            drone_id
            for drone_id, state in states.items()
            if state.status is not DroneStatus.DELIVERED
        ]
        if undelivered:
            ids = ", ".join(f"D{drone_id}" for drone_id in undelivered)
            raise SimulationError(
                f"schedule ended before these drones were delivered: {ids}"
            )
        return output_lines

    def _simulate_turn(
        self,
        states: dict[int, DroneState],
        moves: list[Move],
        turn_number: int,
    ) -> tuple[dict[int, DroneState], str]:
        """Validate and apply all movements for one turn."""
        moves_by_drone: dict[int, Move] = {}
        for requested_move in moves:
            if requested_move.drone_id not in states:
                raise SimulationError(
                    f"turn {turn_number}: unknown drone "
                    f"D{requested_move.drone_id}"
                )
            if requested_move.drone_id in moves_by_drone:
                raise SimulationError(
                    f"turn {turn_number}: D{requested_move.drone_id} has "
                    "more than one move"
                )

            current_state = states[requested_move.drone_id]
            if current_state.status is not DroneStatus.AT_ZONE:
                raise SimulationError(
                    f"turn {turn_number}: D{requested_move.drone_id} "
                    "cannot start "
                    "a move from its current state"
                )
            moves_by_drone[requested_move.drone_id] = requested_move

        next_states: dict[int, DroneState] = {}
        movement_tokens: list[tuple[int, str]] = []
        link_usage: dict[tuple[str, str], int] = {}
        link_limits: dict[tuple[str, str], int] = {}

        for drone_id, state in states.items():
            if state.status is DroneStatus.DELIVERED:
                next_states[drone_id] = state
                continue

            if state.status is DroneStatus.IN_TRANSIT:
                next_state, token = self._complete_transit(
                    drone_id,
                    state,
                    link_usage,
                    link_limits,
                    turn_number,
                )
                next_states[drone_id] = next_state
                movement_tokens.append((drone_id, token))
                continue

            if state.status is not DroneStatus.AT_ZONE:
                raise SimulationError(
                    f"turn {turn_number}: D{drone_id} has an unknown state"
                )
            if state.zone_name is None:
                raise SimulationError(
                    f"turn {turn_number}: D{drone_id} has no current zone"
                )

            move = moves_by_drone.get(drone_id)
            if move is None:
                next_states[drone_id] = state
                continue

            next_state, token = self._start_move(
                drone_id,
                state.zone_name,
                move.destination_zone,
                link_usage,
                link_limits,
                turn_number,
            )
            next_states[drone_id] = next_state
            movement_tokens.append((drone_id, token))

        self._validate_link_capacities(
            link_usage,
            link_limits,
            turn_number,
        )
        self._validate_zone_capacities(next_states, turn_number)
        output_line = " ".join(
            token for _, token in sorted(movement_tokens)
        )
        return next_states, output_line

    def _complete_transit(
        self,
        drone_id: int,
        state: DroneState,
        link_usage: dict[tuple[str, str], int],
        link_limits: dict[tuple[str, str], int],
        turn_number: int,
    ) -> tuple[DroneState, str]:
        """Complete a restricted crossing that began on the prior turn."""
        if state.connection_key is None or state.destination_zone is None:
            raise SimulationError(
                f"turn {turn_number}: D{drone_id} has incomplete transit data"
            )

        link_a, link_b = state.connection_key
        try:
            connection = self._graph.get_connection(link_a, link_b)
            destination = self._graph.get_zone(state.destination_zone)
        except KeyError as error:
            raise SimulationError(
                f"turn {turn_number}: D{drone_id} has invalid transit data"
            ) from error

        if destination.is_blocked():
            raise SimulationError(
                f"turn {turn_number}: D{drone_id} is in transit to a "
                "blocked zone"
            )

        # A restricted crossing uses the link on the arrival turn too.
        self._record_link_usage(connection, link_usage, link_limits)
        next_state = self._state_after_arrival(destination.name)
        return next_state, f"D{drone_id}-{destination.name}"

    def _start_move(
        self,
        drone_id: int,
        source_zone: str,
        destination_name: str,
        link_usage: dict[tuple[str, str], int],
        link_limits: dict[tuple[str, str], int],
        turn_number: int,
    ) -> tuple[DroneState, str]:
        """Validate and start one movement from a zone."""
        try:
            destination = self._graph.get_zone(destination_name)
            connection = self._graph.get_connection(
                source_zone,
                destination_name,
            )
        except KeyError as error:
            raise SimulationError(
                f"turn {turn_number}: invalid move for D{drone_id}"
            ) from error

        if destination.is_blocked():
            raise SimulationError(
                f"turn {turn_number}: D{drone_id} cannot enter blocked "
                f"zone {destination.name}"
            )
        try:
            movement_cost = destination.move_cost()
        except ValueError as error:
            raise SimulationError(
                f"turn {turn_number}: invalid destination zone "
                f"{destination.name}"
            ) from error

        self._record_link_usage(connection, link_usage, link_limits)
        if movement_cost == 1:
            return (
                self._state_after_arrival(destination.name),
                f"D{drone_id}-{destination.name}",
            )
        if movement_cost == 2:
            next_state = DroneState(
                status=DroneStatus.IN_TRANSIT,
                connection_key=connection.key(),
                destination_zone=destination.name,
            )
            # Keep the declared endpoint order for the required output.
            connection_name = f"{connection.a}-{connection.b}"
            return next_state, f"D{drone_id}-{connection_name}"
        raise SimulationError(
            f"turn {turn_number}: unsupported movement cost {movement_cost}"
        )

    def _state_after_arrival(self, zone_name: str) -> DroneState:
        """Return the state after a drone arrives at a zone."""
        if zone_name == self._end_zone:
            return DroneState(status=DroneStatus.DELIVERED)
        return DroneState(
            status=DroneStatus.AT_ZONE,
            zone_name=zone_name,
        )

    @staticmethod
    def _record_link_usage(
        connection: Connection,
        link_usage: dict[tuple[str, str], int],
        link_limits: dict[tuple[str, str], int],
    ) -> None:
        """Count one drone using a connection during this turn."""
        key = connection.key()
        link_usage[key] = link_usage.get(key, 0) + 1
        link_limits[key] = connection.max_link_capacity

    def _validate_link_capacities(
        self,
        link_usage: dict[tuple[str, str], int],
        link_limits: dict[tuple[str, str], int],
        turn_number: int,
    ) -> None:
        """Reject any connection used beyond capacity this turn."""
        for key, number_using in link_usage.items():
            capacity = link_limits[key]
            if number_using > capacity:
                name = f"{key[0]}-{key[1]}"
                raise SimulationError(
                    f"turn {turn_number}: connection {name} used by "
                    f"{number_using} drones; capacity is {capacity}"
                )

    def _validate_zone_capacities(
        self,
        states: dict[int, DroneState],
        turn_number: int,
    ) -> None:
        """Reject any zone that exceeds capacity after this turn."""
        zone_occupancy: dict[str, int] = {}
        for state in states.values():
            if state.status is not DroneStatus.AT_ZONE:
                continue
            if state.zone_name is None:
                raise SimulationError(
                    f"turn {turn_number}: at-zone drone has no zone"
                )
            zone_occupancy[state.zone_name] = (
                zone_occupancy.get(state.zone_name, 0) + 1
            )

        for zone_name, number_present in zone_occupancy.items():
            zone = self._graph.get_zone(zone_name)
            capacity = zone.capacity()
            if capacity is not None and number_present > capacity:
                raise SimulationError(
                    f"turn {turn_number}: zone {zone_name} contains "
                    f"{number_present} drones; capacity is {capacity}"
                )
