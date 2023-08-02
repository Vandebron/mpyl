# 🖐️ Usage

## ..MPyL CLI

Install MPyL

```shell
pip install mpyl
mpyl --help
```

#### Health check

⭐ It is recommended to run this before running any other commands.
```shell
mpyl health
```
Will validate the configuration and check if all required tools are installed.

##### Command structure

```
.. include:: tests/cli/test_resources/main_help_text.txt
```

Top level commands options are passed on to sub commands and need to be specified *before* the sub command.
In ```mpyl projects --filter <name> list ```, the `--filter` option applies to all `project` commands, like `list`
or `lint`.

###### Projects

```
.. include:: tests/cli/test_resources/projects_help_text.txt
```

###### Build

```
.. include:: tests/cli/test_resources/build_help_text.txt
```

##### MPyL configuration

MPyL can be configured through a file that adheres to the `mpyl_config.yml`
[schema](https://vandebron.github.io/mpyl/schema/mpyl_config.schema.yml).  
Which configuration fields need to be set depends on your usecase. The error messages that you
encounter while using the cli may guide you through the process.
Note that the included `mpyl_config.example.yml` is just an example. 

Secrets can be injected
through environment variable substitution via the
[pyaml-env](https://github.com/mkaranasou/pyaml_env) library. 
Note that values for which the ENV variable is not set, 
will be absent in the resulting configuration dictionary.
<details>
  <summary>Example config</summary>
```yaml
.. include:: mpyl_config.example.yml
```
</details>



Check the [schema](https://vandebron.github.io/mpyl/schema/run_properties.schema.yml) for `run_properties.yml`, which contains detailed
documentation and can be used to enable on-the-fly validation and auto-completion in your IDE.

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

#### YAML auto completion 

![Schema based autocompletion](documentation_images/autocompletion.gif)

###### Intellij IDEA or PyCharm
Go to: `Preferences | Languages & Frameworks | Schemas and DTDs | JSON Schema Mappings`
- Add new schema
- Add matching schema file from latest release:
  - */deployment/project.yml -> https://vandebron.github.io/mpyl/schema/project.schema.yml
  - mpyl_config.example.yml -> https://vandebron.github.io/mpyl/schema/mpyl_config.schema.yml
  - run_properties.yml -> https://vandebron.github.io/mpyl/schema/run_properties.schema.yml
- Select version: ``JSON Schema Version 7``
- Add YAML files corresponding to the schema or add the file pattern. (For instance, adding the file pattern `project.yml` to the `project.schema.yml` will take care of autocompletion in any `project.yml`.)


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

## ..report the outcome of a pipeline run

MPyL comes with built-in reporters for *Github*, *Jira* and *Slack*. See `mpyl.reporting.targets` how to configure
them and for instructions on how to create your own reporter.

## ..create a custom step

See `mpyl.steps`.

## ..create a build step

### Building a docker image

If the output of your build step is a docker image, you can use the `mpyl.steps.build.docker_after_build` step to
make sure the resulting image is tagged, pushed to the registry and made available as an artifact for 
later (deploy) steps.

## ..create a test step

### Junit test results

MPyL can parse Junit test results for reporting purposes. Your test step needs to produce a 
`mpyl.steps.models.ArtifactType.JUNIT_TESTS` artifact.
See `mpyl.steps.test.echo` for an example of how such an artifact can be created.

### Integration tests 
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

## ..create a custom CI-CD flow

MPyL is not a task or even a tool to define and run CI-CD flows. It does however provide a building blocks that can
easily be plugged into your own CI-CD flow.
Here's an example using [Dagster](https://dagster.io/) as a runner

<details>
  <summary>Dagster flow runner</summary>
```python
.. include:: mpyl-dagster-example.py
```
</details>

It can be started from the command line with `dagit --workspace workspace.yml`.

![Dagster flow](documentation_images/dagster-flow-min.png)
![Dagster run](documentation_images/dagster-run-min.png)

