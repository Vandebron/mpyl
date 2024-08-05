# Release notes

## MPyL 1.7.1


#### BPM Diagram deploy remove Docker dependency
- Remove the usage of Docker when deploying BPM diagrams
- Instead, rely on the tool being pre-installed in the cluster (similar to Scala etc.)


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.7.1)

## MPyL 1.7.0


#### Project.yml changes
- Add a `pipeline` field to select which pipeline to run (e.g. which Github Actions workflow) to use for a specific project

### Run plan output
- changed the format of the run plan JSON file to make parsing easier, reduce the amount of redundant values and consequently the size of the file

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.7.0)

## MPyL 1.6.11


#### Project.yml changes
- Make projectId field mandatory to prevent rbac issues in rancher
- Add optional field for project type

#### Camunda
- Some small changes and bugfixes to the camunda step logic


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.6.11)

## MPyL 1.6.10


#### Deploy existing jobs
- Fix the helm list cmd function to include the kube-context flag
- Fixes the issue where existing jobs wouldn't be found and thus not deleted


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.6.10)

## MPyL 1.6.9


#### Cypress postdeploy
- Remove the cypress postdeploy step
- Slightly change the postdeploy config to align with other stages


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.6.9)

## MPyL 1.6.8


#### Configurable deployment cluster

- Be able to specify a list of target clusters to deploy to
- Be able to specify default targets per environment
- Be able to override the default targets in the `project.yaml`

```yaml
deployment:
  cluster:
    pr: 'leaf-test'
    test: 'test'
    acceptance: 'acce'
    production: 'prod'
```

#### Additional Traefik routes

Be able to define additional, generic Traefik routes in the `project.yaml` that are referenced from the mpyl_config.yaml

project.yaml
```yaml
traefik:
    hosts:
      - host:
          pr: "Host(`payments-{PR-NUMBER}.{CLUSTER-ENV}.nl`)"
          test: "Host(`payments.test.nl`)"
          acceptance: "Host(`payments.acceptance1.nl`)"
          production: "Host(`payments.nl`)"
        tls:
          all: "le-custom-prod-wildcard-cert"
        insecure: true
        whitelists:
          test:
            - "Test"
        additionalRoute: "ingress-intracloud-https"
```

mpyl_config.yaml
```yaml
deployment:
    additionalTraefikRoutes:
      - name: "ingress-intracloud-https"
        clusterEnv:
          pr: "test-other"
          test: "test-other"
          acceptance: "acce-other"
          production: "acce-other"
        middlewares:
          - "intracloud-middleware@kubernetescrd"
        entrypoints:
          - "intracloud"
```

#### Additional Traefik configuration

It is also possible to define the additional traefik configuration in the `mpyl_config.yml`:

```yaml
deployment:
    traefikDefaults:
      httpMiddleware: "traefik-https-redirect@kubernetescrd"
      tls: "le-custom-prod-wildcard-cert"
```

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.6.8)

## MPyL 1.6.7


#### Improvements
- Improve dependency linting: projects cannot depend on themselves
- General logging improvements
- Improved `BPM Diagram Deploy` step
- Cypress code improvements

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.6.7)

## MPyL 1.6.6


#### Pass changed files
- Allow to pass a .json of changed files to determine the run plan
- The file format has to be a list/dict of `{"path/to/file": "change_type"}`, where `change_type` is one of `["A", "C", "D", "M", "R"]`

#### Run plan
- Add the maintainers field to the run plan json


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.6.6)

## MPyL 1.6.5


#### Tests
- Execute a single sbt `test` command instead of `test:compile` and `test:test` sequentially (removes the need for the experimental thin client)

### Dependency management
- Always re-execute a stage for a project when one or more of their dependencies are modified
- Produce a hash of the modified files even when the stage is cached (so a follow-up commit can be cached)


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.6.5)

## MPyL 1.6.4


#### Run results
- Account for parallel runs when reading and writing the run results
- Test results are now also added to the output artifact instead of just to a file

### Run plan
- The run plan file is now written to `.mpyl/run_plan.pickle` and `.mpyl/run_plan.json` (replaces the old confusing `build_plan` name)

### Other changes
- The root `.mpyl` folder is now also cleaned up as part of `mpyl build clean`
- Do not fail the build when trying to create a Kubernetes namespace that already exists


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.6.4)

## MPyL 1.6.3


#### Build status
- Write a simple build plan in json format to `.mpyl/build_plan.json` when using the `build status` command.

#### CloudFront Kubernetes Deploy
- Remove support for CloudFront Kubernetes Deploy step. 



Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.6.3)

## MPyL 1.6.2


#### Memory limits
- Doubled the general memory limit for dagster repos to 1024, as agreed within the dagster guild to prevent OOM.

#### Chart improvements
- Be able to specify `alerts` in the project yaml when doing `Kubernetes Job Deploy` step
- Create charts for these prometheus rules


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.6.2)

## MPyL 1.6.1


#### Bugfixes
- Do not try to hash deleted or renamed files when building a cache key


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.6.1)

## MPyL 1.6.0


#### Improvements
- Implement a different way to determine the build plan
- Change the layout of the build plan print to improve transparency
- Allow passing --stage to the build status command

#### Build set caching
Store the build set in disk and read it back when `--sequential` is passed as a parameter, preventing us to rebuild the plan on subsequent
stages. Which means there is no need to diff with the main branch, thus no need to fetch the entire main branch history
before running mpyl.
This is a significant performance improvement as you only need to do a clone with full history for the first stage,
and run all others using a shallow clone (much faster to check out on repositories with many commits).


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.6.0)

## MPyL 1.5.1


#### Bugfixes
- Always add changes to the build plan for the deploy stage


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.5.1)

## MPyL 1.5.0


#### Argocd

Add support for an argocd repository and workflow:
- Can be toggled on by setting `kubernetes.deployAction` to 'KubectlManifest' in the `mpyl_config.yaml` file.
- An `argoRepository` and `argoGithub` object have been added to the `vcs` section in the `mpyl_config.yaml` file to
  configure the argocd repository and github repository.
- The `manifest.yaml` file will be created during the deploy step.
- The command to push the k8s manifests to the argocd repository is `mpyl build artifacts push --artifact-type argo`. 
- An additional `deployment.yaml` file will be created in the push command, it contains some extra metadata for argocd.
- A pull request will be created in the configured argocd repository with the created k8s manifest files.
- The folder in the argocd repo structure has the following pattern: `k8s-manifests/{project_name}/{target}/{namespace}/*.yaml`.

#### Manual selection
Include project overrides in list of projects.

#### Multiple deploy targets

Allow multiple deploy targets when using the jenkins cli command.


#### Stage configuration

MPyL can be configured to use an arbitrary set of build stages. Typical CI/CD stages are `build`, `test` or `deploy`.
See `mpyl.steps` for the steps that come bundled and how to define and register your own.

<details>
  <summary>Example stage configuration</summary>
```yaml
.. include:: mpyl_stages.schema.yml
```
</details>


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.5.0)

## MPyL 1.4.20


#### Traefik priority rules per environment

You can now configure Traefik route priorities per environment:

```yaml
deployment:
  traefik:
    hosts:
      - host:
          all: "Host(`host1.example.com`)"
          servicePort: 1234
          priority:
            all: 10
      - host:
          all: "Host(`host2.example.com`)"
          servicePort: 1235
          priority:
            pr: 20
            test: 30
            acceptance: 40
            production: 50
```


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.20)

## MPyL 1.4.19


#### ECR repo
- New ECR repositories now allow for mutable image tags


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.19)

## MPyL 1.4.18


#### Project id
Project id is now a required property for non override project.yml's that have a deploy stage defined. It can/will be used
for rbac purposes in rancher.

#### Deployment strategy
Make deployment strategy configurable in `project.yml` and `mpyl_config.yml`:

```yaml
kubernetes:
  deploymentStrategy:
    rollingUpdate:
      maxUnavailable: "25%"
      maxSurge: "25%"
    type: "RollingUpdate"
```

#### Cache repo
- Fix bug when pushing artifacts

#### ECR repo
- Create ECR repository if it doesn't exist

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.18)

## MPyL 1.4.17


#### Bugfixes
- Fix updating of pr body's that include "----"
- Don't fail the Github pr body update function based on the mpyl run result
- Fix loading of custom `ExecutionException` with pickle
- Add a retry on the artifact caching push to avoid issues on parallel runs
- Fix the cypress docker image


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.17)

## MPyL 1.4.16


#### Bugfixes
- Fix non-cron jobs deployments


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.16)

## MPyL 1.4.15


#### Add AWS ECR
- MPyL can now push/pull images to/from AWS ECR. Check mpyl_config file to set this.

#### Enhancements
- Adds the optional `hasSwagger` field to enhance PR descriptions. This update ensures accurate URL display for services that do not use Swagger

#### Manual build improvements
- Do not get changes from the remote repository when doing manual build

#### Cron job improvements
- Allow cron jobs to be configured per environment


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.15)

## MPyL 1.4.14


#### Sealed Secrets and Dagster Deploy
- The DagsterDeploy step now supports sealed secrets.
- The Dagster UserCode helm chart is deployed with an extra manifest that contains the sealed secrets that are manually sealed and documented in the `project.yml`


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.14)

## MPyL 1.4.13


#### Ship typing information
- MPyL can now be type checked via `mypy`.

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.13)

## MPyL 1.4.12


#### Enhancements
- Several small code improvements
- Improve sbt test step

#### Bug Fixes
- Fix `mpyl build clean` command for override projects
- Fix test results collection on compile errors for sbt test
- Make sure sbt test coverage always gets turned off again


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.12)

## MPyL 1.4.11


#### Enhancements
- Set resources for Dagster user code servers (hardcoded)

#### Cronjob deployment
- Add `timeZone` field to job specification

#### CLI improvements
- Add `--dryrun` flag

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.11)

## MPyL 1.4.10


#### Bug fixes
- Fix tag builds by taking the tag env variable into account in the new logic of v1.4.9


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.10)

## MPyL 1.4.9


#### Bug fixes
- Fix manual deployment bug where the build plan for the deploy stage wasn't taking the manual selection into account.


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.9)

## MPyL 1.4.8


#### Discovery

Add debug logging to build plan discovery methods
This provides more explanation on _why_ certain projects are selected for each stage
Can be invoked by setting the `--verbose` for the `build` subcommand, e.g. `mpyl build --verbose status`

#### Bug fixes
- Add `command` and `args` fields to Kubernetes jobs
- Fixes a bug when a non-changed project is selected whose base path includes fully a changed file's path.
I.e. when the changed file is `projects/project-name/src/main.py` and a project's base path is `projects/project-name-other`,
this other project was wrongly selected as changed.


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.8)

## MPyL 1.4.7


#### Spark Deployment
- Configure replica count for spark jobs

#### Dagster deployment
- Set `DOCKER_IMAGE` build argument to the full docker image path

#### Cloudfront Deploy
- Use local docker image when running with --dry-run

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.7)

## MPyL 1.4.6


#### Enhancement
- Shorten helm release names for dagster user deployment helm charts by using fullnameOverride
- Cover more special cases for dagster user deployment helm charts by unittests

#### Linting

- Enable extended checks by default
- Fail command if one of the extended checks fail


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.6)

## MPyL 1.4.5


#### Override option for dagster user deployments' helm charts

- Enable users to override the serviceAccount in the user deployment helm chart of dagster with a global serviceAccount

#### Bugfixes
- Fix Spark Deploy Step: inject sealed secrets, set job argument correctly

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.5)

## MPyL 1.4.4


#### Bugfixes

- Filter out override projects from the `projects` cli commands
- Sort the `projects names` results alphabetically
- Fix the fact that whitelists are being cached between charts/projects, thus subsequent charts/projects contain the whitelists from previous ones
- Add default build_args for DockerBuild and DockerTest stages

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.4)

## MPyL 1.4.3


#### Manual project selection
Allows for passing a comma separated string of projects to be passed to the run cli, using the `-p` or `--projects` 
flags. This will override the default change detection behavior and the `-all` flag.

#### Traefik configuration
- Create HTTP ingress routes that redirect to the HTTPS one
- Add priority for routes
- Add insecure option

#### Kubernetes configuration 
- Set both maintainer and maintainers fields in the metadata
- Use “service” as the default name of containers

#### Bugfixes
- Use the full image path when pulling images in `CloudFront Kubernetes Deploy` and `Deploy From Docker Container`

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.3)

## MPyL 1.4.2


#### Bugfixes

- Fix on how the selected DockerRegistry is being opened when writing the values of a dagster user code helm chart
- Fix ruamel.yaml.YAML() name overshadowing with the yaml package in the k8s module

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.2)

## MPyL 1.4.1


#### Bugfixes

- Fix project overlays (merging children projects with their parent)
- Github Check output only shows test summary, not the full test output
- Get target branch in cache repo from the run properties
- Only transition non-Epic Jira tickets to 'To Do'

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.1)

## MPyL 1.4.0


#### Customizable stages

Stages are now customizable. You can add the stages to the run_properties according to the defined schema, for example:

```yaml
stages:
  - name: 'build'
    icon: '🏗️'
  - name: 'test'
    icon: '📋'
```

#### Support single stage runs

It is now possible to run a single stage. For example, to run only the `build` stage:

```bash
mpyl build run --stage build
```

If you want the results / report of the previous stage run to be combined with your current stage run, use the
`--sequential` flag. Without this flag, the previous results will be overwritten. The results are stored in a local
file in `.mpyl` using `pickle`, see `mpyl-reporter.py` for an example on how to use them.

#### Remote artifact caching

Remote caching can be used now to significantly speed up builds.
The mechanisms are described in [the documentation](https://vandebron.github.io/mpyl/mpyl.html#caching-build-artifacts)

##### Artifact caching
Is done by bookending your build commands with `mpyl build artifacts push` and `mpyl build artifacts pop`.
```shell
mpyl build artifacts pull
mpyl build run
mpyl build artifacts push --artifact-type cache
```

##### Docker image caching

Allows you to cache from docker images in the registry. This is particularly useful in scenarios where the local
filesystem cannot be relied upon to persist between builds, such as in CI environments.

#### Implicit dependencies

If dependencies are defined for the build stage they now implicitly also apply for the test and deploy stages.

#### Support for project overlaying

The MPyL recognizes the `project-override-*.yml` files and merges them to the parent yml(`project.yml`) file in the same
directory.
Using this functionality, you can define different deployments for the same project.
For example, you can deploy the same project with different settings to different environments.

#### Bugfixes

- Fix TLS creation in ingress routes

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.4.0)

## MPyL 1.3.2


#### Bug Fixes

- Fix the cypress kubectl config merging and passing to docker for linux environments
- Fix jira ticket state switching to only switch from 'to do' to 'in progress'


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.3.2)

## MPyL 1.3.1


#### Target specific whitelists

Now have the possibility to specify target specific whitelisting rules.
This means that for the same rule, we can apply different lists of IPs, depending on the target environment:
Change in the `mpyl_config.yaml` file:

```yaml
whiteLists:
  default: [ "VPN" ]
  addresses:
    - name: "VPN"
      all: [ "10.0.0.1" ]
    - name: 'Outside-World'
      all: [ '0.0.0.0/0' ]
    - name: 'K8s-Test'
      all: [ '1.2.3.0', '1.2.3.1' ]
    - name: 'TargetSpecificWhitelist'
      pr: ['1.2.3.4']
      test: ['1.2.3.4']
      acceptance: ['2.3.4.5']
      production: ['3.4.5.6']
```

#### Add support for various kubernetes resources

- Add support for `Role` and `RoleBinding` resources
- Be able to specify `command` and `args` in `Container` resources

#### Fix bug in the Cypress tests

- Account for multiple config files being passed in the KUBECONFIG env var


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.3.1)

## MPyL 1.3.0


#### Support for multiple docker registries

You can now specify multiple docker registries in the config file.
The `docker` field in the `mpyl_config.yml` now takes a list of registries:
```yaml
docker:
  defaultRegistry: 'acme.docker.com'
  registries:
    - hostName: 'acme.docker.com'
      userName: !ENV ${DOCKER_REGISTRY_USR:docker_user}
      password: !ENV ${DOCKER_REGISTRY_PSW:docker_password}
```
which can be referenced in the `project.yaml` by the `hostName` field

```yaml
docker:
  hostName: 'acme.docker.com'
```

#### Automatic config updates

Running `mpyl health` will now automatically update your config file with the latest version of the config file from the repo. 
This will allow you to get the latest changes to the config file without having to manually update it.

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.3.0)

## MPyL 1.2.1

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.2.1)

## MPyL 1.2.0


#### Automated project.yml upgrades

A new cli command `mpyl projects upgrade` allows you to upgrade your `project.yml` to the latest version. It will
automatically add new sections and fields when necessary.

Future upgrade scripts should be added to `mpyl.projects.versioning`.
#### Kubernetes deploy actions
In `mpyl_config.yaml` the deploy action now needs to be explicitly set.
```yaml
kubernetes:
  deployAction: HelmDeploy
```
There are four deploy actions available:
- `HelmDeploy` - deploys the helm chart
- `HelmDryRun` - runs a helm dry run against the cluster
- `HelmTemplate` - renders a helm chart on the file system to the folder specified in the `helmTemplateOutputPath` property
- `KubectlManifest` - renders the deployment as manifest file specified in the `kubectlManifestOutputPath` property. This manifest can be deployed with a `kubectl -f <path>` command.

#### Image pull secrets
Default image pull secrets now need to be configured globally in `mpyl_config.yml`
```yaml
  deployment:
    kubernetes:
      imagePullSecrets:
        - name: 'acme-registry'
```

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.2.0)

## MPyL 1.1.0


#### Hotfix for mapping multiple ports to the same service

Due to a bug in the mapping of multiple ports to the same service, the following configuration:
```yaml
deployment:
  kubernetes:
  portMappings:
    8081: 8081
  traefik:
    hosts:
      ...
      - host:
          all: "Host(`some.other.host.com`)"
        servicePort: 4091
        priority: 1000
```
resulted in `8081` being used as servicePort in the treafik rule instead of `4091`.

#### Release notes

The release notes (as you are reading them now) are generated from the `releases/notes` directory in the project repository.
Whenever a release has changes that require your attention like: new cli commands, new features, breaking changes, upgrade
instructions, etc. they will be included here.

#### Create startup probes by default

When a project is using livenesProbes, but has no startupProbe defined, we resort to creating a startup probe from the
default values defined in the `mpyl_config.yml` file. This is done to prevent the project from being marked as
unhealthy.

#### Fix namespace interpolation in the Traefik default hosts

The default hosts for Traefik are now interpolated with the namespace of the project in test/acceptance/production.

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.1.0)

## MPyL 1.0.11


#### Retraction note

Due to a bug in the release process, the `1.0.11` had to be retracted. It is not available in the registry anymore and
all changes have been subsumed into `1.0.12`.

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.11)

## MPyL 1.0.10


#### Support for service monitor
The prometheus [ServiceMonitor](https://doc.crds.dev/github.com/prometheus-operator/kube-prometheus/monitoring.coreos.com/ServiceMonitor/v1@v0.7.0)
CRD and a corresponding [PrometheusRule](https://doc.crds.dev/github.com/prometheus-operator/kube-prometheus/monitoring.coreos.com/PrometheusRule/v1@v0.7.0)
are deployed whenever the `metrics` field is defined in `project.yml`


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.10)

## MPyL 1.0.9


##### Support for reference environment variables
Support for reference environment variables. All standard types: `secretkeyref`, `fieldRef` and `resourceFieldRef` are 
support. This allows one to reference secrets, fields and resource fields from other resources in the same namespace.

##### Repo command
`mpyl repo` is new command group with the following subcommands:

 - `status` shows the status of the repository in terms of branch checked out, revision and revisions since branching off from base (main/master).
 - `init` allows you to initialize the local repository to prepare it for use with MPyL PR builds.


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.9)

## MPyL 1.0.8


Parallel execution of cypress tests is now supported, increasing performance on longer suites more than 2x.


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.8)

## MPyL 1.0.7


Step executors are discovered by a plugin mechanism. This allows for custom step executors to be added to the system 
without having to modify the core codebase. See the 
[steps documentation](https://vandebron.github.io/mpyl/mpyl/steps.html#how-do-i-create-my-own-custom-step)


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.7)

## MPyL 1.0.6

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.6)

## MPyL 1.0.5

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.5)

## MPyL 1.0.4


Upload assets to S3 deploy step


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.4)

## MPyL 1.0.3

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.3)

## MPyL 1.0.2


Display build and ticket info in Github PR comment.


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.2)

## MPyL 1.0.1


 - `mpyl build jenkins` uses `--follow` by default, as it it's more instructive for first time use
 - `mpyl build jenkins` has `--silent` mode, in which we block until the Jenkins build is finished but filter out the logs
 - rename hidden .mpl folder to .mpyl
 - introduce possibility to filter documentation changes from invalidation logic

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.1)

## MPyL 1.0.0


##### First stable release
This release supports both PR and release/tag builds.
MPyL now pulls in the main branch (to determine revision deltas) independently when necessary.

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.0)

