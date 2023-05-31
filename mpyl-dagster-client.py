import subprocess
import sys
import threading
import time

from dagster import DagsterRunStatus
from dagster_graphql import DagsterGraphQLClient, DagsterGraphQLClientError


def log_subprocess_output(pipe, stop_event):
    for line in iter(pipe.readline, b''):  # b'\n'-separated lines
        print(f'{event.is_set()}' + line.decode(sys.stdout.encoding).replace('\n', ''))
        if stop_event.is_set():
            print("Event set, stopping logs")
            break


def start_run():
    time.sleep(5)
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


if __name__ == "__main__":
    with subprocess.Popen(['dagster', 'dev', '-f', 'mpyl-dagster-example.py'], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, shell=False) as dagster:
        event = threading.Event()
        t = threading.Thread(target=start_run)

        log_thread = threading.Thread(target=log_subprocess_output, args=[dagster.stdout, event])
        log_thread.start()
        t.start()
        print("joining dagster thread")
        t.join()

        print("joining logging thread")
        event.set()
        log_thread.join()
        print("killing dagster")
        dagster.terminate()
    sys.exit()
