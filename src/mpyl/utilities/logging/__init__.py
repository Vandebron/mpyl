"""Console logging for utilities for the `rich` library."""

from rich.errors import ConsoleError
from rich.text import Text


def try_parse_ansi(text: str):
    try:
        return Text.from_ansi(text)
    except ConsoleError:
        return Text(text)
