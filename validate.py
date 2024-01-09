import concurrent.futures
import os
import shutil
import subprocess
import time
from concurrent.futures import Future
from dataclasses import dataclass

from rich.console import RenderableType, Console
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table

from src.mpyl.utilities.logging import try_parse_ansi

COMMANDS = [
    "pipenv run format",
    "pipenv run lint",
    "pipenv run lint-test",
    "pipenv run check-types",
    "pipenv run check-types-test",
    "pipenv run test",
]


def run_command(command: str):
    try:
        result = subprocess.run(
            f"PIPENV_QUIET=1 {command}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr

        return JobResult(command, stdout, stderr, exit_code)

    except Exception as e:
        return JobResult(command, "", f"Error running command {command}: {str(e)}", 1)


@dataclass
class Job:
    command: str
    future: Future


@dataclass
class JobResult:
    command: str
    stdout: str
    stderr: str
    exit_code: int


def trim(error_message: str) -> str:
    lines = error_message.splitlines()
    if len(lines) <= 10:
        return "\n".join(lines).strip()

    return "\n".join(error_message.splitlines()[-10:])


def to_row(job: Job) -> list[RenderableType]:
    status = Spinner("clock")
    output = ""
    if job.future.done():
        result: JobResult = job.future.result()
        output = result.stdout if result.stdout else result.stderr
        status = f":green_heart:" if result.exit_code == 0 else f":broken_heart:"
    return [
        status,
        f"[italic]{job.command.replace('pipenv run ', '')}",
        try_parse_ansi(trim(output).strip()),
    ]


def create_progress_table(jobs: list[Job]) -> Table:
    table = Table(
        *["Status", "Command", "Message"],
        title="Validate sourcecode",
    )
    for job in jobs:
        table.add_row(*to_row(job))

    return table


def all_tasks_done(jobs_to_finish: list[Job]) -> bool:
    return all([job.future.done() for job in jobs_to_finish])


def all_tasks_success(results: list[JobResult]) -> bool:
    return all([job.exit_code == 0 for job in results])


def play_sound(success: bool):
    if shutil.which("afplay") is None:
        Console().bell()
        return

    sound = "Glass.aiff" if success else "Sosumi.aiff"
    os.system(f"afplay /System/Library/Sounds/{sound}")


with concurrent.futures.ThreadPoolExecutor(max_workers=len(COMMANDS)) as executor:
    jobs: list[Job] = [Job(cmd, executor.submit(run_command, cmd)) for cmd in COMMANDS]
    with Live(create_progress_table(jobs), refresh_per_second=4) as live:
        while not all_tasks_done(jobs):
            time.sleep(0.2)
            live.update(create_progress_table(jobs))
        play_sound(all_tasks_success([job.future.result() for job in jobs]))
