# setuptools-docker

A light-weight setuptools extension for building docker images from python
projects.

Python wheels are the preferred packaging format for distributing python
libraries or applications. However, in cloud native computation services
get packaged and deployed as docker/oci images. This project aims at
making the packaging of python services for such environments as easy
and as repeatable as building a wheel. It takes heavy inspiration from
[jib](https://github.com/GoogleContainerTools/jib).

## Usage

setuptools-docker extends setuptools with one additional command:
`bdist_docker`. It will typically be used like this:

```commandline
python -m setup bdist_docker
```

For a reference of arguments see `python -m setup bdist_docker --help`

## Configuration via file

setuptools-docker utilizes the configuration mechanisms of setuptools
itself, e.g., `setup.cfg`. 

It adds a new section `[bdist_docker]`, e.g.:
```ini
[bdist_docker]
extra_requirements =
    gunicorn[gevent]
user_id = 1100
environment_vars =
    FIZZ=BUZZ
```

### Options
| Key                       | Type | Description                                                       | Default                  |
|---------------------------|------|-------------------------------------------------------------------|--------------------------|
| image_name                | str  | image name (optionally incl. registry)                            | metadata name            |
| image_tag                 | str  | image tag                                                         | metadata version         |
| requirements_file         | str  | pip requirements file to install into image                       |                          |
| extra_requirements        | list | extra pip requirements to install into image                      |                          |
| index_url                 | str  | pip index url to install dependencies from                        | (pip default index)      |
| index_username            | str  | username for authentication to PIP index                          |                          |
| index_password            | str  | password for authentication to PIP index                          |                          |
| base_image                | str  | base image for final stage                                        | python:3.8-slim-bullseye |
| extra_os_packages         | list | extra deb packages to install into final stage                    |                          |
| builder-extra-os-packages | list | extra deb packages to install into builder stage                  |                          |
| user_id                   | int  | user id for docker USER directive                                 |                          |
| entrypoint                | list | entrypoint in exec form                                           |                          |
| command                   | list | command in exec form                                              |                          |
| init_scripts              | list | path/to/extra/init/scripts to run (prior to provided entrypoint ) |                          |
| pip_cache_docker          | bool | whether to use docker cache for pip cache dir                     | True                     |
| environment_vars          | list | environment variables to set via docker ENV directive             |                          |
