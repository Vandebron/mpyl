"""SBT config"""
import ast
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SbtConfig:
    java_opts: str
    sbt_opts: str
    sbt_command: str
    test_with_coverage: bool
    verbose: bool

    @staticmethod
    def from_config(config: Dict):
        sbt_config = config.get('sbt', None)
        if not sbt_config:
            raise KeyError(f"'sbt' could not be loaded from {config}")
        return SbtConfig(sbt_command=sbt_config['command'],
                         java_opts=sbt_config['javaOpts'],
                         sbt_opts=sbt_config['sbtOpts'],
                         test_with_coverage=(str(sbt_config['testWithCoverage']).lower() == 'true'),
                         verbose=(str(sbt_config['verbose']).lower() == 'true')
                         )

    def to_command(self):
        cmd = [self.sbt_command]
        if self.verbose:
            cmd.append('-v')
        cmd.extend([f'-J{opt}' for opt in self.java_opts.split(' ')])
        cmd.extend([f'-D{opt}' for opt in self.sbt_opts.split(' ')])
        return cmd
