""" Model representation of run-specific configuration. """

import pkgutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Dict

from ruamel.yaml import YAML, yaml_object  # type: ignore

from ..project import Project, Stage, Target
from ..validation import validate

yaml = YAML()


@dataclass(frozen=True)
class VersioningProperties:
    revision: str
    branch: Optional[str]
    pr_number: Optional[int]
    tag: Optional[str]

    def validate(self) -> Optional[str]:
        if not self.pr_number and not self.tag:
            return "Either pr_number or tag need to be set"
        return None

    @property
    def identifier(self) -> str:
        return self.tag if self.tag else f"pr-{self.pr_number}"


@dataclass(frozen=True)
class RunContext:
    build_id: str
    """Uniquely identifies the run. Typically a monotonically increasing number"""
    run_url: str
    """Link back to the run executor"""
    change_url: str
    """Link to changes"""
    tests_url: str
    """Link to test results"""
    user: str
    """Name of of the user that triggered the run"""
    user_email: Optional[str]
    """Email of of the user that triggered the run"""

    @staticmethod
    def from_configuration(run_details: Dict):
        return RunContext(
            build_id=run_details["id"],
            run_url=run_details["run_url"],
            change_url=run_details["change_url"],
            tests_url=run_details["tests_url"],
            user=run_details["user"],
            user_email=run_details["user_email"],
        )


@dataclass(frozen=True)
class ConsoleProperties:
    log_level: str
    show_paths: bool
    width: Optional[int]

    @staticmethod
    def from_configuration(build_config: Dict):
        console_config = build_config["console"]
        width = console_config.get("width", 130)
        return ConsoleProperties(
            log_level=console_config.get("logLevel", "INFO"),
            show_paths=console_config.get("showPaths", False),
            width=None if width == 0 else width,
        )


@yaml_object(yaml)
@dataclass(frozen=True)
class RunProperties:
    """Contains information that is specific to a particular run of the pipeline"""

    details: RunContext
    """Run specific details"""
    target: Target
    """The deploy target"""
    versioning: VersioningProperties
    config: dict
    """Globally specified configuration, to be used by specific steps. Complies with the schema as
    specified in `mpyl_config.schema.yml`
     """
    console: ConsoleProperties
    """Settings for the console output"""

    @staticmethod
    def for_local_run(
        config: Dict, revision: str, branch: Optional[str], tag: Optional[str]
    ):
        return RunProperties(
            details=RunContext("", "", "", "", "", None),
            target=Target.PULL_REQUEST,
            versioning=VersioningProperties(revision, branch, 123, tag),
            config=config,
            console=ConsoleProperties("INFO", True, 130),
        )

    @staticmethod
    def from_configuration(run_properties: Dict, config: Dict):
        build_dict = pkgutil.get_data(__name__, "../schema/run_properties.schema.yml")

        if build_dict:
            validate(run_properties, build_dict.decode("utf-8"))

        build = run_properties["build"]
        versioning_config = build["versioning"]

        tag: Optional[str] = versioning_config.get("tag")
        pr_from_config: Optional[str] = versioning_config.get("pr_number")
        pr_num: Optional[int] = (
            None if tag else (int(pr_from_config) if pr_from_config else None)
        )

        versioning = VersioningProperties(
            revision=versioning_config["revision"],
            branch=versioning_config["branch"],
            pr_number=pr_num,
            tag=tag,
        )
        console = ConsoleProperties.from_configuration(build)

        return RunProperties(
            details=RunContext.from_configuration(build["run"]),
            target=Target(
                build["parameters"].get("deploy_target", None)
                or Target.PULL_REQUEST.value  # pylint: disable=no-member
            ),
            versioning=versioning,
            config=config,
            console=console,
        )


@yaml_object(yaml)
@dataclass(frozen=True)
class ArtifactType(Enum):
    def __eq__(self, other):
        return self.value == other.value

    @classmethod
    def from_yaml(cls, _, node):
        return ArtifactType(int(node.value.split("-")[1]))

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_scalar(
            "!ArtifactType",
            f"{node._name_}-{node._value_}",  # pylint: disable=protected-access
        )

    DOCKER_IMAGE = 1
    """A docker image"""
    JUNIT_TESTS = 2
    """A test suite in junit compatible `.xml` format"""
    DEPLOYED_HELM_APP = 3
    """A helm chart deployed to kubernetes"""
    NONE = 4


@yaml_object(yaml)
@dataclass(frozen=True)
class Artifact:
    artifact_type: ArtifactType
    revision: str
    producing_step: str
    spec: dict


@yaml_object(yaml)
@dataclass(frozen=True)
class Input:
    project: Project
    run_properties: RunProperties
    """Run specific properties"""
    required_artifact: Optional[Artifact] = None
    dry_run: bool = False


@yaml_object(yaml)
@dataclass()
class Output:
    success: bool
    message: str
    produced_artifact: Optional[Artifact] = None

    @staticmethod
    def path(target_path: str, stage: Stage):
        return Path(target_path, f"{stage.name}.yml")

    def write(self, target_path: str, stage: Stage):
        Path(target_path).mkdir(parents=True, exist_ok=True)
        with Output.path(target_path, stage).open(mode="w+", encoding="utf-8") as file:
            yaml.dump(self, file)

    @staticmethod
    def try_read(target_path: str, stage: Stage):
        path = Output.path(target_path, stage)
        if path.exists():
            with open(path, encoding="utf-8") as file:
                return yaml.load(file)
        return None


def input_to_artifact(artifact_type: ArtifactType, step_input: Input, spec: dict):
    return Artifact(
        artifact_type=artifact_type,
        revision=step_input.run_properties.versioning.revision,
        producing_step=step_input.project.name,
        spec=spec,
    )
