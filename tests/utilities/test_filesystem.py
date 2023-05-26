import logging
from unittest.mock import patch
import unittest

from mpyl.utilities.filesystem import create_directory, delete_directory


class TestFileSystem(unittest.TestCase):

    @patch('mpyl.utilities.filesystem.os.makedirs')
    @patch('mpyl.utilities.filesystem.os.path.exists')
    def test_create_directory_should_succeed(self, mock_path_exists, mock_makedirs):
        mock_path_exists.return_value = False
        is_created = create_directory(logger=logging.getLogger(), dir_name="tmp")
        mock_makedirs.assert_called_once()
        assert is_created

    @patch('mpyl.utilities.filesystem.os.makedirs')
    @patch('mpyl.utilities.filesystem.os.path.exists')
    def test_create_directory_should_fail(self, mock_path_exists, mock_makedirs):
        mock_path_exists.return_value = True
        is_created = create_directory(logger=logging.getLogger(), dir_name="tmp", overwrite=False)
        mock_makedirs.assert_not_called()
        assert not is_created

    @patch('mpyl.utilities.filesystem.shutil.rmtree')
    def test_delete_directory_should_succeed(self, mock_rmtree):
        is_deleted = delete_directory(logger=logging.getLogger(), dir_name="tmp")
        mock_rmtree.assert_called_once()
        assert is_deleted

    @patch('mpyl.utilities.filesystem.shutil.rmtree')
    def test_delete_directory_should_fail(self, mock_rmtree):
        mock_rmtree.side_effect = OSError()
        is_deleted = delete_directory(logger=logging.getLogger(), dir_name="tmp")
        assert not is_deleted

