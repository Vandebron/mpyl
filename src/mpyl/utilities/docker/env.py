from mpyl import parse_config
from mpyl.project import Project, Target
from mpyl.steps.models import RunProperties


def write_env_to_file(project: Project, run_properties: RunProperties) -> str:
    env_str: str = '\n'.join([f'{e.key}={e.get_value(run_properties.target)}' for e in project.deployment.properties.env])

    env_file_name: str = run_properties.config['docker']['envFileName']
    env_file = open(env_file_name, 'x')
    env_file.write(env_str)
    env_file.close()

    return env_file_name
