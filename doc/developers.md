# Chromobius Developer Documentation

## Index

- [Repository Layout](#Repository_Layout)
- [Building chromobius as a standalone command line tool](#build-cli)
    - [with bazel](#build-cli-bazel)
    - [with cmake](#build-cli-cmake)
    - [with gcc](#build-cli-gcc)
    - [with clang](#build-cli-clang)
- [Building chromobius as a python package](#build-python)
    - [with bazel](#build-python-bazel)
    - [with cmake](#build-python-cmake)
    - [with cibuildwheels](#build-python-cibuildwheels)
    - [with pip](#build-python-pip)
- [Running tests](#test)
    - [python unit tests](#test-python)
    - [C++ unit tests with Bazel](#test-bazel)
    - [C++ unit tests with cmake](#test-cmake)
- [Running performance benchmarks](#perf)
    - [with bazel](#perf-bazel)
    - [with cmake](#perf-cmake)

<a class="anchor" id="Repository_Layout"></a>
## Repository Layout

- `src/chromobius/`: C++ code implementing Chromobius and its python package.
- `src/clorco/`: Python code for generating color code and surface code circuits used to test Chromobius.
- `src/gen/`: Generic utilities for making circuits; used by `src/clorco/`.
- `tools/`: Bash scripts for generating circuits and statistics and plots presented in the paper.

<a class="anchor" id="build-cli"></a>
## Building chromobius as a standalone command line tool

<a class="anchor" id="build-cli-bazel"></a>
### with bazel:

```bash
bazel build :chromobius
```

Or, to run the tool:

```bash
bazel run :chromobius
```

<a class="anchor" id="build-cli-cmake"></a>
### with cmake:

```bash
cmake .
make chromobius_pybind
```

Then, to run the built tool:

```bash
out/chromobius
```

<a class="anchor" id="build-cli-gcc"></a>
### with gcc:

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

<a class="anchor" id="build-cli-clang"></a>
### with clang:

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

<a class="anchor" id="build-python"></a>
## Building chromobius as a python package

<a class="anchor" id="build-python-bazel"></a>
### with bazel:

```bash
bazel build :chromobius_dev_wheel
pip install bazel-bin/chromobius-0.0.dev0-py3-none-any.whl
```

<a class="anchor" id="build-python-cmake"></a>
### with cmake:

```bash
# Requires pybind11 and python to be installed on your system.
cmake .
make chromobius_pybind
# output is in `out/` with a path that depends on your machine
# e.g. it might be `out/chromobius.cpython-311-x86_64-linux-gnu.so`
```

<a class="anchor" id="build-python-cibuildwheel"></a>
### with cibuildwheel:

```bash
pip install cibuildwheel
# See https://cibuildwheel.readthedocs.io/en/stable/options/#build-skip for CIBW_BUILD values
CIBW_BUILD=cp311-manylinux_x86_64 cibuildwheel --platform linux
# output is in `wheelhouse/` with a path that depends on platform/target
# e.g. it might be `out/chromobius-0.0.dev0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`
```

<a class="anchor" id="build-python-pip"></a>
### with pip:

```bash
# Must be run from the chromobius git repository root.
# Note this will build the package AND install it into your python environment.
pip install .
# output is in `python_build_chromobius/` under a platform dependent directory and filename
# e.g. it might be `python_build_chromobius/lib.linux-x86_64-cpython-311/chromobius.cpython-311-x86_64-linux-gnu.so`
```


<a class="anchor" id="test"></a>
## Running unit tests

<a class="anchor" id="test-python"></a>
### python unit tests

The python unit tests check that the circuit generation utilities
are working correctly, and that Chromobius can decode the generated
circuits.

Note that these tests require the chromobius python package to be installed.

```bash
pip install -r requirements.txt
pytest src
```

<a class="anchor" id="test-bazel"></a>
### C++ unit tests with bazel

```bash
bazel test :all
```

<a class="anchor" id="test-cmake"></a>
### C++ unit tests with cmake

```bash
# Requires googletest to be installed on your system.
cmake .
make chromobius_test
out/chromobius_test
```

<a class="anchor" id="perf"></a>
## Running performance benchmarks

<a class="anchor" id="perf-bazel"></a>
### with bazel

```bash
bazel run :chromobius_perf
```

<a class="anchor" id="perf-cmake"></a>
### with cmake

```bash
cmake .
make chromobius_perf
out/chromobius_perf
```
