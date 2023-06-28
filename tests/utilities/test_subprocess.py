import logging

from src.mpyl.utilities.subprocess import custom_check_output


class TestSubProcess:
    def test_should_capture_output(self):
        output = custom_check_output(logging.getLogger(), "ls -la")
        assert output.success

    def test_should_handle_invalid_command(self):
        output = custom_check_output(logging.getLogger(), "invalidcommand")
        assert not output.success
