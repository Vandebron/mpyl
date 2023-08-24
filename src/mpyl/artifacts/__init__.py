from pathlib import Path

from ..project import load_project
from ..utilities.repo import Repository


class Artifacts:
    repo: Repository

    def __init__(self, repo: Repository):
        self.repo = repo

    def get_build_artifacts_paths(self) -> list[Path]:
        found_projects: list[Path] = [
            Path(
                load_project(
                    self.repo.root_dir, Path(project_path), strict=False
                ).target_path
            )
            for project_path in self.repo.find_projects()
        ]

        return [path for path in found_projects if path.exists()]

    @staticmethod
    def pull(branch: str) -> None:
        print("inside pull: ", branch)
        # find branch in repo
        # pull if exists

    def push(self, branch: str) -> None:
        artifacts = self.get_build_artifacts_paths()
        print("inside push: ", artifacts)
        print("inside push: ", branch)
        # create branch if not exists
        # checkout branch
        # commit artifacts to branch
