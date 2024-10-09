import sys

from src.mpyl import main_group, add_commands


def build(arguments: list[str]) -> None:
    """CLI entry point."""

    add_commands()
    main_group(arguments, standalone_mode=False)


if __name__ == "__main__":
    argv = sys.argv
    build(argv[1:])
