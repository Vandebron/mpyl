# Usage

## ..MPyL CLI

Install MPyL

```shell
pip install mpyl
mpyl --help
```

##### Command structure

Top level commands options are passed on to sub commands and need to be specified *before* the sub command.
In ```mpyl projects --filter <name> list ```, the `--filter` option applies to all `project` commands, like `list`
or `lint`.

##### MPyL configuration

MPyL can be configured through a file that adheres to the `config.yml`
[schema](https://vandebron.github.io/mpyl/schema/mpyl_config.schema.yml).  
Which configuration fields need to be set depends on your usecase. The error messages that you
encounter while using the cli may guide you through the process.
<details>
  <summary>Example config</summary>
```yaml
.. include:: config.yml
```
</details>

#### Auto completion
Usability of the CLI is *greatly enhanced* by autocompletion. 
To enable autocompletion, depending on your terminal, do the following:

###### Bash
Add this to ``~/.bashrc``:
```shell
eval "$(_MPYL_COMPLETE=bash_source mpyl)"
```
###### Zsh
Add this to ``~/.zshrc``:
```shell
eval "$(_MPYL_COMPLETE=zsh_source mpyl)"
```
###### Fish
Add this to ``~/.config/fish/completions/foo-bar.fish``:
```shell
eval (env _MPYL_COMPLETE=fish_source mpyl)
```


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
- `kubernetes` is a required parameter if `deploy` stage is set to `Kubernetes Deploy`.

The [schema](https://vandebron.github.io/mpyl/schema/project.schema.yml) for `project.yml` contains detailed
documentation and
can be used to enable on-the-fly validation and auto-completion in your IDE.

### Dockerfile-mpl

This is a multi-stage docker file, that has at least a `builder` and in most cases also
a `tester` stage.
`WORKDIR` needs to be identical to root path of the sourcecode.
The `tester` stage needs run the unittests and write the results (
in [Junit XML format](https://llg.cubic.org/docs/junit/))
to a folder named `$WORKDIR/target/test-reports/`.
<details>
  <summary>Example `Dockerfile-mpl`</summary>
```docker
.. include:: tests/projects/service/deployment/Dockerfile-mpl
```
</details>

Values can be set dynamically through environment variable substitution via the 
[pyaml-env](https://github.com/mkaranasou/pyaml_env) library. Note that keys for which the ENV variable is not
will be absent in the resulting configuration dictionary.


### docker-compose-test.yml
If your project includes "integration tests" that require a docker container to run during the test stage,
you can define these containers in a file named `docker-compose-test.yml`. For example, to test your database schema
upgrades, with a real postgres database:
<details>
  <summary>Example `docker-compose-test.yml`</summary>
```yaml
.. include:: tests/projects/service/deployment/docker-compose-test.yml
```
</details>

Note: make sure to define a reliable `healthcheck` to prevent your tests from being run before the database is 
fully up and running.

## ..report the outcome of a pipeline run

MPyL comes with built-in reporters for *Github*, *Jira* and *Slack*. See `mpyl.reporting.targets` how to configure
them and for instructions on how to create your own reporter.

## ..create a custom step

See `mpyl.steps`.