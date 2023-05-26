"""Filesystem related utility methods"""

import os
import shutil
from logging import Logger


def create_directory(logger: Logger, dir_name: str, overwrite=True) -> bool:
    """
    Creates a directory

    :param logger: the logger to use
    :param dir_name: the directory to create
    :param overwrite: if True, the directory will be deleted if it already exists
    :return: True if the directory was created, False otherwise
    """
    if os.path.exists(dir_name) and overwrite:
        delete_directory(logger=logger, dir_name=dir_name)

    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
        return True

    logger.warning(f"Could not create directory: '{dir_name}' already exists")
    return False


def delete_directory(logger: Logger, dir_name: str) -> bool:
    """
    Deletes a directory

    :param logger: the logger to use
    :param dir_name: the directory to delete
    :return: True if the directory was deleted, False otherwise
    """
    try:
        shutil.rmtree(dir_name)
        return True
    except OSError as exc:
        logger.warning(f'Could not delete directory: {dir_name} - {exc.strerror}')
        return False
