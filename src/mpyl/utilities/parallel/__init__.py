"""Utility tool for running commands in parallel"""

import itertools
from asyncio import Future
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, Any


def run_in_parallel(
    commands: list[dict[Callable, dict[str, Any]]], number_of_threads: int
) -> list[str]:
    threads: list[Future] = []
    executor = ProcessPoolExecutor(max_workers=number_of_threads)
    for command in commands:
        for function, args in command.items():
            threads.append(executor.submit(function, **args))

    results: list[str] = list(
        itertools.chain.from_iterable([thread.result() for thread in threads])
    )

    return results
