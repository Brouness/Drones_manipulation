class ParseError(Exception):
    def __init__(self, line_nb: int, line: str) -> None:
        self.message = f"ParseError in line:{line_nb} '{line}'"
        super().__init__(self.message)
