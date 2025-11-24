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
if(WIN32)
    # Use a shorter path for dependencies to avoid MAX_PATH issues on Windows.
    set(FETCHCONTENT_BASE_DIR "C:/tmp/deps" CACHE PATH "Override fetchcontent dir" FORCE)
endif()

find_package(GTest QUIET)
if(NOT GTest_FOUND)
    message(STATUS "GTest not found. Will try fetching and building from source.")
    FetchContent_Declare(googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        # Note: keep the version of GTest here and in .github/workflows/ci.yml the same.
        GIT_TAG        release-1.12.1
    )
    # For Windows: prevent overriding parent project's compiler/linker settings.
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)
    if(TARGET GTest::gtest)
        message(STATUS "GTest fetch successful.")
        set(GTest_FOUND TRUE)
    else()
        message(WARNING "Failed to find GoogleTest. Some tests will not be built. To fix "
            "this, follow the Standalone CMake Project install instructions for GTest "
            "at https://github.com/google/googletest/blob/master/googletest/README.md")
    endif()
endif()

set(SIMD_WIDTH 128)
FetchContent_Declare(stim
    GIT_REPOSITORY https://github.com/quantumlib/stim.git
    GIT_TAG 1320ad7eac7de34d2e9c70daa44fbc6d84174450) # v1.15.dev0 (what PyMatching 2.2.2 uses)
FetchContent_GetProperties(stim)
if(NOT stim_POPULATED)
    FetchContent_MakeAvailable(stim)
endif()

FetchContent_Declare(pymatching
    GIT_REPOSITORY https://github.com/oscarhiggott/pymatching.git
    GIT_TAG 08f4f03fc876bd3e13351b677241fc2e160b8b38) # v2.2.2
FetchContent_GetProperties(pymatching)
if(NOT pymatching_POPULATED)
    FetchContent_MakeAvailable(pymatching)
endif()

add_executable(chromobius src/main.cc ${SOURCE_FILES_NO_MAIN})
target_compile_options(chromobius PRIVATE -O3 -Wall -Wpedantic)
target_link_options(chromobius PRIVATE -O3)
target_link_libraries(chromobius libstim libpymatching)
install(TARGETS chromobius RUNTIME DESTINATION bin)

add_library(libchromobius ${SOURCE_FILES_NO_MAIN})
set_target_properties(libchromobius PROPERTIES PREFIX "")
target_include_directories(libchromobius PUBLIC src)
target_link_libraries(libchromobius PRIVATE libstim libpymatching)
if(NOT(MSVC))
    target_compile_options(libchromobius PRIVATE -O3 -Wall -Wpedantic -fPIC -fno-strict-aliasing)
    target_link_options(libchromobius PRIVATE -O3)
else()
    target_compile_options(libchromobius PRIVATE)
endif()
install(TARGETS libchromobius LIBRARY DESTINATION)
install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/src/" DESTINATION "include" FILES_MATCHING PATTERN "*.h" PATTERN "*.inl")

add_executable(chromobius_perf ${SOURCE_FILES_NO_MAIN} ${PERF_FILES})
target_compile_options(chromobius_perf PRIVATE -Wall -Wpedantic -O3 -g -fno-omit-frame-pointer -DNDEBUG)
target_link_options(chromobius_perf PRIVATE -pthread)
target_link_libraries(chromobius_perf PRIVATE libstim libpymatching)

if(GTest_FOUND)
    add_executable(chromobius_test ${SOURCE_FILES_NO_MAIN} ${TEST_FILES})
    target_link_libraries(chromobius_test GTest::gtest GTest::gtest_main libstim libpymatching)
    target_compile_options(chromobius_test PRIVATE -Wall -Wpedantic -g -fno-omit-frame-pointer -fno-strict-aliasing
        -fsanitize=undefined -fsanitize=address)
    target_link_options(chromobius_test PRIVATE -g -fno-omit-frame-pointer -fsanitize=undefined -fsanitize=address)

    add_executable(chromobius_test_o3 ${SOURCE_FILES_NO_MAIN} ${TEST_FILES})
    target_link_libraries(chromobius_test_o3 GTest::gtest GTest::gtest_main libstim libpymatching)
    target_compile_options(chromobius_test_o3 PRIVATE -O3 -Wall -Wpedantic -fno-strict-aliasing)
    target_link_options(chromobius_test_o3 PRIVATE)
else()
    message(WARNING "Skipped target 'chromobius_test' because GoogleTest could not be found. "
        "To fix this, follow the Standalone CMake Project install instructions for GTest "
        "at https://github.com/google/googletest/blob/master/googletest/README.md")
endif()

find_package(Python COMPONENTS Interpreter Development)

# Look for the same Pybind version range as ci.yml uses.
find_package(pybind11 2.11.1...<2.12.0 QUIET CONFIG)
if(NOT pybind11_FOUND)
    message(STATUS "Pybind11 not found or the version found is not the version needed. "
        "Will try fetching and building the desired version from source.")
    FetchContent_Declare(pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11.git
        GIT_TAG        v2.11.2
    )
    FetchContent_MakeAvailable(pybind11)
    if(TARGET pybind11::pybind11)
        message(STATUS "Pybind11 fetch successful.")
        set(pybind11_FOUND TRUE)
    endif()
endif()
if ((pybind11_FOUND AND Python_FOUND) OR "$ENV{CMAKE_FORCE_PYBIND_CHROMOBIUS}")
    pybind11_add_module(chromobius_pybind ${PYBIND_FILES} ${SOURCE_FILES_NO_MAIN})
    set_target_properties(chromobius_pybind PROPERTIES OUTPUT_NAME chromobius)
    target_compile_options(chromobius_pybind PRIVATE -O3 -DNDEBUG)
    target_link_libraries(chromobius_pybind PRIVATE libstim libpymatching)
    target_link_options(chromobius_pybind PRIVATE -O3)

    set(SETUPPY_PATH "${CMAKE_CURRENT_SOURCE_DIR}/setup.py")
    file(READ ${SETUPPY_PATH} SETUPPY_TEXT)
    string(REGEX MATCH "__version__[ \t]*=[ \t]*[\"']([^\"']+)[\"']" _ ${SETUPPY_TEXT})
    if(NOT CMAKE_MATCH_1)
        message(FATAL_ERROR "Could not find __version__ string in ${SETUPPY_PATH}.")
    else()
        message(STATUS "Chromobius version is ${CMAKE_MATCH_1}")
    endif()
    set(CHROMOBIUS_VERSION_INFO "${CMAKE_MATCH_1}")
    add_compile_definitions(CHROMOBIUS_VERSION_INFO=${CHROMOBIUS_VERSION_INFO})

    message(STATUS "Added chromobius_pybind target.")
else()
    message(WARNING "Skipped target 'chromobius_pybind' because `pybind11` could not be found. "
        "To fix this, install pybind11. On Debian and Ubuntu Linux distributions, the "
        "package name is 'pybind11-dev'. For other systems, please see the pybind11 "
        "instructions at https://pybind11.readthedocs.io/.")
endif()
