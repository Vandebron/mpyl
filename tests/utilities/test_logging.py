from src.mpyl.utilities.logging import try_parse_ansi


class TestLogging:
    def test_ansi_logging(self):
        ansi = "\x1b[38;5;196mHello\x1b[0m"
        output = try_parse_ansi(ansi)
        assert output.plain == "Hello"
