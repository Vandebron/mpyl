from dagster import job, repository, op


@op
def op_hello():
    print("Hello World!")


@job
def hello_job():
    op_hello()


@repository
def my_repository():
    return [
        hello_job
    ]
