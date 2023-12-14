# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

cmake_minimum_required(VERSION 3.13)
project(chromobius)
include_directories(src)
set(CMAKE_CXX_STANDARD 20)
if (NOT DEFINED CMAKE_RUNTIME_OUTPUT_DIRECTORY)
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY out)
endif()
if (NOT DEFINED CMAKE_LIBRARY_OUTPUT_DIRECTORY)
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY out)
endif()
if (NOT DEFINED CMAKE_ARCHIVE_OUTPUT_DIRECTORY)
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY out)
endif()
if (NOT DEFINED CMAKE_OSX_DEPLOYMENT_TARGET)
  set(CMAKE_OSX_DEPLOYMENT_TARGET 10.15)
endif()

# Make changes to file_lists trigger a reconfigure.
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS file_lists/source_files_no_main)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS file_lists/test_files)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS file_lists/perf_files)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS file_lists/pybind_files)
file(STRINGS file_lists/source_files_no_main SOURCE_FILES_NO_MAIN)
file(STRINGS file_lists/test_files TEST_FILES)
file(STRINGS file_lists/perf_files PERF_FILES)
file(STRINGS file_lists/pybind_files PYBIND_FILES)

include(FetchContent)
FetchContent_Declare(stim
        GIT_REPOSITORY https://github.com/quantumlib/stim.git
        GIT_TAG 3e38d12d0a0fb3022646b694137b733a4700d300)
FetchContent_GetProperties(stim)
if(NOT stim_POPULATED)
  FetchContent_Populate(stim)
  add_subdirectory(${stim_SOURCE_DIR})
endif()

FetchContent_Declare(pymatching
        GIT_REPOSITORY https://github.com/oscarhiggott/pymatching.git
        GIT_TAG 40dcf8c01273ff7e23a7105d5cdc410ada067001)
FetchContent_GetProperties(pymatching)
if(NOT pymatching_POPULATED)
  FetchContent_Populate(pymatching)
  add_subdirectory(${pymatching_SOURCE_DIR})
endif()

add_executable(chromobius src/main.cc ${SOURCE_FILES_NO_MAIN} ${PYMATCHING_SOURCE_FILES_NO_MAIN})
target_compile_options(chromobius PRIVATE -O3 -Wall -Wpedantic)
target_link_options(chromobius PRIVATE -O3)
target_link_libraries(chromobius libstim libpymatching)
install(TARGETS chromobius RUNTIME DESTINATION bin)

add_library(libchromobius ${SOURCE_FILES_NO_MAIN})
set_target_properties(libchromobius PROPERTIES PREFIX "")
target_include_directories(libchromobius PUBLIC src)
target_link_libraries(libchromobius PRIVATE libstim libpymatching)
if(NOT(MSVC))
    target_compile_options(libchromobius PRIVATE -O3 -Wall -Wpedantic -fPIC -fno-strict-aliasing ${MACHINE_FLAG})
    target_link_options(libchromobius PRIVATE -O3)
else()
    target_compile_options(libchromobius PRIVATE ${MACHINE_FLAG})
endif()
install(TARGETS libchromobius LIBRARY DESTINATION)
install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/src/" DESTINATION "include" FILES_MATCHING PATTERN "*.h" PATTERN "*.inl")

add_executable(chromobius_perf ${SOURCE_FILES_NO_MAIN} ${PYMATCHING_SOURCE_FILES_NO_MAIN} ${PERF_FILES})
target_compile_options(chromobius_perf PRIVATE -Wall -Wpedantic -O3 -g -fno-omit-frame-pointer -DNDEBUG)
target_link_options(chromobius_perf PRIVATE -pthread)
target_link_libraries(chromobius_perf PRIVATE libstim libpymatching)

find_package(GTest QUIET)
if(${GTest_FOUND})
    add_executable(chromobius_test ${SOURCE_FILES_NO_MAIN} ${PYMATCHING_SOURCE_FILES_NO_MAIN} ${TEST_FILES})
    target_link_libraries(chromobius_test GTest::gtest GTest::gtest_main libstim libpymatching)
    target_compile_options(chromobius_test PRIVATE -Wall -Wpedantic -g -fno-omit-frame-pointer -fno-strict-aliasing -fsanitize=undefined -fsanitize=address ${MACHINE_FLAG})
    target_link_options(chromobius_test PRIVATE -g -fno-omit-frame-pointer -fsanitize=undefined -fsanitize=address)

    add_executable(chromobius_test_o3 ${SOURCE_FILES_NO_MAIN} ${PYMATCHING_SOURCE_FILES_NO_MAIN} ${TEST_FILES})
    target_link_libraries(chromobius_test_o3 GTest::gtest GTest::gtest_main libstim libpymatching)
    target_compile_options(chromobius_test_o3 PRIVATE -O3 -Wall -Wpedantic -fno-strict-aliasing ${MACHINE_FLAG})
    target_link_options(chromobius_test_o3 PRIVATE)
else()
    message("WARNING: Skipped chromobius_test target. `GTest` not found. To fix, follow Standalone CMake Project install instructions at https://github.com/google/googletest/blob/master/googletest/README.md")
endif()

find_package(Python COMPONENTS Interpreter Development)
find_package(pybind11 CONFIG)
if ((${pybind11_FOUND} AND ${Python_FOUND}) OR "$ENV{CMAKE_FORCE_PYBIND_CHROMOBIUS}")
    pybind11_add_module(chromobius_pybind ${PYBIND_FILES} ${SOURCE_FILES_NO_MAIN})
    set_target_properties(chromobius_pybind PROPERTIES OUTPUT_NAME chromobius)
    target_compile_options(chromobius_pybind PRIVATE -O3 -DNDEBUG)
    target_link_libraries(chromobius_pybind PRIVATE libstim libpymatching)
    target_link_options(chromobius_pybind PRIVATE -O3)
else()
    message("WARNING: Skipped chromobius_pybind target. `pybind11` not found. To fix, install pybind11. On debian based distributions, the package name is `pybind11-dev`")
endif()
