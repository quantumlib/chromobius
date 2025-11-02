# Notes about the continuous integration workflow

The continous integration workflow in [`ci.yml`](ci.yml) triggers automatically
on pushes, pull requests, and merge queue events. It can also be [triggered
manually](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
from either the Actions tab on GitHub or via the GitHub APIs. Manual invocations
like that are useful for limited testing and debugging (particularly when a
problem only seems to show up on GitHub itself), but for more significant
development and testing of the workflow itself, we use the
[`act`](https://github.com/nektos/act) extension for GitHub's CLI program
[`gh`](https://cli.github.com/) to run the workflow on a local computer.
For the benefit of future Chromobius maintainers, this document summarizes how
to set up an environment for working with [`act`](https://github.com/nektos/act)
to run and test the CI workflow.

## Local testing of the CI workflow with `act`

The overall process consists of these steps, which are described in more detail
in the subsections below:

1.  Clone the Chromobius repository to a local Linux computer.

2.  Install and configure the following programs:

    * The GitHub CLI program [`gh`](https://cli.github.com/)
    * The [`act` extension](https://nektosact.com/installation/gh.html) for `gh`
    * The [`pypiserver`](https://github.com/pypiserver/pypiserver) Python program
    * The free and open-source Docker Community Edition (CE) version of
      [Docker Engine](https://docs.docker.com/engine/#licensing) (note: this is not
      the same as Docker Desktop, which is _not_ needed)

3.  Create a Docker image that will be used by `gh act` to run the GitHub
    Actions workflow in `ci.yml`.

4.  Start [`pypiserver`](https://github.com/pypiserver/pypiserver) on your
    computer.

5.  Run `gh act` with specific arguments, observe the results of the run, edit
    the workflow file (if necessary), and repeat until satisfied.

Note that the CI workflow in `ci.yml` contains a build step with a matrix of
Linux, macOS, and Windows operating systems. It is not possible to run all of
them on the same machine because of architectural differences, so when we test
the workflow locally, we tell `gh act` to select a subset of the matrix. This is
explained below.

### Creation of Docker images to use as workflow job runners

For `gh act` to run a workflow, it needs to be told what Docker images to use
for job runners. It is usually not possible to use GitHub's actual runner images
(even though they are made freely available by GitHub) due to differences in
hardware assumptions. Thankfully, some approximations to the GitHub images is
available from other sources. For our testing, we create customized versions of
runners that pre-install some software known to be provided on GitHub.

For this project, here is the `Dockerfile` we use for the Linux runner:

```dockerfile
# Start from a base image that is already configured for act.
FROM catthehacker/ubuntu:act-latest

USER root

# Add software that is pre-installed on GitHub Linux runners.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        curl \
        golang-go \
        jq \
        python3 python3-dev cython3 \
        shellcheck \
        yamllint \
    && \
    # Clean up the apt cache to keep the image small.
    rm -rf /var/lib/apt/lists/*
```

Here is the shell command used to build the image:

```shell
docker build -t ubuntu-act:latest .
docker image prune
```

The Docker image will be named `ubuntu-act`. This name is mapped to the names of
GitHub runners used in `ci.yml` in a way explained in the next subsection.

### Configuration of `act`

`gh act` reads a configuration file that can be used to set some run-time
parameters. This can be used to map the name of the Docker image built in the
step above to the name of the runners used in the workflow. Certain other
parameters are also essential to provide, notably `--pull=false` and the
`--artifact-server-path` option. Here is an example of a `~/.actrc` file:

```shell
# The -P flag maps a GitHub runner name (inside the workflow file) to the name
# of a Docker image on the local computer. For example, the following maps the
# GitHub runner named "ubuntu-latest" to the local docker image "ubuntu-act".
-P ubuntu-latest=ubuntu-act:latest
-P ubuntu-24.04=ubuntu-act:latest

# If using a local docker image for the job runners, need to use --pull=false
# or else will get the error "Error response from daemon: pull access denied".
--pull=false

# This tells act where to put artifacts saved using `actions/upload-artifact`.
--artifact-server-path /tmp/act-artifacts

# These are some miscellaneous performance improvements. For the number of
# CPUs, change the number from 4 to something suitable for your computer.
--container-options "--cpus=4"
--use-new-action-cache
--action-offline-mode

# This tells act to remove containers after workflow failures.
--rm
```

The `ci.yml` workflow has steps where it uploads and download build artifacts.
When running on GitHub, the artifact storage is on GitHub itself; when running
locally, `gh act` needs to be told to run its own artifact server. The
configuration above tells `gh act` to store the artfacts in a local directory,
but this directory has to be created before running `gh act`. In the example
configuration used here, the artifact directory is `/tmp/act-artifacts/`:

```shell
mkdir /tmp/act-artifacts
```

### Start a local test PyPI server

The `ci.yml` workflow includes steps to upload the latest developer release to
[test.pypi.org](https://test.pypi.org). A limitation with using test.pypi.org
(and pypi.org, for that matter) is that a given file can only be uploaded once.
This is inconvenient when developing and testing workflows, but thankfully, it
is possible to run a basic PyPI server locally and avoid this limitation.

The [`pypiserver`](https://github.com/pypiserver/pypiserver) package is great
for this use-case scenario. The server can be run with or without user
authentication; for simplicity, we use it without authentication. Starting
`pypiserver` is as simple as running this one-line command:

```shell
pypi-server run -v -P . -a . /tmp/pypiserver-packages
```

In the command line above, we used `/tmp/pypiserver-packages` as the location
where `pypiserver` will store uploaded packages; a different location could be
chosen if you prefer.

`pypiserver` will by default start listening on port 8080 for connections from
any host using the HTTP protocol (not HTTPS). In combination with turning off
user authentication, the use of HTTP simplifies using the server for testing on
a personal computer, but this insecure configuration would be unsuitable for
other situations. Make sure to configure it appropriately for your environment.

### Running `gh act`

Once `pypiserver` is running, in order for the containerized process in `gh act`
to be able to contact it, we need to set certain variables to redirect the
accesses to `test.pypi.org` to go to the local server instead. The following is
an example of a command we use to run the workflow in debug mode. The command is
meant to be executed from the top level of the Chromobius source directory. Note
that this selects a specific OS from the matrix in `build_dist` (namely the
entries using `ubuntu-24.04` as the operating system); the matrix selection
value would need to be changed when running this command on a different
operating system and hardware architecture.

```shell
ip_address="$(hostname -I | xargs)"
test_server="http://${ip_address}:8080"
gh act workflow_dispatch \
    --matrix os:ubuntu-24.04 \
    --container-options '--network host' \
    --input debug=true \
    --input upload_to_pypi=false \
    --env testpypi_endpoint_url=${test_server} \
    --env testpypi_index_url=${test_server}/simple \
    --env testpypi_user=test \
    --env testpypi_password=test \
    --env PIP_TRUSTED_HOST=${ip_address} \
    --env GITHUB_WORKFLOW_REF=refs/heads/main \
    -W .github/workflows/ci.yml
```

The `--input` options in the command line above are used to variables that are
used in the workflow to change some behaviors when debugging. The `--env`
options set certain environment variables: the `testpypi_*` variables override
values inside the workflow, the `PIP_TRUSTED_HOST` environment variable tells
the `pip install` commands that the local `pypiserver` can be trusted even
though it uses HTTP, and the `GITHUB_WORKFLOW_REF` setting sets a variablue that
is normally set by GitHub when a workflow is running in that environment.

Experienced developers may wonder why the command above needs to find the IP
address instead of using the common host name `localhost` or the address
`127.0.0.1`. The layers of software and containers involved can result in the
environment inside the workflow to fail to resolve `localhost` properly. In our
experience, the combination of telling Docker to use "--network host" mode and
using explicit IP addresses has been more consistently successful in allowing
the `pip` commands in the `upload_to_testpypi` workflow job to reach the
test PyPI server running on the local computer.

### Miscellaneous tips

Sometimes it's useful to add the `--verbose` option to the `gh act` command
above to get more information about what is happening.

If the workflow running inside `act` inexplicably starts producing weird errors
such as files suddently not found when they were found before, it may be due to
corruption in the `act` cache. (One way that can happen is when runs are
terminated using, e.g., <kbd>control</kbd><kbd>c</kbd>.) To resolve this, try to
clean up everything, which is to say:

1.  Delete all artifacts in the `act` artifact directory. If you are using
    `/tmp/act-artifacts` for the artifact directory, then you can do that
    with a command such as this:

    ```shell
    rm -rf /tmp/act-artifacts/*
    ```

2.  Delete everything in the `act` cache (which is located in
    `$HOME/.cache/act/` by default):

    ```shell
    rm -rf ~/.cache/act/*
    rm -rf ~/.cache/actcache/*
    ```

3.  Delete all docker containers and volumes:

    ```shell
    docker system prune --all
    docker volume prune --all
    ```

The above is something of a sledgehammer to apply to this problem, but sometimes
a sledgehammer is what it takes.
