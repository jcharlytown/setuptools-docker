import os
import pathlib
import random
import shutil
import subprocess
from string import ascii_letters
from typing import Dict, List, Optional, Tuple

from furl import furl
from jinja2 import Environment, FileSystemLoader

INDEX_SECRET_NAME = "INDEX_PASSWORD"


def prepare_context(
    context_path: str,
    wheel_file: str,
    base_image: str = "python:3.8-slim-bullseye",
    extra_os_packages: List[str] = [],
    builder_extra_os_packages: List[str] = [],
    requirements_file: Optional[str] = None,
    extra_requirements: List[str] = [],
    index_url: Optional[str] = None,
    index_username: Optional[str] = None,
    index_password: Optional[str] = None,
    init_scripts: List[str] = [],
    entrypoint: List[str] = [],
    command: List[str] = [],
    user_id: Optional[int] = None,
    pip_cache: bool = True,
    env_vars: List[Tuple[str, str]] = [],
) -> Dict[str, str]:

    entrypoint_exec_form = (
        str(["/app/docker-entrypoint.sh"] + entrypoint).replace("'", '"')
        if entrypoint
        else None
    )
    command_exec_form = str(command).replace("'", '"') if command else None
    init_scripts_base = list(map(lambda s: os.path.basename(s), init_scripts))

    index_url_with_auth = _render_index_url(index_url, index_username, index_password)

    dockerfile_template = Environment(
        loader=FileSystemLoader(searchpath=os.path.dirname(os.path.realpath(__file__))),
        trim_blocks=True,
    ).get_template("Dockerfile.j2")

    pip_requirements = (
        [f"-r {requirements_file}"] if requirements_file else []
    ) + extra_requirements

    dockerfile = dockerfile_template.render(
        wheel_file=wheel_file,
        base_image=base_image,
        extra_os_packages=extra_os_packages,
        builder_extra_os_packages=builder_extra_os_packages,
        requirements_file=requirements_file,
        pip_requirements=pip_requirements,
        index_url=index_url_with_auth,
        index_url_needs_secret=index_password is not None,
        init_scripts_base=init_scripts_base,
        entrypoint_exec_form=entrypoint_exec_form,
        command_exec_form=command_exec_form,
        user_id=user_id,
        pip_cache=pip_cache,
        env_vars=env_vars,
    ).replace("__BS__", "\\")

    pathlib.Path(context_path).mkdir(parents=True, exist_ok=True)

    # write Dockerfile
    with open(os.path.join(context_path, "Dockerfile"), "w") as dockerfile_f:
        dockerfile_f.write(dockerfile)

    entrypoint_script = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "docker-entrypoint.sh"
    )

    # copy wheel and other files
    for to_copy in [str(entrypoint_script), wheel_file]:
        shutil.copy(to_copy, context_path)

    if requirements_file:
        shutil.copy(requirements_file, context_path)

    for init_script in init_scripts:
        shutil.copy(init_script, context_path)

    return {INDEX_SECRET_NAME: index_password} if index_password else {}


def build_image(
    context_path: str, image_name: str, image_tag: str, secrets: Dict[str, str] = {}
):
    subprocess_env = secrets.copy()
    subprocess_env["PATH"] = os.environ["PATH"]
    subprocess_env["USER"] = os.environ["USER"]
    subprocess_env["HOME"] = os.environ["HOME"]
    subprocess_env["DOCKER_BUILDKIT"] = "1"
    subprocess.run(
        [
            "docker",
            "build",
        ]
        + _secrets_args(secrets)
        + [
            "-f",
            str(os.path.join(context_path, "Dockerfile")),
            "-t",
            f"{image_name}:{image_tag}",
            str(context_path),
        ],
        env=subprocess_env,
    ).check_returncode()


def _secrets_args(secrets: Dict[str, str]) -> List[str]:
    def gen():
        for s in secrets.keys():
            yield "--secret"
            yield f"id={s},env={s}"

    return list(gen())


def _render_index_url(
    url: str = None, user: str = None, password: str = None
) -> Optional[str]:
    if url is None:
        return None
    f = furl(url)

    if not f.scheme:
        f.scheme = "https"
    if user:
        f.username = user

    if not password:
        return str(f)
    else:
        pw_placeholder = _rand_pw_placeholder(str(f))
        f.password = pw_placeholder
        return str(f).replace(
            pw_placeholder, f"$(cat /run/secrets/{INDEX_SECRET_NAME})"
        )


def _rand_pw_placeholder(url: str) -> str:
    s = "PASSWORD"
    while url.count(s) > 0:
        s = "".join(random.choice(ascii_letters) for i in range(5))

    return s
