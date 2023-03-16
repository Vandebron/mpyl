"""Command Line Interface for MPyL"""
import logging

from rich.console import Console
from rich.logging import RichHandler

FORMAT = "%(message)s"


def create_console_logger(local: bool, verbose: bool) -> Console:
    console = Console(markup=True, width=None if local else 135, no_color=False, log_path=False, color_system='256')
    logging.basicConfig(
        level="DEBUG" if verbose else "INFO", format=FORMAT, datefmt="[%X]",
        handlers=[RichHandler(markup=True,
                              console=console, show_path=local)]
    )
    return console
