import os

from mpyl import main_group, add_commands
from mpyl.steps import IPluginRegistry

from plugins.gradle import BuildGradle, TestGradle

IPluginRegistry.plugins.append(BuildGradle)
IPluginRegistry.plugins.append(TestGradle)

add_commands()
os.environ["SOME_CREDENTIAL"] = "cred"
main_group(
    ["build", "-c", "mpyl_config.example.yml", "run", "--all"], standalone_mode=False
)
