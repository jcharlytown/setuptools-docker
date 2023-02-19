import pytest
import tempfile
import os
import shutil
import urllib.request
import docker
import requests
import time
import socket

from setuptools_docker.docker import _render_index_url, prepare_context, build_image
from requests.exceptions import ConnectionError


@pytest.fixture(scope="session")
def docker_client():
    client = docker.APIClient()
    return client


@pytest.fixture(scope="session")
def tmp_dir():
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


@pytest.fixture()
def test_context_dir(tmp_dir):
    path = os.path.join(tmp_dir, "context")
    try:
        os.mkdir(path)
        yield str(path)
    finally:
        shutil.rmtree(path)


@pytest.fixture(scope="session")
def test_wheel_path(tmp_dir):
    filename, _ = urllib.request.urlretrieve(
        "https://files.pythonhosted.org/packages/e4/dd/5b190393e6066286773a67dfcc2f9492058e9b57c4867a95f1ba5caf0a83/gunicorn-20.1.0-py3-none-any.whl",
        os.path.join(tmp_dir, "gunicorn-20.1.0-py3-none-any.whl"),
    )
    return filename


@pytest.fixture()
def pypi_proxy():
    dc = docker.from_env()
    this_dir = os.path.dirname(os.path.abspath(__file__))
    nginx_cfg = str(os.path.join(this_dir, "nginx_proxy", "default.conf"))
    passwd_file = str(os.path.join(this_dir, "nginx_proxy", ".htpasswd"))

    container = None
    try:
        container = dc.containers.run(
            "nginx",
            detach=True,
            volumes={
                nginx_cfg: {
                    "bind": "/etc/nginx/conf.d/default.conf",
                    "mode": "ro",
                },
                passwd_file: {
                    "bind": "/etc/apache2/.htpasswd",
                    "mode": "ro",
                },
            },
            ports={"80/tcp": 8080},
            remove=True,
        )

        # takes a short while for nginx to become ready -> wait until health endpoint is up
        for i in range(1, 5):
            if i == 5:
                raise Exception("Container failed to start")
            try:
                res = requests.get("http://localhost:8080/health")
                if res.status_code == 200:
                    break
            except ConnectionError:
                pass

            time.sleep(1)

        yield container
    finally:
        if container:
            container.stop()


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


def build_and_inspect_test_image(docker_client, target=None, **kwargs):
    secrets = prepare_context(**kwargs)
    build_image(
        context_path=kwargs.get("context_path"),
        image_name="setuptools-docker-unittest",
        image_tag="latest",
        target=target,
        secrets=secrets,
    )

    return docker_client.inspect_image("setuptools-docker-unittest:latest")


@pytest.mark.parametrize(
    "user_id",
    [None, "1100"],
)
def test_user(test_context_dir, test_wheel_path, docker_client, user_id):
    image_info = build_and_inspect_test_image(
        docker_client,
        context_path=test_context_dir,
        wheel_file=test_wheel_path,
        user_id=user_id,
    )
    assert image_info["Config"]["User"] == (str(user_id) if user_id else "")


@pytest.mark.parametrize("custom_env_vars", [[], [("FIZZ", "BUZZ"), ("LEFT", "r*g%t")]])
def test_env_vars(test_context_dir, test_wheel_path, docker_client, custom_env_vars):
    image_info = build_and_inspect_test_image(
        docker_client,
        context_path=test_context_dir,
        wheel_file=test_wheel_path,
        env_vars=custom_env_vars,
    )
    env = image_info["Config"]["Env"]
    for name, value in custom_env_vars:
        assert f"{name}={value}" in env

    # default envvars
    assert "PYTHONDONTWRITEBYTECODE=1" in env
    assert "PYTHONUNBUFFERED=1" in env


@pytest.mark.parametrize(
    "entrypoint",
    [[], ["cat"], ["cat", "testfile"]],
)
def test_entrypoint(test_context_dir, test_wheel_path, docker_client, entrypoint):
    image_info = build_and_inspect_test_image(
        docker_client,
        context_path=test_context_dir,
        wheel_file=test_wheel_path,
        entrypoint=entrypoint,
    )
    assert image_info["Config"]["Entrypoint"] == ["/app/docker-entrypoint.sh"] + (
        entrypoint if entrypoint else ["python"]
    )


@pytest.mark.parametrize(
    "command",
    [[], ["--version"], ["-v", "-d"]],
)
def test_command(test_context_dir, test_wheel_path, docker_client, command):
    image_info = build_and_inspect_test_image(
        docker_client,
        context_path=test_context_dir,
        wheel_file=test_wheel_path,
        command=command,
    )
    assert image_info["Config"]["Cmd"] == (command if command else None)


def test_os_packages(test_context_dir, test_wheel_path, docker_client):
    build_and_inspect_test_image(
        docker_client,
        target="builder",
        context_path=test_context_dir,
        wheel_file=test_wheel_path,
        extra_os_packages=["tree", "sl"],
    )
    docker_hl_client = docker.from_env()

    output = str(
        docker_hl_client.containers.run(
            "setuptools-docker-unittest:latest", entrypoint="apt list"
        )
    )
    assert "tree/stable" not in output
    assert "sl/stable" not in output

    # also check that packages are not in final image
    build_and_inspect_test_image(
        docker_client,
        target=None,
        context_path=test_context_dir,
        wheel_file=test_wheel_path,
        extra_os_packages=["tree", "sl"],
    )

    output = str(
        docker_hl_client.containers.run(
            "setuptools-docker-unittest:latest", entrypoint="apt list"
        )
    )
    assert "tree/stable" in output
    assert "sl/stable" in output


def test_builder_os_packages(test_context_dir, test_wheel_path, docker_client):
    build_and_inspect_test_image(
        docker_client,
        target="builder",
        context_path=test_context_dir,
        wheel_file=test_wheel_path,
        builder_extra_os_packages=["tree", "sl"],
    )
    docker_hl_client = docker.from_env()

    output = str(
        docker_hl_client.containers.run(
            "setuptools-docker-unittest:latest", entrypoint="apt list"
        )
    )
    assert "tree/stable" in output
    assert "sl/stable" in output

    # also check that packages are not in final image
    build_and_inspect_test_image(
        docker_client,
        target=None,
        context_path=test_context_dir,
        wheel_file=test_wheel_path,
        builder_extra_os_packages=["tree", "sl"],
    )

    output = str(
        docker_hl_client.containers.run(
            "setuptools-docker-unittest:latest", entrypoint="apt list"
        )
    )
    assert "tree/stable" not in output
    assert "sl/stable" not in output


def test_python_interpreter(test_context_dir, test_wheel_path, docker_client):
    build_and_inspect_test_image(
        docker_client,
        context_path=test_context_dir,
        wheel_file=test_wheel_path,
    )
    docker_hl_client = docker.from_env()

    output = str(
        docker_hl_client.containers.run(
            "setuptools-docker-unittest:latest", entrypoint=["python", "--version"]
        )
    )

    assert "3.8" in output


def test_pip_packages(tmp_dir, test_context_dir, test_wheel_path, docker_client):
    with open(os.path.join(tmp_dir, "requirements.txt"), "w") as f:
        f.write("werkzeug")

    build_and_inspect_test_image(
        docker_client,
        context_path=test_context_dir,
        wheel_file=test_wheel_path,
        extra_requires=["gevent"],
        requirements_file=f.name,
    )
    docker_hl_client = docker.from_env()

    output = str(
        docker_hl_client.containers.run(
            "setuptools-docker-unittest:latest", entrypoint="pip list"
        )
    )

    assert "gunicorn" in output
    assert "Werkzeug" in output
    assert "gevent" in output


def test_private_registry(test_context_dir, test_wheel_path, docker_client, pypi_proxy):
    res = requests.get("http://localhost:8080/simple/gevent")
    assert res.status_code == 401

    hostname = socket.gethostname()
    build_and_inspect_test_image(
        docker_client,
        context_path=test_context_dir,
        wheel_file=test_wheel_path,
        extra_requires=["gevent"],
        index_url=f"http://{hostname}:8080/simple",
        index_username="julian",
        index_password="7v#>HNzt/)H>xzDzoAjBrxtL:w9{GX",
        pip_extra_args=f"--trusted-host {hostname}",
    )
    docker_hl_client = docker.from_env()

    output = str(
        docker_hl_client.containers.run(
            "setuptools-docker-unittest:latest", entrypoint="pip list"
        )
    )

    assert "gunicorn" in output
    assert "gevent" in output
