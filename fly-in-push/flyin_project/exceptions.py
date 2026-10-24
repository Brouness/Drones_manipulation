"""Project-specific exceptions."""


class ParseError(Exception):
    """Report a map parsing error with its source line."""

    def __init__(self, reason: str, line_nb: int, line: str) -> None:
        self.reason = reason
        self.line_nb = line_nb
        self.line = line
        self.message = f"ParseError {reason} in line:{line_nb} '{line}'"
        super().__init__(self.message)
