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

## Notes about running the CI workflow with `act`

The basic process is this:

1.  Clone the Chromobius repository to a local Linux computer

2.  Install and configure the GitHub CLI program [`gh`](https://cli.github.com/)

3.  Install and configure the `act` extension for `gh`:
    ```shell
    gh extension install nektos/gh-act
    ```

4.  Create Docker images for custom runners that will be used by `gh act`
    (described below)

5.  Proceed in a typical edit-run-repeat cycle until satisfied

Note that the CI workflow contains a build job that uses a matrix of Linux,
macOS, and Windows operating systems. It is not possible to run all of them on
the same machine because of architectural differences, so when we run the
workflow locally, we tell `gh act` to select a subset of the matrix. This is
explained below.

### Creation of Docker images to use as workflow job runners

For `gh act` to run a workflow, it needs to be told what Docker images to use
for job runners. It is usually not possible to use GitHub's actual runner images
(even though they are made freely available by GitHub) due to differences in
hardware assumptions. Thankfully, some approximations to the GitHub images is
available from other sources. For our testing, we create customized versions of
runners that pre-install some software known to be provided on GitHub.

For this project, here is the `Dockerfile` we use:

```dockerfile
# Start from a base image that is already configured for act.
FROM catthehacker/ubuntu:act-latest

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 python3-dev \
        cmake \
        golang-go \
        shellcheck \
        yamllint \
    && \
    # Clean up the apt cache to keep the image small
    rm -rf /var/lib/apt/lists/*
```

Here is the shell command used to build the image:

```shell
docker build -t ubuntu-act:latest .
```

The runner name `ubuntu-act` is used in the next section.


### Configuration of `act`

`gh act` reads a configuration file that can be used to set some run-time
parameters. Here is an example of one we have used. We save this in a file named
`.actrc`.

```shell
# Define the docker images that will be used for the job runners.
# This assumes that a Docker image with the name `ubuntu-act` has been created.
-P ubuntu-latest=ubuntu-act:latest
-P ubuntu-24.04=ubuntu-act:latest

# Must use --pull=false with local images, or else get the following error:
# "Error response from daemon: pull access denied for ubuntu-act".
--pull=false

# Change the following number depending on how many CPUs you have available and
# want to let the Docker container use.
--container-options "--cpus=10"

# Remove containers after workflow failures.
--rm

# Add some miscellaneous performance improvement flags.
--use-new-action-cache
--action-offline-mode
```

### Miscellaneous additional setup steps

The `ci.yml` workflow has steps where it uploads and download build artifacts.
When running on GitHub, the artifact storage is on GitHub itself; when running
locally, `gh act` needs to be told to run its own artifact server. The
configuration in the next section tells `gh act` to store the artfacts in a
local directory, but this directory has to be created ahead of time. In the
example used here, the artifact directory is `$HOME/.act-artifacts/`.

```shell
mkdir -p $HOME/.act-artifacts
```

### Running `gh act`

The following is an example of acommand we use to run the workflow in debug
mode. The command is meant to be executed from the top level of the Chromobius
source directory. _JOBNAME_ stands for one of the jobs in `ci.yml`. (For
example, _JOBNAME_ could be `run_main`.) Finally, note that this selects a
specific OS from the matrix in `build_dist`; the choice would need to change
when running this on another platform.

```shell
gh act workflow_dispatch -j JOBNAME \
    --artifact-server-path $HOME/.act-artifacts \
    --matrix os:ubuntu-24.04 \
    --var act=true \
    --input debug=true \
    --env GITHUB_WORKFLOW_REF=refs/heads/main \
    --secret TEST_PYPI_API_TOKEN \
    --no-recurse -W .github/workflows/ci.yml
```

Note: the option `--secret` above will make `gh act` prompt interactively for a
token to be used with test.pypi.org. You can copy-paste a token at the prompt,
or use other methods (described in the [`act`](https://github.com/nektos/act)
documentation) to provide the token.

The `--var` and `input` options in the command line above set variables that are
used in the workflow to change some behaviors for local testing and debugging.

The `--no-recurse` option prevents `act` from triggering other workflows it may
find in the workflows directory, and the flag `-W` test `act` which specific
workflow file to use.
