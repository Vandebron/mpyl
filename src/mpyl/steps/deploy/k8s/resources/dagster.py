def to_user_code_values(
    env_vars: dict,
    env_secrets: dict,
    project_name: str,
    suffix: str,
    tag: str,
    repo_file_path: str,
) -> dict:
    return {
        "deployments": [
            {
                "dagsterApiGrpcArgs": ["--python-file", repo_file_path],
                "env": env_vars,
                "envSecrets": env_secrets,
                "image": {
                    "pullPolicy": "Always",
                    "imagePullSecrets": [{"name": "bigdataregistry"}],
                    "tag": tag,
                    "repository": f"bigdataregistry.azurecr.io/{project_name}",
                },
                "includeConfigInLaunchedRuns": {"enabled": True},
                "name": f"{project_name}{suffix}",
                "port": 3030,
            }
        ]
    }


def to_grpc_server_entry(host: str, name: str, port: int) -> dict:
    return {"grpc_server": {"host": host, "location_name": name, "port": port}}
