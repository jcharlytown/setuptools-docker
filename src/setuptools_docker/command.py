import os
import re
from typing import Dict, List, Optional, Tuple

from setuptools import Command

from .docker import build_image, prepare_context


class bdist_docker(Command):
    description = "Create docker image"
    user_options = [
        ("build-context=", None, "directory for building docker context"),
        (
            "image-name=",
            "n",
            "Name of the docker image to be build. Defaults to package name",
        ),
        (
            "image-tag=",
            "t",
            "Tag of the docker image to be build. Defaults to package version",
        ),
        ("index-url=", "i", "--index-url parameter for pip install"),
        (
            "builder-extra-os-packages=",
            None,
            "Extra debian packages to install into builder image",
        ),
        ("base-image=", "b", "Base image to extend when building target image"),
        (
            "extra-os-packages=",
            None,
            "Extra debian packages to install into target image",
        ),
        (
            "requirements-file=",
            "r",
            "Requirements file for installing dependencies via pip",
        ),
        ("extra-requirements=", None, "Extra packages to install via pip"),
        ("index-username=", None, "Username for auth with python package index"),
        ("index-password=", None, "Password for auth with python package index"),
        ("user-id=", "u", "Id of os user to run within container"),
        ("entrypoint=", "e", "Entrypoint for docker image"),
        ("command=", "c", "Command for docker image"),
        ("init-scripts=", None, "Extra init scripts to add to image"),
        ("pip-cache-docker=", None, "Utilize docker cache for pip"),
        ("environment-vars=", None, "Environment variables to set in target image"),
    ]

    boolean_options = ["pip-cache-docker"]

    def initialize_options(self) -> None:
        self.build_context = None
        self.image_name = None
        self.image_tag = None
        self.builder_extra_os_packages = None
        self.base_image = "python:3.8-slim-bullseye"
        self.extra_os_packages = None
        self.requirements_file = None
        self.extra_requirements = None
        self.index_url = None
        self.index_username = None
        self.index_password = None
        self.user_id = None
        self.entrypoint = None
        self.command = None
        self.init_scripts = None
        self.pip_cache_docker = True
        self.environment_vars = None

    def finalize_options(self) -> None:
        #print(inspect.getmembers(self.distribution))
        print(self.distribution.entry_points)
        if self.image_name is None:
            dist_name = self.distribution.metadata.name
            self.image_name = dist_name

        if self.image_tag is None:
            dist_version = self.distribution.metadata.version
            if dist_version is not None:
                dist_version = dist_version.replace("+", "_")
            self.image_tag = dist_version

        if self.build_context is None:
            build_cmd_obj = self.distribution.get_command_obj("build")
            build_cmd_obj.ensure_finalized()
            build_base = getattr(build_cmd_obj, "build_base")
            self.build_context = os.path.join(build_base, "docker")

    def run(self) -> None:
        self.run_command("bdist_wheel")

        wheel_file = None
        for dist_file in self.distribution.dist_files:
            if dist_file[0] == "bdist_wheel":
                wheel_file = dist_file[2]

        secrets: Dict[str, str] = prepare_context(
            context_path=self.build_context,
            wheel_file=wheel_file,
            base_image=self.base_image,
            extra_os_packages=_parse_list(self.extra_os_packages),
            builder_extra_os_packages=_parse_list(self.builder_extra_os_packages),
            requirements_file=self.requirements_file,
            extra_requirements=_parse_list(self.extra_requirements),
            index_url=self.index_url,
            index_username=self.index_username,
            index_password=self.index_password,
            init_scripts=_parse_list(self.init_scripts),
            entrypoint=_parse_list(self.entrypoint),
            command=_parse_list(self.command),
            user_id=self.user_id,
            pip_cache=self.pip_cache_docker,
            env_vars=_parse_envvars(_parse_list(self.environment_vars)),
        )

        build_image(
            context_path=self.build_context,
            image_name=self.image_name,
            image_tag=self.image_tag,
            secrets=secrets,
        )


def _parse_list(l: Optional[str]) -> List[str]:
    if l is None:
        return []

    if "\n" in l:
        vs = l.splitlines()
    else:
        vs = l.split(" ")

    return [v.strip() for v in vs if v.strip()]


def _parse_envvars(l: List[str]) -> List[Tuple[str, str]]:
    def match(e: str):
        m = re.search(r"^([a-zA-Z_]\w*)=(\w+)$", e)
        if m:
            return m
        else:
            raise Exception(f"Invalid environment var mapping: {e}")

    return [(m.group(1), m.group(2)) for m in map(match, l)]
