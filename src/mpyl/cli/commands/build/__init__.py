"""CLI support for Jenkins multibranch pipeline"""
import pkgutil
import tempfile
from dataclasses import dataclass
from enum import Enum

import simpleaudio as sa


@dataclass(frozen=True)
class Sound(Enum):
    SUCCESS = 'success'
    FAILURE = 'failure'


def play_sound(sound: Sound):
    sound_bytes = pkgutil.get_data(__name__, f"./sounds/{sound.value}.wav")
    if sound_bytes:
        with tempfile.NamedTemporaryFile() as sound_file:
            sound_file.write(sound_bytes)
            sa.WaveObject.from_wave_file(sound_file.name).play().wait_done()
