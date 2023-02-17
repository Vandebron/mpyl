# Modular Pypeline Library
[![python](https://img.shields.io/badge/Python-3.9-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
![build-and-test-module](https://github.com/Vandebron/pympl/actions/workflows/build-package.yml/badge.svg?branch=main)
[![publish-documentation](https://github.com/Vandebron/mpyl/actions/workflows/docs.yml/badge.svg?branch=main)](https://vandebron.github.io/mpyl)
[![version](https://img.shields.io/github/v/tag/Vandebron/pympl.svg?color=blue&include_prereleases=&sort=semver)](https://pypi.org/project/mpyl/)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/PyCQA/pylint)

This tool is loosely based on the principles described in https://www.jenkins.io/blog/2019/01/08/mpl-modular-pipeline-library/
but completely independent of Jenkins

## Usage
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
This is a multi-stage docker file, that has at least an `builder` and in most cases also
a `tester` stage.
`WORKDIR` needs to be identical to root path of the sourcecode.
The `tester` stage needs run the unittests and write the results (in [Junit XML format](https://llg.cubic.org/docs/junit/))
to a folder named `$WORKDIR/target/test-reports/`.
See this [example](test/docker/deployment/Dockerfile-mpl).


## Proposed implementation

- Usability
  - Self documented where possible: `project.yml` schema, CLI --help for each argument, concise and guiding logging
  - Built for us and by us. This should not be a one-person project.
  - Easily extensible via custom build steps
  - Strikes the right balance between concise, intuitive <-> explicit, transparent
- Clearly defined data model and interfaces for:
  - project metadata (name, env vars, dependencies)
  - run specific information (initiator, branch/tag, build target)
  - input and output types of individual steps
- Replaceablity
  - Independent from Jenkins (or any other build executor) 
  - Runs locally, with no OS dependencies in as far as possible.
  - Where OS dependencies e.g. kubectl, helm are unavoidable, they are included in a docker image that can be used inside the executor
- Non functional
  - Implemented in our default scripting language: Python
  - Type safe (mypy)
  - Extensively unit tested

## Analysis of Jenkins based MPL

### The good

- keeps knowledge local
- truly modular: reusable but independent steps
- simple build but effective build orchestration
- completely tailored to our needs: no bloat or overabstraction
- unit tested logic
- `project.yml` metadata
  - gives useful information about the project it relates to
  - is self documented via a schema
  - gives insight in project depenendencies
- supports PR centered development via staging environments
- basic workflow is simple: build, test, deploy, acceptance test

### The bad

- implicitly depends on presence of Jenkins plugins
- many caveats due to running in Jenkins sandbox
- hard to grasp for new developers

### The ugly

- awkward Jenkins module project structure
- very obscure error messages and exceptions
- deploy steps cannot be executed or simulated locally
- logic needs to be written in groovy
- code that depends on IO is virtually untestable
