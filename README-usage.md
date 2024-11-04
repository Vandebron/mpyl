# 🖐️ Usage

## ..MPyL CLI

### Suggested first time use

#### 1. Install MPyL

```shell
pip install mpyl
mpyl --help
```

#### 2. Health check

⭐ It is recommended to run this before running any other commands.
```shell
mpyl health
```
Will validate the configuration and check if all required tools are installed.

#### 3. Run a local build via the CLI

Find out which projects need to be built.
```shell
mpyl build status
```
Run a build.
```shell
mpyl build run
```

#### 4. Run a CI build on your Pull Request

Create a pull request.
```shell
gh pr create --draft
```
If you use MPyL in a github action, a build will be triggered automatically and the results will be reported there.

### Command structure

```
.. include:: tests/cli/test_resources/main_help_text.txt
```

Top level commands options are passed on to sub commands and need to be specified *before* the sub command.
In ```mpyl projects --filter <name> list ```, the `--filter` option applies to all `project` commands, like `list`
or `lint`.

<details>
  <summary>Projects</summary>
```
.. include:: tests/cli/test_resources/projects_help_text.txt
```
</details>

<details>
  <summary>Build</summary>
```
.. include:: tests/cli/test_resources/build_help_text.txt
```
</details>

##### MPyL configuration

MPyL can be configured through a file that adheres to the `mpyl_config.yml`
[schema](https://vandebron.github.io/mpyl/schema/mpyl_config.schema.yml).
Which configuration fields need to be set depends on your use case. The error messages that you
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

###### Stage configuration

MPyL can be configured to use an arbitrary set of build stages. Typical CI/CD stages are `build`, `test` or `deploy`.
See `mpyl.steps` for the steps that come bundled and how to define and register your own.

<details>
  <summary>Example stage configuration</summary>
```yaml
.. include:: mpyl_stages.schema.yml
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

## ..setting up a CI-CD flow

MPyL is not a taskrunner nor is it a tool to define and run CI-CD flows. It does however provide a building blocks that can
easily be plugged into any existing CI-CD platform.

### Github actions

Github actions are a natural fit for MPyL. To build a pull request, you can use the following workflow:
```yaml
name: Build pull request
on:
  push:
    branches-ignore: [ 'main' ]

jobs:
  Build_PR:
    name: Build and deploy the pull request
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install MPyL
        run: pip install 'mpyl==<latest_version>'

      - name: Print execution plan
        run: mpyl build status

      - name: Build run
        run: mpyl build run
```

### Dagster
Although [dagster](https://dagster.io/)'s primary focus is data processing and lineage, it can be used as a runner for MPyL.
It provides a nice UI to inspect the flow and logs. It supports concurrent execution of steps in a natural way.
These features make it a convenient runner for local development and debugging.

<details>
  <summary>Dagster flow runner</summary>
```python
.. include:: mpyl-dagster-example.py
```
</details>

It can be started from the command line with `dagit --workspace workspace.yml`.

![Dagster flow](documentation_images/dagster-flow-min.png)
![Dagster run](documentation_images/dagster-run-min.png)

## ..caching build artifacts

#### Docker images

Docker image layers built in previous runs can be used as a cache for subsequent runs. An external cache source can
be configured in `mpyl_config.yml` as follows:

```yaml
docker:
  registry:
    cache:
      cacheFromRegistry: true
      custom:
        to: 'type=gha,mode=max'
        from: 'type=gha'
```

The `to` and `from` fields map to `--cache-to` and `--cache-from`
[buildx arguments](https://docs.docker.com/engine/reference/commandline/buildx_build/#cache-from).

The docker cache can be used in both the `mpyl.steps.build.dockerbuild` and `mpyl.steps.test.dockertest` steps.

#### Artifacts

MPyL's artifact metadata is stored in the hidden `.mpyl` folders next to `project.yml`.
These folders are used to cache information about (intermediate) build results.
A typical `.mpyl` folder has a file for each executed stage. The `BUILD.yml` file contains the metadata for the
build step. For example:
```yaml
message: Pushed ghcr.io/samtheisens/nodeservice:pr-6
produced_artifact: !Artifact
  artifact_type: !ArtifactType DOCKER_IMAGE-1
  revision: b6c87b70c3c16174bdacac6c7dd4ef71b4bb0047
  producing_step: After Docker Build
  spec: !DockerImageSpec
    image: ghcr.io/samtheisens/nodeservice:pr-6
```
These files speed up subsequent runs by preventing steps from being executed when their inputs have not changed.

🧹 These `.mpyl` folders can be safely deleted to force a full rebuild via
```shell
mpyl build clean
```

## ..create a custom step

See `mpyl.steps`.

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
