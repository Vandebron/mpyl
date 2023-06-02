"""Entrypoint for cli"""

if __name__ == "__main__" and __package__ is None:
    # https://peps.python.org/pep-0366/
    __package__ = "mpyl"  # pylint: disable=redefined-builtin

    from . import main

    main()
