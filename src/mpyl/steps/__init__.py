"""
## What is a Step?
A `Step` is a unit of execution within a pipeline run. Each step relates to one particular `mpyl.project.Stage`.
For example, there are some built in steps in the `Build` stage like `mpyl.steps.build.dockerbuild.BuildDocker` or
`mpyl.steps.build.sbt.BuildSbt`. Both of these steps compile and assemble source code into a bundle that is embedded
in a docker image.


## How do I create my own custom step?

### Before you start
A step can either be *built in* to `MPyL` or defined within the context of a particular pipeline. The latter is easier
to do and is the best option if the likelihood of the logic being of use in other contexts is small.

.. note:: The benefits of standard artifact types
   It is recommended to have your steps produce any of the standard artifact types. This allows you to benefit from
   the tooling embedded in MPyL to process them. For example: if a step in the `Test` stage produces an artifact of type
   `ArtifactType.JUNIT_TESTS`, the test results can be reported in a unified way by any of the `mpyl.reporting`
   reporters regardless of whether the tests were run by a `jest` or a `scala` test.


### Implementation

Let's assume you want to create a new step for the `Build` stage that creates a builds a `Java` maven project and embeds
it a docker image.

Implement the `Step` interface as `BuildJava(Step)`, or however you want to call it. For an example you could have
 a look at the `mpyl.steps.build.echo.BuildEcho`.

##### Important constructor properties
 - `Meta.name` is how you can refer to this step from a `project.yml`. The `mpyl.steps.steps.Steps` executor will pick
 up the `Step` implementation that has the name described in `stages.build` to execute the build step.
```yaml
name: 'javaService'
stages:
    build: 'Java Build'
description: 'A simple Java service'
```
 -  `Meta.stage` describes the `mpyl.project.Stage to which the step relates. It can only be executed in this context.
 -  `Step.produced_artifact` defines the `mpyl.steps.models.ArtifactType` that this step produces. In our example case
 this would be `mpyl.steps.models.ArtifactType.DOCKER_IMAGE`.
 - The `Step.after` is a postprocessing step, which we can set to `mpyl.steps.build.docker_after_build.AfterBuildDocker`
 in this case. It will push the image produced by this step to a registry.

##### Return type

Your step needs to return an `mpyl.steps.models.Output` object with fields that are hopefully self-explanatory.
The `produced_artifact` can be constructed with `mpyl.steps.models.input_to_artifact`. The `spec` parameter is for
specifying `ArtifactType` specific metadata, that can be picked up by another step that has `ArtifactType.DOCKER_IMAGE`
as `required_artifact`, like `mpyl.steps.deploy.kubernetes.DeployKubernetes` for example.
```python
input_to_artifact(ArtifactType.DOCKER_IMAGE, step_input, spec=DockerImageSpec(image=image_tag)
```

##### Step input
The step receives an `mpyl.steps.models.Input` for `execute`. If your step needs configuration settings, like for
example `mpyl.utilities.docker.DockerConfig`, this can be constructed from the `mpyl.steps.models.RunProperties.config`
dictionary on `mpyl.steps.models.Input.run_properties`.
Make sure to update the schema under `src/mpyl/schema/mpyl_config.schema.yml` accordingly, so that the configuration
remains type safe and mistakes are found as early as possible.

##### Registration with the executor
Importing the module in which your step is defined is enough to register it.
Steps are automatically registered with the `mpyl.steps.steps.Steps` executor via the `IPluginRegistry` metaclass.
"""
from __future__ import annotations

from dataclasses import dataclass
from logging import Logger
from typing import Optional, List

from .models import ArtifactType, Input, Output
from ..project import Stage


class IPluginRegistry(type):
    plugins: List[type] = []

    def __init__(cls, name, _bases, _attrs):
        super().__init__(cls)
        if name != "Step":
            IPluginRegistry.plugins.append(cls)


@dataclass(frozen=True)
class Meta:
    name: str
    """External, unique identifier. The step can be referred to by this name from `project.yml`"""
    description: str
    version: str
    stage: str
    """The stage that this step relates to"""

    def __str__(self) -> str:
        return f"{self.name}: {self.version}"


class Step(metaclass=IPluginRegistry):
    """Abstract base class for execution steps. Any execution step (e.g. build, test, deploy) will need to implement
    this interface.
    """

    meta: Meta
    """Information _about_ the specific instance of `Step`. For example its name, description, version or the stage
    to which it applies.
    """
    produced_artifact: ArtifactType
    """The type of the artifact produced by this step """
    required_artifact: ArtifactType
    """Is set to something other than `ArtifactType.NONE` if this step depends on an artifact produced by the execution
    of an earlier step. For example: a step in the `Deploy` stage, may need to deploy a docker image that was produced
    in the `Build` stage."""
    before: Optional[Step]
    after: Optional[Step]
    """Will be executed after completion of this step. Can be used for shared post processing steps, like pushing the
    produced docker image to a registry or filing test results."""

    def __init__(
        self,
        logger: Logger,
        meta: Meta,
        produced_artifact: ArtifactType,
        required_artifact: ArtifactType,
        before: Optional[Step] = None,
        after: Optional[Step] = None,
    ) -> None:
        self._logger = logger.getChild(meta.name.replace(" ", ""))
        self.meta = meta
        self.produced_artifact = produced_artifact
        self.required_artifact = required_artifact
        self.before = before
        self.after = after

    def execute(self, step_input: Input) -> Output:
        """Execute an individual step for a specific `project` at a specific `stage` of the pipeline.
        :param step_input: The input of the project along with its build properties and required artifact (if any).
        :return Output: The result of the execution. `success` will be `False` if any exception was thrown during
        execution.
        """
        return Output(
            success=False,
            message=f"Not implemented for {step_input.project.name}",
            produced_artifact=None,
        )
