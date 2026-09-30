from graph import Graph
import exceptions

def read_logical_lines(path: str) -> list[tuple[int, str]]:
    my_list: list[int, str] = []
    with open(path, 'r') as file:
        for line_number, line in enumerate(file.readlines()):
            line = line.strip().split('#')
            if line[0]:
                what_we_need: str = ""
                tuple_: list[int, str] = []
                for char in line[0].strip():
                    what_we_need += char
                tuple_.append(line_number + 1)
                tuple_.append(what_we_need)
                my_list.append(tuple(tuple_))
    return my_list


def parse_nb_drones(line_no: int, line: str) -> int:
    valde: str = "nb_drones:"
    idx = 0
    nb = ""
    for i, char in enumerate(line):
        if char == ":":
            i += 1
            break
        if char != valde[idx] or char in "-+":
            raise exceptions.ParseError(f"ParseError in line:{line_no} '{char}'")
        idx += 1
    for idx, char in enumerate(line[i:].strip()):
        if char not in "0123456789":
            raise exceptions.ParseError(f"Number of drones must be a psitive integer line {line_no}")
        nb += char
    if not nb:
        raise exceptions.ParseError(f"Empty value for number of drones line {line_no}")
    return int(nb)


if __name__ == "__main__":
    list_ = read_logical_lines("maps/easy/01_linear_path.txt")
    for line in list_:
        print(line)
    try:
        print(parse_nb_drones(list_[0][0], list_[0][1]))
    except exceptions.ParseError as e:
        print(e)
