import pytest

from setuptools_docker.command import _parse_envvars


@pytest.mark.parametrize(
    "list, expected_tuples",
    [
        (
            ["blub=bla"],
            [("blub", "bla")],
        ),
        (
            ["blub=bla", "hello=world"],
            [("blub", "bla"), ("hello", "world")],
        ),
        (
            [],
            [],
        ),
    ],
)
def test_envvars_parsing(list, expected_tuples):
    actual = _parse_envvars(list)
    assert actual == expected_tuples


@pytest.mark.parametrize(
    "list",
    [
        (["blub="]),
        (["blub=bla"], ["blub="]),
        (["=bla"]),
        (["blablub"]),
        (["blub=bla=fizz"]),
        (["%=illegal"]),
    ],
)
def test_envars_parsing_illegal(list):
    with pytest.raises(Exception):
        _parse_envvars(list)
