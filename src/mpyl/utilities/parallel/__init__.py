"""Utility tool for running commands in parallel"""

from concurrent.futures import ProcessPoolExecutor, Future
from dataclasses import dataclass
from typing import Callable, Any, TypeVar, Type, Iterable

T = TypeVar("T")


@dataclass(frozen=True)
class ParallelObject:
    function: Callable
    parameters: dict[Any, Any]


def run_in_parallel(
    commands: list[ParallelObject],
    number_of_threads: int,
    _return_type: Type[T],
) -> list[T]:
    threads: list[Future] = []
    executor = ProcessPoolExecutor(max_workers=number_of_threads)
    for command in commands:
        threads.append(executor.submit(command.function, **command.parameters))

    results: list[T] = list(__flatten([thread.result() for thread in threads]))

    return results


def __flatten(object_to_flatten: Any):
    for i in object_to_flatten:
        if isinstance(i, Iterable) and not isinstance(i, (str, bytes)):
            yield from __flatten(i)
        else:
            yield i
