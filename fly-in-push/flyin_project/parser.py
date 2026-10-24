"""Parse a Fly-in map file into a graph and map metadata."""

from dataclasses import dataclass

from exceptions import ParseError
from graph import Graph
from models import Connection, Zone, ZoneType


@dataclass
class ParsedMap:
    """Collect the parsed drone count, graph, start, and end zones."""

    nb_drones: int
    graph: Graph
    start_zone: Zone
    end_zone: Zone


def read_logical_lines(path: str) -> list[tuple[int, str]]:
    """Read non-empty, comment-free lines with original line numbers."""
    logical_lines: list[tuple[int, str]] = []
    with open(path, "r", encoding="utf-8") as map_file:
        for line_number, raw_line in enumerate(map_file, start=1):
            cleaned = raw_line.split("#", 1)[0].strip()
            if cleaned:
                logical_lines.append((line_number, cleaned))
    return logical_lines


def parse_nb_drones(line_no: int, line: str) -> int:
    """Parse the required first-line drone-count declaration."""
    if ":" not in line:
        raise ParseError("':' not in the line", line_no, line)

    key, value = line.split(":", 1)
    if key.strip() != "nb_drones":
        raise ParseError("expected nb_drones declaration", line_no, line)

    value = value.strip()
    if not value.isascii() or not value.isdigit():
        raise ParseError(
            "number of drones must be a positive integer",
            line_no,
            line,
        )

    nb_drones = int(value)
    if nb_drones <= 0:
        raise ParseError(
            "number of drones must be a positive integer",
            line_no,
            line,
        )
    return nb_drones


def parse_metadata(
    metadata: str,
    line_number: int,
    source_line: str,
) -> dict[str, str]:
    """Parse whitespace-separated metadata key=value pairs."""
    content = metadata.strip()
    if not content:
        raise ParseError(
            "metadata block cannot be empty",
            line_number,
            source_line,
        )

    result: dict[str, str] = {}
    for token in content.split():
        if token.count("=") != 1:
            raise ParseError(
                f"metadata item must contain exactly one '=': {token}",
                line_number,
                source_line,
            )
        key, value = token.split("=", 1)
        if not key or not value:
            raise ParseError(
                f"metadata key and value cannot be empty: {token}",
                line_number,
                source_line,
            )
        if key in result:
            raise ParseError(
                f"duplicate metadata key: {key}",
                line_number,
                source_line,
            )
        result[key] = value
    return result


def _split_header_and_metadata(
    line: str,
    line_number: int,
) -> tuple[str, dict[str, str]]:
    """Separate a declaration header from its optional metadata block."""
    open_count = line.count("[")
    close_count = line.count("]")
    if open_count > 1 or close_count != open_count:
        raise ParseError(
            "metadata must use one matching pair of brackets",
            line_number,
            line,
        )

    if open_count == 0:
        return line, {}

    header, suffix = line.split("[", 1)
    if not suffix.endswith("]"):
        raise ParseError(
            "metadata block must end with ']'",
            line_number,
            line,
        )
    metadata_text = suffix[:-1].strip()
    metadata = parse_metadata(metadata_text, line_number, line)
    return header.strip(), metadata


def parse_zone_line(line: str, line_number: int) -> Zone:
    """Parse one hub declaration and create its Zone object."""
    clean_line = line.strip()
    if not clean_line:
        raise ParseError("zone line cannot be empty", line_number, line)

    header, metadata = _split_header_and_metadata(clean_line, line_number)
    fields = header.split()
    if len(fields) != 4:
        raise ParseError(
            "expected a hub type, name, x coordinate, and y coordinate",
            line_number,
            line,
        )

    hub_kind, name, x_text, y_text = fields
    if hub_kind not in {"hub:", "start_hub:", "end_hub:"}:
        raise ParseError(
            "expected hub:, start_hub:, or end_hub:",
            line_number,
            line,
        )

    try:
        x = int(x_text)
        y = int(y_text)
    except ValueError as error:
        raise ParseError(
            "zone coordinates must be integers",
            line_number,
            line,
        ) from error

    allowed = {"zone", "color", "max_drones"}
    unknown = set(metadata) - allowed
    if unknown:
        raise ParseError(
            f"unknown zone metadata: {', '.join(sorted(unknown))}",
            line_number,
            line,
        )

    zone_type = ZoneType.NORMAL
    if "zone" in metadata:
        try:
            zone_type = ZoneType(metadata["zone"])
        except ValueError as error:
            raise ParseError(
                f"invalid zone type: {metadata['zone']}",
                line_number,
                line,
            ) from error

    is_start = hub_kind == "start_hub:"
    is_end = hub_kind == "end_hub:"
    max_drones = 1

    # The specification ignores this metadata on start and end zones.
    if "max_drones" in metadata and not (is_start or is_end):
        capacity_text = metadata["max_drones"]
        if not capacity_text.isascii() or not capacity_text.isdigit():
            raise ParseError(
                "max_drones must be a positive integer",
                line_number,
                line,
            )
        max_drones = int(capacity_text)
        if max_drones <= 0:
            raise ParseError(
                "max_drones must be greater than zero",
                line_number,
                line,
            )

    try:
        return Zone(
            name=name,
            x=x,
            y=y,
            color=metadata.get("color"),
            zone_type=zone_type,
            max_drones=max_drones,
            is_start=is_start,
            is_end=is_end,
        )
    except ValueError as error:
        raise ParseError(str(error), line_number, line) from error


def parse_connection_line(line: str, line_number: int) -> Connection:
    """Parse one connection declaration and its optional capacity."""
    clean_line = line.strip()
    if not clean_line:
        raise ParseError(
            "connection line cannot be empty",
            line_number,
            line,
        )

    header, metadata = _split_header_and_metadata(clean_line, line_number)
    fields = header.split()
    if len(fields) != 2 or fields[0] != "connection:":
        raise ParseError(
            "expected 'connection: <zone1>-<zone2>'",
            line_number,
            line,
        )

    endpoints = fields[1]
    if endpoints.count("-") != 1:
        raise ParseError(
            "connection endpoints must be separated by one '-'",
            line_number,
            line,
        )
    zone_a, zone_b = endpoints.split("-", 1)
    if not zone_a or not zone_b:
        raise ParseError(
            "both connection endpoints must have a name",
            line_number,
            line,
        )

    allowed = {"max_link_capacity"}
    unknown = set(metadata) - allowed
    if unknown:
        raise ParseError(
            f"unknown connection metadata: {', '.join(sorted(unknown))}",
            line_number,
            line,
        )

    capacity = 1
    if "max_link_capacity" in metadata:
        capacity_text = metadata["max_link_capacity"]
        if not capacity_text.isascii() or not capacity_text.isdigit():
            raise ParseError(
                "max_link_capacity must be a positive integer",
                line_number,
                line,
            )
        capacity = int(capacity_text)
        if capacity <= 0:
            raise ParseError(
                "max_link_capacity must be greater than zero",
                line_number,
                line,
            )

    try:
        return Connection(
            a=zone_a,
            b=zone_b,
            max_link_capacity=capacity,
        )
    except ValueError as error:
        raise ParseError(str(error), line_number, line) from error


def parse_map(source_lines: list[tuple[int, str]]) -> ParsedMap:
    """Parse logical lines, build the graph, and validate start/end zones."""
    if not source_lines:
        raise ParseError(
            "map is empty; expected nb_drones declaration",
            1,
            "<empty file>",
        )

    first_line_number, first_line = source_lines[0]
    nb_drones = parse_nb_drones(first_line_number, first_line)
    graph = Graph()
    start_zone: Zone | None = None
    end_zone: Zone | None = None
    zone_kinds = {"hub:", "start_hub:", "end_hub:"}

    for line_number, source_line in source_lines[1:]:
        line = source_line.strip()
        if not line:
            continue

        declaration = line.split(":", 1)[0].strip()
        if declaration == "nb_drones":
            raise ParseError(
                "nb_drones must be declared only on the first line",
                line_number,
                source_line,
            )

        record_kind = line.split(maxsplit=1)[0]
        if record_kind in zone_kinds:
            zone = parse_zone_line(line, line_number)
            if zone.is_start:
                if start_zone is not None:
                    raise ParseError(
                        "more than one start_hub was defined",
                        line_number,
                        source_line,
                    )
                start_zone = zone
            if zone.is_end:
                if end_zone is not None:
                    raise ParseError(
                        "more than one end_hub was defined",
                        line_number,
                        source_line,
                    )
                end_zone = zone
            try:
                graph.add_zone(zone)
            except ValueError as error:
                raise ParseError(
                    str(error),
                    line_number,
                    source_line,
                ) from error
        elif record_kind == "connection:":
            connection = parse_connection_line(line, line_number)
            try:
                # This also enforces that endpoints were declared earlier.
                graph.add_connection(connection)
            except (KeyError, ValueError) as error:
                raise ParseError(
                    str(error),
                    line_number,
                    source_line,
                ) from error
        else:
            raise ParseError(
                f"unknown map declaration: {record_kind}",
                line_number,
                source_line,
            )

    last_line_number, last_line = source_lines[-1]
    if start_zone is None:
        raise ParseError(
            "map is missing a start_hub declaration",
            last_line_number,
            last_line,
        )
    if end_zone is None:
        raise ParseError(
            "map is missing an end_hub declaration",
            last_line_number,
            last_line,
        )

    return ParsedMap(
        nb_drones=nb_drones,
        graph=graph,
        start_zone=start_zone,
        end_zone=end_zone,
    )
