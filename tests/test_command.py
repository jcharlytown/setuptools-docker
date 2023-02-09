import pytest

from setuptools_docker.command import _parse_envvars, _parse_list


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
        (["blub="], [("blub", "")]),
        (["blub=bla=fizz"], [("blub", "bla=fizz")]),
        (["blub=="], [("blub", "=")]),
        (
            [],
            [],
        ),
        (['BLA="!@#$%^&*()='], [("BLA", '"!@#$%^&*()=')]),
    ],
)
def test_envvars_parsing(list, expected_tuples):
    actual = _parse_envvars(list)
    assert actual == expected_tuples


@pytest.mark.parametrize(
    "list",
    [
        (["=bla"]),
        (["blablub"]),
        (["%=illegal"]),
    ],
)
def test_envars_parsing_illegal(list):
    with pytest.raises(Exception):
        _parse_envvars(list)


def test_envars_parsing_e2e():
    s = """
    
    BLA="!@#$%^&*()=

    """
    assert _parse_envvars(_parse_list(s)) == [("BLA", '"!@#$%^&*()=')]
