from mpyl import main_group, add_commands
from mpyl.steps import IPluginRegistry


from plugins.gradle import BuildGradle

IPluginRegistry.plugins.append(BuildGradle)

add_commands()
main_group(
    ["build", "-c", "mpyl_config.example.yml", "run", "--all"], standalone_mode=False
)
