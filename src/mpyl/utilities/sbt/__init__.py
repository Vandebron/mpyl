"""SBT config"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SbtConfig:
    java_opts_file_name: str = '.jvmopts'
    sbt_opts: str = '-Xmx4G -Xms4G -XX:+UseG1GC -XX:+CMSClassUnloadingEnabled -Xss2M -Duser.timezone=GMT ' \
                    '-Dsbt.log.noformat=true '
    sbt_command: str = 'sbt --client'
