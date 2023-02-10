import dagster
from dagster import job, op, DynamicOut, DynamicOutput, get_dagster_logger, Output, Failure
from dagster import DagsterInstance, execute_job, reconstructable


@op
def log_hello(hello_input: str):
    """
    An op definition. This example op is idempotent and outputs the input but logs the input to the console.

    """
    get_dagster_logger().info(f"Found something to log: {hello_input}")
    return hello_input


@op
def hello():
    """
    An op definition. This example op outputs a single string.

    For more hints about writing Dagster ops, see our documentation overview on Ops:
    https://docs.dagster.io/concepts/ops-jobs-graphs/ops
    """
    return "Hello, Dagster!"


@job
def say_hello_job_logging():
    """
    A job definition. This example job has two serially dependent operations.

    For more hints on writing Dagster jobs, see our documentation overview on Jobs:
    https://docs.dagster.io/concepts/ops-jobs-graphs/jobs-graphs
    """
    log_hello(hello())


if __name__ == "__main__":
    result = say_hello_job_logging.execute_in_process()
    print(f"Result: {result.success}")
