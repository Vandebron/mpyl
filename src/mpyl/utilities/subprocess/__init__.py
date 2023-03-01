"""Utilities related to launching a subprocess"""

import subprocess
from logging import Logger

from ...steps.models import Output


def custom_check_output(logger: Logger, command: list[str], pipe_output=True, shell=False) -> Output:
    command_argument = ' '.join(command)
    logger.info(f"Executing: '{command_argument}'")
    try:
        output = subprocess.run(
            command,
            stdout=subprocess.PIPE if pipe_output else None,
            stderr=subprocess.PIPE if pipe_output else None,
            shell=shell,
            check=True,
        )
        if output.returncode == 0:
            if pipe_output:
                message = output.stdout.decode()
                logger.info(message)

            return Output(success=True, message='Subprocess executed successfully')

    except subprocess.CalledProcessError as exc:
        message = f"'{command_argument}': failed with return code: {exc.returncode} err: {exc.stderr.decode()}"
        logger.warning(message, exc_info=True)

    return Output(success=False, message='Subprocess failed')
