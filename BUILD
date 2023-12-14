package(default_visibility = ["//visibility:public"])

load("@rules_python//python:packaging.bzl", "py_wheel")

SOURCE_FILES_NO_MAIN = glob(
    [
        "src/**/*.cc",
        "src/**/*.h",
        "src/**/*.inl",
    ],
    exclude = glob([
        "src/**/*.test.cc",
        "src/**/*.test.h",
        "src/**/*.perf.cc",
        "src/**/*.perf.h",
        "src/**/*.pybind.cc",
        "src/**/*.pybind.h",
        "src/**/main.cc",
    ]),
)

TEST_FILES = glob(
    [
        "src/**/*.test.cc",
        "src/**/*.test.h",
    ],
)

PERF_FILES = glob(
    [
        "src/**/*.perf.cc",
        "src/**/*.perf.h",
    ],
)

PYBIND_FILES = glob(
    [
        "src/**/*.pybind.cc",
        "src/**/*.pybind.h",
    ],
)

cc_binary(
    name = "chromobius",
    srcs = SOURCE_FILES_NO_MAIN + glob(["src/**/main.cc"]),
    copts = [
        "-std=c++20",
        "-O3",
        "-DNDEBUG",
    ],
    includes = ["src/"],
    deps = [
        "@pymatching//:libpymatching",
        "@stim//:stim_lib",
    ],
)

cc_binary(
    name = "chromobius_perf",
    srcs = SOURCE_FILES_NO_MAIN + PERF_FILES,
    copts = [
        "-O3",
        "-std=c++20",
        "-DNDEBUG",
    ],
    data = glob(["test_data/**"]),
    includes = ["src/"],
    deps = [
        "@pymatching//:libpymatching",
        "@stim//:stim_lib",
    ],
)

cc_test(
    name = "chromobius_test",
    srcs = SOURCE_FILES_NO_MAIN + TEST_FILES,
    copts = [
        "-std=c++20",
    ],
    data = glob(["test_data/**"]),
    includes = ["src/"],
    deps = [
        "@gtest",
        "@gtest//:gtest_main",
        "@pymatching//:libpymatching",
        "@stim//:stim_lib",
    ],
)

cc_binary(
    name = "chromobius.so",
    srcs = SOURCE_FILES_NO_MAIN + PYBIND_FILES,
    copts = [
        "-O3",
        "-std=c++20",
        "-fvisibility=hidden",
        "-DNDEBUG",
        "-DCHROMOBIUS_VERSION_INFO=0.0.dev0",
    ],
    includes = ["src/"],
    linkshared = 1,
    deps = [
        "@pybind11",
        "@pymatching//:libpymatching",
        "@stim//:stim_lib",
    ],
)

genrule(
    name = "chromobius_wheel_files",
    srcs = ["doc/chromobius.pyi"],
    outs = ["chromobius.pyi"],
    cmd = "cp $(location doc/chromobius.pyi) $@",
)

py_wheel(
    name = "chromobius_dev_wheel",
    distribution = "chromobius",
    requires = [
        "numpy",
        "stim",
    ],
    version = "0.0.dev0",
    deps = [
        ":chromobius.so",
        ":chromobius_wheel_files",
    ],
)
