""" Abstract base class for execution steps. Any execution step (e.g. build, test, deploy) will need to implement
this class.
"""

from __future__ import annotations

from logging import Logger
from typing import List, Optional

from .models import Meta, Input, Output, ArtifactType


class IPluginRegistry(type):
    plugin_registries: List[type] = []

    def __init__(cls, name, _bases, _attrs):
        super().__init__(cls)
        if name != 'Step':
            IPluginRegistry.plugin_registries.append(cls)


class Step(metaclass=IPluginRegistry):
    """ Information and execution of a single building step inside the pipeline. """
    meta: Meta
    """Information _about_ the specific instance of `Step`. For example its name, description, version or the stage
    to which it applies.
    """
    produced_artifact: ArtifactType
    """ The type of the artifact produced by this step """
    required_artifact: ArtifactType
    before: Optional[Step]
    after: Optional[Step]

    def __init__(self, logger: Logger, meta: Meta, produced_artifact: ArtifactType,
                 required_artifact: ArtifactType, before: Optional[Step] = None, after: Optional[Step] = None) -> None:
        self._logger = logger.getChild(meta.name.replace(' ', ''))
        self.meta = meta
        self.produced_artifact = produced_artifact
        self.required_artifact = required_artifact
        self.before = before
        self.after = after

    def execute(self, step_input: Input) -> Output:
        """ Execute an individual step for a specific `project` at a specific `stage` of the pipeline.
        :param step_input: The input of the project along with its build properties and required artifact (if any).
        :return Output: The result of the execution. `success` will be `False` if any exception was thrown during
        execution.
        """
        return Output(success=False, message=f"Not implemented for {step_input.project.name}", produced_artifact=None)
