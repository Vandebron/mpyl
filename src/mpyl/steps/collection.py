"""A collection of all available step executors."""
import importlib
import importlib.util
import pkgutil
from logging import Logger
from typing import Optional

from . import Step, IPluginRegistry
from ..project import Stage, Project
from ..steps import ArtifactType


class StepsCollection:
    _step_executors: set[Step]

    def __init__(self, logger: Logger) -> None:
        self._step_executors = set()
        package = "mpyl.steps"
        local_package = f"src.{package}"
        default_library_location, alternative_library_location = (
            (local_package, package)
            if importlib.util.find_spec("src")
            else (package, local_package)
        )
        location = default_library_location

        self.__load_steps_in_module(logger, ".", location)

        self.__load_steps_in_module(logger, ".", alternative_library_location)
        location = alternative_library_location

        logger.debug(f"Loaded {len(IPluginRegistry.plugins)} executors from {location}")
        if not IPluginRegistry.plugins:
            logger.warning(f"No executors found. Check {location} for plugins.")

        for plugin in IPluginRegistry.plugins:
            step_instance: Step = plugin(logger)
            meta = step_instance.meta
            logger.debug(
                f"{meta.name} for stage {meta.stage} registered. Description: {meta.description}"
            )
            self._step_executors.add(step_instance)

    @staticmethod
    def __load_steps_in_module(
        logger: Logger, module_root: str, base_path: str
    ) -> None:
        try:
            module = importlib.import_module(module_root, base_path)

            module_names = [
                modname
                for _, modname, _ in pkgutil.walk_packages(
                    path=module.__path__,
                    prefix=module.__name__ + ".",
                    onerror=lambda x: None,
                )
            ]

            for modname in module_names:
                importlib.import_module(modname)
            return None
        except ModuleNotFoundError as exc:
            logger.debug(f"Module {module_root} at {base_path} not found {exc}")
            return None

    def get_stage_for_producing_artifact(
        self, project: Project, artifact: ArtifactType
    ) -> Optional[str]:
        for stage, step in project.stages.all().items():
            if step is not None:
                executor = self.get_executor(Stage(stage, "icon"), step)
                if executor is not None:
                    if executor.produced_artifact == artifact:
                        return stage
        return None

    def get_executor(self, stage: Stage, step_name: str) -> Optional[Step]:
        executors = filter(
            lambda e: step_name == e.meta.name and e.meta.stage == stage.name,
            self._step_executors,
        )
        return next(executors, None)
