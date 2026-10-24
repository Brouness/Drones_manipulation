"""Unit tests for the Fly-in project components."""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from graph import Graph
from main import main
from models import Connection, Zone, ZoneType
from parser import ParsedMap, parse_map, read_logical_lines
from pathfinder import Pathfinder
from scheduler import Scheduler
from simulator import Move, SimulationError, Simulator
from visualizer import Visualizer


def parse_text(text: str) -> ParsedMap:
    """Parse an in-memory map while preserving source line numbers."""
    source_lines: list[tuple[int, str]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        cleaned = raw_line.split("#", 1)[0].strip()
        if cleaned:
            source_lines.append((line_number, cleaned))
    return parse_map(source_lines)


class ModelAndGraphTests(unittest.TestCase):
    """Test model validation and undirected graph behavior."""

    def test_zone_cost_and_unlimited_endpoint_capacity(self) -> None:
        """Restricted zones cost two turns; endpoints are unlimited."""
        restricted = Zone("R", 0, 0, zone_type=ZoneType.RESTRICTED)
        start = Zone("S", 0, 0, is_start=True)
        self.assertEqual(restricted.move_cost(), 2)
        self.assertIsNone(start.capacity())

    def test_graph_connection_is_undirected(self) -> None:
        """A connection can be looked up in either endpoint order."""
        graph = Graph()
        graph.add_zone(Zone("A", 0, 0))
        graph.add_zone(Zone("B", 1, 0))
        connection = Connection("A", "B", max_link_capacity=2)
        graph.add_connection(connection)
        self.assertIs(graph.get_connection("B", "A"), connection)
        self.assertEqual(
            tuple(zone.name for zone in graph.neighbors("A")),
            ("B",),
        )


class ParserTests(unittest.TestCase):
    """Test logical-line reading and complete-map parsing."""

    def test_reader_skips_blank_and_comment_only_lines(self) -> None:
        """Leading blank/comment lines do not hide the first declaration."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            map_path = Path(temporary_directory) / "map.txt"
            map_path.write_text(
                "  # comment\n\nnb_drones: 1\n",
                encoding="utf-8",
            )
            self.assertEqual(
                read_logical_lines(str(map_path)),
                [(3, "nb_drones: 1")],
            )

    def test_parser_builds_map_and_keeps_capacities(self) -> None:
        """Zone and connection metadata are converted into model fields."""
        parsed = parse_text(
            """nb_drones: 2
start_hub: S 0 0
hub: A 1 0 [max_drones=3]
end_hub: E 2 0
connection: S-A [max_link_capacity=2]
connection: A-E
"""
        )
        self.assertEqual(parsed.nb_drones, 2)
        self.assertEqual(parsed.graph.get_zone("A").capacity(), 3)
        self.assertEqual(
            parsed.graph.get_connection("A", "S").max_link_capacity,
            2,
        )


class PathfindingTests(unittest.TestCase):
    """Test weighted single-drone route selection."""

    def test_pathfinder_chooses_fewer_turns(self) -> None:
        """A longer-in-edges normal path beats a costly restricted path."""
        parsed = parse_text(
            """nb_drones: 1
start_hub: S 0 0
hub: R 1 0 [zone=restricted]
hub: A 0 1
end_hub: E 2 0
connection: S-R
connection: R-E
connection: S-A
connection: A-E
"""
        )
        path = Pathfinder(parsed.graph).find_path("S", "E")
        self.assertEqual(path, ["S", "A", "E"])

    def test_pathfinder_prefers_priority_on_equal_turn_routes(self) -> None:
        """Priority is a tie-break, not a reduction in movement cost."""
        parsed = parse_text(
            """nb_drones: 1
start_hub: S 0 0
hub: P 1 0 [zone=priority]
hub: A 1 1
end_hub: E 2 0
connection: S-P
connection: P-E
connection: S-A
connection: A-E
"""
        )
        path = Pathfinder(parsed.graph).find_path("S", "E")
        self.assertEqual(path, ["S", "P", "E"])


class SimulationAndSchedulingTests(unittest.TestCase):
    """Test restricted timing, reservations, and the scheduler output."""

    def test_restricted_move_arrives_automatically_next_turn(self) -> None:
        """The schedule includes a transit turn but no transit move."""
        parsed = parse_text(
            """nb_drones: 1
start_hub: S 0 0
hub: R 1 0 [zone=restricted]
end_hub: E 2 0
connection: S-R
connection: R-E
"""
        )
        simulator = Simulator(parsed.graph, 1, "S", "E")
        result = simulator.run(
            [[Move(1, "R")], [], [Move(1, "E")]]
        )
        self.assertEqual(result, ["D1-S-R", "D1-R", "D1-E"])

    def test_scheduler_pipelines_drones_on_a_capacity_one_route(self) -> None:
        """A departure frees a zone for another drone in the same turn."""
        parsed = parse_text(
            """nb_drones: 2
start_hub: S 0 0
hub: A 1 0 [max_drones=1]
end_hub: E 2 0
connection: S-A [max_link_capacity=1]
connection: A-E [max_link_capacity=1]
"""
        )
        schedule = Scheduler(
            parsed.graph,
            parsed.nb_drones,
            parsed.start_zone.name,
            parsed.end_zone.name,
        ).create_schedule()
        result = Simulator(
            parsed.graph,
            parsed.nb_drones,
            parsed.start_zone.name,
            parsed.end_zone.name,
        ).run(schedule)
        self.assertEqual(
            result,
            ["D1-A", "D1-E D2-A", "D2-E"],
        )

    def test_restricted_link_is_reserved_for_both_transit_turns(self) -> None:
        """A following drone waits until the first restricted crossing ends."""
        parsed = parse_text(
            """nb_drones: 2
start_hub: S 0 0
hub: R 1 0 [zone=restricted]
end_hub: E 2 0
connection: S-R [max_link_capacity=1]
connection: R-E [max_link_capacity=1]
"""
        )
        schedule = Scheduler(
            parsed.graph,
            parsed.nb_drones,
            parsed.start_zone.name,
            parsed.end_zone.name,
        ).create_schedule()
        result = Simulator(
            parsed.graph,
            parsed.nb_drones,
            parsed.start_zone.name,
            parsed.end_zone.name,
        ).run(schedule)
        self.assertEqual(
            result,
            [
                "D1-S-R",
                "D1-R",
                "D1-E D2-S-R",
                "D2-R",
                "D2-E",
            ],
        )

    def test_scheduler_uses_an_alternate_route_for_congestion(self) -> None:
        """A second drone can use a free branch instead of waiting."""
        parsed = parse_text(
            """nb_drones: 2
start_hub: S 0 0
hub: A 1 0 [max_drones=1]
hub: B 1 1 [max_drones=1]
end_hub: E 2 0
connection: S-A
connection: A-E
connection: S-B
connection: B-E
"""
        )
        schedule = Scheduler(
            parsed.graph,
            parsed.nb_drones,
            parsed.start_zone.name,
            parsed.end_zone.name,
        ).create_schedule()
        result = Simulator(
            parsed.graph,
            parsed.nb_drones,
            parsed.start_zone.name,
            parsed.end_zone.name,
        ).run(schedule)
        self.assertEqual(result, ["D1-A D2-B", "D1-E D2-E"])

    def test_simulator_rejects_connection_over_capacity(self) -> None:
        """Two simultaneous traversals over a one-lane link are invalid."""
        parsed = parse_text(
            """nb_drones: 2
start_hub: S 0 0
end_hub: E 1 0
connection: S-E [max_link_capacity=1]
"""
        )
        simulator = Simulator(parsed.graph, 2, "S", "E")
        with self.assertRaises(SimulationError):
            simulator.run(
                [[Move(1, "E"), Move(2, "E")]]
            )


class EntryPointAndVisualizerTests(unittest.TestCase):
    """Test command-line orchestration and optional visualization."""

    def test_main_prints_required_movement_output(self) -> None:
        """The CLI prints only movement lines by default."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            map_path = Path(temporary_directory) / "map.txt"
            map_path.write_text(
                """nb_drones: 1
start_hub: S 0 0
end_hub: E 1 0
connection: S-E
""",
                encoding="utf-8",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main([str(map_path)])
            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "D1-E\n")
            self.assertEqual(stderr.getvalue(), "")

    def test_visualizer_reports_zone_and_transit_states(self) -> None:
        """The optional view shows a restricted crossing and arrival."""
        parsed = parse_text(
            """nb_drones: 1
start_hub: S 0 0
hub: R 1 0 [zone=restricted]
end_hub: E 2 0
connection: S-R
connection: R-E
"""
        )
        stream = io.StringIO()
        Visualizer(
            parsed.graph,
            parsed.nb_drones,
            parsed.start_zone.name,
            parsed.end_zone.name,
        ).render(["D1-S-R", "D1-R", "D1-E"], stream, color=False)
        rendered = stream.getvalue()
        self.assertIn("in transit S->R", rendered)
        self.assertIn("D1: R", rendered)
        self.assertIn("D1: delivered", rendered)


if __name__ == "__main__":
    unittest.main()
