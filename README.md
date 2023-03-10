# Modular Pypeline Library
[![python](https://img.shields.io/badge/Python-3.9-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
![build-and-test-module](https://github.com/Vandebron/pympl/actions/workflows/build-package.yml/badge.svg?branch=main)
![coverage](https://camo.githubusercontent.com/e35bc0e8a0231ed12f0b23394c8abbaffb720b84f620de4cc84134ecec8ca704/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f436f6465253230436f7665726167652d37362532352d737563636573733f7374796c653d666c6174)
[![publish-documentation](https://github.com/Vandebron/mpyl/actions/workflows/docs.yml/badge.svg?branch=main)](https://vandebron.github.io/mpyl)
[![version](https://img.shields.io/github/v/tag/Vandebron/pympl.svg?color=blue&include_prereleases=&sort=semver)](https://pypi.org/project/mpyl/)
[![package downloads](https://img.shields.io/pypi/dw/mpyl.svg)](https://pypi.org/project/mpyl)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/PyCQA/pylint)


# What is MPyL?

MPyL stands for Modular Pipeline Library (in Python).

This library is loosely based on the principles described in https://www.jenkins.io/blog/2019/01/08/mpl-modular-pipeline-library/
but completely independent of Jenkins or any other CI/CD platform.
It's mission statement is described [here](./README-motivation.md).

###  📚 Documentation
Detailed, searchable documentation can be found at [https://vandebron.github.io/mpyl](https://vandebron.github.io/mpyl)

## Technologies

### Requirements
The following technologies are expected to be present on the local OS:
 - [Python](https://www.python.org/) >= 3.9
 - [Pip](https://pypi.org/project/pip/) >= 23.0.1
 - [Pipenv](https://pypi.org/project/pipenv/) >= 2023.2.18
 - [Docker](https://www.docker.com/) > 20
 - [Docker compose](https://docs.docker.com/compose/install/linux/) installed as plugin (`docker compose version`) >= v2.2.3
 - [Git](https://git-scm.com/) SCM

### Bundled
MPyL is extensible and has minimal footprint. Having said that, batteries for the following technologies are included.

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

