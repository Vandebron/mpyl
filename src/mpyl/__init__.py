"""
.. include:: ../../README.md

## Technologies

### Requirements
The following technologies are expected to be present on the local OS:
 - [Python](https://www.python.org/) >= 3.9
 - [Pip](https://pypi.org/project/pip/) >= 23.0.1
 - [Pipenv](https://pypi.org/project/pipenv/) >= 2023.2.18
 - [Docker](https://www.docker.com/) > 20
 - [Docker compose](https://docs.docker.com/compose/install/linux/)
 installed as plugin (`docker compose version`) >= v2.2.3
 - [Git](https://git-scm.com/) SCM

### Bundled
MPyL is extensible and has a minimal footprint. Having said that, batteries for the following technologies are included.

##### CI/CD
###### Build
 - [Docker](https://www.docker.com/) `mpyl.steps.build.dockerbuild`
 - [Scala (SBT)](https://www.scala-sbt.org/) `mpyl.steps.build.sbt`

###### Testing
 - [Junit](https://junit.org/) `mpyl.steps.models.ArtifactType.JUNIT_TESTS`

###### Deployment
 - [K8S](https://kubernetes.io/) `mpyl.steps.deploy.kubernetes`
 - [Helm](https://helm.sh/) `mpyl.steps.deploy.k8s.helm`

##### Reporting
 - [Jira](https://www.atlassian.com) `mpyl.reporting.targets.jira`
 - [Github](https://github.com/) `mpyl.reporting.targets.github`
 - [Slack](https://slack.com/) `mpyl.reporting.targets.slack`

.. include:: ../../README-usage.md

.. include:: ../../README-dev.md
"""

from importlib.metadata import version as version_meta

import click

from .cli.commands.build import build
from .cli.commands.meta_info import version
from .cli.commands.projects import projects
from .utilities.pyaml_env import parse_config
from .utilities.repo import RepoConfig, Repository


@click.group(name='mpyl')
def main_group():
    """Command Line Interface for MPyL"""


def main():
    main_group.help = f"Command Line Interface for MPyL {version_meta('mpyl')}"
    main_group.add_command(projects)
    main_group.add_command(build)
    main_group.add_command(version)
    main_group()  # pylint: disable = no-value-for-parameter
