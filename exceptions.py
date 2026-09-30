class ParseError(Exception):
    def __init__(self) -> None:
        super().__init__(self.message)
