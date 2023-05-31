import time

from dagster import DagsterRunStatus
from dagster_graphql import DagsterGraphQLClient, DagsterGraphQLClientError

if __name__ == "__main__":
    client = DagsterGraphQLClient("localhost", port_number=3000)
    try:
        new_run_id: str = client.submit_job_execution(
            job_name="ci_cd_flow",
            run_config={
                "ops": {
                    "deploy_projects": {
                        "config": {
                            "simulate_deploy": False
                        }
                    },
                    "find_build_projects": {
                        "config": {
                            "find_all": True
                        }
                    },
                    "find_test_projects": {
                        "config": {
                            "find_all": True
                        }
                    },
                    "find_deploy_projects": {
                        "config": {
                            "find_all": True
                        }
                    },

                },
                "execution": {
                    "config": {
                        "multiprocess": {},
                    }
                }},
        )
        status = DagsterRunStatus.NOT_STARTED
        while status not in {DagsterRunStatus.SUCCESS, DagsterRunStatus.FAILURE, DagsterRunStatus.CANCELED}:
            status = client.get_run_status(new_run_id)
            print(f"Run status: {new_run_id} {status}")
            time.sleep(2)
        print("Run is finished")
    except DagsterGraphQLClientError as exc:
        print(exc)
        raise exc
