*This project has been created as part of the 42 curriculum by ybourajl42.*

# Fly-in Drones

## Description

Fly-in is a Python 3.10+ project that routes a fleet of drones through an
undirected graph of zones. The program parses a map, plans a turn-by-turn
schedule, validates that schedule, and prints the movement of each drone.

A normal or priority destination takes one turn to enter. A restricted
destination takes two turns: the drone occupies the connection during both
turns and cannot wait on it. Blocked zones cannot be entered. Zone and
connection capacities are enforced.

## Instructions

The project has no runtime dependencies. Python 3.10 or later is required.

```sh
python3 main.py examples/simple.map
```

To see a human-readable view of the movements and end-of-turn drone
positions, use:

```sh
python3 main.py examples/simple.map --visualize
```

The required movement lines are written to standard output. The optional
visualization is written to standard error. Add `--color` to force ANSI
colors in the visualization.

Install development tools and run the available checks with:

```sh
make install
make test
make lint
```

Other useful Make targets are `make run MAP=examples/simple.map`,
`make visualize MAP=examples/simple.map`, `make debug MAP=examples/simple.map`,
and `make clean`.

## Example

Input (`examples/simple.map`):

```text
nb_drones: 2
start_hub: S 0 0
hub: A 1 0 [max_drones=1]
end_hub: E 2 0
connection: S-A [max_link_capacity=1]
connection: A-E [max_link_capacity=1]
```

Expected movement output:

```text
D1-A
D1-E D2-A
D2-E
```

## Algorithm and implementation

- `parser.py` removes comments, reports source-line errors, builds validated
  `Zone` and `Connection` objects, and creates the `Graph`.
- `pathfinder.py` uses Dijkstra's algorithm to minimize the single-drone
  movement cost. Priority zones are a tie-break preference after total turns.
- `scheduler.py` searches a time-expanded graph for each drone. Its states
  include a zone and an end-of-turn time. It considers waiting, reserves
  capacity by zone and turn, and reserves restricted connections over both
  transit turns. Drones are planned in ID order, so this prioritized
  reservation heuristic is valid and concurrency-aware, but it does not
  guarantee a globally optimal fleet schedule.
- `simulator.py` independently validates each proposed turn, including
  automatic restricted arrivals, link capacity, final zone occupancy, and
  delivery of every drone.
- `visualizer.py` shows each turn and the resulting zone, transit, or delivered
  state. It does not change the official movement output.

## Project files

- `models.py`: zone types, zones, and connections.
- `graph.py`: undirected graph storage and lookup.
- `parser.py`: map-file parsing and validation.
- `pathfinder.py`: single-drone weighted route search.
- `scheduler.py`: fleet scheduling with time-based reservations.
- `simulator.py`: schedule validation and movement output.
- `visualizer.py`: optional terminal view.
- `main.py`: command-line entry point.

## Resources

- Python documentation: <https://docs.python.org/3/>
- Python `heapq` documentation: <https://docs.python.org/3/library/heapq.html>
- Python `argparse` documentation: <https://docs.python.org/3/library/argparse.html>
- Dijkstra's algorithm: <https://cp-algorithms.com/graph/dijkstra.html>

AI was used as a tutoring and development aid for explaining the assignment,
reviewing code, and scaffolding parts of the parser, pathfinder, simulator,
scheduler, command-line entry point, and documentation. The project author
should review, run, and be able to explain every part before submission.

## Before submission

Replace `<YOUR_42_LOGIN>` in the first line with your actual 42 login. Review
all code and documentation, run the tests and lint targets, and verify the
assignment's performance requirements on the provided maps.
