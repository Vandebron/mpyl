"""A collection of all available step executors."""
import importlib
import pkgutil
from logging import Logger
from typing import Optional

from . import Step, IPluginRegistry
from ..project import Stage


class StepsCollection:
    _step_executors: set[Step]

    def __init__(self, logger: Logger, base_path: Optional[str] = None) -> None:
        self._step_executors = set()
        self._base_path = base_path
        self.__load_steps_in_module('.')

        for plugin in IPluginRegistry.plugins:
            step_instance: Step = plugin(logger)
            meta = step_instance.meta
            logger.debug(f"{meta.name} for stage {meta.stage} registered. Description: {meta.description}")
            self._step_executors.add(step_instance)

    def __load_steps_in_module(self, module_root: str):
        module = importlib.import_module(module_root, f'{self._base_path + "." if self._base_path else ""}mpyl.steps')
        for _, modname, _ in pkgutil.walk_packages(path=module.__path__, prefix=module.__name__ + '.',
                                                   onerror=lambda x: None):
            importlib.import_module(modname)

    def get_executor(self, stage: Stage, step_name: str) -> Optional[Step]:
        executors = filter(lambda e: step_name == e.meta.name and e.meta.stage == stage, self._step_executors)
        return next(executors, None)
