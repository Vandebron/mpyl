"""Utility for running commands in parallel"""
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Any, TypeVar, Iterable

T = TypeVar("T")


@dataclass(frozen=True)
class ParallelCommand:
    function: Callable
    parameters: dict[str, Any]


def run_in_parallel(
    commands: list[ParallelCommand],
    number_of_threads: int,
) -> list[T]:
    threads: list[Future] = []
    executor = ThreadPoolExecutor(max_workers=number_of_threads)
    for command in commands:
        threads.append(executor.submit(command.function, **command.parameters))

    results: list[T] = list(__flatten([thread.result() for thread in threads]))

    return results


def __flatten(object_to_flatten: Any):
    if isinstance(object_to_flatten, Iterable):
        for i in object_to_flatten:
            if isinstance(i, Iterable) and not isinstance(i, (str, bytes)):
                yield from __flatten(i)
            else:
                yield i
