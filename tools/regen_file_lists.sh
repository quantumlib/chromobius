#!/bin/bash
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

set -e

#########################################################################
# Regenerate file_lists
#########################################################################

if [ "$#" -ne 1 ]; then
    FOLDER=file_lists
else
    FOLDER=$1
fi

# Get to this script's git repo root.
cd "$( dirname "${BASH_SOURCE[0]}" )"
cd "$(git rev-parse --show-toplevel)"

# LC_ALL=C forces sorting to happen by byte value
find src | grep "\\.\\(cc\\|h\\)$" | grep -v "\\.\(test\|perf\|pybind\)\\.\\(cc\\|h\\)$" | grep -v "main\\.cc$" | LC_ALL=C sort > "${FOLDER}/source_files_no_main"
find src | grep "\\.test\\.\\(cc\\|h\\)$" | LC_ALL=C sort > "${FOLDER}/test_files"
find src | grep "\\.perf\\.\\(cc\\|h\\)$" | LC_ALL=C sort > "${FOLDER}/perf_files"
find src | grep "\\.pybind\\.\\(cc\\|h\\)$" | LC_ALL=C sort > "${FOLDER}/pybind_files"

# Regenerate 'chromobius.h' to include all relevant headers.
{
    echo "#ifndef _CHROMOBIUS_H";
    echo "#define _CHROMOBIUS_H";
    echo "/// WARNING: THE chromobius C++ API MAKES NO COMPATIBILITY GUARANTEES.";
    echo "/// It may change arbitrarily and catastrophically from minor version to minor version.";
    echo "/// If you need a stable API, use chromobius's Python API.";
    find src | grep "\\.h$" | grep -v "\\.\(test\|perf\|pybind\)\\.h$" | grep -v "src/chromobius\\.h" | LC_ALL=C sort | sed 's/src\/\(.*\)/#include "\1"/g';
    echo "#endif";
} > src/chromobius.h
