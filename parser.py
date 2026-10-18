import exceptions

def read_logical_lines(path: str) -> list[tuple[int, str]]:
    my_list: list[tuple] = []
    with open(path, 'r') as file:
        for line_number, line in enumerate(file.readlines(), 1):
            line = line.strip().split('#', 1)
            if line[0]:
                what_we_need: str = ""
                tuple_: list[int, str] = []
                for char in line[0].strip():
                    what_we_need += char
                tuple_.append(line_number)
                tuple_.append(what_we_need)
                my_list.append(tuple(tuple_))
    return my_list


def parse_nb_drones(line_no: int, line: str) -> int:
    valde: str = "nb_drones"
    splited_line: list[str] = line.split(":", 1)
    idx = 0
    nb = ""
    if splited_line[0].strip() != valde:
        raise exceptions.ParseError("invalide word in map", line_no, line)
    for char in splited_line[1].strip():
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


if __name__ == "__main__":
    list_ = read_logical_lines("maps/easy/01_linear_path.txt")
    for line in list_:
        print(line)
    try:
        print(parse_nb_drones(list_[0][0], list_[0][1]))
    except exceptions.ParseError as e:
        print(e)
