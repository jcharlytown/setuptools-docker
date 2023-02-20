import subprocess
import os
import sys
import requests
import docker
import time


def test_example():
    this_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = str(os.path.join(this_dir, ".."))
    example_dir = str(os.path.join(root_dir, "example"))

    # subprocess.check_call(["rm", "-rf", str(os.path.join(root_dir, "dist"))])
    # wheel_ps = subprocess.run(
    #    [sys.executable, "-m", "setup", "bdist_wheel"],
    #    cwd=root_dir,
    #    shell=False,
    #    capture_output=True,
    # )
    # wheel_ps.check_returncode()

    # subprocess.run(
    #    [sys.executable, "-m", "pip", "install", "../dist/*.whl"],
    #    cwd=example_dir,
    #    shell=False,
    #    capture_output=True,
    # )

    bdist_docker_ps = subprocess.run(
        [
            sys.executable,
            "-m",
            "setup",
            "bdist_docker",
            "--image-name",
            "example",
            "--image-tag",
            "latest",
        ],
        cwd=example_dir,
        shell=False,
        capture_output=True,
    )
    assert bdist_docker_ps.returncode == 0

    container = None
    try:
        client = docker.from_env()
        container = client.containers.run(
            "example", remove=True, ports={"8000/tcp": 8000}, detach=True
        )
        time.sleep(2)

        res = requests.get("http://localhost:8000/")
        res.raise_for_status()
        assert res.json() == {"hello": "world"}
    finally:
        if container:
            container.stop()
