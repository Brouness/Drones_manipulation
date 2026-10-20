import exceptions
from models import ZoneType


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
            raise exceptions.ParseError("the character is not a digit", line_no, line)
        nb += char
    if not nb:
        raise exceptions.ParseError("empty word", line_no, line)
    digit: int = int(nb)
    if digit <= 0:
        raise exceptions.ParseError("number of drones must be a positive int", line_no, line)
    return digit


def check_value(data: str) -> bool:
    key_value: list[str] = data.split("=", 1)
    if key_value[0] == "color":
        for char in key_value[1]:
            if not char.isalpha():
                return True
    if key_value[0] == "max_drones":
        nb: str = ""
        for char in key_value[1]:
            if not char.isdigit():
                return True
            nb += char
        if int(nb) <= 0:
            return True
    if key_value[0] == "zone":
        if key_value[1] not in ZoneType:
            return True
    return False


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


def parse_zone_line(line: str, line_number: int) -> dict[str, str]:
    valide_hubs: list[str] = ["hub:", "start_hub:", "end_hub:"]
    my_dict: dict[str, str] = {}
    split_line: list[str] = line.split(" ")
    if split_line[0] not in valide_hubs:
        raise exceptions.ParseError(f"hubs must be in {valide_hubs}", line_number, line)
    for data in split_line:
        print(data)
    return my_dict


if __name__ == "__main__":
    list_ = read_logical_lines("maps/easy/01_linear_path.txt")
    for line in list_:
        print(line)
    try:
        print(parse_nb_drones(list_[0][0], list_[0][1]))
    except exceptions.ParseError as e:
        print(e)
    print("hello")
    print(list_[1][1].split("[")[1])
    print(parse_metadata(list_[1][1].split("[")[1].replace("]", ""), list_[1][0], list_[1][1]))
    print(parse_zone_line(list_[1][1], list_[1][0]))
