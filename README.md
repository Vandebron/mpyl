# Modular Pipelines in Python
![build-and-test-module](https://github.com/Vandebron/pympl/actions/workflows/build-package.yml/badge.svg?branch=main)
![version](https://img.shields.io/github/v/tag/Vandebron/pympl.svg?color=blue&include_prereleases=&sort=semver)

The aim of this tool is to be a better version of https://github.com/Vandebron/mpl-modules

## Run instructions

```shell
dagit --workspace ./workspace.yml 
```

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
