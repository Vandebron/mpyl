from logging import Logger
from typing import List

from .models import Meta, Input, Output


class IPluginRegistry(type):
    plugin_registries: List[type] = list()

    def __init__(cls, name, bases, attrs):
        super().__init__(cls)
        if name != 'Step':
            IPluginRegistry.plugin_registries.append(cls)


class Step(object, metaclass=IPluginRegistry):
    meta: Meta

    def __init__(self, logger: Logger, meta: Meta) -> None:
        self._logger = logger.getChild(meta.name.replace(' ', ''))
        self.meta = meta

    def execute(self, step_input: Input) -> Output:
        return Output(success=False, message="Not implemented")
