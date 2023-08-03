"""CI build related command group"""
import os
import shutil
from dataclasses import dataclass
from enum import Enum

from rich.console import Console


@dataclass(frozen=True)
class Sound(Enum):
    SUCCESS = "Glass.aiff"
    FAILURE = "Sosumi.aiff"


def play_sound(sound: Sound):
    if shutil.which("afplay") is None:
        Console().bell()
        return

    os.system(f"afplay /System/Library/Sounds/{sound.value}")
