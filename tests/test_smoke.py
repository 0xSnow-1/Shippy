import sys


def test_python_version_is_3_12_or_newer() -> None:
    assert sys.version_info >= (3, 12)
