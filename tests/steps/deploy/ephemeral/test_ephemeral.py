import os
from pathlib import Path

from mpyl.project import load_project
from mpyl.steps.models import Input
from mpyl.utilities.docker import write_env_to_file
from tests import root_test_path
from tests.test_resources import test_data


class TestEphemeral:
    resource_path = root_test_path / 'projects' / 'ephemeral' / 'deployment'

    def test_replace_default_with_none(self):
        step_input = Input(load_project(self.resource_path, Path('project.yml'), True), test_data.RUN_PROPERTIES, None)
        assert len(step_input.project.deployment.properties.env) == 4
        write_env_to_file(step_input.project, test_data.RUN_PROPERTIES)
        env_file_name = step_input.run_properties.config['docker']['envFileName']

        with open(env_file_name, 'r') as file:
            envs = file.readlines()
            assert len(envs) == 4

        os.remove(env_file_name)
