"""Ephemeral related utility methods"""

from ...project import Target, Project


def get_env_variables(project: Project, target: Target) -> dict[str, str]:
    if project.deployment is None:
        raise KeyError(f'No deployment information was found for project: {project.name}')
    if len(project.deployment.properties.env) == 0:
        raise KeyError(f'No properties.env is defined for project: {project.name}')

    env_variables: dict[str, str] = {
        env_variable.key: env_variable.get_value(target) for env_variable in
        project.deployment.properties.env
    }

    return env_variables
