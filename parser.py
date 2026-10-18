import exceptions

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


def parse_metadata(line: str, line_number: int) -> None:
     

if __name__ == "__main__":
    list_ = read_logical_lines("maps/easy/01_linear_path.txt")
    for line in list_:
        print(line)
    try:
        print(parse_nb_drones(list_[0][0], list_[0][1]))
    except exceptions.ParseError as e:
        print(e)
