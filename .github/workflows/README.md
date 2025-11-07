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
    * The free and open-source Docker Community Edition (CE) version of
      [Docker Engine](https://docs.docker.com/engine/#licensing) (note: this is not
      the same as Docker Desktop, which is _not_ needed)

3.  Create a Docker image that will be used by `gh act` to run the GitHub
    Actions workflow in `ci.yml`.

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
# The hash below is for the image tagged act-24.04-20251102.
FROM ghcr.io/catthehacker/ubuntu@sha256:8943e69edcada5141b8c1fcc1a84bab15568a49f438387bd858cb3e4df5a436d

# Switch to the root user to have permission to install packages.
USER root

# Add some software that is pre-installed on GitHub Linux runners.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        clang \
        cmake \
        golang-go \
        libclang-dev \
        libclang-rt-dev \
        ninja-build \
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
# of a Docker image on the local computer. The following maps the runner named
# "ubuntu-24.04" (used in ci.yml) to the local docker image "ubuntu-act".
-P ubuntu-24.04=ubuntu-act:latest

# If using a local docker image for the job runners, need to use --pull=false
# or else will get the error "Error response from daemon: pull access denied".
--pull=false

# This tells act where to put artifacts saved using `actions/upload-artifact`.
--artifact-server-path /tmp/act-artifacts

# These are some miscellaneous performance improvements.
--use-new-action-cache
--action-offline-mode

# This tells act to remove containers after workflow failures.
--rm
```

### Running `gh act`

The following is an example of a command we use to run the workflow in debug
mode. The command is meant to be executed from the top level of the Chromobius
source directory. Note that this example shows how to select a specific OS from
the matrix in `build_dist` (namely the entries using `ubuntu-24.04` as the
operating system); this matrix selection value would need to be changed when
running this command on a different operating system and hardware architecture.

```shell
gh act workflow_dispatch \
    --matrix os:ubuntu-24.04 \
    --input debug=true \
    --input upload_to_pypi=false \
    --env GITHUB_WORKFLOW_REF=refs/heads/main \
    --norecurse -W .github/workflows/ci.yml
```

The `--input` options in the command line above are used to variables that are
used in the workflow to change some behaviors when debugging. The `--env` option
sets the `GITHUB_WORKFLOW_REF` environment variablue that is normally set by
GitHub when a workflow is running in that environment.

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
