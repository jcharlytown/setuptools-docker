import pytest

from setuptools_docker.docker import _render_index_url


@pytest.mark.parametrize(
    "url, user, pw, expected_url",
    [
        (
            "http://pypi.org",
            "julian",
            "supersecret",
            "http://julian:$(cat /run/secrets/INDEX_PASSWORD)@pypi.org",
        ),
        ("http://pypi.org", None, None, "http://pypi.org"),
    ],
)
def test_render_index_url(url, user, pw, expected_url):
    res_url = _render_index_url(url, user, pw)
    assert res_url == expected_url
