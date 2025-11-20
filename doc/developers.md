# Chromobius Developer Documentation

## Index

- [Repository Layout](#Repository_Layout)
- [Building Chromobius as a standalone command line tool](#build-cli)
    - [with Bazel](#build-cli-bazel)
    - [with CMake](#build-cli-cmake)
    - [with GCC](#build-cli-gcc)
    - [with Clang](#build-cli-clang)
- [Building Chromobius as a python package](#build-python)
    - [with Bazel](#build-python-bazel)
    - [with CMake](#build-python-cmake)
    - [with cibuildwheel](#build-python-cibuildwheel)
    - [with pip](#build-python-pip)
- [Running tests](#test)
    - [Python unit tests](#test-python)
    - [C++ unit tests with Bazel](#test-bazel)
    - [C++ unit tests with CMake](#test-cmake)
- [Running performance benchmarks](#perf)
    - [with Bazel](#perf-bazel)
    - [with CMake](#perf-cmake)

## <a class="anchor" id="Repository_Layout"></a>Repository Layout

- `src/chromobius/`: C++ code implementing Chromobius and its Python package.
- `src/clorco/`: Python code for generating color code and surface code circuits used to test Chromobius.
- `src/gen/`: Generic utilities for making circuits; used by `src/clorco/`.
- `tools/`: Bash scripts for generating circuits and statistics and plots presented in the paper.

## <a class="anchor" id="build-cli"></a>Building Chromobius as a standalone command line tool

### <a class="anchor" id="build-cli-bazel"></a>with Bazel:

```bash
bazel build :chromobius
```

Or, to run the tool:

```bash
bazel run :chromobius
```

### <a class="anchor" id="build-cli-cmake"></a>with CMake:

```bash
cmake .
make chromobius
```

Then, to run the built tool:

```bash
out/chromobius
```

### <a class="anchor" id="build-cli-gcc"></a>with GCC:

```bash
# This must be run from the repository root.
# This requires that you have libstim and libpymatching installed.

readarray -d '' CC_FILES_TO_BUILD < \
    <( \
      find src \
      | grep "\\.cc$" \
      | grep -v "\\.\(test\|perf\|pybind\)\\.cc$" \
    )

g++ \
    -I src \
    -std=c++20 \
    -O3 \
    -march=native \
    ${CC_FILES_TO_BUILD[@]} \
    -l stim \
    -l pymatching
```

### <a class="anchor" id="build-cli-clang"></a>with Clang:

```bash
# This must be run from the repository root.
# This requires that you have libstim and libpymatching installed.

readarray -d '' CC_FILES_TO_BUILD < \
    <( \
      find src \
      | grep "\\.cc$" \
      | grep -v "\\.\(test\|perf\|pybind\)\\.cc$" \
    )

clang \
    -I src \
    -std=c++20 \
    -O3 \
    -march=native \
    ${CC_FILES_TO_BUILD[@]} \
    -l "stdc++" \
    -l m \
    -l stim \
    -l pymatching
```

Then, to run the built tool:

```bash
./a.out
```

## <a class="anchor" id="build-python"></a>Building Chromobius as a Python package

### <a class="anchor" id="build-python-bazel"></a>with Bazel:

```bash
bazel build :chromobius_dev_wheel
pip install bazel-bin/chromobius-0.0.dev0-py3-none-any.whl
```

### <a class="anchor" id="build-python-cmake"></a>with CMake:

```bash
# Requires pybind11 and Python to be installed on your system.
cmake .
make chromobius_pybind
# output is in `out/` with a path that depends on your machine
# e.g. it might be `out/chromobius.cpython-311-x86_64-linux-gnu.so`
```

### <a class="anchor" id="build-python-cibuildwheel"></a>with cibuildwheel:

```bash
pip install cibuildwheel
# See https://cibuildwheel.readthedocs.io/en/stable/options/#build-skip for CIBW_BUILD values
CIBW_BUILD=cp311-manylinux_x86_64 cibuildwheel --platform linux
# output is in `wheelhouse/` with a path that depends on platform/target
# e.g. it might be `out/chromobius-0.0.dev0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`
```

### <a class="anchor" id="build-python-pip"></a>with pip:

```bash
# Must be run from the chromobius git repository root.
# Note this will build the package AND install it into your Python environment.
pip install .
# output is in `python_build_chromobius/` under a platform dependent directory and filename
# e.g. it might be `python_build_chromobius/lib.linux-x86_64-cpython-311/chromobius.cpython-311-x86_64-linux-gnu.so`
```

## <a class="anchor" id="test"></a>Running unit tests

### <a class="anchor" id="test-python"></a>Python unit tests

The Python unit tests check that the circuit generation utilities
are working correctly, and that Chromobius can decode the generated
circuits.

Note that these tests require the Chromobius Python package to be installed.

```bash
pip install -r requirements.txt
pytest src
```

### <a class="anchor" id="test-bazel"></a>C++ unit tests with Bazel

```bash
bazel test :all
```

### <a class="anchor" id="test-cmake"></a>C++ unit tests with CMake

```bash
# Requires googletest to be installed on your system.
cmake .
make chromobius_test
out/chromobius_test
```

## <a class="anchor" id="perf"></a>Running performance benchmarks

### <a class="anchor" id="perf-bazel"></a>with Bazel

```bash
bazel run :chromobius_perf
```

### <a class="anchor" id="perf-cmake"></a>with CMake

```bash
cmake .
make chromobius_perf
out/chromobius_perf
```

##  <a class="anchor" id="release-checklist"></a>Releasing a new version

New development releases are uploaded to the [Chromobius project on PyPI](https://pypi.org/project/chromobius/)
automatically by a continuous integration workflow on GitHub. The updates are triggered when pull requests are merged
into the main branch of the repository.

Stable releases are performed manually by following these steps:

*   Create an off-main-branch release commit
    - [ ] `git checkout main -b SOMEBRANCHNAME`
    - [ ] Search `.py` files and replace `__version__ = 'X.Y.dev0'` with `__version__ = 'X.Y.0'`
    - [ ] `git commit -a -m "Bump to vX.Y.0"`
    - [ ] `git tag vX.Y.0`
    - [ ] Push the tag to GitHub
    - [ ] Check the GitHub `Actions` tab and confirm CI is running on the tag
*   Collect Python wheels from GitHub
    - [ ] Wait for CI to finish validating and producing artifacts for the tag
    - [ ] Download all the wheels created as artifacts by the CI workflow
    - [ ] Do manual sanity checks, e.g., by installing one of the wheels and running tests
*   Bump to next dev version on main branch
    - [ ] `git checkout main -b SOMEBRANCHNAME`
    - [ ] Search `.py` files and replace `__version__ = 'X.Y.dev0'` with `__version__ = 'X.(Y+1).dev0'`
    - [ ] `git commit -a -m "Start vX.(Y+1).dev"`
    - [ ] Push to GitHub as a branch and merge into main using a pull request
*   Start a draft release on GitHub
    - [ ] For the title, use two-word theming of most important changes
    - [ ] In the body, list the user-visible fixes, additions, and other changes
    - [ ] Attach the wheels to the release
*   Do these irreversible and public viewable steps last!
    - [ ] Upload wheels/sdists to PyPI
    - [ ] Publish the GitHub release notes
    - [ ] Announce the release
