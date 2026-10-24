"""Command-line entry point for the Fly-in drone simulator."""

import argparse
import sys
from pathlib import Path
from typing import Sequence

from exceptions import ParseError
from parser import parse_map, read_logical_lines
from scheduler import Scheduler, SchedulingError
from simulator import SimulationError, Simulator
from visualizer import Visualizer


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    argument_parser = argparse.ArgumentParser(
        description=(
            "Schedule Fly-in drones through a zone map and simulate "
            "their movements."
        )
    )
    argument_parser.add_argument(
        "map_file",
        type=Path,
        help="path to the Fly-in map file",
    )
    argument_parser.add_argument(
        "--visualize",
        action="store_true",
        help="show a colored turn-by-turn view on stderr",
    )
    argument_parser.add_argument(
        "--color",
        action="store_true",
        help="force ANSI colors in the visual view",
    )
    return argument_parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments, build a schedule, simulate it, and print output."""
    argument_parser = build_argument_parser()
    arguments = argument_parser.parse_args(argv)

    try:
        source_lines = read_logical_lines(str(arguments.map_file))
        parsed_map = parse_map(source_lines)
        scheduler = Scheduler(
            graph=parsed_map.graph,
            nb_drones=parsed_map.nb_drones,
            start_zone=parsed_map.start_zone.name,
            end_zone=parsed_map.end_zone.name,
        )
        schedule = scheduler.create_schedule()
        simulator = Simulator(
            graph=parsed_map.graph,
            nb_drones=parsed_map.nb_drones,
            start_zone=parsed_map.start_zone.name,
            end_zone=parsed_map.end_zone.name,
        )
        output_lines = simulator.run(schedule)
    except (OSError, ParseError, SchedulingError, SimulationError) as error:
        print(f"fly-in: error: {error}", file=sys.stderr)
        return 1

    if output_lines:
        print("\n".join(output_lines), flush=True)

    if arguments.visualize:
        visualizer = Visualizer(
            graph=parsed_map.graph,
            nb_drones=parsed_map.nb_drones,
            start_zone=parsed_map.start_zone.name,
            end_zone=parsed_map.end_zone.name,
        )
        visualizer.render(
            output_lines,
            stream=sys.stderr,
            color=arguments.color,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
