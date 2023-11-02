"""Console logging for utilities for the `rich` library."""

from rich.errors import ConsoleError
from rich.text import Text
from rich.markup import escape


def try_parse_ansi(text: str):
    escaped = escape(text)
    try:
        return Text.from_ansi(escaped)
    except ConsoleError:
        return Text(escaped)
