# Modular Pypeline Library
[![python](https://img.shields.io/badge/Python-3.9-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
![build-and-test-module](https://github.com/Vandebron/pympl/actions/workflows/build-package.yml/badge.svg?branch=main)
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

# Quickstart

###  📚 Documentation
 Detailed, searchable, documentation can be found at [https://vandebron.github.io/mpyl](https://vandebron.github.io/mpyl)

### Run instructions

1. Install dependencies
    ```shell
    pipenv install -d
    ```
2. Run the Dagit UI
    ```shell
    dagit --workspace ./workspace.yml 
    ```

For developer instructions and troubleshooting, see [developer readme](./README-dev.md)

### Usage

All CI/CD related files reside in a `./deployment` sub folder, relative to the project source code folder.
A typical deployment folder may contain the following files
```shell
├── Dockerfile-mpl
├── project.yml
└── docker-compose-test.yml
```
#### project.yml
The `project.yml` defines which steps needs to be executed during the CI/CD process.
```yaml
name: batterypackApi
stages:
  build: Sbt Build
  test: Sbt Test
  deploy: Kubernetes Deploy
```
- `name` is a required parameter
- `stages` are optional parameters. Stages that are undefined will be skipped. Depending on the
  type of project you want to build, you need to specify an appropriate action to be performed in each stage.
  For example: `Sbt Build` can be used for scala projects, and `Docker Build` can be used for front-end projects.
- `kubernetes` is a required parameter if `deploy` stage is set to `Kubernetes Deploy`. More details on this parameter can be found [here](src/nl/vandebron/jenkins/projects/BuildProject.groovy)

The [schema](https://vandebron.github.io/mpyl/schema/project.schema.yml) for `project.yml` contains detailed documentation and
can be used to enable on-the-fly validation and auto-completion in your IDE.

#### Dockerfile-mpl
This is a multi-stage docker file, that has at least a `builder` and in most cases also
a `tester` stage.
`WORKDIR` needs to be identical to root path of the sourcecode.
The `tester` stage needs run the unittests and write the results (in [Junit XML format](https://llg.cubic.org/docs/junit/))
to a folder named `$WORKDIR/target/test-reports/`.
See this [example](test/docker/deployment/Dockerfile-mpl).



