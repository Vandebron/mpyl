""" This module is called on to push your kubernetes manifest to a(n) (argo) repo during the `mpyl.steps.deploy step."""

import shutil
from logging import Logger
from pathlib import Path
from tempfile import TemporaryDirectory

from .deploy_config import get_namespace
from .rancher import ClusterConfig
from ....project import Target
from ....steps import Input, Output
from ....utilities.repo import RepoConfig, Repository
from ....utilities.subprocess import custom_check_output


def push_manifest_to_repo(
    logger: Logger,
    step_input: Input,
    rancher_config: ClusterConfig,
    manifest_path: Path,
) -> Output:
    git_config = step_input.run_properties.config["vcs"]["argoRepository"]
    if not git_config:
        raise ValueError("No argocd repository configured")
    argocd_repo_config = RepoConfig.from_git_config(git_config=git_config)
    with TemporaryDirectory() as tmp_repo_dir:
        with Repository.from_clone(
            config=argocd_repo_config, repo_path=Path(tmp_repo_dir)
        ) as argo_repo:
            branch = "feature/TECH-610-implement-argocd-2"  # This can be main later
            if argo_repo.local_branch_exists(branch_name=branch):
                argo_repo.delete_local_branch(
                    branch_name=branch
                )  # To enforce latest version of branch
            branch_exists = argo_repo.remote_branch_exists(branch_name=branch)
            if branch_exists:
                argo_repo.checkout_branch(branch_name=branch)
            else:
                argo_repo.create_branch(branch_name=branch)

            folder_name = __get_folder_name(step_input=step_input)
            new_file_path = Path(
                tmp_repo_dir,
                folder_name,
                get_namespace(step_input.run_properties, step_input.project),
                step_input.project.name,
                manifest_path.name,
            )
            shutil.copytree(
                src=manifest_path.parent,
                dst=new_file_path.parent,
                dirs_exist_ok=True,
            )

            #  validate manifest
            validate_command = (
                f"kubectl apply -f {manifest_path} --context {rancher_config.context} "
                f"--dry-run=server"
            )
            validation_result = custom_check_output(logger, validate_command)

            if not validation_result.success:
                return validation_result

            if argo_repo.has_changes:
                argo_repo.stage(".")
                argo_repo.commit(
                    f"Committing new manifest for project {step_input.project.name} on environment {folder_name}"
                )
                argo_repo.push(branch)

                return Output(success=True, message="Manifest pushed to argocd repo")
            return Output(success=True, message="No changes in manifest detected")


def __get_folder_name(step_input: Input) -> str:
    if step_input.run_properties.target in (
        Target.PULL_REQUEST_BASE,
        Target.PULL_REQUEST,
    ):
        return "test"
    return step_input.run_properties.target.name.lower()
