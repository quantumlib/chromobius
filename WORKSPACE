load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository")

git_repository(
    name = "stim",
    commit = "da4594c5ede00a063ec2b84bd830f846b5d097dd",
    remote = "https://github.com/quantumlib/stim.git",
)

git_repository(
    name = "pymatching",
    commit = "40dcf8c01273ff7e23a7105d5cdc410ada067001",
    remote = "https://github.com/oscarhiggott/pymatching.git",
)

http_archive(
    name = "gtest",
    sha256 = "353571c2440176ded91c2de6d6cd88ddd41401d14692ec1f99e35d013feda55a",
    strip_prefix = "googletest-release-1.11.0",
    urls = ["https://github.com/google/googletest/archive/refs/tags/release-1.11.0.zip"],
)

http_archive(
    name = "pybind11",
    build_file = "@pybind11_bazel//:pybind11.BUILD",
    sha256 = "832e2f309c57da9c1e6d4542dedd34b24e4192ecb4d62f6f4866a737454c9970",
    strip_prefix = "pybind11-2.10.4",
    urls = ["https://github.com/pybind/pybind11/archive/v2.10.4.tar.gz"],
)

http_archive(
    name = "pybind11_bazel",
    sha256 = "e8355ee56c2ff772334b4bfa22be17c709e5573f6d1d561c7176312156c27bd4",
    strip_prefix = "pybind11_bazel-2.11.1",
    urls = ["https://github.com/pybind/pybind11_bazel/releases/download/v2.11.1/pybind11_bazel-2.11.1.tar.gz"],
)

http_archive(
    name = "rules_python",
    sha256 = "0a8003b044294d7840ac7d9d73eef05d6ceb682d7516781a4ec62eeb34702578",
    strip_prefix = "rules_python-0.24.0",
    url = "https://github.com/bazelbuild/rules_python/releases/download/0.24.0/rules_python-0.24.0.tar.gz",
)

load("@rules_python//python:repositories.bzl", "py_repositories")
load("@pybind11_bazel//:python_configure.bzl", "python_configure")

py_repositories()

python_configure(name = "local_config_python")
