# Release notes

## MPyL 1.0.11

#### Highlights

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

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.11)

## MPyL 1.0.10

#### Highlights

#### Support for service monitor
The prometheus [ServiceMonitor](https://doc.crds.dev/github.com/prometheus-operator/kube-prometheus/monitoring.coreos.com/ServiceMonitor/v1@v0.7.0)
CRD and a corresponding [PrometheusRule](https://doc.crds.dev/github.com/prometheus-operator/kube-prometheus/monitoring.coreos.com/PrometheusRule/v1@v0.7.0)
are deployed whenever the `metrics` field is defined in `project.yml`


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.10)

## MPyL 1.0.9

#### Highlights

##### Support for reference environment variables
Support for reference environment variables. All standard types: `secretkeyref`, `fieldRef` and `resourceFieldRef` are 
support. This allows one to reference secrets, fields and resource fields from other resources in the same namespace.

##### Repo command
`mpyl repo` is new command group with the following subcommands:

 - `status` shows the status of the repository in terms of branch checked out, revision and revisions since branching off from base (main/master).
 - `init` allows you to initialize the local repository to prepare it for use with MPyL PR builds.


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.9)

## MPyL 1.0.8

#### Highlights

Parallel execution of cypress tests is now supported, increasing performance on longer suites more than 2x.


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.8)

## MPyL 1.0.7

#### Highlights

Step executors are discovered by a plugin mechanism. This allows for custom step executors to be added to the system 
without having to modify the core codebase. See the 
[steps documentation](https://vandebron.github.io/mpyl/mpyl/steps.html#how-do-i-create-my-own-custom-step)


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.7)

## MPyL 1.0.6

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.6)

## MPyL 1.0.5

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.5)

## MPyL 1.0.4

#### Highlights

Upload assets to S3 deploy step


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.4)

## MPyL 1.0.3

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.3)

## MPyL 1.0.2

#### Highlights

Display build and ticket info in Github PR comment.


Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.2)

## MPyL 1.0.1

#### Highlights

 - `mpyl build jenkins` uses `--follow` by default, as it it's more instructive for first time use
 - `mpyl build jenkins` has `--silent` mode, in which we block until the Jenkins build is finished but filter out the logs
 - rename hidden .mpl folder to .mpyl
 - introduce possibility to filter documentation changes from invalidation logic

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.1)

## MPyL 1.0.0

#### Highlights

##### First stable release
This release supports both PR and release/tag builds.
MPyL now pulls in the main branch (to determine revision deltas) independently when necessary.

Details on [Github](https://github.com/Vandebron/mpyl/releases/tag/1.0.0)

