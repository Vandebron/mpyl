"""
Wrapper around `pyaml_env`'s `parse_config`. Sets default values in config to `None`
"""
from pathlib import Path

from pyaml_env import parse_config as original_parse_config
from dotenv import load_dotenv


def parse_config(path: Path) -> dict:
    load_dotenv(Path(".env"))

    def default_to_none(obj, default_value="N/A"):
        if isinstance(obj, (list, tuple, set)):
            return type(obj)(default_to_none(x) for x in obj if x is not default_value)
        if isinstance(obj, dict):
            return type(obj)(
                (default_to_none(k), default_to_none(v))
                for k, v in obj.items()
                if k is not default_value and v is not default_value
            )
        if obj == default_value:
            return None
        return obj

    parsed = original_parse_config(str(path))
    return default_to_none(parsed)
