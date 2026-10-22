import exceptions
from models import ZoneType, dataclass, Zone, Connection
from graph import Graph


@dataclass
class ParsedMap:
    nb_drones: int
    graph: Graph
    start_zone: Zone
    end_zone: Zone


def read_logical_lines(path: str) -> list[tuple[int, str]]:
    my_list: list[tuple[int, str]] = []
    with open(path, 'r', encoding="UTF-8") as file:
        for line_number, line in enumerate(file, 1):
            copy_line: str = line
            raw_line = copy_line.strip().split('#', 1)
            if raw_line[0]:
                cleaned_text = raw_line[0].strip()
                my_list.append((line_number, cleaned_text))
    return my_list


def parse_nb_drones(line_no: int, line: str) -> int:
    valde: str = "nb_drones"
    if ":" not in line:
        raise exceptions.ParseError("':' not in the line", line_no, line)
    split_line: list[str] = line.split(":", 1)
    nb = ""
    if split_line[0].strip() != valde:
        raise exceptions.ParseError("invalide word in map", line_no, line)
    for char in split_line[1].strip():
        base: str = "0123456789"
        if char not in base:
            raise exceptions.ParseError(
                "the character is not a digit", line_no, line)
        nb += char
    if not nb:
        raise exceptions.ParseError("empty word", line_no, line)
    digit: int = int(nb)
    if digit <= 0:
        raise exceptions.ParseError(
            "number of drones must be a positive int", line_no, line)
    return digit


def parse_metadata(
    metadata: str,
    line_number: int,
    source_line: str,
        ) -> dict[str, str]:
    """Parse the text inside a metadata block into key/value pairs."""
    result: dict[str, str] = {}
    content: str = metadata.strip()

    if not content:
        raise exceptions.ParseError(
            "metadata block cannot be empty",
            line_number,
            source_line,
        )

    for token in content.split():
        if token.count("=") != 1:
            raise exceptions.ParseError(
                f"metadata item must contain exactly one '=': {token}",
                line_number,
                source_line,
            )

        key, value = token.split("=", 1)

        if not key or not value:
            raise exceptions.ParseError(
                f"metadata key and value cannot be empty: {token}",
                line_number,
                source_line,
            )

        if key in result:
            raise exceptions.ParseError(
                f"duplicate metadata key: {key}",
                line_number,
                source_line,
            )

        result[key] = value

    return result


def parse_zone_line(line: str, line_number: int) -> Zone:
    """Parse one hub declaration and create its Zone object."""
    source_line = line
    clean_line = line.strip()

    if not clean_line:
        raise exceptions.ParseError(
            "zone line cannot be empty",
            line_number,
            source_line,
        )

    open_brackets = clean_line.count("[")
    close_brackets = clean_line.count("]")

    if open_brackets > 1 or close_brackets != open_brackets:
        raise exceptions.ParseError(
            "metadata must use one matching pair of brackets",
            line_number,
            source_line,
        )

    metadata: dict[str, str] = {}

    if open_brackets == 1:
        header, metadata_suffix = clean_line.split("[", 1)

        if not metadata_suffix.endswith("]"):
            raise exceptions.ParseError(
                "metadata block must end with ']'",
                line_number,
                source_line,
            )

        metadata_text = metadata_suffix[:-1].strip()
        metadata = parse_metadata(metadata_text, line_number, source_line)
    else:
        header = clean_line

    fields = header.split()

    if len(fields) != 4:
        raise exceptions.ParseError(
            "expected a hub type, name, x coordinate, and y coordinate",
            line_number,
            source_line,
        )

    hub_kind, name, x_text, y_text = fields
    valid_hub_kinds = {"hub:", "start_hub:", "end_hub:"}

    if hub_kind not in valid_hub_kinds:
        raise exceptions.ParseError(
            "expected hub:, start_hub:, or end_hub:",
            line_number,
            source_line,
        )

    try:
        x = int(x_text)
        y = int(y_text)
    except ValueError as error:
        raise exceptions.ParseError(
            "zone coordinates must be integers",
            line_number,
            source_line,
        ) from error

    allowed_metadata = {"zone", "color", "max_drones"}
    unknown_keys = set(metadata) - allowed_metadata

    if unknown_keys:
        raise exceptions.ParseError(
            f"unknown zone metadata: {', '.join(sorted(unknown_keys))}",
            line_number,
            source_line,
        )

    zone_type = ZoneType.NORMAL

    if "zone" in metadata:
        try:
            zone_type = ZoneType(metadata["zone"])
        except ValueError as error:
            raise exceptions.ParseError(
                f"invalid zone type: {metadata['zone']}",
                line_number,
                source_line,
            ) from error

    is_start = hub_kind == "start_hub:"
    is_end = hub_kind == "end_hub:"
    max_drones = 1

    # The subject says max_drones is ignored on start and end zones.
    if "max_drones" in metadata and not (is_start or is_end):
        capacity_text = metadata["max_drones"]

        if not capacity_text.isascii() or not capacity_text.isdigit():
            raise exceptions.ParseError(
                "max_drones must be a positive integer",
                line_number,
                source_line,
            )

        max_drones = int(capacity_text)

        if max_drones <= 0:
            raise exceptions.ParseError(
                "max_drones must be greater than zero",
                line_number,
                source_line,
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
        raise exceptions.ParseError(
            str(error),
            line_number,
            source_line,
        ) from error


def parse_connection_line(line: str, line_number: int) -> Connection:
    """Parse one connection declaration into a Connection object."""
    source_line = line
    clean_line = line.strip()

    if not clean_line:
        raise exceptions.ParseError(
            "connection line cannot be empty",
            line_number,
            source_line,
        )

    open_brackets = clean_line.count("[")
    close_brackets = clean_line.count("]")

    if open_brackets > 1 or close_brackets != open_brackets:
        raise exceptions.ParseError(
            "metadata must use one matching pair of brackets",
            line_number,
            source_line,
        )

    metadata: dict[str, str] = {}

    if open_brackets == 1:
        header, metadata_suffix = clean_line.split("[", 1)

        if not metadata_suffix.endswith("]"):
            raise exceptions.ParseError(
                "metadata block must end with ']'",
                line_number,
                source_line,
            )

        metadata_text = metadata_suffix[:-1].strip()
        metadata = parse_metadata(
            metadata_text,
            line_number,
            source_line,
        )
    else:
        header = clean_line

    fields = header.split()

    if len(fields) != 2:
        raise exceptions.ParseError(
            "expected 'connection: <zone1>-<zone2>'",
            line_number,
            source_line,
        )

    connection_kind, endpoints = fields

    if connection_kind != "connection:":
        raise exceptions.ParseError(
            "expected a connection: declaration",
            line_number,
            source_line,
        )

    if endpoints.count("-") != 1:
        raise exceptions.ParseError(
            "connection endpoints must be separated by one '-'",
            line_number,
            source_line,
        )

    zone_a, zone_b = endpoints.split("-", 1)

    if not zone_a or not zone_b:
        raise exceptions.ParseError(
            "both connection endpoints must have a name",
            line_number,
            source_line,
        )

    allowed_metadata = {"max_link_capacity"}
    unknown_keys = set(metadata) - allowed_metadata

    if unknown_keys:
        unknown = ", ".join(sorted(unknown_keys))
        raise exceptions.ParseError(
            f"unknown connection metadata: {unknown}",
            line_number,
            source_line,
        )

    capacity = 1

    if "max_link_capacity" in metadata:
        capacity_text = metadata["max_link_capacity"]

        if not capacity_text.isascii() or not capacity_text.isdigit():
            raise exceptions.ParseError(
                "max_link_capacity must be a positive integer",
                line_number,
                source_line,
            )

        capacity = int(capacity_text)

        if capacity <= 0:
            raise exceptions.ParseError(
                "max_link_capacity must be greater than zero",
                line_number,
                source_line,
            )

    try:
        return Connection(
            a=zone_a,
            b=zone_b,
            max_link_capacity=capacity,
        )
    except ValueError as error:
        raise exceptions.ParseError(
            str(error),
            line_number,
            source_line,
        ) from error


def parse_map(source_lines: list[tuple[int, str]]) -> ParsedMap:
    """Parse logical input lines and validate the complete map."""
    if not source_lines:
        raise exceptions.ParseError(
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

        # A drone-count declaration is allowed only as the first
        # logical line.
        declaration = line.split(":", 1)[0].strip()
        if declaration == "nb_drones":
            raise exceptions.ParseError(
                "nb_drones must be declared only on the first line",
                line_number,
                source_line,
            )

        record_kind = line.split(maxsplit=1)[0]

        if record_kind in zone_kinds:
            zone = parse_zone_line(line, line_number)

            if zone.is_start:
                if start_zone is not None:
                    raise exceptions.ParseError(
                        "more than one start_hub was defined",
                        line_number,
                        source_line,
                    )
                start_zone = zone

            if zone.is_end:
                if end_zone is not None:
                    raise exceptions.ParseError(
                        "more than one end_hub was defined",
                        line_number,
                        source_line,
                    )
                end_zone = zone

            try:
                graph.add_zone(zone)
            except ValueError as error:
                raise exceptions.ParseError(
                    str(error),
                    line_number,
                    source_line,
                ) from error

        elif record_kind == "connection:":
            connection = parse_connection_line(line, line_number)

            try:
                """Adding each connection here means its endpoints must
                already have been defined."""
                graph.add_connection(connection)
            except (KeyError, ValueError) as error:
                raise exceptions.ParseError(
                    str(error),
                    line_number,
                    source_line,
                ) from error

        else:
            raise exceptions.ParseError(
                f"unknown map declaration: {record_kind}",
                line_number,
                source_line,
            )

    last_line_number, last_line = source_lines[-1]

    if start_zone is None:
        raise exceptions.ParseError(
            "map is missing a start_hub declaration",
            last_line_number,
            last_line,
        )

    if end_zone is None:
        raise exceptions.ParseError(
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


if __name__ == "__main__":
    lines = read_logical_lines(
        "/home/ybourajl/youness_space_work/fly_in/maps/easy/03_basic_capacity.txt")
    x = parse_map(lines)
    print(x.nb_drones)
    print(x.graph._adjacency)
    print(x.end_zone.color)
