"""SBT config"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SbtConfig:
    java_opts = '-Xmx4G -Xms4G -XX:+UseG1GC -XX:+CMSClassUnloadingEnabled -Xss2M'
    sbt_opts: str = 'user.timezone=GMT sbt.log.noformat=true'
    sbt_command: str = 'sbt'

    def to_command(self):
        cmd = [self.sbt_command, '-v']
        cmd.extend([f'-J{opt}' for opt in self.java_opts.split(' ')])
        cmd.extend([f'-D{opt}' for opt in self.sbt_opts.split(' ')])
        return cmd
