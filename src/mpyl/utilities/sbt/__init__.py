"""SBT config"""
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SbtConfig:
    java_opts: str
    sbt_opts: str
    sbt_command: str

    @staticmethod
    def from_config(config: Dict):
        try:
            return SbtConfig(sbt_command=config['sbt']['command'],
                             java_opts=config['sbt']['javaOpts'],
                             sbt_opts=config['sbt']['sbtOpts'])
        except KeyError as exc:
            raise KeyError(f'Sbt config could not be loaded from {config}') from exc

    def to_command(self):
        cmd = [self.sbt_command, '-v']
        cmd.extend([f'-J{opt}' for opt in self.java_opts.split(' ')])
        cmd.extend([f'-D{opt}' for opt in self.sbt_opts.split(' ')])
        return cmd
