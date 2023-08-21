"""Utilities related to launching a subprocess"""

import subprocess
from logging import Logger
from typing import Union

from ...steps.models import Output


def custom_check_output(
    logger: Logger, command: Union[str, list[str]], capture_stdout: bool = False
) -> Output:
    """
    Wrapper around subprocess.Popen
    ⚠️ Using this function implies an implicit runtime OS dependency.
    Avoid this if at all possible. For example, to run docker commands, use the bundled docker client (python-on-whales)
    which makes the dependency on docker explicit and adds a lot of convenience methods.
    """
    if isinstance(command, str):
        command = command.split(" ")

    command_argument = " ".join(command)
    logger.info(f"Executing: '{command_argument}'")
    try:
        if capture_stdout:
            out = subprocess.check_output(command, stderr=subprocess.STDOUT).decode(
                "utf-8"
            )
            return Output(success=True, message=out)

        with subprocess.Popen(command, stdout=subprocess.PIPE, text=True) as process:
            if not process.stdout:
                raise RuntimeError(
                    f"Process {command_argument} does not have an stdout"
                )

            for line in iter(process.stdout.readline, ""):
                if line:
                    print(line.rstrip())
                if process.poll() is not None:
                    break
            success = process.wait() == 0
            if not success:
                logger.warning(
                    "Subprocess failed" + f" with {process.stderr.read()}"
                    if process.stderr
                    else ""
                )
                return Output(success=False, message="Subprocess failed")

            return Output(success=True, message="Subprocess executed successfully")

    except subprocess.CalledProcessError as exc:
        logger.warning(
            f"'{command_argument}': failed with return code: {exc.returncode} err: "
            f"{exc.stderr.decode() if exc.stderr else 'No stderr output'}",
            exc_info=True,
        )

    except FileNotFoundError:
        logger.warning(f"'{command_argument}: file not found", exc_info=True)

    return Output(success=False, message="Subprocess failed")
