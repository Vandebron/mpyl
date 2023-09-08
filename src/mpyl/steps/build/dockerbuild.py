"""
### Docker build step
This is a step that builds a docker image from its specification in Dockerfile-mpl.

### Dockerfile-mpl

This is a [multi-stage](https://docs.docker.com/build/building/multi-stage/) docker file, that has at
least a `builder` and in most cases also a `tester` stage.
`WORKDIR` needs to be identical to root path of the sourcecode.

The `tester` stage needs to run the unittests and write the results (
in [Junit XML format](https://llg.cubic.org/docs/junit/))
to a folder named `$WORKDIR/target/test-reports/`.

#### Example Dockerfile-mpl
```docker
.. include:: ../../../../tests/projects/service/deployment/Dockerfile-mpl
```
"""

from logging import Logger

from .docker_after_build import AfterBuildDocker
from .. import Step, Meta
from ..models import Input, Output, ArtifactType, input_to_artifact
from ...constants import BUILD_ARTIFACTS_FOLDER
from ...project import Stage
from ...utilities.docker import (
    DockerConfig,
    build,
    docker_image_tag,
    docker_file_path,
    login,
    DockerImageSpec,
)

DOCKER_IGNORE_DEFAULT = ["**/target/*", f"**/{BUILD_ARTIFACTS_FOLDER}/*"]


class BuildDocker(Step):
    def __init__(self, logger: Logger) -> None:
        super().__init__(
            logger=logger,
            meta=Meta(
                name="Docker Build",
                description="Build docker image",
                version="0.0.1",
                stage=Stage.BUILD,
            ),
            produced_artifact=ArtifactType.DOCKER_IMAGE,
            required_artifact=ArtifactType.NONE,
            after=AfterBuildDocker(logger=logger),
        )

    def execute(self, step_input: Input) -> Output:
        docker_config = DockerConfig.from_dict(step_input.run_properties.config)
        build_target = docker_config.build_target
        if not build_target:
            raise ValueError("docker.buildTarget must be specified")

        image_tag = docker_image_tag(step_input)
        dockerfile = docker_file_path(
            project=step_input.project, docker_config=docker_config
        )

        if not step_input.dry_run:
            # log in to registry, because we may need to pull in a base image
            login(logger=self._logger, docker_config=docker_config)

        success = build(
            logger=self._logger,
            root_path=docker_config.root_folder,
            file_path=dockerfile,
            image_tag=image_tag,
            target=build_target,
            docker_config=docker_config,
        )
        artifact = input_to_artifact(
            ArtifactType.DOCKER_IMAGE, step_input, spec=DockerImageSpec(image=image_tag)
        )

        with open(".dockerignore", "w+", encoding="utf-8") as ignore_file:
            contents = "\n".join(DOCKER_IGNORE_DEFAULT)
            ignore_file.write(contents)

        if success:
            return Output(
                success=True,
                message=f"Built {step_input.project.name}",
                produced_artifact=artifact,
            )

        return Output(
            success=False,
            message=f"Failed to build docker image for {step_input.project.name}",
            produced_artifact=None,
        )
