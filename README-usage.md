# Usage

## ..defining projects

### File structure
All CI/CD related files reside in a `./deployment` sub folder, relative to the project source code folder.
A typical deployment folder may contain the following files
```shell
├── Dockerfile-mpl
├── project.yml
└── docker-compose-test.yml
```
### project.yml
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

### Dockerfile-mpl
This is a multi-stage docker file, that has at least a `builder` and in most cases also
a `tester` stage.
`WORKDIR` needs to be identical to root path of the sourcecode.
The `tester` stage needs run the unittests and write the results (in [Junit XML format](https://llg.cubic.org/docs/junit/))
to a folder named `$WORKDIR/target/test-reports/`.
See this [example](test/docker/deployment/Dockerfile-mpl).


## ..report the outcome of a pipeline run
MPyL comes with built-in reporters for *Github*, *Jira* and *Slack*. See `mpyl.reporting.targets` how to configure
them and for instructions on how to create your own reporter.

## ..create a custom step
See `mpyl.steps`.