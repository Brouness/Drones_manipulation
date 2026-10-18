class ParseError(Exception):
    def __init__(self, reason: str, line_nb: int, line: str) -> None:
        self.message = f"ParseError {reason} in line:{line_nb} '{line}'"
        super().__init__(self.message)
