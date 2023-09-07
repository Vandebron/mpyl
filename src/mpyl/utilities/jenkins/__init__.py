"""Utility functions for Jenkins"""
from dataclasses import dataclass

from ...project import Target


@dataclass(frozen=True)
class JenkinsConfig:
    url: str
    pipelines: dict[str, str]
    default: str

    @staticmethod
    def from_config(values: dict):
        jenkins_config = values.get("jenkins")
        if not jenkins_config:
            raise KeyError("jenkins should be defined in config")
        return JenkinsConfig(
            url=jenkins_config["url"],
            pipelines=jenkins_config["pipelines"],
            default=jenkins_config["defaultPipeline"],
        )

    @property
    def default_pipeline(self) -> str:
        return self.pipelines[self.default]


@dataclass(frozen=True)
class Pipeline:
    target: Target
    tag: str
    url: str
    pipeline: str
    body: str
    jenkins_config: JenkinsConfig

    def _to_path(self):
        return f"PR-{self.tag}" if self.target == Target.PULL_REQUEST else self.tag

    def pipeline_location(self) -> str:
        return f'{self.jenkins_config.url}job/{self.jenkins_config.pipelines[self.pipeline].replace(" ", "%20")}/'

    def job_location(self) -> str:
        return f"{self.pipeline_location}job/{self._to_path()}/"

    def job_name(self) -> str:
        return f"{self.jenkins_config.pipelines[self.pipeline]}/{self._to_path()}"

    def build_location(self) -> str:
        return f"{self.pipeline_location()}view/change-requests/job/{self._to_path()}/lastBuild/"

    def human_readable(self) -> str:
        return f"[link={self.url}]#{self.tag}[/link]"
