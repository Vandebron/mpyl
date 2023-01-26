from __future__ import annotations

from logging import Logger
from typing import List, Optional

from .models import Meta, Input, Output, ArtifactType


class IPluginRegistry(type):
    plugin_registries: List[type] = []

    def __init__(cls, name):
        super().__init__(cls)
        if name != 'Step':
            IPluginRegistry.plugin_registries.append(cls)


class Step(metaclass=IPluginRegistry):
    meta: Meta
    produced_artifact: ArtifactType
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
        return Output(success=False, message=f"Not implemented for {step_input.project.name}", produced_artifact=None)
