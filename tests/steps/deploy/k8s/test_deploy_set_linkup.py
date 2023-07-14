from src.mpyl.steps.deploy.k8s import substitute_namespaces, ProjectName


class TestDeploySetLinkup:
    project1 = ProjectName("energy-dashboard", "webapps")
    project2 = ProjectName("nginx", "webapps")
    project3 = ProjectName("main-website", "webapps")

    projects_to_deploy = {project1, project2}
    all_projects = {project1, project2, project3}

    def test_should_link_up_deploy_set(self):
        envs = {
            "KEY_1": "http://energy-dashboard.{namespace}.svc.cluster.local:4082",
            "KEY_2": "http://main-website.{namespace}.svc.cluster.local:4050",
            "KEY_3": "test-{PR-NUMBER}.play-backend.zonnecollectief.nl",
            "KEY_4": "abcd",
        }

        expected_envs = {
            "KEY_1": "http://energy-dashboard.pr-1234.svc.cluster.local:4082",
            "KEY_2": "http://main-website.webapps.svc.cluster.local:4050",
            "KEY_3": "test-1234.play-backend.zonnecollectief.nl",
            "KEY_4": "abcd",
        }

        replaced_envs = substitute_namespaces(
            envs, self.all_projects, self.projects_to_deploy, 1234
        )

        assert replaced_envs == expected_envs

    def test_should_link_up_to_base_services_if_not_pr(self):
        envs = {
            "KEY_1": "http://energy-dashboard.{namespace}.svc.cluster.local:4082",
            "KEY_2": "http://main-website.{namespace}.svc.cluster.local:4050",
            "KEY_3": "abcd",
        }
        expected_envs = {
            "KEY_1": "http://energy-dashboard.webapps.svc.cluster.local:4082",
            "KEY_2": "http://main-website.webapps.svc.cluster.local:4050",
            "KEY_3": "abcd",
        }
        replaced_envs = substitute_namespaces(
            envs, self.all_projects, self.projects_to_deploy, None
        )

        assert replaced_envs == expected_envs

    def test_should_replace_namespace_with_subproject(self):
        envs = {
            "KEY_1": "http://energy-dashboard.{namespace}.svc.cluster.local:4082",
            "KEY_2": "http://main-website.{namespace=fallback}.svc.cluster.local:4050",
        }

        expected_envs = {
            "KEY_1": "http://energy-dashboard.pr-1234.svc.cluster.local:4082",
            "KEY_2": "http://main-website.fallback.svc.cluster.local:4050",
        }

        replaced_envs = substitute_namespaces(
            envs, self.all_projects, self.projects_to_deploy, 1234
        )

        assert replaced_envs == expected_envs
